import requests
from ui_lib.config import EV_BASE_URL, HTTP_TIMEOUT_S

def extract_batch(application_id: str, applicant_eid: str, documents: list[dict], form: dict | None, eid_raw: dict | None) -> list[dict]:
    payload = {"application_id": application_id, "applicant_eid": applicant_eid, "documents": documents}
    if form is not None: payload["form"] = form
    if eid_raw is not None: payload["eid_raw"] = eid_raw
    r = requests.post(f"{EV_BASE_URL}/extract/batch", json=payload, timeout=HTTP_TIMEOUT_S*2)
    r.raise_for_status()
    return r.json()

def validate(application_id: str, form: dict, extracts: list[dict]) -> dict:
    facts_by_doc = {}
    for er in extracts:
        dt = er.get("doc_type"); facts = er.get("facts", {})
        if dt and facts and dt not in facts_by_doc:
            facts_by_doc[dt] = facts
    payload = {"application_id": application_id, "form": form, "facts_by_doc": facts_by_doc}
    r = requests.post(f"{EV_BASE_URL}/validate", json=payload, timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()
