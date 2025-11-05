from typing import Any, Dict, List


def facts_by_doc_from_extracts(extracts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Map doc_type -> facts (first instance wins)."""
    by_doc: Dict[str, Any] = {}
    for er in extracts or []:
        doc_type = er.get("doc_type")
        facts = er.get("facts") or {}
        if doc_type and facts and doc_type not in by_doc:
            by_doc[doc_type] = facts
    return by_doc

