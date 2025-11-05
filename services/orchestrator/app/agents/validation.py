from __future__ import annotations
import json
from typing import Any, Dict, List
from crewai import Crew, Process, Task
from app.agents._base import make_agent
from app.agents.tools import ValidateTool
from app.utils.extracts import facts_by_doc_from_extracts


def run_validation_agent(
    *,
    validate_tool: ValidateTool,
    application_id: str,
    application: Dict[str, Any],
    extracts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    agent = make_agent(
        role="Validation Agent",
        goal=(
            "Run rule-based and cross-document checks for an application by calling "
            "the run_validation tool, and summarize issues by severity."
        ),
        backstory=(
            "You are a compliance and risk analyst. You never skip validation and you never ignore critical issues."
        ),
        tools=[validate_tool],
        max_iter=3,
    )

    form = application.get("form") or {}
    facts_by_doc = facts_by_doc_from_extracts(extracts)

    description = f"""
Validate the application using the validation service.

Application form JSON:
{json.dumps(form, ensure_ascii=False)}

Extracted facts by document type:
{json.dumps(facts_by_doc, ensure_ascii=False)}

Protocol:
1) Call `run_validation` once with: application_id, form, facts_by_doc.
2) Use the tool result as the ground truth. Return ONLY the JSON ValidationReport.
"""

    task = Task(description=description, expected_output="A JSON ValidationReport.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))

    try:
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise ValueError
        # if clarifications exist and no critical, allow proceed
        clar = (application or {}).get("clarification_answers") or {}
        if clar:
            has_critical = any(i.get("severity") == "critical" for i in report.get("issues", []))
            if not has_critical and report.get("next_action") in {"ask_user", "halt"}:
                report["next_action"] = "proceed"
        return report
    except Exception:
        return {
            "application_id": application_id,
            "issues": [
                {
                    "code": "LLM_PARSE_ERROR",
                    "key": "validation_output",
                    "severity": "critical",
                    "message": "Validation Agent returned invalid JSON.",
                    "sources": [],
                    "suggested_value": None,
                    "confidence": 0.0,
                }
            ],
            "next_action": "halt",
            "reconciled": {},
            "raw_output": raw,
        }

