# ui_lib/workflows/apply.py
from __future__ import annotations

from typing import List, Tuple, Dict, Any
from ui_lib.clients import docs as docs_client
from ui_lib.clients import ev as ev_client
from ui_lib.clients import orchestrator as orch_client

# Optional type hint without importing Streamlit at import time
try:
    from streamlit.runtime.uploaded_file_manager import UploadedFile  # type: ignore
except Exception:  # pragma: no cover
    UploadedFile = Any  # fallback for type checking/runtime outside Streamlit

__all__ = ["upload_extract_attach"]

def upload_extract_attach(
    app_id: str,
    applicant: Dict[str, Any],
    files_with_types: List[Tuple[str, UploadedFile]],
    form: Dict[str, Any],
) -> tuple[list[dict], list[dict], dict]:
    """
    1) POST /ingest (docs service)
    2) POST /extract/batch (ev service)
    3) POST /applications/{eid}/attach-extracts (orchestrator)
    Returns: (documents, extracts, attach_resp)
    """
    # 1) ingest
    ingest_resp = docs_client.ingest(
        application_id=app_id,
        applicant_eid=applicant["emirates_id"],
        files_with_types=files_with_types,
    )
    documents: list[dict] = ingest_resp.get("documents", [])

    # 2) extract
    # Build a minimal eid_raw from known applicant fields (safe defaults)
    eid_raw = {
        "name_ar": "",
        "name_en": ((applicant.get("name") or {}).get("full_en")) or "",
        "dob": applicant.get("dob"),
        "nationality": applicant.get("nationality"),
        "gender": applicant.get("gender") or "M",
        "issue_date": "2023-01-01",
        "expiry_date": "2026-01-01",
        "residency_type": "resident",
        "occupation": "",
        "issue_emirate": applicant.get("region_emirate") or "Dubai",
        "employer": "",
        "eid_number": applicant.get("emirates_id"),
    }

    extracts: list[dict] = ev_client.extract_batch(
        application_id=app_id,
        applicant_eid=applicant["emirates_id"],
        documents=documents,
        form=form,
        eid_raw=eid_raw,
    )

    # 3) attach
    attach_resp = orch_client.attach_extracts(
        eid=applicant["emirates_id"],
        application_id=app_id,
        extracts=extracts,
    )

    return documents, extracts, attach_resp
