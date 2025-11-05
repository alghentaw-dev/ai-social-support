# services/orchestrator/app/routers/applications.py
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING, UpdateOne
from uuid import uuid4
import os, time
from fastapi import Body
from app.pipeline import run_multi_agent_pipeline
from schemas.models import (
    Application, Applicant, ApplicantForm, ExtractResult
)

router = APIRouter()

class DecisionPipelineResponse(BaseModel):
    extracts: List[dict]
    validation_report: dict
    reconciliation: dict
    ml_score: dict
    decision: dict

def mongo():
    uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
    dbname = os.getenv("MONGO_DB", "appdb")
    cli = MongoClient(uri)
    db = cli.get_database(dbname)

    # indexes (idempotent)
    db.applications.create_index([("applicant.emirates_id", ASCENDING)], unique=True)
    db.extracts.create_index([("applicant_eid", ASCENDING), ("doc_id", ASCENDING)], unique=True)
    return db

class DraftRequest(BaseModel):
    applicant: Applicant
    form: ApplicantForm

@router.post("/applications/draft")
def create_draft(req: DraftRequest):
    db = mongo()

    if req.applicant.emirates_id != req.form.applicant_eid:
        raise HTTPException(status_code=400, detail="applicant_eid mismatch between applicant and form")

    now = int(time.time())
    application_id = f"app-{uuid4().hex[:8]}"

    app_doc = Application(
    application_id=application_id,
    applicant=req.applicant,
    form=req.form,
    ).model_dump(mode="json", exclude_none=True)

    app_doc["status"]["created_at"] = now
    app_doc["status"]["updated_at"] = now

    # One active application per EID (simplify); upsert:
    db.applications.update_one(
        {"applicant.emirates_id": req.applicant.emirates_id},
        {"$set": app_doc},
        upsert=True
    )

    return {"ok": True, "application_id": application_id, "applicant_eid": req.applicant.emirates_id}

class AttachExtractsRequest(BaseModel):
    application_id: str
    extracts: List[ExtractResult]

class AttachExtractsRequest(BaseModel):
    application_id: str
    extracts: List[ExtractResult]

@router.post("/applications/{eid}/attach-extracts")
def attach_extracts(eid: str, req: AttachExtractsRequest):
    db = mongo()
    app_row = db.applications.find_one({"applicant.emirates_id": eid})
    if not app_row:
        raise HTTPException(status_code=404, detail="Application for EID not found")

    now = int(time.time())
    ops: list = []

    for er in req.extracts:
        if er.applicant_eid != eid:
            raise HTTPException(status_code=400, detail=f"EID mismatch in extract {er.doc_id}")
        if er.application_id != req.application_id:
            raise HTTPException(status_code=400, detail=f"application_id mismatch in extract {er.doc_id}")

        # JSON-safe dump (even if today it's just floats/bools, this is safer)
        doc = er.model_dump(mode="json", exclude_none=True) | {"updated_at": now}

        ops.append(
            UpdateOne(
                {"applicant_eid": eid, "doc_id": er.doc_id},
                {"$set": doc},
                upsert=True,
            )
        )

    if ops:
        db.extracts.bulk_write(ops)

    db.applications.update_one(
        {"applicant.emirates_id": eid},
        {"$set": {"status.updated_at": now}},
    )

    return {"ok": True, "attached": len(ops)}

from fastapi import Query
from fastapi.responses import JSONResponse

def _strip_id(doc: dict | None):
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc

@router.get("/applications")
def list_applications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("status.updated_at"),   # e.g. "status.updated_at" or "-status.updated_at"
):
    """
    Return a paginated list of applications only (no extracts).
    """
    db = mongo()
    key = sort.lstrip("-")
    direction = ASCENDING if not sort.startswith("-") else -1
    cursor = (
        db.applications
        .find({}, projection={"_id": False})   # drop Mongo _id
        .sort(key, direction)
        .skip(offset)
        .limit(limit)
    )
    items = list(cursor)
    total = db.applications.estimated_document_count()
    return {"ok": True, "total": total, "count": len(items), "items": items, "offset": offset, "limit": limit}


@router.get("/applications/{eid}/details")
def get_application_details(eid: str):
    """
    Return one application (identified by applicant EID) and all related extracts.
    """
    db = mongo()

    app_row = db.applications.find_one({"applicant.emirates_id": eid})
    if not app_row:
        raise HTTPException(status_code=404, detail="Application for EID not found")

    # fetch all extracts tied to this EID (and implicitly this application)
    extracts = list(
        db.extracts
        .find({"applicant_eid": eid}, projection={"_id": False})
        .sort([("doc_type", ASCENDING), ("doc_id", ASCENDING)])
    )

    # normalize mongo docs (remove _id if any sneaks in)
    app_doc = _strip_id(app_row)

    return JSONResponse(
        content={
            "ok": True,
            "application": app_doc,
            "extracts": extracts,
            "counts": {
                "extracts": len(extracts),
            },
        }
    )


@router.post("/applications/{eid}/run_pipeline", response_model=DecisionPipelineResponse)
def run_pipeline_for_applicant(eid: str):
    """
    Convenience endpoint that:
      - loads application + extracts from Mongo,
      - calls the multi-agent Crew pipeline,
      - returns final decision + intermediate artifacts.
    """
    db = mongo()
    app_row = db.applications.find_one({"applicant.emirates_id": eid})
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    # Re-use _strip_id helper from this module
    app_doc = _strip_id(app_row)

    extracts = [
        _strip_id(er)
        for er in db.extracts.find({"applicant_eid": eid})
    ]

    result = run_multi_agent_pipeline(
        application=app_doc,
        documents=None,         # for now we assume extraction is already done
        extracts=extracts,
    )

    return DecisionPipelineResponse(**result)