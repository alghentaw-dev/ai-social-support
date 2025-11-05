import json
import re
from typing import Any, Dict


def parse_json_lenient(raw: str) -> Dict[str, Any]:
    """Try strict JSON, else pull the largest {...} block; fallback to REVIEW."""
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{(?:[^{}]|(?R))*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {
        "final_decision": "REVIEW",
        "ml_decision": "REVIEW",
        "ml_probability": 0.5,
        "policy_reasons": ["LLM_PARSE_ERROR"],
        "human_readable_rationale": (
            "The Decisioning Agent returned malformed output; sending for manual review."
        ),
        "appeal_instructions": (
            "A caseworker will review your application and may request additional documents."
        ),
        "raw_output": raw,
    }

