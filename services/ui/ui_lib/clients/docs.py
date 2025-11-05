import requests
from ui_lib.config import DOCS_BASE_URL, HTTP_TIMEOUT_S

def ingest(application_id: str, applicant_eid: str, files_with_types: list[tuple[str, "UploadedFile"]]) -> dict:
    data = [("application_id", application_id), ("applicant_eid", applicant_eid)]
    files = []
    for doc_type, uploaded in files_with_types:
        if uploaded is None: 
            continue
        content = uploaded.read()
        files.append(("files", (uploaded.name, content, uploaded.type or "application/octet-stream")))
        data.append(("doc_types", doc_type))
    if not files:
        raise ValueError("No documents selected to upload")
    r = requests.post(f"{DOCS_BASE_URL}/ingest", data=data, files=files, timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()
