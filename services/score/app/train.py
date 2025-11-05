# services/score/app/train.py
from __future__ import annotations
import os, json, hashlib, joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, precision_recall_curve, classification_report
from .features import build_features_from_dataframe, FeaturesMeta


def train_model(data_path: str, out_dir: str, label_col: str = "eligible"):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    y = df[label_col].astype(int)
    X_raw = df.drop(columns=[label_col])

    X, meta = build_features_from_dataframe(X_raw)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000))
    ])
    pipe.fit(X_train, y_train)

    cal = CalibratedClassifierCV(pipe, cv=5, method="sigmoid")
    cal.fit(X_train, y_train)

    y_proba = cal.predict_proba(X_test)[:, 1]
    roc_auc = roc_auc_score(y_test, y_proba)
    precision, recall, thresholds = precision_recall_curve(y_test, y_proba)
    report = classification_report(y_test, (y_proba >= 0.5).astype(int), output_dict=True)

    feature_hash = hashlib.md5(",".join(meta.feature_names).encode()).hexdigest()[:8]
    model_file = f"eligibility_model_{feature_hash}.pkl"
    model_path = os.path.join(out_dir, model_file)
    joblib.dump(cal, model_path)

    with open(os.path.join(out_dir, "feature_meta.json"), "w") as f:
        f.write(meta.model_dump_json(indent=2))

    metrics = {
        "roc_auc": float(roc_auc),
        "precision": precision.tolist(),
        "recall": recall.tolist(),
        "thresholds": thresholds.tolist(),
        "report": report,
        "model_file": model_file
    }
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(out_dir, "report.md"), "w") as f:
        f.write(f"# Model Report\nROC_AUC: {roc_auc:.3f}\n")

    return {
        "model_dir": out_dir,
        "model_file": model_file,
        "roc_auc": roc_auc,
        "n_rows": len(df),
        "n_features": len(meta.feature_names)
    }
