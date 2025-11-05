from __future__ import annotations
import json
from typing import Any, Dict, List
from crewai import Crew, Process, Task
from app.agents._base import make_agent
from app.agents.tools import AskUserTool


def run_reconciliation_agent(
    *,
    application: Dict[str, Any],
    extracts: List[Dict[str, Any]],
    validation_report: Dict[str, Any],
    ask_user_tool: AskUserTool,
) -> Dict[str, Any]:
    applicant_eid = (
        application.get("form", {}).get("applicant_eid")
        or application.get("applicant", {}).get("emirates_id")
    )

    agent = make_agent(
        role="Reconciliation Agent",
        goal=(
            "Resolve conflicts between declared form data and extracted facts, and decide when user clarification is needed."
        ),
        backstory=(
            "You consolidate conflicting evidence into a single canonical profile and only ask the user when confidence is low."
        ),
        tools=[ask_user_tool],
        max_iter=5,
    )

    description = f"""
Clarification answers (if any):
{json.dumps(application.get("clarification_answers", {}), ensure_ascii=False, indent=2)}

Application JSON:
{json.dumps(application, ensure_ascii=False)}

Extracted docs:
{json.dumps(extracts, ensure_ascii=False)}

ValidationReport:
{json.dumps(validation_report, ensure_ascii=False)}

Applicant EID: {applicant_eid}

Protocol:
- Identify conflicts (income/name/DOB/address, any high/critical).
- Choose a canonical value per field OR ask for clarification via tool.
- Output STRICT JSON with keys: reconciled_profile, unresolved_issues, pending_questions, confidence.
"""

    task = Task(description=description, expected_output="JSON reconciliation object.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))

    try:
        rec = json.loads(raw)
        if not isinstance(rec, dict):
            raise ValueError
        return rec
    except Exception:
        return {
            "reconciled_profile": {},
            "unresolved_issues": [
                {
                    "code": "LLM_PARSE_ERROR",
                    "key": "reconciliation_output",
                    "reason": "Reconciliation Agent returned invalid JSON.",
                    "severity": "high",
                }
            ],
            "pending_questions": [],
            "confidence": 0.0,
            "raw_output": raw,
        }

