
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .models import RecommendRequest, RecommendationResponse, MatchRequest, GapRequest
from .taxonomy import load_taxonomy, role_by_name
from .recommender import build_recommendations, compute_role_scores, compute_gaps_for_role
from .llm_client import LLMClient

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TAX = load_taxonomy(settings.TAXONOMY_PATH)
LLM = LLMClient(settings.LLM_RUNTIME_ADDR, settings.LLM_MODEL)

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": settings.APP_NAME}

@app.post("/recommend/cv", response_model=RecommendationResponse)
def recommend_cv(req: RecommendRequest):
    rec = build_recommendations(req.facts, TAX, top_k_roles=req.top_k_roles)
    if not req.prefer_local_rules and settings.LLM_MODEL:
        # optional polish of the explanation
        rec.explanation = LLM.polish(rec.explanation or "")
    return rec

@app.post("/recommend/match")
def recommend_match(req: MatchRequest):
    suggestions = compute_role_scores(req.facts, TAX, top_k=req.top_k)
    return {"roles": [s.model_dump() for s in suggestions]}

@app.post("/recommend/skills/gap")
def recommend_skill_gap(req: GapRequest):
    role_name = req.target_role
    if not role_name and TAX.get("roles"):
        role_name = TAX["roles"][0]["name"]
    gaps = compute_gaps_for_role(req.facts, TAX, role_name) if role_name else []
    return {"target_role": role_name, "skill_gaps": [g.model_dump() for g in gaps]}
