"""Retrieval metrics over ordered lists of file paths."""
from __future__ import annotations

from typing import Sequence


def hit_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    rel = set(relevant)
    return 1.0 if any(p in rel for p in retrieved[:k]) else 0.0


def reciprocal_rank(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    rel = set(relevant)
    for i, p in enumerate(retrieved, start=1):
        if p in rel:
            return 1.0 / i
    return 0.0


def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    return len(rel & set(retrieved[:k])) / len(rel)
