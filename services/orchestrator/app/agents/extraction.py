from __future__ import annotations
import json
from typing import Any, Dict, List
from crewai import Crew, Process, Task
from app.agents._base import make_agent
from app.agents.tools import ExtractBatchTool


def run_extraction_agent(
    *,
    extract_tool: ExtractBatchTool,
    application_id: str,
    applicant_eid: str,
    application: Dict[str, Any],
    documents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    agent = make_agent(
        role="Extraction Agent",
        goal=(
            "Convert raw uploaded documents into strictly typed ExtractResult "
            "records using the Extraction service. Never guess facts."
        ),
        backstory=(
            "You are a careful data extraction specialist. You always call the "
            "extract_batch tool and you never fabricate document content."
        ),
        tools=[extract_tool],
        max_iter=3,
    )

    description = f"""
You are given an application and its uploaded documents.

Application (JSON):
{json.dumps(application, ensure_ascii=False)}

Documents (JSON list of DocumentRef):
{json.dumps(documents, ensure_ascii=False)}

Protocol:
1) Use the `extract_batch` tool exactly once with: application_id, applicant_eid, documents, form.
2) Return ONLY the JSON list returned by the tool as your final answer (no commentary).
"""

    task = Task(description=description, expected_output="JSON array of ExtractResult.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))
    try:
        out = json.loads(raw)
        if not isinstance(out, list):
            raise ValueError
        return out
    except Exception:
        return [{"raw_output": raw, "error": "ExtractionAgent returned non-JSON"}]
