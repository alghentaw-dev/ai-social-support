from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import extract, validate

app = FastAPI(title="Extraction & Validation Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import logging, os, sys, json

def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

setup_logging()

app.include_router(extract.router)
app.include_router(validate.router)

@app.get("/healthz")
def health():
    return {"ok": True}
