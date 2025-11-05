# services/extract_validate/app/services/resume.py
import os, time, json, logging
from typing import Dict, Any
from schemas.models import ResumeRaw, ResumeFacts
from schemas import load_json_schema                      
from .file_loader import fetch_object
from .text_extract import file_to_text
from .llm_rpc_client import ask_json

logger = logging.getLogger("extract_validate.resume")

SYSTEM_PROMPT = (
    "You extract structured facts from a resume/CV.\n"
    "- Output MUST be a SINGLE JSON object validating the provided JSON Schema.\n"
    "- If a field is unknown, omit it (do NOT invent values).\n"
    "- Normalize dates to ISO (yyyy-mm or yyyy-mm-dd).\n"
    "- Keep titles concise; include measurable metrics when present.\n"
    "- Respond with ONLY JSON (no prose, no code fences)."
)

def _truncate(s: str, n: int = 1000) -> str:
    if s is None:
        return ""
    return s if len(s) <= n else s[:n] + f"... [truncated {len(s)-n} chars]"

def load_resume_raw(object_key: str) -> ResumeRaw:
    data, fname = fetch_object(object_key)
    text = file_to_text(data, fname)
    return ResumeRaw(text=text)

def features_from_raw(raw: ResumeRaw) -> ResumeFacts:
    schema = load_json_schema("resume_extraction")
    model = os.getenv("RESUME_MODEL", "gpt-3.5-turbo")

    prompt = f"Resume text:\n{raw.text[:20000]}\n\nExtract exactly per the provided JSON Schema."

    logger.info(
        "LLM resume extraction: request",
        extra={
            "llm_model": model,
            "prompt_preview": _truncate(prompt, 600),
            "system_preview": _truncate(SYSTEM_PROMPT, 600),
        },
    )

    t0 = time.monotonic()
    data: Dict[str, Any] = ask_json(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model=model,
        json_schema=schema,
        temperature=0.1,
        max_tokens=1500,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "LLM resume extraction: response",
        extra={
            "llm_model": model,
            "latency_ms": latency_ms,
            "json_size": len(json.dumps(data, ensure_ascii=False)),
            "keys": list(data.keys())[:15],
        },
    )

    # derive your six canonical features from the structured JSON (fallbacks if missing)
    employment_current = bool(data.get("derived", {}).get("employment_current",
                            data.get("employment_current", False)))
    employment_tenure_months = int(data.get("derived", {}).get("employment_tenure_months",
                                data.get("employment_tenure_months", 0)))
    recent_job_gap_days = int(data.get("derived", {}).get("recent_job_gap_days",
                            data.get("recent_job_gap_days", 0)))
    occupation_code = str(data.get("derived", {}).get("occupation_code",
                        data.get("occupation_code", "NA")))
    education_level_band = str(data.get("derived", {}).get("education_level_band",
                              data.get("education_level_band", "bachelor")))
    sector_match_to_inflows = bool(data.get("derived", {}).get("sector_match_to_inflows",
                                 data.get("sector_match_to_inflows", False)))

    # pack BOTH: canonical features + full structured payload
    return ResumeFacts(
        employment_current=employment_current,
        employment_tenure_months=employment_tenure_months,
        recent_job_gap_days=recent_job_gap_days,
        occupation_code=occupation_code,
        education_level_band=education_level_band,
        sector_match_to_inflows=sector_match_to_inflows,
        structured=data,   # 👈 everything the LLM returned
    )
