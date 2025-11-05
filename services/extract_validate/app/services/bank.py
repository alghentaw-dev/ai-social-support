import io
from datetime import date, timedelta
import pandas as pd
from schemas.models import BankRaw, BankTxn, BankFacts
from .minio_client import client
from ..settings import settings

def load_bank_raw(object_key: str) -> BankRaw:
    c = client()
    resp = c.get_object(settings.MINIO_BUCKET, object_key)
    data = resp.read()
    resp.close(); resp.release_conn()

    # try excel then csv
    try:
        df = pd.read_excel(io.BytesIO(data))
    except Exception:
        df = pd.read_csv(io.BytesIO(data))

    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"date","amount","description"}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"Bank file missing required columns: {required}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    txns = [
        BankTxn(
            date=r["date"],
            amount=float(r["amount"]),
            description=str(r.get("description","")),
            category=r.get("category"),
            account_id=str(r.get("account_id")) if pd.notna(r.get("account_id")) else None
        )
        for _, r in df.iterrows()
        if pd.notna(r["date"]) and pd.notna(r["amount"])
    ]
    return BankRaw(txns=txns)

def features_from_raw(raw: BankRaw) -> BankFacts:
    if not raw.txns:
        # safe defaults
        return BankFacts(
            salary_inflow_mean_3m=0, salary_variance_3m=0,
            avg_balance_3m=0, min_balance_3m=0,
            expense_to_income_ratio_3m=0, liquidity_buffer_days=0,
            nsf_return_count_3m=0, debt_payment_ratio_3m=0,
            income_stability_index=0, cash_withdraw_pct=0, rent_detected=False
        )
    # Convert to DataFrame for rolling stats
    df = pd.DataFrame([t.model_dump() for t in raw.txns])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    # infer inflow/outflow convention: inflow = positive
    inflow = df[df["amount"] > 0]["amount"]
    outflow = df[df["amount"] < 0]["amount"].abs()

    # last 3 months window
    end = df["date"].max().date()
    start = end - timedelta(days=90)
    d3 = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    inflow3 = d3[d3["amount"] > 0]["amount"]
    outflow3 = d3[d3["amount"] < 0]["amount"].abs()

    salary_inflow_mean_3m = float(inflow3.mean() if not inflow3.empty else 0.0)
    salary_variance_3m = float(inflow3.var() if len(inflow3) > 1 else 0.0)
    total_inflow = float(inflow3.sum())
    total_outflow = float(outflow3.sum())

    expense_to_income_ratio_3m = (total_outflow / total_inflow) if total_inflow > 0 else 0.0

    # naive daily balance curve (approx): start 0, cum-sum
    d3["balance"] = d3["amount"].cumsum()
    avg_balance_3m = float(d3["balance"].mean()) if len(d3) else 0.0
    min_balance_3m = float(d3["balance"].min()) if len(d3) else 0.0

    avg_daily_outflow = float(outflow3.mean()) if len(outflow3) else 0.0
    liquidity_buffer_days = (avg_balance_3m / avg_daily_outflow) if avg_daily_outflow > 0 else 0.0

    # nsf/returned detection via description keywords (mock heuristic)
    nsf_return_count_3m = int((d3["description"].str.contains("RETURN|NSF|BOUNCE", case=False, na=False)).sum())

    # debt payments (loan/cc) heuristics
    debt_mask = d3["description"].str.contains("LOAN|CREDIT CARD|CC BILL|INSTALLMENT", case=False, na=False)
    debt_payments = d3[debt_mask & (d3["amount"] < 0)]["amount"].abs().sum()
    debt_payment_ratio_3m = float(debt_payments / total_inflow) if total_inflow > 0 else 0.0

    # income stability: detect payroll periodicity (monthly)
    payroll_mask = d3["description"].str.contains("SAL|PAYROLL|SALARY", case=False, na=False) & (d3["amount"] > 0)
    income_stability_index = min(1.0, payroll_mask.sum() / 3.0) if len(d3) else 0.0

    cash_withdraw_pct = float(
        d3[d3["description"].str.contains("ATM|CASH WITHDRAW", case=False, na=False) & (d3["amount"] < 0)]["amount"].abs().sum()
        / total_outflow
    ) if total_outflow > 0 else 0.0

    rent_detected = bool((d3["description"].str.contains("RENT|LANDLORD|TENANCY|EJARI", case=False, na=False)).any())

    return BankFacts(
        salary_inflow_mean_3m=salary_inflow_mean_3m,
        salary_variance_3m=salary_variance_3m,
        avg_balance_3m=avg_balance_3m,
        min_balance_3m=min_balance_3m,
        expense_to_income_ratio_3m=expense_to_income_ratio_3m,
        liquidity_buffer_days=liquidity_buffer_days,
        nsf_return_count_3m=nsf_return_count_3m,
        debt_payment_ratio_3m=debt_payment_ratio_3m,
        income_stability_index=income_stability_index,
        cash_withdraw_pct=cash_withdraw_pct,
        rent_detected=rent_detected
    )
