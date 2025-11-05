# services/ml/features.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Tuple
import pandas as pd


# -----------------------------
# 1. Typed input & meta schema
# -----------------------------

class ApplicationRecord(BaseModel):
    """Normalized application view after extraction + aggregation."""
    eid: str

    # Form fields
    declared_monthly_income: float = 0.0
    family_size: int = 1
    employment_status: str = "Unknown"

    # Bank statement aggregates
    avg_monthly_income: float = 0.0
    avg_monthly_expenses: float = 0.0

    # Credit report
    credit_score: float = 600.0
    total_debt: float = 0.0

    # Assets & liabilities
    asset_value: float = 0.0
    liabilities_value: float = 0.0


class FeaturesMeta(BaseModel):
    version: str = "1.0.0"
    feature_names: List[str]


# -----------------------------
# 2. Core feature builder
# -----------------------------

def build_features(app: ApplicationRecord) -> Tuple[pd.DataFrame, FeaturesMeta]:
    """
    Map a single ApplicationRecord into a single-row DataFrame of numeric features.
    Deterministic, no access to labels.
    """
    employment = app.employment_status.lower()

    f = {
        "declared_monthly_income": app.declared_monthly_income,
        "family_size": app.family_size,
        "employment_is_unemployed": 1 if employment == "unemployed" else 0,
        "employment_is_self_employed": 1 if employment == "self-employed" else 0,

        "avg_monthly_income": app.avg_monthly_income,
        "avg_monthly_expenses": app.avg_monthly_expenses,
        "credit_score": app.credit_score,
        "total_debt": app.total_debt,
        "asset_value": app.asset_value,
        "liabilities_value": app.liabilities_value,

        # Derived features
        "net_worth": app.asset_value - app.liabilities_value,
        "debt_to_income_ratio": app.total_debt / max(app.avg_monthly_income, 1.0),
        "financial_stress_index": (app.liabilities_value + app.avg_monthly_expenses)
                                  / max(app.avg_monthly_income, 1.0),
        "income_per_capita": app.avg_monthly_income / max(app.family_size, 1),
    }

    df = pd.DataFrame([f])
    meta = FeaturesMeta(feature_names=list(df.columns))
    return df, meta


# -----------------------------
# 3. Helper for training: multi-row build
# -----------------------------

def build_features_from_dataframe(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, FeaturesMeta]:
    """
    Vectorized helper for training: take a df with columns matching ApplicationRecord fields
    + 'eligible' label, and return X, meta.
    """
    records = []
    for _, row in df_raw.iterrows():
        app = ApplicationRecord(
            eid=str(row.get("eid", "")),
            declared_monthly_income=float(row.get("declared_monthly_income", 0.0)),
            family_size=int(row.get("family_size", 1)),
            employment_status=str(row.get("employment_status", "Unknown")),
            avg_monthly_income=float(row.get("avg_monthly_income", 0.0)),
            avg_monthly_expenses=float(row.get("avg_monthly_expenses", 0.0)),
            credit_score=float(row.get("credit_score", 600.0)),
            total_debt=float(row.get("total_debt", 0.0)),
            asset_value=float(row.get("asset_value", 0.0)),
            liabilities_value=float(row.get("liabilities_value", 0.0)),
        )
        features_row, _ = build_features(app)
        records.append(features_row.iloc[0])

    X = pd.DataFrame(records)
    meta = FeaturesMeta(feature_names=list(X.columns))
    return X, meta
