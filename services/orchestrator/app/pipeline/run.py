
# ─────────────────────────────────────────────────────────────
# File: services/orchestrator/app/pipeline/run.py
# ─────────────────────────────────────────────────────────────
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple
from app.observability.langfuse import start_trace, span, end_safe
from app.agents import (
    run_extraction_agent,
    run_validation_agent,
    run_reconciliation_agent,
    run_decision_agent,
)
from app.agents.tools import (
    build_default_tools,
    ExtractBatchTool,
    ValidateTool,
    ScoreTool,
    AskUserTool,
)
from app.utils.extracts import facts_by_doc_from_extracts


def run_multi_agent_pipeline(
    *,
    application: Dict[str, Any],
    documents: Optional[List[Dict[str, Any]]] = None,
    extracts: Optional[List[Dict[str, Any]]] = None,
    validation_report: Optional[Dict[str, Any]] = None,
    score_features: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """High‑level entrypoint for orchestrator.

    Returns:
        {
          "extracts": [...],
          "validation_report": {...},
          "reconciliation": {...},
          "ml_score": {...},
          "decision": {...}
        }
    """
      # 🚀 trace per run
    trace = start_trace(
        name="decision_pipeline",
        user_id=applicant_eid,
        metadata={"application_id": app_id},
    )

    # ---- required ids
    app_id = application.get("id") or application.get("application_id")
    applicant_eid = (
        application.get("form", {}).get("applicant_eid")
        or application.get("applicant", {}).get("emirates_id")
    )
    if not app_id or not applicant_eid:
        raise ValueError("application must contain id/application_id and applicant_eid")

    # ---- attach any clarification answers (from Redis via chat_store)
    try:
        from app.services.chat_store import get_clarification_answers

        clar_answers = get_clarification_answers(applicant_eid)
    except Exception:
        clar_answers = {}
    if clar_answers:
        application = dict(application)
        application["clarification_answers"] = clar_answers

    # ---- tools
    tools = build_default_tools()
    extract_tool: ExtractBatchTool = tools["extract_batch"]  # type: ignore
    validate_tool: ValidateTool = tools["run_validation"]  # type: ignore
    score_tool: ScoreTool = tools["score_application"]  # type: ignore
    ask_user_tool: AskUserTool = tools["ask_user_for_clarification"]  # type: ignore

    # 1) Extraction (if needed)
    if extracts is None and documents:
        extracts = run_extraction_agent(
            extract_tool=extract_tool,
            application_id=app_id,
            applicant_eid=applicant_eid,
            application=application,
            documents=documents,
        )
    elif extracts is None:
        extracts = []
    s = span("extraction.result", input={"count": len(extracts or [])})
    end_safe(s)
    # 2) Validation
    if validation_report is None:
        validation_report = run_validation_agent(
            validate_tool=validate_tool,
            application_id=app_id,
            application=application,
            extracts=extracts,
        )
    s = span("validation.result", input={"issues": validation_report.get("issues", []), "next_action": validation_report.get("next_action")})
    end_safe(s)

    # 3) Reconciliation
    reconciliation = run_reconciliation_agent(
        application=application,
        extracts=extracts,
        validation_report=validation_report,
        ask_user_tool=ask_user_tool,
    )

    s = span("reconciliation.result", input=reconciliation)
    end_safe(s)

    # 4) Decision
    ml_score, decision = run_decision_agent(
        score_tool=score_tool,
        application=application,
        reconciliation=reconciliation,
        score_features=score_features,
        validation_report=validation_report,
    )
    s = span("decision.result", input={"ml_score": ml_score, "decision": decision})
    end_safe(s)

    return {
        "extracts": extracts,
        "validation_report": validation_report,
        "reconciliation": reconciliation,
        "ml_score": ml_score,
        "decision": decision,
    }

