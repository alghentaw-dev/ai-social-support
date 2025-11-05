# services/documents/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .routers import ingest, extract
from .storage.minio_store import ensure_bucket

app = FastAPI(title="Document Service (MinIO + Mock OCR)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    # create bucket on startup
    ensure_bucket()

# register routes
app.include_router(ingest.router)
app.include_router(extract.router)

@app.get("/healthz")
def health():
    return {"ok": True}
