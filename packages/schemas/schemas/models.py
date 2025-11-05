# packages/schemas/schemas/models.py
from pydantic import BaseModel, Field, constr
from typing import List, Optional, Literal, Dict, Any
from datetime import date

# ----- Common -----
DocType = Literal["bank","eid","resume","assets_liabilities","credit_report"]



class PersonName(BaseModel):
    first_name: str
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    last_name: Optional[str] = None
    full_ar: Optional[str] = None   # optional Arabic full name
    full_en: Optional[str] = None   # optional English full name

# --- Applicant / Dependent domain entities ---
class Dependent(BaseModel):
    emirates_id: Optional[str] = None  # may be unknown for a child; allow None
    name: PersonName
    relationship: Literal["spouse","child","parent","sibling","other"]
    dob: Optional[date] = None
    nationality: Optional[str] = None
    gender: Optional[Literal["M","F"]] = None
    is_student: Optional[bool] = None
    has_special_needs: Optional[bool] = None

class Applicant(BaseModel):
    emirates_id: str
    name: PersonName
    dob: date
    nationality: str
    gender: Optional[Literal["M","F"]] = None
    address: Optional[str] = None
    marital_status: Optional[Literal["single","married","divorced","widowed","other"]] = None
    region_emirate: Optional[str] = None

class ApplicantForm(BaseModel):
    """Your original form (kept) + link to applicant EID and dependents."""
    applicant_eid: str
    declared_monthly_income: float
    employment_status: Literal["employed","unemployed","self-employed","student","retired"]
    housing_type: Literal["own","rent","other"]
    household_size: int
    dependents: List[Dependent] = []

# --- Application envelope (draft or final) ---
class ApplicationStatus(BaseModel):
    state: Literal["draft","submitted","in_review","approved","rejected"] = "draft"
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

class Application(BaseModel):
    application_id: str                # server-generated UUID/slug
    applicant: Applicant               # normalized applicant entity
    form: ApplicantForm                # the form snapshot (includes dependents)
    status: ApplicationStatus = ApplicationStatus()

class DocumentRef(BaseModel):
    doc_id: str
    application_id: str
    applicant_eid: str         # NEW: denormalize for fast joins
    doc_type: DocType
    filename: str
    object_key: str
    pages: Optional[int] = None
    ocr_confidence: Optional[float] = None


class IngestResponse(BaseModel):
    documents: List[DocumentRef]
    


# =========================
#  EID (RAW -> FEATURES)
# =========================
class EIDRaw(BaseModel):
    name_ar: str
    name_en: str
    dob: date
    nationality: str
    gender: Literal["M","F"]
    issue_date: date
    expiry_date: date
    residency_type: Literal["citizen","resident"]
    occupation: Optional[str] = None
    issue_emirate: Optional[str] = None
    employer: Optional[str] = None
    eid_number: Optional[str] = None   # optional for mock checksum

class EIDFacts(BaseModel):
    age_years: int
    eid_valid: bool
    residency_valid_days_remaining: int
    nationality_group: Literal["UAE","GCC","MENA","ASIA","EU","AFRICA","OTHER"]
    id_name_match_score: float
    demographic_profile_band: Literal["youth","prime","senior"]

# =========================
#  BANK (RAW -> FEATURES)
# =========================
class BankTxn(BaseModel):
    date: date
    amount: float
    description: str
    category: Optional[str] = None   # optional classifier
    account_id: Optional[str] = None

class BankRaw(BaseModel):
    # Suggested CSV/XLSX columns you’ll accept:
    # date, amount, description, category?, account_id?
    txns: List[BankTxn]

class BankFacts(BaseModel):
    salary_inflow_mean_3m: float
    salary_variance_3m: float
    avg_balance_3m: float
    min_balance_3m: float
    expense_to_income_ratio_3m: float
    liquidity_buffer_days: float
    nsf_return_count_3m: int
    debt_payment_ratio_3m: float
    income_stability_index: float
    cash_withdraw_pct: float
    rent_detected: bool

# =========================
#  ASSETS/LIABILITIES (RAW -> FEATURES)
# =========================
class AssetRow(BaseModel):
    type: Literal["cash","property","vehicle","investment","other"]
    value: float

class LiabilityRow(BaseModel):
    type: Literal["loan","credit_card","mortgage","auto_loan","other"]
    limit: Optional[float] = None
    outstanding: float
    emi: Optional[float] = None

class AssetsRaw(BaseModel):
    # Suggested sheets/CSV names: assets.csv, liabilities.csv
    assets: List[AssetRow]
    liabilities: List[LiabilityRow]

class AssetsLiabilitiesFacts(BaseModel):
    total_assets_value: float
    total_liabilities_value: float
    liabilities_to_income_ratio: float
    net_worth: float
    emi_to_income_ratio: float
    credit_utilization_declared: Optional[float] = None

# =========================
#  CREDIT (RAW -> FEATURES)
# =========================
class CreditRaw(BaseModel):
    # Suggested columns for accounts sheet:
    # acct_type, credit_limit, balance, dpd_30_count, dpd_60_count, dpd_90_count, opened_date, closed_date?
    score: Optional[int] = None
    score_band: Optional[Literal["A","B","C","D"]] = None
    accounts: List[Dict[str, Any]]
    inquiries_6m: int
    serious_delinquency: bool

class CreditFacts(BaseModel):
    credit_score_band: Literal["A","B","C","D"]
    credit_utilization_pct: float
    active_accounts_count: int
    recent_hard_inquiries_6m: int
    dpd_30_12m: int
    dpd_60_12m: int
    dpd_90_12m: int
    serious_delinquency_flag: bool

# =========================
#  RESUME (RAW -> FEATURES)
# =========================
from typing import Union

class ResumeRaw(BaseModel):
    # You’ll provide plain text after OCR/PDF-to-text (Orchestrator or Docs can do OCR; here we expect text)
    text: str


# --- Optional, richer LLM-structured resume (all fields optional) ---
class _Cfg(BaseModel):
    model_config = {
        "extra": "ignore",           # ignore unknown keys from LLM
        "populate_by_name": True,
        "strict": False
    }

class ResumeAchievement(_Cfg):
    statement: Optional[str] = None
    metric: Optional[Union[str, float, int]] = None
    impact_area: Optional[str] = None

class ResumeExperienceItem(_Cfg):
    company: Optional[str] = None
    title: Optional[str] = None
    employment_type: Optional[str] = None  # full-time/part-time/contract/...
    start_date: Optional[str] = None       # ISO yyyy-mm or yyyy-mm-dd
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    team_size_managed: Optional[int] = None
    skills_used: Optional[List[str]] = None
    achievements: Optional[List[ResumeAchievement]] = None

class ResumeEducationItem(_Cfg):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ResumeLangItem(_Cfg):
    name: Optional[str] = None
    proficiency: Optional[str] = None  # basic/intermediate/advanced/native

class ResumeSkills(_Cfg):
    hard: Optional[List[str]] = None
    soft: Optional[List[str]] = None
    tools: Optional[List[str]] = None
    languages: Optional[List[ResumeLangItem]] = None

class ResumeContact(_Cfg):
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

class ResumeGap(_Cfg):
    start: Optional[str] = None
    end: Optional[str] = None
    days: Optional[int] = None

class ResumeDerived(_Cfg):
    years_experience_total: Optional[float] = None
    seniority_level: Optional[str] = None  # junior/mid/senior/staff/principal/...
    employment_current: Optional[bool] = None
    latest_tenure_months: Optional[int] = None
    largest_team_managed: Optional[int] = None
    primary_industries: Optional[List[str]] = None
    skills_top: Optional[List[str]] = None
    employment_gaps: Optional[List[ResumeGap]] = None

class ResumeExtraction(_Cfg):
    # All optional so LLM can omit anything safely
    name: Optional[str] = None
    contact: Optional[ResumeContact] = None
    summary: Optional[str] = None
    experience: Optional[List[ResumeExperienceItem]] = None
    education: Optional[List[ResumeEducationItem]] = None
    skills: Optional[ResumeSkills] = None
    certifications: Optional[List[str]] = None
    projects: Optional[List[dict]] = None
    publications: Optional[List[str]] = None
    awards: Optional[List[str]] = None
    volunteering: Optional[List[str]] = None
    availability: Optional[dict] = None
    work_preferences: Optional[dict] = None
    visa_right_to_work: Optional[dict] = None
    derived: Optional[ResumeDerived] = None


# --- Minimal MVP features from resume (now optional-friendly) ---
class ResumeFacts(BaseModel):
    employment_current: Optional[bool] = None
    employment_tenure_months: Optional[int] = None
    recent_job_gap_days: Optional[int] = None
    occupation_code: Optional[str] = None
    education_level_band: Optional[Literal["hs","bachelor","masters+"]] = None
    sector_match_to_inflows: Optional[bool] = None

    # NEW: everything the LLM extracted (names, contacts, experience, skills, etc.)
    structured: Optional[Dict[str, Any]] = None


# --- Utility to drop None when serializing (optional) ---
def nullsafe_dict(model: BaseModel) -> Dict[str, Any]:
    """Return a dict without None values (one level)."""
    return {k: v for k, v in model.model_dump().items() if v is not None}

# ----- Extraction results -----
class ExtractResult(BaseModel):
    application_id: str
    applicant_eid: str         # NEW: link by EID
    doc_id: str
    doc_type: DocType
    raw: Dict[str, Any] = {}
    facts: Dict[str, Any] = {}
    parser_version: str = "v0-mock"

# ----- Validation -----
class ValidationIssue(BaseModel):
    code: str
    key: str
    severity: Literal["low","medium","high","critical"]
    message: str
    sources: List[str]
    suggested_value: Optional[str] = None
    confidence: Optional[float] = None

class ValidationReport(BaseModel):
    application_id: str
    issues: List[ValidationIssue]
    next_action: Literal["proceed","auto_fix","ask_user","halt"] = "proceed"
    reconciled: Dict[str, Any] = {}
