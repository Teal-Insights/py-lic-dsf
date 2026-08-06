"""Shared math helpers for LIC-DSF present-value instruments."""

from __future__ import annotations

from collections.abc import Sequence


def excel_npv(rate: float, cashflows: Sequence[float]) -> float:
    """Excel ``NPV(rate, v1, v2, ...)``: first value discounted one period."""
    total = 0.0
    for i, value in enumerate(cashflows):
        total += value / ((1.0 + rate) ** (i + 1))
    return total


def age(year_index: int) -> int:
    """LIC-DSF age used in some amortization IFs: ``year_index - 1``."""
    return year_index - 1
