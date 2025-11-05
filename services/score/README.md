# 🧮 Eligibility Scoring Service (`score`)

### Machine-Learning microservice for automated social-support eligibility scoring, training, and explainability.

---

## 🚀 Overview

The **`score`** service is a self-contained ML microservice that predicts whether an applicant **should receive social support** based on financial and demographic indicators.  
It exposes REST endpoints to:

- Train a model from CSV data (`/train`)
- Score individual applications (`/score`)
- Explain model decisions (`/explain`)
- Expose decision thresholds (`/thresholds`)
- Report health status (`/healthz`)

All models, thresholds, and explainability artifacts are stored under `/app/models`.

---

## 🧩 Architecture

```text
services/score/
 ├── app/
 │   ├── features.py         # Feature engineering and normalization
 │   ├── train.py            # Model training + calibration
 │   ├── score_core.py       # Runtime scoring and threshold logic
 │   ├── explain.py          # SHAP explainability
 │   ├── thresholds.py       # Decision thresholds helper
 │   ├── config.py           # Environment configuration
 │   └── main.py             # FastAPI entry point
 ├── models/                 # Versioned trained models (created at runtime)
 ├── requirements.txt
 └── Dockerfile
```

The service runs inside a lightweight container and can be built independently or via the project’s `docker-compose.yml`.

---

## ⚙️ Setup

### **Local (Python)**

```bash
cd services/score
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

### **Docker**

```bash
docker compose up --build score
```

---

## 🧠 Algorithm Choice

### **Model:** Logistic Regression (Scikit-learn)

We selected **Logistic Regression** as the baseline because:

| Reason | Justification |
|---------|----------------|
| **Interpretability** | Coefficients directly map to feature importance — essential for government fairness and auditability. |
| **Speed & Simplicity** | Extremely fast to train and serve (<1 MB model). |
| **Calibration-friendly** | Works well with Platt (sigmoid) or isotonic calibration to output reliable probabilities. |
| **Explainability Compatibility** | Fully compatible with SHAP for transparent explanations. |

### **Decision Thresholding**

The raw probability (0–1) from the model is converted into three zones:

| Range | Decision | Meaning |
|--------|-----------|---------|
| ≥ `approve_threshold` | ✅ **APPROVE** | High confidence – applicant in need of support |
| between review and approve | ⚠️ **REVIEW** | Borderline case, route to human reviewer |
| < `review_threshold` | ❌ **SOFT_DECLINE** | Low need or inconsistent data |

Thresholds are auto-computed during training using the precision-recall curve to balance recall (coverage) and precision (fairness).

---

## 🧮 Explainability

### **Tool:** SHAP (SHapley Additive exPlanations)

SHAP assigns each feature a numerical **contribution (shap_value)** showing how much it pushed the model toward approval or decline:

- `+ shap_value` → pushes the prediction **toward APPROVE**
- `− shap_value` → pushes the prediction **toward DECLINE**
- Larger magnitude → greater impact on the decision

Example:

```json
{
  "eid": "784198765432101",
  "top_features": [
    {"name": "avg_monthly_expenses", "value": 3200.0, "shap_value": +0.028},
    {"name": "family_size", "value": 4.0, "shap_value": -0.017},
    {"name": "liabilities_value", "value": 12000.0, "shap_value": +0.009}
  ]
}
```

Interpretation:  
Higher expenses and liabilities increased eligibility, while smaller family size reduced it — consistent with a “need-based” support policy.

---

## 🧰 API Reference

| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/healthz` | `GET` | Health check |
| `/train` | `POST (multipart)` | Upload a CSV to train a new model |
| `/score` | `POST (JSON)` | Score a single applicant |
| `/explain` | `POST (JSON)` | Compute SHAP feature contributions |
| `/thresholds` | `GET` | Return current approve/review thresholds |

---

### **1️⃣ Train a Model**

```bash
curl -X POST http://localhost:8004/train \
  -F "file=@training_features_support_v2.csv"
```

**Response**
```json
{
  "status": "trained",
  "model": {
    "model_dir": "/app/models/eligibility_v20251104_1455",
    "model_file": "eligibility_model_a43f8d0c.pkl",
    "roc_auc": 0.91,
    "n_rows": 40,
    "n_features": 13
  }
}
```

---

### **2️⃣ Score an Application**

```bash
curl -X POST http://localhost:8004/score \
  -H "Content-Type: application/json" \
  -d '{
    "eid": "784198765432104",
    "declared_monthly_income": 2500,
    "family_size": 6,
    "employment_status": "Unemployed",
    "avg_monthly_income": 2200,
    "avg_monthly_expenses": 2800,
    "credit_score": 510,
    "total_debt": 18000,
    "asset_value": 10000,
    "liabilities_value": 12000
  }'
```

**Response**
```json
{
  "eid": "784198765432104",
  "probability": 0.83,
  "decision": "APPROVE",
  "approve_threshold": 0.75,
  "review_threshold": 0.58
}
```

---

### **3️⃣ Explain Decision**

```bash
curl -X POST http://localhost:8004/explain \
  -H "Content-Type: application/json" \
  -d '{ ... same JSON as /score ... }'
```

**Response**
```json
{
  "eid": "784198765432104",
  "top_features": [
    {"name": "avg_monthly_expenses","value":2800,"shap_value":0.041},
    {"name": "liabilities_value","value":12000,"shap_value":0.020},
    {"name": "credit_score","value":510,"shap_value":-0.018}
  ]
}
```

---

## 🧬 Training Data Schema

The `/train` CSV should have the following columns:

| Column | Type | Description |
|---------|------|-------------|
| `eid` | string | Application ID |
| `declared_monthly_income` | float | Income declared in the form |
| `family_size` | int | Number of household members |
| `employment_status` | string | Employed / Self-Employed / Unemployed |
| `avg_monthly_income` | float | Derived from bank data |
| `avg_monthly_expenses` | float | Derived from bank data |
| `credit_score` | int | Credit bureau score |
| `total_debt` | float | Total debt |
| `asset_value` | float | Assets total |
| `liabilities_value` | float | Liabilities total |
| `eligible` | int | Target label (1 = needs support, 0 = not eligible) |

---

## 🧠 Model Lifecycle

1. **Train** → Generates calibrated model and saves:
   - `eligibility_model_<hash>.pkl`
   - `feature_meta.json`
   - `metrics.json`
   - `report.md`
2. **Serve** → Model auto-loaded and cached on first `/score` call.
3. **Explain** → Uses SHAP KernelExplainer with background sampling.
4. **Version** → Each `/train` call creates a new folder under `/app/models/eligibility_v<timestamp>`.

---

## 📊 Metrics & Calibration

- **ROC-AUC** and **precision-recall** metrics are computed after training.  
- Calibration ensures probability outputs reflect real likelihoods of eligibility.  
- Thresholds are derived from the precision-recall curve to maintain policy-aligned false-positive/false-negative trade-offs.

---

## 🧱 Design Principles

- **Transparency:** Simple, explainable model architecture (LogReg + SHAP).  
- **Fairness:** Need-based labeling, calibrated probability thresholds.  
- **Modularity:** Each step (features, train, score, explain) isolated for easy upgrades.  
- **Reproducibility:** Deterministic preprocessing with Pydantic validation.  
- **Extensibility:** Can later integrate GradientBoosting or XGBoost seamlessly.

---

## 🔐 Security & Governance

- Models and CSVs stay local inside container (`/app/models`).  
- No PII leaves the system.  
- Decisions and SHAP explanations can be persisted in PostgreSQL or MongoDB for audit trails.

---

## 🧭 Example Use-Case Mapping

| Persona | Financial State | Expected Decision |
|----------|------------------|-------------------|
| Unemployed, 6 dependents, high debt | High need | ✅ Approve |
| Employed, high income, good credit | Low need | ❌ Decline |
| Moderate income, balanced debt | Borderline | ⚠️ Review |

---

## 🧩 Future Enhancements

- Add `/train/from-minio` endpoint for data pulled from object storage.  
- Add `/models` endpoint to list/download trained versions.  
- Introduce `GradientBoostingClassifier` for non-linear feature interactions.  
- Persist SHAP explanations and metrics to MongoDB or PostgreSQL.  
- Integrate fairness metrics (group parity, approval rate differences).
