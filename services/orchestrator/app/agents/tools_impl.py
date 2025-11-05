# services/orchestrator/app/agents/tools.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Type

import requests
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


# -------------------------------------------------------------------
# Config: backend service URLs
# (override these via env in docker-compose or orchestrator .env)
# -------------------------------------------------------------------
EV_BASE_URL = os.getenv("EV_BASE_URL", "http://extract_validate:8002")
SCORE_BASE_URL = os.getenv("SCORE_BASE_URL","http://localhost:8004")  # no default -> must configure
RECOMMEND_BASE_URL = os.getenv("RECOMMEND_SERVICE_URL", "http://recommend:8006")  # <— NEW

# -------------------------------------------------------------------
# 1) Extraction tool: calls /extract/batch
# -------------------------------------------------------------------

class ExtractBatchInput(BaseModel):
    """Inputs required to call the Extraction & Validation /extract/batch endpoint."""
    application_id: str = Field(..., description="Application ID")
    applicant_eid: str = Field(..., description="Applicant Emirates ID")
    documents: List[Dict[str, Any]] = Field(
        ...,
        description="List of DocumentRef dicts (as returned by /ingest)."
    )
    form: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional ApplicantForm JSON"
    )
    eid_raw: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional EIDRaw JSON (for mock data/testing)."
    )
    resume_raw: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional ResumeRaw JSON (pre-parsed resume text)."
    )


class ExtractBatchTool(BaseTool):
    """
    Tool to perform schema-first extraction via the extract_validate service.
    """
    name: str = "extract_batch"
    description: str = (
        "Call the Extraction service to transform raw documents into "
        "structured ExtractResult objects."
    )
    args_schema: Type[BaseModel] = ExtractBatchInput

    def _run(
        self,
        application_id: str,
        applicant_eid: str,
        documents: List[Dict[str, Any]],
        form: Optional[Dict[str, Any]] = None,
        eid_raw: Optional[Dict[str, Any]] = None,
        resume_raw: Optional[Dict[str, Any]] = None,
    ) -> str:
        url = f"{EV_BASE_URL}/extract/batch"
        payload = {
            "application_id": application_id,
            "applicant_eid": applicant_eid,
            "documents": documents,
            "form": form,
            "eid_raw": eid_raw,
            "resume_raw": resume_raw,
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        # CrewAI tools should return strings; we return JSON-encoded list[ExtractResult]
        return json.dumps(resp.json(), ensure_ascii=False)


# -------------------------------------------------------------------
# 2) Validation tool: calls /validate
# -------------------------------------------------------------------

class ValidateInput(BaseModel):
    application_id: str
    form: Dict[str, Any]
    facts_by_doc: Dict[str, Any]


class ValidateTool(BaseTool):
    """
    Tool to perform rule-based + cross-doc validation via /validate.
    """
    name: str = "run_validation"
    description: str = (
        "Call the Validation service to run policy and cross-document checks "
        "and return a ValidationReport."
    )
    args_schema: Type[BaseModel] = ValidateInput

    def _run(
        self,
        application_id: str,
        form: Dict[str, Any],
        facts_by_doc: Dict[str, Any],
    ) -> str:
        url = f"{EV_BASE_URL}/validate"
        payload = {
            "application_id": application_id,
            "form": form,
            "facts_by_doc": facts_by_doc,
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False)


# -------------------------------------------------------------------
# 3) Scoring tool: calls score service /score
# -------------------------------------------------------------------

class ScoreInput(BaseModel):
    """
    A minimal view of ApplicationRecord.
    You can refine this later to match all fields exactly.
    """
    eid: str
    declared_monthly_income: float
    family_size: int
    employment_status: str
    avg_monthly_income: float
    avg_monthly_expenses: float
    credit_score: float
    total_debt: float
    asset_value: float
    liabilities_value: float

class RecommendInput(BaseModel):
    """
    Minimal CV facts accepted by the Recommendation service.
    You can add more fields if your resume extractor produces them.
    """
    employment_current: Optional[bool] = None
    employment_tenure_months: Optional[int] = None
    recent_job_gap_days: Optional[int] = None
    occupation_code: Optional[str] = None
    education_level_band: Optional[str] = None      # "hs" | "bachelor" | "masters+"
    sector_match_to_inflows: Optional[bool] = None
    skills: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    projects: Optional[List[str]] = None

    # tool controls
    prefer_local_rules: bool = True                 # set False to let service LLM-polish text
    top_k_roles: int = 5


class ScoreTool(BaseTool):
    """
    Tool that calls the ML scoring microservice and returns:
      {
        "eid": ...,
        "probability": ...,
        "decision": "APPROVE" | "REVIEW" | "SOFT_DECLINE",
        ...
      }
    """
    name: str = "score_application"
    description: str = (
        "Call the ML scoring service to get eligibility probability and a "
        "preliminary decision based on financial features."
    )
    args_schema: Type[BaseModel] = ScoreInput

    def _run(
        self,
        eid: str,
        declared_monthly_income: float,
        family_size: int,
        employment_status: str,
        avg_monthly_income: float,
        avg_monthly_expenses: float,
        credit_score: float,
        total_debt: float,
        asset_value: float,
        liabilities_value: float,
    ) -> str:
        if not SCORE_BASE_URL:
            raise RuntimeError("SCORE_BASE_URL environment variable is not configured")

        url = f"{SCORE_BASE_URL}/score"
        payload = {
            "eid": eid,
            "declared_monthly_income": declared_monthly_income,
            "family_size": family_size,
            "employment_status": employment_status,
            "avg_monthly_income": avg_monthly_income,
            "avg_monthly_expenses": avg_monthly_expenses,
            "credit_score": credit_score,
            "total_debt": total_debt,
            "asset_value": asset_value,
            "liabilities_value": liabilities_value,
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False)

class RecommendTool(BaseTool):
    """
    Calls the Recommendation microservice to get:
      - target_roles (role + match_score + why)
      - skill_gaps (skill + severity + suggested_trainings)
      - recommended_programs (name + provider + why)
      - next_steps, confidence, explanation
    """
    name: str = "recommend_from_cv"
    description: str = (
        "Generate career/program recommendations from CV facts "
        "using the Recommendation service."
    )
    args_schema: Type[BaseModel] = RecommendInput

    def _run(
        self,
        employment_current: Optional[bool] = None,
        employment_tenure_months: Optional[int] = None,
        recent_job_gap_days: Optional[int] = None,
        occupation_code: Optional[str] = None,
        education_level_band: Optional[str] = None,
        sector_match_to_inflows: Optional[bool] = None,
        skills: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        certifications: Optional[List[str]] = None,
        projects: Optional[List[str]] = None,
        prefer_local_rules: bool = True,
        top_k_roles: int = 5,
    ) -> str:
        if not RECOMMEND_BASE_URL:
            raise RuntimeError("RECOMMEND_SERVICE_URL is not configured")

        url = f"{RECOMMEND_BASE_URL}/recommend/cv"
        payload = {
            "facts": {
                "employment_current": employment_current,
                "employment_tenure_months": employment_tenure_months,
                "recent_job_gap_days": recent_job_gap_days,
                "occupation_code": occupation_code,
                "education_level_band": education_level_band,
                "sector_match_to_inflows": sector_match_to_inflows,
                "skills": skills,
                "languages": languages,
                "certifications": certifications,
                "projects": projects,
            },
            "prefer_local_rules": prefer_local_rules,
            "top_k_roles": top_k_roles,
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False)

# -------------------------------------------------------------------
# 4) Ask-user tool (stub)
# -------------------------------------------------------------------

class AskUserInput(BaseModel):
    application_id: str
    applicant_eid: str
    question: str


from pydantic import BaseModel
from typing import Type
import json
from app.services.chat_store import append_message

class AskUserInput(BaseModel):
    application_id: str
    applicant_eid: str
    question: str


class AskUserTool(BaseTool):
    """
    Ask the applicant a clarification question by appending a message to their
    Redis chat history. The existing /chat endpoint + Streamlit UI will render
    it like any other assistant message.
    """
    name: str = "ask_user_for_clarification"
    description: str = (
        "Use this when confidence is low or documents conflict, to craft "
        "a clear question that must be answered by the applicant."
    )
    args_schema: Type[BaseModel] = AskUserInput

    def _run(self, application_id: str, applicant_eid: str, question: str) -> str:
        # Put the question into chat history as an assistant message
        chat_text = (
            "I need a quick clarification to continue processing your application:\n\n"
            f"{question}"
        )
        append_message(applicant_eid, "assistant", chat_text)

        # Return a simple JSON payload for the agent's own reasoning
        return json.dumps(
            {
                "application_id": application_id,
                "applicant_eid": applicant_eid,
                "question": question,
                "status": "QUEUED_IN_CHAT",
            },
            ensure_ascii=False,
        )


# Convenience helper to construct all tools
def build_default_tools() -> Dict[str, BaseTool]:
    return {
        "extract_batch": ExtractBatchTool(),
        "run_validation": ValidateTool(),
        "score_application": ScoreTool(),
          "recommend_from_cv": RecommendTool(),                 # <— NEW
        "ask_user_for_clarification": AskUserTool(),
    }
