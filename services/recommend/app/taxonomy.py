
import json
from typing import Dict, Any, List

def load_taxonomy(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def role_names(tax: Dict[str, Any]) -> List[str]:
    return [r["name"] for r in tax.get("roles", [])]

def role_by_name(tax: Dict[str, Any], name: str) -> Dict[str, Any] | None:
    for r in tax.get("roles", []):
        if r.get("name", "").lower() == name.lower():
            return r
    return None
