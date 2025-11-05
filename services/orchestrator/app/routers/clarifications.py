# services/orchestrator/app/routers/clarifications.py
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId
import time

from .applications import mongo  # reuse existing helper

router = APIRouter(prefix="/applications", tags=["clarifications"])


class Clarification(BaseModel):
    id: str = Field(alias="clarification_id")
    application_id: str
    applicant_eid: str
    question: str
    status: str
    answer: Optional[str] = None
    asked_by: Optional[str] = None
    answered_by: Optional[str] = None
    created_at: int
    answered_at: Optional[int] = None


class ClarificationListResponse(BaseModel):
    ok: bool
    clarifications: List[Clarification]


class ClarificationAnswerRequest(BaseModel):
    answer: str


class ClarificationAnswerResponse(BaseModel):
    ok: bool
    clarification: Clarification


def _strip_id(doc: dict) -> dict:
    doc = dict(doc)
    doc["clarification_id"] = str(doc.pop("_id"))
    return doc


@router.get("/{eid}/clarifications", response_model=ClarificationListResponse)
def list_clarifications_for_application(eid: str):
    """
    List all clarifications for a given applicant EID (any status).
    """
    db = mongo()
    cur = db.clarifications.find({"applicant_eid": eid})
    items = [_strip_id(d) for d in cur]
    return {"ok": True, "clarifications": items}


@router.post("/{eid}/clarifications/{clar_id}/answer", response_model=ClarificationAnswerResponse)
def answer_clarification(eid: str, clar_id: str, req: ClarificationAnswerRequest):
    """
    Store an answer for a pending clarification.
    """
    db = mongo()
    try:
        oid = ObjectId(clar_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid clarification_id")

    now = int(time.time())
    result = db.clarifications.find_one_and_update(
        {"_id": oid, "applicant_eid": eid},
        {
            "$set": {
                "answer": req.answer,
                "status": "ANSWERED",
                "answered_at": now,
                "answered_by": "applicant_or_caseworker",
            }
        },
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Clarification not found")

    return {"ok": True, "clarification": _strip_id(result)}
