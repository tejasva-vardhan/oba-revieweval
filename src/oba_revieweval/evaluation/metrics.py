"""Thin wrappers used by unit tests. Official scoring is scoring.py."""

from __future__ import annotations


def precision(true_positive: int, false_positive: int) -> float:
    denom = true_positive + false_positive
    return true_positive / denom if denom else 0.0


def recall(true_positive: int, false_negative: int) -> float:
    denom = true_positive + false_negative
    return true_positive / denom if denom else 0.0


def f1(prec: float, rec: float) -> float:
    if (prec + rec) == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
