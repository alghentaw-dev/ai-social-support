# AI Social Support Application — Monorepo

This repository contains a **full, locally-hosted, multimodal AI workflow** that ingests applicant data & attachments, validates facts, scores eligibility, and produces a decision and enablement recommendations — all orchestrated via agents and surfaced through a Streamlit UI.

> **Goal:** Automate up to ~99% of eligibility decisions within minutes using local LLMs and a transparent, auditable pipeline.

---

## 🧩 Architecture Overview

**Core services (microservices):**

- **documents** – Ingestion to MinIO + mock OCR/parsers, typed extractors  
  _FastAPI @ `:8001`_
- **extract_validate** – Batch extraction (schema-first) + rule-based validation & cross-doc checks  
  _FastAPI @ `:8002`_
- **orchestrator** – Agentic pipeline (CrewAI/LangGraph style) coordinating extract → validate → reconcile → score → decide  
  _FastAPI @ `:8003` (default)_
- **score** – sklearn model serving (LogReg/GBM), SHAP local explainability, model training endpoints  
  _FastAPI @ `:8004`_
- **llm_runtime** – gRPC LLM gateway (Ollama/OpenAI providers) used by extraction/agents  
  _gRPC @ `:51051`_
- **recommend** – Enablement recommendations (job roles, training), rule-first with optional LLM polishing  
  _FastAPI @ `:8006`_
- **ui** – Streamlit front-end (wizard + review/chat)  
  _Streamlit @ `:8501`_

**Shared packages:**

- `packages/schemas` – Pydantic models & JSON Schemas
- `packages/llm_protos` – gRPC stubs for `llm_runtime` (`llmruntime.v1`)

**Data/infra:**

- **MinIO** – object storage for uploaded documents (`documents` service)  
- **MongoDB** – application & extracts store (orchestrator)  
- **PostgreSQL** – system-of-record (optional)  
- **Redis** – chat history & clarifications (orchestrator)  
- **Langfuse** – agent/LLM observability (optional, can be disabled for first run)

> Ports above are defaults; see each service’s `.env.example` for overrides.

### High-level flow

```
UI (Streamlit)
   └─ Orchestrator API
       ├─ documents (/ingest -> MinIO)
       ├─ extract_validate (/extract/batch, /validate)
       ├─ score (/score, /explain, /train)
       ├─ recommend (/recommend/*)
       └─ llm_runtime (gRPC) → Ollama/OpenAI
```

---

## ✅ Prerequisites

- **Docker** & **Docker Compose** (recommended: Docker Desktop or CLI 20.10+)
- Optional for local dev: **Python 3.11+** and `uv`/`pip`
- **Ollama** (if you want to run LLMs locally outside Docker) or set OpenAI credentials

---

## 🚀 Quick Start (One Command)

From the repository root:

```bash
# 1) Copy environment samples (edit later as needed)
cp services/llm_runtime/.env.example services/llm_runtime/.env || true
cp services/documents/.env.example services/documents/.env || true
cp services/extract_validate/.env.example services/extract_validate/.env || true
# (Repeat for any others you plan to customize)

# 2) Start the full stack
docker compose up -d --build

# 3) Open the UI
# Streamlit UI:
# http://localhost:8501    (or 0.0.0.0:8501 in Docker Desktop)
```

If you’re running on a server, ensure the listed ports are reachable or use a reverse proxy.

---

## 🔧 Environment Configuration

Below are the **key** variables per service. Each service ships with a `.env.example` you can copy and adjust.

### `services/documents`
- `DOCS_PORT=8001`
- `MINIO_ENDPOINT=localhost:9000`
- `MINIO_ACCESS_KEY=minioadmin`
- `MINIO_SECRET_KEY=minioadmin`
- `MINIO_SECURE=false`
- `MINIO_BUCKET=documents`
- `ALLOWED_ORIGINS=http://localhost:8501`

### `services/extract_validate`
- `PORT=8002` (if exposed via `.env`/compose)
- `MINIO_*` (if loading from MinIO directly)
- `LLM_RUNTIME_ADDR=llm_runtime:51051` (optional, if using LLM for resume parsing)

### `services/score`
- `SCORE_MODEL_DIR=/app/models/eligibility_v1` (folder must contain `metrics.json` + model)
- `SCORE_PORT=8004`

### `services/orchestrator`
- `EV_BASE_URL=http://extract_validate:8002`
- `SCORE_BASE_URL=http://score:8004` (or `http://localhost:8004` for local dev)
- `REDIS_URL=redis://redis:6379/0` (chat history)
- `MONGO_URL=mongodb://mongo:27017/eligibility`

### `services/llm_runtime`
- `LLMR_LISTEN_HOST=0.0.0.0`
- `LLMR_PORT=51051`
- `DEFAULT_PROVIDER=ollama` (or `openai`)
- `DEFAULT_MODEL=ollama:llama3` (example; remove `ollama:` if provider is openai)
- `OLLAMA_ENDPOINT=http://ollama:11434`
- `OPENAI_BASE_URL=https://api.openai.com/v1`
- `OPENAI_API_KEY=sk-...` (only if using OpenAI)

### `services/recommend`
- `RECO_PORT=8006`
- `RECO_TAXONOMY_PATH=/app/data/taxonomy.json`
- `RECO_LLM_RUNTIME_ADDR=llm_runtime:51051`
- `RECO_LLM_MODEL=` (empty disables polish → rules-only)

### Optional: Langfuse (Observability)
If you enabled the `langfuse` stack in Docker:
- Ensure `CLICKHOUSE_USER` & `CLICKHOUSE_PASSWORD` are set.
- Access UI: `http://localhost:3030` (defaults vary).

---

## 🧪 Health Checks

After `docker compose up`, verify core services:

```bash
curl -s http://localhost:8001/healthz     # documents
curl -s http://localhost:8002/healthz     # extract_validate
curl -s http://localhost:8004/healthz     # score
curl -s http://localhost:8006/healthz     # recommend
# llm_runtime is gRPC; use logs or client probe
```

---

## 🖥️ Using the UI (Happy Path)

1. **Open Streamlit**: `http://localhost:8501`
2. **Step 1 – Application Form**: fill applicant EID, income, employment, household & dependents, then **Create Draft**.
3. **Step 2 – Upload Docs**: upload EID, bank statement, assets/liabilities, credit report, resume; click **Upload, extract & attach**.
4. **Review & Chat** (Page 2): choose your application → see facts by doc, validation issues, and chat with the assistant.  
   - The chat is grounded on your application facts & extracts.  
   - Clarification questions raised by the Reconciliation Agent appear here and your answers are saved to Redis.

---

## 🛠️ API Endpoints (Selected)

> Use these from Postman or `curl` if you prefer scripting.

**documents** (`:8001`):
- `POST /ingest` – multipart upload (files) → MinIO; returns `DocumentRef[]`
- `POST /extract/bank|eid|resume|assets|credit` – mock extractors, return typed facts

**extract_validate** (`:8002`):
- `POST /extract/batch` – input: `{application_id, applicant_eid, documents, form?}` → `ExtractResult[]`
- `POST /validate` – input: `{application_id, form, facts_by_doc}` → `ValidationReport`

**score** (`:8004`):
- `POST /score` – input: `ApplicationRecord` → `{probability, decision}`
- `POST /explain` – same input → top SHAP features
- `POST /train` – upload CSV → trains & versions model (writes `/app/models/<ver>`, updates in-memory pointer)
- `GET /thresholds` – current approve/review thresholds

**recommend** (`:8006`):
- `POST /recommend/cv` – job enablement recommendations from resume facts
- `POST /recommend/match` – role matching
- `POST /recommend/skills/gap` – skill gap analysis

**orchestrator** (`:8003` typical):
- `GET /applications` – list
- `POST /applications/draft` – create
- `POST /applications/{eid}/attach-extracts` – attach results from `extract_validate`
- `GET /applications/{eid}/details` – full view (app + extracts + validation + decision traces)
- `POST /chat` – app-scoped chat; history saved in Redis

> Exact routes can evolve; inspect `services/*/app/routers/*.py` for the authoritative list.

---

## 📦 Model Artifacts (Scoring)

The `score` service expects a **model directory** containing:
- `metrics.json` → includes `"model_file"` and evaluation metrics (precision/recall/roc_auc + thresholds)
- The serialized model (e.g., `model.pkl` via `joblib`)

### Train your first model

```bash
# Example: train from CSV (columns should match ApplicationRecord fields + 'eligible' label)
curl -F "file=@/path/to/train.csv" -F "version=eligibility_v1" http://localhost:8004/train
# The service writes to /app/models/<version> and switches the active model
```

### Explain a decision

```bash
curl -X POST http://localhost:8004/explain \
  -H "Content-Type: application/json" \
  -d '{
    "eid": "784198765432101",
    "declared_monthly_income": 12000,
    "family_size": 3,
    "employment_status": "employed",
    "avg_monthly_income": 12000,
    "avg_monthly_expenses": 8000,
    "credit_score": 650,
    "total_debt": 10000,
    "asset_value": 180000,
    "liabilities_value": 90000
  }'
```

---

## 🧵 Agentic Pipeline & Traces

- **Extraction Agent** – calls `/extract/batch` _exactly once_ and returns `ExtractResult[]`
- **Validation Agent (tool)** – runs `/validate`, flags issues (e.g., income mismatch, EID expiry)
- **Reconciliation Agent** – consolidates conflicts, may **ask user** via Redis-backed chat
- **Decision Agent** – calls `/score`, then merges policy rules + validation → `APPROVE | REVIEW | SOFT_DECLINE`
- **Chat** – `/chat` endpoint renders the agent questions & user answers; history persisted in Redis

For deep debugging, inspect orchestrator logs and (optionally) Langfuse traces if enabled.

---

## 🧑‍💻 Local Dev (Run services individually)

Example — **score**:

```bash
cd services/score
uv pip install -r requirements.txt  # or: pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

Example — **documents**:

```bash
cd services/documents
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

> Start `llm_runtime` when you need LLM-backed extraction or agent reasoning:
>
> ```bash
> cd services/llm_runtime
> pip install -r requirements.txt
> python -m app.server
> ```

---

## 🔍 Troubleshooting

- **UI error: `st.session_state.mode cannot be modified...`**  
  Ensure you set `st.session_state["mode"]` **before** creating widgets bound to `mode`.

- **`Invalid format specifier ... for object of type 'str'` in Decision Agent**  
  This happens when the LLM prints the JSON contract inline within quotes.  
  _Fix_: Orchestrator wrappers already parse LLM output leniently; ensure the Decision Agent prompt ends with a **strict JSON schema** and that `ScoreTool` returns JSON (not text commentary).

- **Langfuse ClickHouse migration complains about `CLICKHOUSE_USER`**  
  Provide `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD` in the compose env; verify ClickHouse is reachable before booting Langfuse.

- **`llm_runtime` import / gRPC version mismatch**  
  Make sure `packages/llm_protos` is installed for all services and your `grpcio` version matches the generated stubs.

- **MinIO 403 / bucket not found**  
  The `documents` service creates the bucket on startup (`ensure_bucket()`), but credentials/endpoints must be correct and MinIO must be reachable from the container network.

---

## 🔐 Security & Privacy (Prototype)

- Local-only LLMs via **Ollama** by default; avoid sending PII externally.  
- Secrets in `.env`, never committed.  
- Logs redact PII where feasible; document hashes for auditability (future work).

---

## 🗺️ Roadmap (Next)

- Add **household graph** in Neo4j for relationship-aware policies
- Expand real parsers (bank/EID/credit) + production OCR
- Add fairness dashboards and drift monitoring
- Harden decision audit trail and digital signatures

---

## 📄 License & Credits

Prototype for the AI Social Support case study.  
Built with FastAPI, Streamlit, scikit‑learn, CrewAI/LangGraph concepts, SHAP, MinIO, and Ollama.
