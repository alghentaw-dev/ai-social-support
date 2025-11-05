# services/score/app/explain.py
from __future__ import annotations
import os, json, joblib, shap, pandas as pd
from dataclasses import dataclass
from typing import List, Optional
from .features import build_features, ApplicationRecord


@dataclass
class FeatureContribution:
    name: str
    value: float
    shap_value: float


_explainer_cache = {}


def load_model(model_dir: str):
    with open(os.path.join(model_dir, "metrics.json")) as f:
        metrics = json.load(f)
    model_path = os.path.join(model_dir, metrics["model_file"])
    model = joblib.load(model_path)
    with open(os.path.join(model_dir, "feature_meta.json")) as f:
        meta = json.load(f)
    return model, meta["feature_names"]


def explain_single(
    app_rec: ApplicationRecord,
    model_dir: str,
    background_data: Optional[pd.DataFrame] = None,
    top_k: int = 5,
) -> List[FeatureContribution]:
    """
    Compute SHAP values for a single applicant safely.
    Works for binary/single-class models and avoids 'length-1 array' errors.
    """
    model, feature_names = load_model(model_dir)
    x, _ = build_features(app_rec)
    x = x[feature_names]

    # Define a scalar prediction function returning the prob of class 1
    def predict_fn(X):
        # X may come as numpy array, wrap to DataFrame
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=feature_names)
        proba = model.predict_proba(X)
        # handle 1- or 2-column outputs
        if proba.shape[1] == 1:
            return proba[:, 0]
        return proba[:, 1]

    cache_key = model_dir
    if cache_key not in _explainer_cache:
        bg = background_data or x.copy()
        _explainer_cache[cache_key] = shap.KernelExplainer(predict_fn, bg)
    explainer = _explainer_cache[cache_key]

    shap_vals = explainer.shap_values(x)
    # If list, pick first array
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[0]

    shap_row = shap_vals[0]
    feats = [
        FeatureContribution(name=n, value=float(v), shap_value=float(s))
        for n, v, s in zip(feature_names, x.iloc[0].values, shap_row)
    ]
    feats.sort(key=lambda f: abs(f.shap_value), reverse=True)
    return feats[:top_k]
