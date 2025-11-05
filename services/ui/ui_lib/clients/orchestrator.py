import requests
from ui_lib.config import ORCH_BASE_URL, HTTP_TIMEOUT_S

def create_draft(applicant: dict, form: dict) -> dict:
    r = requests.post(f"{ORCH_BASE_URL}/applications/draft",
                      json={"applicant": applicant, "form": form},
                      timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def list_applications(limit=50, offset=0) -> dict:
    r = requests.get(f"{ORCH_BASE_URL}/applications",
                     params={"limit": limit, "offset": offset},
                     timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def get_details(eid: str) -> dict:
    r = requests.get(f"{ORCH_BASE_URL}/applications/{eid}/details",
                     timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def attach_extracts(eid: str, application_id: str, extracts: list[dict]) -> dict:
    r = requests.post(f"{ORCH_BASE_URL}/applications/{eid}/attach-extracts",
                      json={"application_id": application_id, "extracts": extracts},
                      timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def chat(eid: str, message: str, reset: bool=False) -> dict:
    r = requests.post(f"{ORCH_BASE_URL}/applications/{eid}/chat",
                      json={"message": message, "reset": reset},
                      timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def chat_history(eid: str) -> list[tuple[str, str]]:
    r = requests.get(f"{ORCH_BASE_URL}/applications/{eid}/chat/history",
                     timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    history = r.json().get("history", [])
    return [(m.get("role", "assistant"), m.get("content", "")) for m in history]

def reset_chat(eid: str) -> None:
    requests.delete(f"{ORCH_BASE_URL}/applications/{eid}/chat/reset",
                    timeout=HTTP_TIMEOUT_S).raise_for_status()

def get_clarifications(eid: str) -> dict:
    r = requests.get(f"{ORCH_BASE_URL}/applications/{eid}/clarifications",
                     timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def answer_clarification(eid: str, clar_id: str, answer: str) -> dict:
    r = requests.post(f"{ORCH_BASE_URL}/applications/{eid}/clarifications/{clar_id}/answer",
                      json={"answer": answer}, timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    return r.json()
