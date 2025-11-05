# services/score/app/thresholds.py
from pydantic import BaseModel
from typing import List


class Metrics(BaseModel):
    precision: List[float]
    recall: List[float]
    thresholds: List[float]
    roc_auc: float


class Thresholds(BaseModel):
    approve: float
    review: float


def pick_thresholds(
    metrics: Metrics,
    target_precision: float = 0.85,
    min_approval_rate: float = 0.1,
) -> Thresholds:
    precision, thresholds = metrics.precision, metrics.thresholds
    best_thr = 0.5
    for p, t in zip(precision[:-1], thresholds):
        if p >= target_precision and t > best_thr:
            best_thr = t
    approve_thr = float(best_thr)
    review_thr = (approve_thr + 0.5) / 2.0
    return Thresholds(approve=approve_thr, review=review_thr)
