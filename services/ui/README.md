# AI Social Support — UI Service (Streamlit)

This document explains how to run, develop, and deploy the **UI service** after refactoring the monolithic `streamlit_app.py` into a **modular, multi‑page** Streamlit app.

> TL;DR: The UI now lives under `services/ui/`, but we keep **requirements.txt**, **.env**, **Dockerfile**, and **docker-compose.yml** at the **root**. Use `docker compose up --build ui` to run.

---

## 1) What changed? (Monolith → Modules)

We split responsibilities into clear, testable modules:

```
services/ui/
├─ app.py                          # main entry (sets page config, sidebar)
├─ pages/
│  ├─ 1_Apply_Wizard.py           # Step 1&2 wizard UI (create draft, upload, extract, attach)
│  └─ 2_Review_Chat.py            # Review application + LLM chat
├─ ui_lib/
│  ├─ __init__.py
│  ├─ config.py                   # service URLs, timeouts, constants
│  ├─ clients/
│  │  ├─ orchestrator.py          # /applications*, /chat*, /clarifications*
│  │  ├─ docs.py                  # /ingest
│  │  └─ ev.py                    # /extract/batch, /validate
│  ├─ state/session.py            # st.session_state defaults & helpers
│  ├─ workflows/apply.py          # ingest → extract → attach pipeline
│  ├─ components/widgets.py       # reusable UI widgets (facts table, etc.)
│  ├─ components/chat.py          # chat renderer + quick prompts
│  └─ utils.py                    # helpers (validation/formatting)
```

**Why this helps**: easier testing, smaller files, reusable UI blocks, and cleaner HTTP clients with `raise_for_status()` and clear payloads.

---

## 2) Prerequisites

- Docker & Docker Compose **OR** Python 3.11+
- (Optional) Make sure ports **8001**, **8002**, **8003** (backends) and **8501** (UI) are free

---

## 3) Env Vars (`.env` at repo root)

These are read by the UI via `ui_lib/config.py` using `python-dotenv`:

```ini
# UI
UI_PORT=8501

# Backend service base URLs the UI calls
DOCS_BASE_URL=http://docs:8001
EV_BASE_URL=http://ev:8002
ORCH_BASE_URL=http://orch:8003

# Optional Streamlit tweaks
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

> If your backends run on localhost (not in Compose), use `http://host.docker.internal:<PORT>` on Windows/Mac. On Linux, use your host IP.

---

## 4) Dependencies (`requirements.txt` at repo root)

Minimum for the UI (add to your existing list if needed):

```
streamlit>=1.38
requests>=2.32
python-dotenv>=1.0
pydantic>=2.8
# Optional, if you render tables/transforms:
# pandas>=2.2
```

Install locally (without Docker):

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 5) Running the UI (Local Python)

From repo root:

```bash
export DOCS_BASE_URL=http://localhost:8001
export EV_BASE_URL=http://localhost:8002
export ORCH_BASE_URL=http://localhost:8003
export STREAMLIT_SERVER_PORT=${UI_PORT:-8501}

streamlit run services/ui/app.py --server.port=$STREAMLIT_SERVER_PORT
```

Open: <http://localhost:8501>

---

## 6) Running with Docker & Compose

**Dockerfile** stays at **root**, but copies `services/ui/` into the image. The `ui` stage runs Streamlit.

**docker-compose.yml** (root) includes a `ui` service that depends on your backends (`orch`, `docs`, `ev`). Example snippet:

```yaml
services:
  ui:
    build:
      context: .
      dockerfile: Dockerfile
      target: ui
    container_name: ui
    env_file:
      - .env
    environment:
      STREAMLIT_SERVER_PORT: "${UI_PORT}"
      DOCS_BASE_URL: "${DOCS_BASE_URL}"
      EV_BASE_URL: "${EV_BASE_URL}"
      ORCH_BASE_URL: "${ORCH_BASE_URL}"
      STREAMLIT_BROWSER_GATHER_USAGE_STATS: "${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}"
    ports:
      - "${UI_PORT}:${UI_PORT}"
    depends_on:
      - orch
      - docs
      - ev
    networks:
      - appnet
    volumes:
      - ./services/ui:/app/services/ui:rw,delegated
      - ./.env:/app/.env:ro
```

Run:

```bash
docker compose up --build ui
# open http://localhost:8501 (or your UI_PORT)
```

> Tip: the volume mount enables hot-reload while editing files in `services/ui/` during development.

---

## 7) How the UI talks to backends

All HTTP calls are isolated in `ui_lib/clients/`:

- **orchestrator.py**
  - `POST /applications/draft`
  - `GET  /applications`
  - `GET  /applications/{eid}/details`
  - `POST /applications/{eid}/attach-extracts`
  - `POST /applications/{eid}/chat`
  - `GET  /applications/{eid}/chat/history`
  - `DELETE /applications/{eid}/chat/reset`
  - `GET  /applications/{eid}/clarifications`
  - `POST /applications/{eid}/clarifications/{clar_id}/answer`

- **docs.py**
  - `POST /ingest` (multipart/form-data — files + doc_types)

- **ev.py**
  - `POST /extract/batch`
  - `POST /validate`

Each client uses `requests`, sets a **base URL** from env (`DOCS_BASE_URL`, `EV_BASE_URL`, `ORCH_BASE_URL`), and calls `raise_for_status()` to fail fast.

---

## 8) Main flows

### A) Apply Wizard (Page: `1_Apply_Wizard.py`)
1. **Create Draft** via orchestrator with applicant + initial form.
2. **Upload** documents to `docs` service (`/ingest`).
3. **Extract** facts via `ev` (`/extract/batch`).
4. **Attach** extracts to application via orchestrator (`/applications/{eid}/attach-extracts`).

### B) Review & Chat (Page: `2_Review_Chat.py`)
- **List** applications (`GET /applications`).
- **Get Details** of selected application (app doc + extracts).
- **Render Chat** with quick prompts; history persists via orchestrator chat endpoints.

---

## 9) Configuration (`ui_lib/config.py`)

```python
import os
from dotenv import load_dotenv
load_dotenv()

DOCS_BASE_URL = os.getenv("DOCS_BASE_URL", "http://localhost:8001")
EV_BASE_URL   = os.getenv("EV_BASE_URL",   "http://localhost:8002")
ORCH_BASE_URL = os.getenv("ORCH_BASE_URL", "http://localhost:8003")

HTTP_TIMEOUT_S = 60
```

> Adjust defaults as needed; the .env will override them in dev/compose.

---

## 10) Streamlit State & Caching

- `ui_lib/state/session.py` initializes session defaults **before** widgets render to avoid errors like:
  > `StreamlitAPIException: st.session_state.<key> cannot be modified after the widget ... is instantiated.`
- Use `@st.cache_data(ttl=30)` for list endpoints to reduce backend load.

---

## 11) Development Tips

- Keep **widgets** and **state updates** in a single place per page to avoid race conditions.
- Validate user inputs (e.g., EID format) before sending requests.
- For large responses, prefer `st.json()` inside expanders to keep pages snappy.
- Use `st.rerun()` after chat sends or resets for a crisp UX.

---

## 12) Testing

- Unit-test `ui_lib/clients/*` with `responses` or `requests-mock`.
- For workflows, mock the clients and validate sequence + payloads.
- Consider `pytest` and a minimal `Makefile` target:

```makefile
test:
	pytest -q
```

---

## 13) Troubleshooting

**Port already in use**
- Change `UI_PORT` in `.env` or free the port.

**CORS / connection refused**
- Ensure backends are reachable from the UI container: names (`docs`,`ev`,`orch`) must match Compose service names & exposed ports.

**Session state errors**
- Initialize via `ensure()` before any widgets; don’t set `st.session_state[...]` for a key after a widget with the same key has been created.

**Missing extracts in Review page**
- Confirm the flow: `/ingest` → `/extract/batch` → `/attach-extracts`. Check backends’ logs for 4xx/5xx responses.

---

## 14) Roadmap

- Role-based views (case worker vs. supervisor)
- Inline decision traceability (per-agent reasoning excerpts)
- Downloadable validation & decision reports (PDF)
- Feature flags for experimental UI components

---

## 15) License

Internal / Private. Do not distribute without permission.
