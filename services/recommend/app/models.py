
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ResumeFacts(BaseModel):
    # Minimal, robust holder for CV facts (extend as needed)
    employment_current: Optional[bool] = None
    employment_tenure_months: Optional[int] = None
    recent_job_gap_days: Optional[int] = None
    occupation_code: Optional[str] = None
    education_level_band: Optional[str] = None      # "hs" | "bachelor" | "masters+"
    sector_match_to_inflows: Optional[bool] = None
    skills: Optional[List[str]] = None              # normalized skills from extraction
    languages: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    projects: Optional[List[str]] = None
    structured: Optional[Dict[str, Any]] = None     # full LLM extraction (optional)

class RoleSuggestion(BaseModel):
    role: str
    match_score: float = 0.0
    why: Optional[str] = None

class SkillGap(BaseModel):
    skill: str
    severity: str = Field(default="medium")  # low/medium/high
    reason: Optional[str] = None
    suggested_trainings: List[str] = []

class ProgramSuggestion(BaseModel):
    name: str
    provider: str
    duration_weeks: Optional[int] = None
    link: Optional[str] = None
    why: Optional[str] = None

class RecommendationResponse(BaseModel):
    target_roles: List[RoleSuggestion] = []
    skill_gaps: List[SkillGap] = []
    recommended_programs: List[ProgramSuggestion] = []
    next_steps: List[str] = []
    confidence: float = 0.7
    explanation: Optional[str] = None

class MatchRequest(BaseModel):
    facts: ResumeFacts
    top_k: int = 5

class GapRequest(BaseModel):
    facts: ResumeFacts
    target_role: Optional[str] = None

class RecommendRequest(BaseModel):
    facts: ResumeFacts
    prefer_local_rules: bool = True          # set False to enable LLM rewrite/polish
    top_k_roles: int = 5
