from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from schemas.models import IngestResponse, DocumentRef, DocType
from ..storage.minio_store import put_file, presign_get
from ..services.mock_parsers import mock_ocr_pages

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("", response_model=IngestResponse)
async def ingest_documents(
    application_id: str = Form(...),
    applicant_eid: str = Form(...),
    files: List[UploadFile] = File(...),
    doc_types: Optional[List[DocType]] = Form(None)  # optional hints in same order
):
    if doc_types and len(doc_types) != len(files):
        raise HTTPException(400, "doc_types length must match files length when provided")

    docs: list[DocumentRef] = []
    for idx, f in enumerate(files):
        blob = await f.read()
        doc_type: DocType = (doc_types[idx] if doc_types else "bank")  # default for demo
        key, doc_id = put_file(application_id, doc_type, f.filename, blob)
        pages, conf = mock_ocr_pages()
        docs.append(DocumentRef(
            doc_id=doc_id,
            applicant_eid=applicant_eid,
            application_id=application_id,
            doc_type=doc_type,
            filename=f.filename,
            pages=pages,
            ocr_confidence=conf,
            object_key=key,
            presigned_url=presign_get(key, 3600)
        ))
    return IngestResponse(documents=docs)
