import io
import pandas as pd
from schemas.models import AssetsRaw, AssetRow, LiabilityRow, AssetsLiabilitiesFacts, ApplicantForm
from .minio_client import client
from ..settings import settings

def _read_frame(data: bytes) -> pd.DataFrame:
    try:
        return pd.read_excel(io.BytesIO(data))
    except Exception:
        return pd.read_csv(io.BytesIO(data))

def load_assets_raw(object_key: str) -> AssetsRaw:
    c = client()
    # expect a single workbook with two sheets OR a zip of two files; for simplicity read one file with a 'sheet' column hint
    resp = c.get_object(settings.MINIO_BUCKET, object_key)
    data = resp.read()
    resp.close(); resp.release_conn()

    df = _read_frame(data)
    df.columns = [c.strip().lower() for c in df.columns]
    # we’ll assume rows differentiate by a 'kind' column: 'asset' or 'liability'
    if "kind" not in df.columns:
        raise ValueError("Assets file must include a 'kind' column with values 'asset' or 'liability'.")

    assets_df = df[df["kind"].str.lower() == "asset"]
    liab_df = df[df["kind"].str.lower() == "liability"]

    assets = [AssetRow(type=str(r["type"]).lower(), value=float(r["value"])) for _, r in assets_df.iterrows()]
    liabilities = [LiabilityRow(
        type=str(r["type"]).lower(),
        limit=float(r["limit"]) if "limit" in liab_df.columns and pd.notna(r["limit"]) else None,
        outstanding=float(r["outstanding"]),
        emi=float(r["emi"]) if "emi" in liab_df.columns and pd.notna(r["emi"]) else None
    ) for _, r in liab_df.iterrows()]

    return AssetsRaw(assets=assets, liabilities=liabilities)

def features_from_raw(raw: AssetsRaw, form: ApplicantForm) -> AssetsLiabilitiesFacts:
    total_assets = sum(a.value for a in raw.assets)
    total_liab = sum(l.outstanding for l in raw.liabilities)
    net_worth = total_assets - total_liab

    total_emi = sum((l.emi or 0.0) for l in raw.liabilities)
    emi_to_income_ratio = (total_emi / form.declared_monthly_income) if form.declared_monthly_income > 0 else 0.0

    # simple declared utilization (credit cards)
    cc = [l for l in raw.liabilities if l.type in ["credit_card","card"]]
    util = 0.0
    if cc:
        used = sum(l.outstanding for l in cc)
        limit = sum((l.limit or 0.0) for l in cc)
        util = (used/limit)*100 if limit > 0 else 0.0

    liab_to_income = (total_liab / form.declared_monthly_income) if form.declared_monthly_income > 0 else 0.0

    return AssetsLiabilitiesFacts(
        total_assets_value=total_assets,
        total_liabilities_value=total_liab,
        liabilities_to_income_ratio=liab_to_income,
        net_worth=net_worth,
        emi_to_income_ratio=emi_to_income_ratio,
        credit_utilization_declared=util
    )
