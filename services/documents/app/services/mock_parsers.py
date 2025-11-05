from typing import Tuple
from schemas.models import BankFacts, EIDFacts, ResumeFacts, AssetsLiabilitiesFacts, CreditFacts
import random

def mock_ocr_pages() -> Tuple[int, float]:
    return random.choice([1,2,3]), 0.92

def parse_bank(_: str) -> BankFacts:
    return BankFacts(
        salary_inflow_mean_3m=12000.0, salary_variance_3m=500.0,
        avg_balance_3m=8200.0, min_balance_3m=1500.0,
        expense_to_income_ratio_3m=0.68, liquidity_buffer_days=25.0,
        nsf_return_count_3m=0, debt_payment_ratio_3m=0.18,
        income_stability_index=0.95, cash_withdraw_pct=0.07,
        rent_detected=True
    )

def parse_eid(_: str) -> EIDFacts:
    return EIDFacts(age_years=34, eid_valid=True, residency_valid_days_remaining=365,
                    nationality_group="MENA", id_name_match_score=0.93, demographic_profile_band="prime")

def parse_resume(_: str) -> ResumeFacts:
    return ResumeFacts(employment_current=True, employment_tenure_months=28, recent_job_gap_days=0,
                       occupation_code="213-SoftwareEngineer", education_level_band="masters+",
                       sector_match_to_inflows=True)

def parse_assets(_: str) -> AssetsLiabilitiesFacts:
    return AssetsLiabilitiesFacts(total_assets_value=180000.0, total_liabilities_value=90000.0,
                                  liabilities_to_income_ratio=0.62, net_worth=90000.0,
                                  emi_to_income_ratio=0.28, credit_utilization_declared=0.35)

def parse_credit(_: str) -> CreditFacts:
    return CreditFacts(credit_score_band="B", credit_utilization_pct=32.0, active_accounts_count=4,
                       recent_hard_inquiries_6m=1, dpd_30_12m=0, dpd_60_12m=0, dpd_90_12m=0,
                       serious_delinquency_flag=False)
