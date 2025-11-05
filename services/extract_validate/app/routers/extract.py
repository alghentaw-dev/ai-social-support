from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from schemas.models import DocumentRef, ExtractResult, ApplicantForm, EIDRaw, ResumeRaw
from ..services import eid as eid_svc
from ..services import bank as bank_svc
from ..services import assets as assets_svc
from ..services import credit as credit_svc
from ..services import resume as resume_svc

router = APIRouter(prefix="/extract", tags=["extract"])

class ExtractBatchRequest(BaseModel):
    application_id: str
    applicant_eid: str
    documents: List[DocumentRef]
    # Pass form to allow name-match / demographic band on EID
    form: Optional[ApplicantForm] = None
    # For EID mock raw input (if you want to bypass OCR)
    eid_raw: Optional[EIDRaw] = None
    # For resume, you can pass pre-extracted text
    resume_raw: Optional[ResumeRaw] = None

@router.post("/batch", response_model=List[ExtractResult])
def extract_batch(req: ExtractBatchRequest):
    results: list[ExtractResult] = []
    for d in req.documents:
        if d.doc_type == "eid":
            # prefer provided raw mock; else make a dummy
            raw = req.eid_raw or EIDRaw(
                name_ar="محمد علي", name_en="Mohammed Ali",
                dob=req.form.dob if req.form else "1992-01-01",
                nationality=req.form.nationality if req.form else "Syria",
                gender="M",
                issue_date="2023-01-01", expiry_date="2026-01-01",
                residency_type="resident",
                occupation="Engineer", issue_emirate="Dubai",
                employer="Setplex", eid_number="784198765432101"
            )
            facts = eid_svc.to_facts(raw, req.form)  # uses name match & demographic band
            results.append(ExtractResult(application_id=req.application_id, applicant_eid = req.applicant_eid, doc_id=d.doc_id, doc_type=d.doc_type,
                                         raw=raw.model_dump(), facts=facts.model_dump()))

        elif d.doc_type == "bank":
            raw = bank_svc.load_bank_raw(d.object_key)
            facts = bank_svc.features_from_raw(raw)
            results.append(ExtractResult(application_id=req.application_id,applicant_eid = req.applicant_eid, doc_id=d.doc_id, doc_type=d.doc_type,
                                         raw={}, facts=facts.model_dump()))

        elif d.doc_type == "assets_liabilities":
            raw = assets_svc.load_assets_raw(d.object_key)

            # Prefer the real form from the request (it has applicant_eid + income)
            if req.form is not None:
                form_for_assets = req.form
            else:
                # Safe minimal default so the endpoint still works in manual tests
                form_for_assets = ApplicantForm(
                    applicant_eid=d.applicant_eid,          # from DocumentRef
                    declared_monthly_income=1.0,            # avoid divide-by-zero
                    employment_status="employed",
                    housing_type="rent",
                    household_size=1,
                    dependents=[],
                )

            facts = assets_svc.features_from_raw(raw, form_for_assets)
            results.append(
                ExtractResult(
                    application_id=req.application_id,
                    applicant_eid=d.applicant_eid,
                    doc_id=d.doc_id,
                    doc_type=d.doc_type,
                    raw={},                       # we only care about facts here
                    facts=facts.model_dump(),
                )
            )


        elif d.doc_type == "credit_report":
            raw = credit_svc.load_credit_raw(d.object_key)
            facts = credit_svc.features_from_raw(raw)
            results.append(ExtractResult(application_id=req.application_id,applicant_eid = req.applicant_eid, doc_id=d.doc_id, doc_type=d.doc_type,
                                         raw={}, facts=facts.model_dump()))

        elif d.doc_type == "resume":
           raw = resume_svc.load_resume_raw(d.object_key)   # ⬅️ fetch from MinIO + extract text
           facts = resume_svc.features_from_raw(raw)        # ⬅️ LLM to JSON facts
           results.append(ExtractResult(
               application_id=req.application_id, applicant_eid = req.applicant_eid,doc_id=d.doc_id, doc_type=d.doc_type,
               raw={}, facts=facts.model_dump()
           ))
    return results
