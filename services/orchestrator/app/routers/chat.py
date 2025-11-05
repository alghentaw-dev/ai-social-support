from fastapi import APIRouter, HTTPException
from typing import List, Literal
from pydantic import BaseModel
from pymongo import ASCENDING
import json
import time

from app.services import chat_store
from app.services.chat_store import (
    # history
    load_history,
    save_history,
    append_message,
    reset_chat,
    # clar answers (legacy KV by question)
    record_clarification_answer,
    get_clarification_answers,
    # pending clarifications (stateful)
    peek_pending_clarification,
    pop_pending_clarification,
    mark_clarification_answered,
    append_answer_audit,
    queue_clarification_question,
    pending_clarification_count,
)
from app.services.chat_llm import generate_answer
from app.pipeline import run_multi_agent_pipeline
from .applications import mongo, _strip_id

router = APIRouter()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: int


class ChatRequest(BaseModel):
    message: str
    reset: bool = False


class ChatResponse(BaseModel):
    ok: bool
    reply: str
    history: List[ChatMessage]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_app_context(eid: str) -> dict:
    """Build the JSON context for the LLM (application + extracts)."""
    db = mongo()
    app_row = db.applications.find_one({"applicant.emirates_id": eid})
    if not app_row:
        raise HTTPException(status_code=404, detail="Application for EID not found")

    extracts = list(
        db.extracts.find({"applicant_eid": eid}, projection={"_id": False})
        .sort([("doc_type", ASCENDING), ("doc_id", ASCENDING)])
    )
    app_doc = _strip_id(app_row)
    return {
        "application_id": app_doc.get("application_id"),
        "status": app_doc.get("status", {}),
        "applicant": app_doc.get("applicant", {}),
        "form": app_doc.get("form", {}),
        "extracts": extracts,
    }


def _format_history_for_prompt(history: List[dict]) -> str:
    """Convert message history into a readable text conversation for the model."""
    lines: List[str] = []
    for msg in history:
        role = msg.get("role", "user")
        prefix = "User" if role == "user" else "Assistant"
        content = msg.get("content", "")
        lines.append(f"{prefix}: {content}")
    return "\n".join(lines)


def _run_pipeline_and_summarize(eid: str) -> str:
    """Common helper: run multi-agent pipeline and append a summary + queue clarifications."""
    db = mongo()

    app_row = db.applications.find_one({"applicant.emirates_id": eid})
    if not app_row:
        summary = "❌ Application not found."
        append_message(eid, "assistant", summary)
        return summary

    app_doc = _strip_id(app_row)
    extracts = [_strip_id(e) for e in db.extracts.find({"applicant_eid": eid})]

    # Inject clarifications (legacy KV: {question: answer})
    clar_answers = get_clarification_answers(eid)
    app_doc["clarification_answers"] = clar_answers

    result = run_multi_agent_pipeline(application=app_doc, extracts=extracts)

    summary = (
        "✅ **Pipeline completed**\n\n"
        f"- Extracted docs: {len(result.get('extracts', []))}\n"
        f"- Validation issues: {len(result.get('validation_report', {}).get('issues', []))}\n"
        f"- Decision: {result.get('decision', {}).get('final_decision')}\n\n"
        f"**Rationale:** {result.get('decision', {}).get('human_readable_rationale')}"
    )
    append_message(eid, "assistant", summary)

    # Queue any new clarification questions (stateful) and echo to chat
    rec = result.get("reconciliation", {}) or {}
    for q in rec.get("pending_questions", []):
        qtext = (q.get("question") or "").strip()
        qid = (q.get("qid") or "").strip() or str(hash((eid, qtext, time.time())))
        if qtext:
            # Queue in Redis for machine-readable state
            queue_clarification_question(eid, qtext, qid, meta={"application_id": app_doc.get("application_id")})
            # Append human-facing prompt
            append_message(
                eid,
                "assistant",
                f"❓ Clarification needed:\n\n{qtext}\n\n_Please reply here with the answer so we can continue processing._",
            )

    return summary


# ---------------------------------------------------------------------------
# Main Chat Endpoint
# ---------------------------------------------------------------------------
@router.post("/applications/{eid}/chat", response_model=ChatResponse)
def chat_with_application(eid: str, req: ChatRequest):
    message = (req.message or "").strip()

    # 1) Reset chat if requested
    if req.reset:
        save_history(eid, [])
    history = load_history(eid)

    # 2) Append user message
    append_message(eid, "user", message)
    history = load_history(eid)

    # 3) If a clarification is pending, treat this message as its answer
    pending = peek_pending_clarification(eid)
    if pending:
        qid = pending.get("qid")
        question = pending.get("question", "").strip()

        # Store answer (compat KV for pipeline), mark + audit, pop pending
        record_clarification_answer(eid, question, message)
        pop_pending_clarification(eid)
        if qid:
            mark_clarification_answered(eid, qid, int(time.time()))
        append_answer_audit(eid, qid or "", question, message)

        append_message(eid, "assistant", "✅ Thanks for clarifying — re-running the pipeline...")

        try:
            summary = _run_pipeline_and_summarize(eid)
            messages = [ChatMessage(**m) for m in load_history(eid)]
            return ChatResponse(ok=True, reply=summary, history=messages)
        except Exception as ex:
            err = f"⚠️ Pipeline failed: {ex}"
            append_message(eid, "assistant", err)
            messages = [ChatMessage(**m) for m in load_history(eid)]
            return ChatResponse(ok=False, reply=err, history=messages)

    # 4) Detect explicit pipeline trigger
    if message.lower() in {"run pipeline", "run eligibility pipeline", "analyze application"}:
        # Gentle warning if clarifications pending
        if pending_clarification_count(eid) > 0:
            append_message(
                eid,
                "assistant",
                "ℹ️ There’s a pending clarification question. I’ll run the pipeline, "
                "but the decision may remain **REVIEW** until you answer it."
            )

        append_message(eid, "assistant", "🚀 Running the eligibility pipeline, please wait...")
        try:
            summary = _run_pipeline_and_summarize(eid)
            messages = [ChatMessage(**m) for m in load_history(eid)]
            return ChatResponse(ok=True, reply="Pipeline executed successfully.", history=messages)
        except Exception as ex:
            err = f"⚠️ Pipeline failed: {ex}"
            append_message(eid, "assistant", err)
            messages = [ChatMessage(**m) for m in load_history(eid)]
            return ChatResponse(ok=False, reply=err, history=messages)

    # 5) Regular chat flow (non-pipeline message)
    context = _build_app_context(eid)
    history_text = _format_history_for_prompt(history)
    context_json = json.dumps(context, ensure_ascii=False, indent=2)

    system = (
        "You are an AI assistant helping with government social-support applications.\n"
        "You must strictly base your answers on the provided application context "
        "(form data and document extracts). If something is not in the context, "
        "say you don't know.\n"
        "Do not invent eligibility decisions; explain using the given facts only."
    )

    prompt = (
        "You are chatting with an applicant or case worker about a social support application.\n"
        "Below is the application context as JSON (form + document extracts):\n\n"
        f"{context_json}\n\n"
        "Conversation so far:\n"
        f"{history_text}\n\n"
        "Now answer the user's last message as the Assistant. Be concise and clear.\n"
    )

    try:
        raw_reply = generate_answer(
            prompt=prompt,
            system=system,
            temperature=0.2,
            max_tokens=512,
        )
        assistant_reply = (raw_reply or "").strip()
        if not assistant_reply:
            assistant_reply = (
                "I'm sorry, I couldn't generate a response right now. "
                "Please try again in a moment."
            )
        append_message(eid, "assistant", assistant_reply)
        ok = True
        reply_text = assistant_reply
    except Exception as ex:
        reply_text = f"⚠️ Chat failed: {ex}"
        append_message(eid, "assistant", reply_text)
        ok = False

    messages = [ChatMessage(**msg) for msg in load_history(eid)]
    return ChatResponse(ok=ok, reply=reply_text, history=messages)


# ---------------------------------------------------------------------------
# History + Reset Endpoints
# ---------------------------------------------------------------------------
@router.get("/applications/{eid}/chat/history")
def get_chat_history(eid: str):
    """Return full chat history for this applicant from Redis."""
    history = chat_store.load_history(eid)
    return {"history": history}


@router.delete("/applications/{eid}/chat/reset")
def reset_chat_history(eid: str):
    """Reset (delete) chat and clarification history for this applicant."""
    reset_chat(eid)
    append_message(eid, "assistant", "🧹 Chat history and clarifications have been reset.")
    return {
        "ok": True,
        "reply": "Chat history and clarifications cleared.",
        "history": [],
    }
