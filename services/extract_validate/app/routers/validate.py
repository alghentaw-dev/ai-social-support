from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
import re

from schemas.models import (
    ApplicantForm,
    ValidationIssue,
    ValidationReport,
)

router = APIRouter(prefix="/validate", tags=["validate"])


# =========================
# Helpers (pure functions)
# =========================

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        return float(str(x).strip().replace(",", ""))
    except Exception:
        return default


def _pct_diff(a: float, b: float) -> float:
    """Symmetric percentage difference in [0, 1+] (0==same)."""
    a = float(a); b = float(b)
    denom = max(1.0, (abs(a) + abs(b)) / 2.0)
    return abs(a - b) / denom


def _days_until(d: Optional[str]) -> Optional[int]:
    """
    Expect ISO date "YYYY-MM-DD" (or any datetime parseable by fromisoformat).
    Returns days from today. None if not parseable / missing.
    """
    if not d:
        return None
    try:
        if "T" in d:
            dt = datetime.fromisoformat(d)
            return (dt.date() - date.today()).days
        else:
            dt = date.fromisoformat(d)
            return (dt - date.today()).days
    except Exception:
        return None


_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")  # len 15-34 typical


def _looks_like_iban(iban: Optional[str]) -> bool:
    if not iban:
        return False
    s = iban.replace(" ", "").upper()
    return bool(_IBAN_RE.match(s))


def _eid_checksum_ok(eid: Optional[str]) -> bool:
    """
    Very light EID checksum placeholder:
    - digits only, length 15 (common formatted)
    - simple Luhn-like mod10 on last digit (toy; replace with real algo if available)
    """
    if not eid:
        return False
    digits = re.sub(r"\D", "", eid)
    if len(digits) < 9:
        return False
    # Luhn-style check
    total = 0
    parity = (len(digits) - 1) % 2
    for i, ch in enumerate(digits):
        d = ord(ch) - 48
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _norm_name(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return re.sub(r"[^A-Za-z\s]", " ", s).lower().split()


def _name_tokens_match(a: Optional[str], b: Optional[str]) -> float:
    """
    Token Jaccard similarity in [0,1]. Handles order & extra middle names.
    """
    ta, tb = set(_norm_name(a)), set(_norm_name(b))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / max(1, union)


# =========================
# Request / Endpoint
# =========================

class ValidateRequest(BaseModel):
    application_id: str
    form: ApplicantForm
    # {doc_type: facts_dict} e.g. {"bank": {...}, "eid": {...}, "credit": {...}}
    facts_by_doc: Dict[str, Dict[str, Any]]


@router.post("", response_model=ValidationReport)
def validate(req: ValidateRequest) -> ValidationReport:
    """
    Rule-based validation with actionable severity + next_action:
      - INCOME_MISMATCH (uses 3m mean inflow as observed)
      - INCOME_NEGATIVE_MARGIN (expenses > income materially)
      - EID_EXPIRED / EID_EXPIRING_SOON
      - IBAN_FORMAT_INVALID
      - EID_CHECKSUM_FAIL
      - NAME_MISMATCH / DOB_MISMATCH / ADDRESS_MISMATCH
    """
    issues: List[ValidationIssue] = []

    form = req.form
    facts = req.facts_by_doc or {}

    bank = facts.get("bank", {})
    eid_doc = facts.get("eid", {})
    credit = facts.get("credit", {})  # optional, for extra signals
    profile = facts.get("profile", {})  # optional normalized profile (name/dob/address)

    # -----------------------------
    # 1) Income mismatch / anomalies
    # -----------------------------
    declared_income = _safe_float(getattr(form, "declared_monthly_income", 0.0))
    observed_income = _safe_float(bank.get("salary_inflow_mean_3m", 0.0))
    observed_expenses = _safe_float(bank.get("monthly_outflow_mean_3m", 0.0))

    if declared_income > 0 and observed_income > 0:
        diff = _pct_diff(declared_income, observed_income)  # 0..1
        if diff > 0.25:
            sev = "medium" if diff <= 0.50 else "high"
            issues.append(
                ValidationIssue(
                    code="INCOME_MISMATCH",
                    key="declared_monthly_income",
                    severity=sev,
                    message=(
                        "Declared monthly income differs from observed bank inflow "
                        f"by {int(diff*100)}%."
                    ),
                    sources=["form", "bank"],
                    suggested_value=observed_income,
                    confidence=0.8 if sev == "medium" else 0.9,
                )
            )

    # Income vs expenses (negative or tight margin)
    if observed_income > 0:
        margin = (observed_income - observed_expenses) / max(1.0, observed_income)
        if margin < -0.05:  # expenses exceed income by >5%
            issues.append(
                ValidationIssue(
                    code="INCOME_NEGATIVE_MARGIN",
                    key="observed_margin",
                    severity="high",
                    message="Observed expenses exceed observed income (negative margin).",
                    sources=["bank"],
                    suggested_value=None,
                    confidence=0.85,
                )
            )
        elif margin < 0.05:  # within ±5%
            issues.append(
                ValidationIssue(
                    code="INCOME_TIGHT_MARGIN",
                    key="observed_margin",
                    severity="low",
                    message="Observed expenses nearly equal observed income (tight margin).",
                    sources=["bank"],
                    suggested_value=None,
                    confidence=0.7,
                )
            )

    # -----------------------------
    # 2) EID expiry window
    # -----------------------------
    days_left = None
    # accept either bank/eid facts: "residency_valid_days_remaining" or "eid_expiry_date"
    if "residency_valid_days_remaining" in eid_doc:
        try:
            days_left = int(eid_doc.get("residency_valid_days_remaining"))
        except Exception:
            days_left = None
    if days_left is None:
        days_left = _days_until(eid_doc.get("eid_expiry_date"))

    if days_left is not None:
        if days_left < 0:
            issues.append(
                ValidationIssue(
                    code="EID_EXPIRED",
                    key="eid.expiry",
                    severity="critical",
                    message="Residency/EID is expired.",
                    sources=["eid"],
                    suggested_value=None,
                    confidence=0.95,
                )
            )
        elif days_left <= 60:
            severity = "medium" if days_left > 30 else "high"
            issues.append(
                ValidationIssue(
                    code="EID_EXPIRING_SOON",
                    key="eid.expiry",
                    severity=severity,
                    message=f"Residency/EID will expire in {days_left} days.",
                    sources=["eid"],
                    suggested_value=None,
                    confidence=0.9 if severity == "high" else 0.8,
                )
            )

    # -----------------------------
    # 3) IBAN & EID checksum format
    # -----------------------------
    iban_val = (form.iban or "").strip() if hasattr(form, "iban") else ""
    if iban_val and not _looks_like_iban(iban_val):
        issues.append(
            ValidationIssue(
                code="IBAN_FORMAT_INVALID",
                key="iban",
                severity="medium",
                message="IBAN does not match expected format.",
                sources=["form"],
                suggested_value=None,
                confidence=0.85,
            )
        )

    eid_number = (form.emirates_id or "") if hasattr(form, "emirates_id") else ""
    if eid_number and not _eid_checksum_ok(eid_number):
        issues.append(
            ValidationIssue(
                code="EID_CHECKSUM_FAIL",
                key="emirates_id",
                severity="high",
                message="EID checksum validation failed.",
                sources=["form"],
                suggested_value=None,
                confidence=0.9,
            )
        )

    # -----------------------------
    # 4) Cross-document consistency
    # -----------------------------
    form_name = getattr(form, "full_name", None) or getattr(form, "name", None)
    doc_name = profile.get("full_name") or eid_doc.get("full_name") or bank.get("account_holder_name")

    if form_name and doc_name:
        name_sim = _name_tokens_match(form_name, doc_name)
        if name_sim < 0.6:
            issues.append(
                ValidationIssue(
                    code="NAME_MISMATCH",
                    key="full_name",
                    severity="high" if name_sim < 0.3 else "medium",
                    message=f"Name mismatch across documents (similarity={name_sim:.2f}).",
                    sources=["form", "eid", "bank"],
                    suggested_value=doc_name,
                    confidence=0.85,
                )
            )

    form_dob = getattr(form, "dob", None)
    doc_dob = profile.get("dob") or eid_doc.get("dob")
    if form_dob and doc_dob and str(form_dob) != str(doc_dob):
        issues.append(
            ValidationIssue(
                code="DOB_MISMATCH",
                key="dob",
                severity="high",
                message="Date of birth differs across documents.",
                sources=["form", "eid"],
                suggested_value=doc_dob,
                confidence=0.9,
            )
        )

    form_address = getattr(form, "address", None)
    doc_address = profile.get("address") or bank.get("address") or eid_doc.get("address")
    if form_address and doc_address:
        # simple normalization
        f_norm = re.sub(r"\W+", " ", str(form_address)).strip().lower()
        d_norm = re.sub(r"\W+", " ", str(doc_address)).strip().lower()
        if f_norm and d_norm and f_norm != d_norm:
            issues.append(
                ValidationIssue(
                    code="ADDRESS_MISMATCH",
                    key="address",
                    severity="medium",
                    message="Address differs across documents.",
                    sources=["form", "eid", "bank"],
                    suggested_value=doc_address,
                    confidence=0.75,
                )
            )

    # -----------------------------
    # 5) Decide next_action
    # -----------------------------
    severities = {i.severity for i in issues}
    if "critical" in severities:
        next_action = "halt"
    elif "high" in severities:
        next_action = "ask_user"
    elif "medium" in severities:
        # If only medium issues remain, likely clarification is enough
        next_action = "ask_user"
    else:
        next_action = "proceed"

    # Reconciled placeholder (can be filled by Reconciliation Agent later)
    reconciled: Dict[str, Any] = {}

    return ValidationReport(
        application_id=req.application_id,
        issues=issues,
        next_action=next_action,
        reconciled=reconciled,
    )
