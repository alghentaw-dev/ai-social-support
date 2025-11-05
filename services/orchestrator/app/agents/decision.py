from __future__ import annotations
import json
from typing import Any, Dict, Optional, Tuple
from crewai import Crew, Process, Task
from app.agents._base import make_agent
from app.agents.tools import ScoreTool
from app.utils.json_parse import parse_json_lenient


def _infer_features(application: Dict[str, Any], rec_profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "eid": rec_profile.get("applicant_eid") or application.get("applicant", {}).get("emirates_id", ""),
        "declared_monthly_income": float(
            rec_profile.get("declared_monthly_income")
            or application.get("form", {}).get("declared_monthly_income", 0.0)
        ),
        "family_size": int(application.get("form", {}).get("household_size", 1)),
        "employment_status": str(application.get("form", {}).get("employment_status", "Unknown")),
        "avg_monthly_income": float(rec_profile.get("observed_monthly_income") or 0.0),
        "avg_monthly_expenses": float(rec_profile.get("observed_monthly_expenses") or 0.0),
        "credit_score": float(rec_profile.get("credit_score_estimate") or 600.0),
        "total_debt": float(rec_profile.get("total_debt_estimate") or 0.0),
        "asset_value": float(rec_profile.get("asset_value_estimate") or 0.0),
        "liabilities_value": float(rec_profile.get("liabilities_value_estimate") or 0.0),
    }


def run_decision_agent(
    *,
    score_tool: ScoreTool,
    application: Dict[str, Any],
    reconciliation: Dict[str, Any],
    score_features: Optional[Dict[str, Any]],
    validation_report: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    agent = make_agent(
        role="Decisioning Agent",
        goal=(
            "Combine ML score, hard policy rules, and validation findings to make an APPROVE/REVIEW/SOFT_DECLINE recommendation."
        ),
        backstory=(
            "You are a senior policy analyst; when in doubt, send for REVIEW."
        ),
        tools=[score_tool],
        max_iter=5,
    )

    rec_profile = reconciliation.get("reconciled_profile") or {}
    features = score_features or _infer_features(application, rec_profile)
    clar_answers = application.get("clarification_answers", {})

    description = f"""
Make an eligibility decision.

Application:
{json.dumps(application, ensure_ascii=False)}

Reconciled profile:
{json.dumps(reconciliation, ensure_ascii=False)}

ValidationReport:
{json.dumps(validation_report, ensure_ascii=False)}

Score features:
{json.dumps(features, ensure_ascii=False)}

Clarification answers:
{json.dumps(clar_answers, ensure_ascii=False)}

Protocol:
1) Call `score_application` exactly once with the provided features.
2) Apply policy rules:
   - if validation.next_action == "halt" OR any critical issue => SOFT_DECLINE (reason: validation_failure)
   - if validation.next_action == "ask_user" => REVIEW until clarification
3) Merge ML decision & probability with policy rules. Provide reasons + short rationale + appeal instructions.
Return STRICT JSON with keys:
{{
  "final_decision": "APPROVE" | "REVIEW" | "SOFT_DECLINE",
  "ml_decision": "APPROVE" | "REVIEW" | "SOFT_DECLINE",
  "ml_probability": <float>,
  "policy_reasons": ["..."],
  "human_readable_rationale": "...",
  "appeal_instructions": "..."
}}
"""

    task = Task(description=description, expected_output="JSON decision object.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))
    decision = parse_json_lenient(raw)

    ml_score = {
        "decision": decision.get("ml_decision", "REVIEW"),
        "probability": decision.get("ml_probability", 0.5),
    }
    return ml_score, decision
