from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import InMemoryStore
    from .domain import StoredEvent


def apk(actual: list[str], predicted: list[str], k: int = 12) -> float:
    """Calculate Average Precision at K (AP@K)."""
    if not actual:
        return 0.0
    if len(predicted) > k:
        predicted = predicted[:k]

    score = 0.0
    num_hits = 0.0
    actual_set = set(actual)

    for i, p in enumerate(predicted):
        if p in actual_set and p not in predicted[:i]:
            num_hits += 1.0
            score += num_hits / (i + 1.0)

    return score / min(len(actual_set), k)


def mapk(actual_list: list[list[str]], predicted_list: list[list[str]], k: int = 12) -> float:
    """Calculate Mean Average Precision at K (MAP@K)."""
    if not actual_list:
        return 0.0
    return sum(apk(a, p, k) for a, p in zip(actual_list, predicted_list)) / len(actual_list)


def ndcg_k(actual: list[str], predicted: list[str], k: int = 10) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K (NDCG@K)."""
    if not actual:
        return 0.0
    actual_set = set(actual)
    predicted = predicted[:k]

    dcg = 0.0
    for i, item in enumerate(predicted):
        if item in actual_set:
            dcg += 1.0 / math.log2(i + 2)

    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(actual_set), k)))
    return dcg / idcg if idcg > 0 else 0.0


def precision_recall_k(actual: list[str], predicted: list[str], k: int = 12) -> tuple[float, float]:
    """Calculate Precision@K and Recall@K."""
    if not actual or not predicted:
        return 0.0, 0.0
    actual_set = set(actual)
    pred_set = set(predicted[:k])

    hits = len(actual_set.intersection(pred_set))
    precision = hits / len(pred_set) if pred_set else 0.0
    recall = hits / len(actual_set)
    return precision, recall


def compute_eval_metrics(store: InMemoryStore, events: list[StoredEvent], k: int = 12) -> dict:
    """Report honestly that request-time state is not a leakage-safe offline holdout."""
    return {
        "available": False,
        "evaluation_mode": "offline_holdout_required",
        "k": k,
        "evaluated_customers": 0,
        "reason": "The serving event log is not a leakage-safe offline holdout. Run scripts/spark_evaluate.py against timestamped transactions.",
    }
