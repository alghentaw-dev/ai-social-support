from __future__ import annotations
import os, contextvars
from typing import Any, Dict, Optional
from langfuse import Langfuse

# cached client
_LF: Optional[Langfuse] = None
# context-local current trace id
_CURRENT_TRACE_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("lf_trace_id", default=None)

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if (v is not None and v != "") else default

def lf() -> Langfuse:
    """Get a singleton Langfuse client (env-only; no settings dependency)."""
    global _LF
    if _LF is None:
        _LF = Langfuse(
            public_key=_env("LANGFUSE_PUBLIC_KEY"),
            secret_key=_env("LANGFUSE_SECRET_KEY"),
            host=_env("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            enabled=True,
            sdk_integration="llm-runtime",
        )
    return _LF

def start_trace(name: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Any:
    t = lf().trace(name=name, user_id=user_id, metadata=(metadata or {}))
    _CURRENT_TRACE_ID.set(getattr(t, "id", None))
    return t

def get_current_trace_id() -> Optional[str]:
    return _CURRENT_TRACE_ID.get()

def span(name: str, input: Any = None, trace_id: Optional[str] = None, **meta) -> Any:
    tid = trace_id if trace_id is not None else get_current_trace_id()
    return lf().span(trace_id=tid, name=name, input=input, metadata=meta or {})

def generation(
    name: str,
    model: str,
    prompt: str,
    system: str = "",
    output: Optional[str] = None,
    trace_id: Optional[str] = None,
    **meta,
) -> Any:
    tid = trace_id if trace_id is not None else get_current_trace_id()
    return lf().generation(
        trace_id=tid,
        name=name,
        model=model or "unknown",
        input={"system": system, "prompt": prompt},
        output=output,
        metadata=meta or {},
    )

def end_safe(obj: Any):
    try:
        obj.end()
    except Exception:
        pass
