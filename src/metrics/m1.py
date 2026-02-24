from __future__ import annotations

from typing import Iterable, Sequence


def m1_mae(ideal: Sequence[float], approx: Sequence[float]) -> float:
    if len(ideal) != len(approx) or len(ideal) == 0:
        raise ValueError("M1 expects equal-length non-empty vectors of expectation values.")
    return sum(abs(a - b) for a, b in zip(ideal, approx)) / len(ideal)


def m1_rmse(ideal: Sequence[float], approx: Sequence[float]) -> float:
    if len(ideal) != len(approx) or len(ideal) == 0:
        raise ValueError("M1 expects equal-length non-empty vectors of expectation values.")
    return (sum((a - b) ** 2 for a, b in zip(ideal, approx)) / len(ideal)) ** 0.5
