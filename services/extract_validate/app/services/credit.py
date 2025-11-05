import io
import pandas as pd
from schemas.models import CreditRaw, CreditFacts
from .minio_client import client
from ..settings import settings

def load_credit_raw(object_key: str) -> CreditRaw:
    c = client()
    resp = c.get_object(settings.MINIO_BUCKET, object_key)
    data = resp.read()
    resp.close(); resp.release_conn()

    try:
        df = pd.read_excel(io.BytesIO(data))
    except Exception:
        df = pd.read_csv(io.BytesIO(data))

    df.columns = [c.strip().lower() for c in df.columns]

    # Optional metadata row could include score/score_band; for simplicity assume columns may exist
    score = int(df.attrs.get("score", 700)) if hasattr(df, "attrs") else None
    score_band = None

    accounts = df.to_dict(orient="records")
    # Inquiries and serious_delinquency could come as separate rows or summary columns; here keep params
    inquiries = int(df["inquiries_6m"].iloc[0]) if "inquiries_6m" in df.columns else 0
    serious = bool(df["serious_delinquency"].iloc[0]) if "serious_delinquency" in df.columns else False
    return CreditRaw(score=score, score_band=score_band, accounts=accounts, inquiries_6m=inquiries, serious_delinquency=serious)

def band_from_score(score: int | None) -> str:
    if score is None: return "B"
    if score >= 750: return "A"
    if score >= 680: return "B"
    if score >= 610: return "C"
    return "D"

def features_from_raw(raw: CreditRaw) -> CreditFacts:
    df = pd.DataFrame(raw.accounts) if raw.accounts else pd.DataFrame(columns=["credit_limit","balance","dpd_30_count","dpd_60_count","dpd_90_count","status"])
    df.columns = [c.strip().lower() for c in df.columns]

    active = df[df.get("status","active").str.lower().isin(["active","open"])] if "status" in df.columns else df
    limits = active.get("credit_limit", pd.Series(dtype=float)).fillna(0)
    balances = active.get("balance", pd.Series(dtype=float)).fillna(0)

    util = float(balances.sum()/limits.sum()*100) if limits.sum() > 0 else 0.0
    d30 = int(active.get("dpd_30_count", pd.Series(dtype=int)).fillna(0).sum())
    d60 = int(active.get("dpd_60_count", pd.Series(dtype=int)).fillna(0).sum())
    d90 = int(active.get("dpd_90_count", pd.Series(dtype=int)).fillna(0).sum())
    count = int(len(active))

    return CreditFacts(
        credit_score_band=band_from_score(raw.score),   # or raw.score_band if provided
        credit_utilization_pct=util,
        active_accounts_count=count,
        recent_hard_inquiries_6m=raw.inquiries_6m,
        dpd_30_12m=d30,
        dpd_60_12m=d60,
        dpd_90_12m=d90,
        serious_delinquency_flag=raw.serious_delinquency
    )
