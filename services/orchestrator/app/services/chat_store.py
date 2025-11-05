import json
import os
import time
from typing import List, Dict, Any, Optional

import redis

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CHAT_TTL_SECONDS = int(os.getenv("CHAT_TTL_SECONDS", str(60 * 60 * 12)))  # 12h
CHAT_MAX_MESSAGES = int(os.getenv("CHAT_MAX_MESSAGES", "40"))

# Key helpers (namespaced & explicit)
def _k_history(eid: str) -> str: return f"chat:{eid}:history"                 # JSON list
def _k_clar_kv(eid: str) -> str: return f"chat:{eid}:clar_kv"                 # HSET question -> answer (compat)
def _k_pending_q(eid: str) -> str: return f"chat:{eid}:pending_clarifications" # pending questions (list of JSON)
def _k_answered_idx(eid: str) -> str: return f"chat:{eid}:answered_idx"        # HSET qid -> ts (audit)
def _k_answered_log(eid: str) -> str: return f"chat:{eid}:answered_log"        # LPUSH JSON {qid, question, answer, ts}

# ------------------------------------------------------------------------------
# Redis client (fail-soft)
# ------------------------------------------------------------------------------
def _get_client() -> Optional[redis.Redis]:
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None

_r = _get_client()

# ------------------------------------------------------------------------------
# Chat history
# ------------------------------------------------------------------------------
def load_history(eid: str) -> List[Dict[str, Any]]:
    """
    Returns list of messages:
    { "role": "user"|"assistant", "content": str, "ts": int }
    """
    if not _r:
        return []
    raw = _r.get(_k_history(eid))
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_history(eid: str, history: List[Dict[str, Any]]) -> None:
    if not _r:
        return
    try:
        if len(history) > CHAT_MAX_MESSAGES:
            history = history[-CHAT_MAX_MESSAGES:]
        _r.set(_k_history(eid), json.dumps(history, ensure_ascii=False), ex=CHAT_TTL_SECONDS)
    except Exception:
        # fail-soft: ignore write errors
        pass

def append_message(eid: str, role: str, content: str) -> List[Dict[str, Any]]:
    # minimal schema guard
    role = "assistant" if role not in {"user", "assistant"} else role
    content = "" if content is None else str(content)

    history = load_history(eid)
    history.append({"role": role, "content": content, "ts": int(time.time())})
    save_history(eid, history)
    return history

# ------------------------------------------------------------------------------
# Clarification answers (backward compatible KV by question)
# ------------------------------------------------------------------------------
def record_clarification_answer(eid: str, question: str, answer: str) -> None:
    """Store a clarification mapping question -> answer (legacy/compat)."""
    if not _r:
        return
    key = _k_clar_kv(eid)
    try:
        _r.hset(key, question, answer)
        _r.expire(key, CHAT_TTL_SECONDS)
    except Exception:
        pass

def get_clarification_answers(eid: str) -> Dict[str, str]:
    """Retrieve all clarification answers (question -> answer)."""
    if not _r:
        return {}
    key = _k_clar_kv(eid)
    try:
        return _r.hgetall(key) or {}
    except Exception:
        return {}

# ------------------------------------------------------------------------------
# Pending clarifications (state machine hooks)
# ------------------------------------------------------------------------------
def queue_clarification_question(
    eid: str,
    question: str,
    qid: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Push a pending clarification (acts as a stack: newest first).
    Payload is JSON: {qid, question, meta}
    """
    if not _r:
        return
    payload = {"qid": qid, "question": question, "meta": meta or {}}
    try:
        _r.lpush(_k_pending_q(eid), json.dumps(payload, ensure_ascii=False))
        _r.expire(_k_pending_q(eid), CHAT_TTL_SECONDS)
    except Exception:
        pass

def peek_pending_clarification(eid: str) -> Optional[Dict[str, Any]]:
    """Return the most recent pending clarification without removing it."""
    if not _r:
        return None
    try:
        raw = _r.lindex(_k_pending_q(eid), 0)
        return json.loads(raw) if raw else None
    except Exception:
        return None

def pop_pending_clarification(eid: str) -> Optional[Dict[str, Any]]:
    """Pop and return the most recent pending clarification."""
    if not _r:
        return None
    try:
        raw = _r.lpop(_k_pending_q(eid))
        return json.loads(raw) if raw else None
    except Exception:
        return None

def pending_clarification_count(eid: str) -> int:
    if not _r:
        return 0
    try:
        return int(_r.llen(_k_pending_q(eid)))
    except Exception:
        return 0

def list_pending_clarifications(eid: str, limit: int = 20) -> List[Dict[str, Any]]:
    """For audit/UI: returns up to 'limit' pending clarifications (newest first)."""
    if not _r:
        return []
    try:
        items = _r.lrange(_k_pending_q(eid), 0, max(0, limit - 1))
        out = []
        for it in items:
            try:
                out.append(json.loads(it))
            except Exception:
                continue
        return out
    except Exception:
        return []

# ------------------------------------------------------------------------------
# Answered clarifications (lightweight audit)
# ------------------------------------------------------------------------------
def mark_clarification_answered(eid: str, qid: str, ts: int) -> None:
    """Mark qid as answered + append audit log."""
    if not _r:
        return
    try:
        _r.hset(_k_answered_idx(eid), qid, ts)
        _r.expire(_k_answered_idx(eid), CHAT_TTL_SECONDS)
    except Exception:
        pass

def append_answer_audit(eid: str, qid: str, question: str, answer: str, ts: Optional[int] = None) -> None:
    """Append a structured audit record (LPUSH)."""
    if not _r:
        return
    ts = ts or int(time.time())
    rec = {"qid": qid, "question": question, "answer": answer, "ts": ts}
    try:
        _r.lpush(_k_answered_log(eid), json.dumps(rec, ensure_ascii=False))
        _r.expire(_k_answered_log(eid), CHAT_TTL_SECONDS)
    except Exception:
        pass

def list_answered_audit(eid: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Newest-first answered clarification audit records."""
    if not _r:
        return []
    try:
        items = _r.lrange(_k_answered_log(eid), 0, max(0, limit - 1))
        out = []
        for it in items:
            try:
                out.append(json.loads(it))
            except Exception:
                continue
        return out
    except Exception:
        return []

# ------------------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------------------
def reset_chat(eid: str) -> None:
    """
    Clear chat history, pending clarifications, and clarification answers/audit.
    """
    if not _r:
        return
    try:
        _r.delete(_k_history(eid))
        _r.delete(_k_clar_kv(eid))
        _r.delete(_k_pending_q(eid))
        _r.delete(_k_answered_idx(eid))
        _r.delete(_k_answered_log(eid))
    except Exception:
        pass
