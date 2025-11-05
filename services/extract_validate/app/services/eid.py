from datetime import date
from dateutil.relativedelta import relativedelta
from rapidfuzz import fuzz
from schemas.models import EIDRaw, EIDFacts, ApplicantForm

def nationality_group(nat: str) -> str:
    n = nat.upper()
    if n in {"UAE","UNITED ARAB EMIRATES"}: return "UAE"
    if n in {"KSA","BAHRAIN","KUWAIT","OMAN","QATAR"}: return "GCC"
    if n in {"SYRIA","LEBANON","JORDAN","EGYPT","IRAQ","MOROCCO","ALGERIA","TUNISIA","PALESTINE","YEMEN","SUDAN","LIBYA"}: return "MENA"
    if n in {"INDIA","PAKISTAN","BANGLADESH","SRI LANKA","NEPAL"}: return "ASIA"
    if n in {"FRANCE","GERMANY","UK","ITALY","SPAIN","NETHERLANDS"}: return "EU"
    if n in {"NIGERIA","KENYA","ETHIOPIA","SOUTH AFRICA","GHANA"}: return "AFRICA"
    return "OTHER"

def eid_checksum_ok(eid_number: str | None) -> bool:
    if not eid_number: return True  # mock: accept None as valid
    # simple mock: digits only and length 15..18
    return eid_number.isdigit() and 15 <= len(eid_number) <= 18

def age_years(dob: date) -> int:
    today = date.today()
    return relativedelta(today, dob).years

def residency_days(expiry: date) -> int:
    today = date.today()
    return max(0, (expiry - today).days)

def name_match_score(eid_en: str, form_full: str) -> float:
    return fuzz.token_set_ratio(eid_en or "", form_full or "") / 100.0

def demo_band(age: int, household_size: int) -> str:
    if age < 25: return "youth"
    if age < 60: return "prime"
    return "senior"

def to_facts(raw: EIDRaw, form: ApplicantForm | None) -> EIDFacts:
    """
    Convert raw EID fields + optional form info into normalized EIDFacts.

    Note: ApplicantForm no longer carries `full_name`, so we:
      - Default `id_name_match_score` to 1.0 (no penalty)
      - Use form.household_size when present, otherwise 1
    """
    age = age_years(raw.dob)

    # Name match: if in future ApplicantForm gets a full_name again, we use it.
    # For now, fall back to 1.0 so we don't crash.
    if form is not None and hasattr(form, "full_name"):
        match_score = name_match_score(raw.name_en, getattr(form, "full_name"))
    else:
        match_score = 1.0

    household_size = getattr(form, "household_size", 1) if form is not None else 1

    return EIDFacts(
        age_years=age,
        eid_valid=eid_checksum_ok(raw.eid_number),
        residency_valid_days_remaining=residency_days(raw.expiry_date),
        nationality_group=nationality_group(raw.nationality),  # type: ignore
        id_name_match_score=match_score,
        demographic_profile_band=demo_band(age, household_size),
    )
