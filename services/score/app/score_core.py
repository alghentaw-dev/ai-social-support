# services/score/app/score_core.py
from __future__ import annotations
import json, os, joblib
import pandas as pd
from typing import Literal, Dict, Tuple

from .features import ApplicationRecord, build_features
from .thresholds import Metrics, pick_thresholds

_MODEL_CACHE: Dict[str, Tuple[object, object]] = {}

def load_model_bundle(model_dir: str):
    if model_dir in _MODEL_CACHE:
        return _MODEL_CACHE[model_dir]

    metrics_path = os.path.join(model_dir, "metrics.json")
    with open(metrics_path) as f:
        metrics_raw = json.load(f)

    model_file = metrics_raw["model_file"]
    model_path = os.path.join(model_dir, model_file)
    model = joblib.load(model_path)

    metrics = Metrics(
        precision=metrics_raw["precision"],
        recall=metrics_raw["recall"],
        thresholds=metrics_raw["thresholds"],
        roc_auc=metrics_raw["roc_auc"],
    )
    thr = pick_thresholds(metrics)
    _MODEL_CACHE[model_dir] = (model, thr)
    return model, thr


def score_application(app: ApplicationRecord, model_dir: str):
    model, thr = load_model_bundle(model_dir)
    X, _ = build_features(app)
    p = float(model.predict_proba(X)[0, 1])
    if p >= thr.approve:
        decision: Literal["APPROVE", "REVIEW", "SOFT_DECLINE"] = "APPROVE"
    elif p >= thr.review:
        decision = "REVIEW"
    else:
        decision = "SOFT_DECLINE"
    return {
        "eid": app.eid,
        "probability": p,
        "decision": decision,
        "approve_threshold": thr.approve,
        "review_threshold": thr.review,
    }
