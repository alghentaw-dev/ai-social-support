import json, requests
from ..settings import settings

_JSON_SCHEMA = """
Return ONLY valid JSON matching:
{
  "employment_current": boolean,
  "employment_tenure_months": integer,
  "recent_job_gap_days": integer,
  "occupation_code": string,        // e.g., '213-SoftwareEngineer' (SOC/ISCO or best-effort)
  "education_level_band": "hs" | "bachelor" | "masters+",
  "sector_match_to_inflows": boolean
}
"""

_PROMPT_TEMPLATE = """You are an expert CV parser.
Extract concise facts from this resume text and respond with STRICT JSON (no prose).

{json_schema}

Resume:
\"\"\"
{resume_text}
\"\"\""""

def _build_prompt(resume_text: str) -> str:
    return _PROMPT_TEMPLATE.format(json_schema=_JSON_SCHEMA, resume_text=resume_text[:20000])

def _call_ollama(prompt: str) -> str:
    url = f"{settings.LLM_ENDPOINT}/api/generate"
    payload = {
               "model": settings.LLM_MODEL,
               "prompt": prompt,
               "stream": False,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")

def extract_resume_fields(resume_text: str) -> dict:
    prompt = _build_prompt(resume_text)
    out = _call_ollama(prompt).strip()
    # best-effort extract JSON
    # Some models wrap JSON in markdown fences; unwrap if needed.
    if out.startswith("```"):
        out = out.strip("` \n")
        # remove possible language tag like json
        if out.lower().startswith("json"):
            out = out[4:].lstrip()
    # try parse
    try:
        return json.loads(out)
    except Exception:
        # minimal fallback
        return {
            "employment_current": True,
            "employment_tenure_months": 12,
            "recent_job_gap_days": 0,
            "occupation_code": "NA",
            "education_level_band": "bachelor",
            "sector_match_to_inflows": True
        }
