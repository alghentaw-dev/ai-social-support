from fastapi import APIRouter, Body
from pydantic import BaseModel
from schemas.models import (BankFacts, EIDFacts, ResumeFacts,
                            AssetsLiabilitiesFacts, CreditFacts, DocType)
from ..services import mock_parsers

router = APIRouter(prefix="/extract", tags=["extract"])

class ExtractRequest(BaseModel):
    application_id: str
    doc_id: str | None = None
    doc_type: DocType
    object_key: str | None = None  # location in MinIO (not used by mocks)

@router.post("/bank", response_model=BankFacts)
async def extract_bank(req: ExtractRequest = Body(...)):
    return mock_parsers.parse_bank(req.object_key or "")

@router.post("/eid", response_model=EIDFacts)
async def extract_eid(req: ExtractRequest = Body(...)):
    return mock_parsers.parse_eid(req.object_key or "")

@router.post("/resume", response_model=ResumeFacts)
async def extract_resume(req: ExtractRequest = Body(...)):
    return mock_parsers.parse_resume(req.object_key or "")

@router.post("/assets", response_model=AssetsLiabilitiesFacts)
async def extract_assets(req: ExtractRequest = Body(...)):
    return mock_parsers.parse_assets(req.object_key or "")

@router.post("/credit", response_model=CreditFacts)
async def extract_credit(req: ExtractRequest = Body(...)):
    return mock_parsers.parse_credit(req.object_key or "")
