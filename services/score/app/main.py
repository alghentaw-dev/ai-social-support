# services/score/app/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
import os, shutil, tempfile, datetime

from .config import settings
from .features import ApplicationRecord
from .score_core import score_application, load_model_bundle
from .explain import explain_single
from .train import train_model


app = FastAPI(title=settings.APP_NAME)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/score")
def score_endpoint(app_rec: ApplicationRecord):
    try:
        return score_application(app_rec, settings.MODEL_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain")
def explain_endpoint(app_rec: ApplicationRecord):
    try:
        feats = explain_single(app_rec, settings.MODEL_DIR)
        return {"eid": app_rec.eid, "top_features": [f.__dict__ for f in feats]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/thresholds")
def thresholds_endpoint():
    _, thr = load_model_bundle(settings.MODEL_DIR)
    return {"approve": thr.approve, "review": thr.review}


@app.post("/train")
def train_endpoint(
    file: UploadFile = File(...),
    version: str = Form(default=None)
):
    """Train a new model from uploaded CSV and version it."""
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        ver = version or datetime.datetime.now().strftime("eligibility_v%Y%m%d_%H%M")
        out_dir = f"/app/models/{ver}"
        os.makedirs(out_dir, exist_ok=True)

        result = train_model(tmp_path, out_dir)
        # update latest pointer (you can store symlink or config update)
        settings.MODEL_DIR = out_dir
        return {"status": "trained", "model": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
