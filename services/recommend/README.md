
# Recommendation Service (CV-based)

FastAPI microservice that produces role and training recommendations from CV facts.

## Endpoints

- `GET /healthz` — health probe
- `POST /recommend/cv` — main endpoint
- `POST /recommend/match` — return top-N role matches only
- `POST /recommend/skills/gap` — compute skill gaps for a target role

### Request/Response (POST /recommend/cv)

**Request**
```json
{
  "facts": {
    "employment_current": true,
    "employment_tenure_months": 18,
    "recent_job_gap_days": 0,
    "education_level_band": "bachelor",
    "skills": ["Python","FastAPI","Git","Docker"],
    "languages": ["English"],
    "certifications": ["PMP"]
  },
  "prefer_local_rules": true,
  "top_k_roles": 5
}
```

**Response**
```json
{
  "target_roles": [
    {"role":"Backend Engineer","match_score":0.8,"why":"..."},
    {"role":"ML Engineer","match_score":0.52,"why":"..."}
  ],
  "skill_gaps": [
    {"skill":"databases","severity":"high","reason":"Core skill not evidenced","suggested_trainings":[]}
  ],
  "recommended_programs": [
    {"name":"FastAPI Bootcamp","provider":"Udemy","duration_weeks":3,"link":null,"why":"Supports target role: Backend Engineer"}
  ],
  "next_steps": ["Refine CV ...","Tailor your CV for the top role: Backend Engineer."],
  "confidence": 0.8,
  "explanation": "Scores are computed from overlap ..."
}
```

## Run locally

```bash
cd services/recommend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8006
```

## Docker

```bash
docker build -t recommend:latest services/recommend
docker run --rm -p 8006:8006 recommend:latest
```

## Compose snippet

```yaml
recommend:
  build: ./services/recommend
  environment:
    RECO_TAXONOMY_PATH: /app/data/taxonomy.json
    RECO_LLM_RUNTIME_ADDR: llm_runtime:51051
    RECO_LLM_MODEL: ""   # set a model id to enable LLM polish
  ports:
    - "8006:8006"
  depends_on:
    - llm_runtime
```

## Orchestrator Tool (example)

```python
import httpx

async def call_recommend(base_url: str, facts: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{base_url}/recommend/cv", json={
            "facts": facts, "prefer_local_rules": True, "top_k_roles": 5
        })
        resp.raise_for_status()
        return resp.json()
```

## Notes

- Deterministic scoring based on skills overlap (core vs nice-to-have).
- Optional LLM polish via your existing gRPC LLM runtime when `RECO_LLM_MODEL` is set.
- Extend `data/taxonomy.json` with sector-specific roles and training programs.
- Add auth (e.g., shared secret) behind a reverse proxy if exposed beyond internal network.
- Add unit tests (pytest) for rules and recommender functions.
```
