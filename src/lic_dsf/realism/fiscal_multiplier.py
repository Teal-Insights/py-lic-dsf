"""Realism 2 — fiscal multiplier impulse and underlying growth."""

from __future__ import annotations

import pandas as pd

from lic_dsf.realism.types import MultiplierAssumptions


def fiscal_adjustment_from_primary_balance(
    primary_balance_pct: pd.Series,
) -> pd.Series:
    """Year-on-year fiscal adjustment from primary balance % GDP.

    Excel Realism 2 R6: ``PB_t − PB_{t-1}`` (ppt; (+) = improvement).

    Args:
        primary_balance_pct: Primary balance / GDP (negative = deficit).

    Returns:
        Fiscal adjustment series (NaN in the first year).
    """
    pb = primary_balance_pct.astype(float).sort_index()
    return (pb - pb.shift(1)).astype(float)


def unit_impulse(
    assumptions: MultiplierAssumptions,
    lags: range | list[int],
) -> pd.Series:
    """Unit impulse ``−m × p^t`` for each lag ``t``.

    Args:
        assumptions: Multiplier ``m`` and persistence ``p``.
        lags: Integer lags (Excel Realism 2 time index).

    Returns:
        Series indexed by lag.
    """
    return pd.Series(
        {t: -assumptions.m * (assumptions.persistence**t) for t in lags},
        dtype=float,
    )


def cumulative_multiplier_impact(
    fiscal_adjustment: pd.Series,
    assumptions: MultiplierAssumptions,
    first_projection_year: int,
) -> pd.Series:
    """Cumulative growth impact of fiscal adjustments under multiplier ``m``.

    For each projection year ``t``,
    ``impact_t = Σ_{s≤t} adj_s × (−m × p^{t−s})`` over projection years ``s``.

    Args:
        fiscal_adjustment: Year-on-year PB improvement (ppt of GDP).
        assumptions: Multiplier assumptions.
        first_projection_year: First year receiving adjustment shocks.

    Returns:
        Cumulative growth impact series over projection years.
    """
    adj = fiscal_adjustment.astype(float).sort_index()
    years = [y for y in adj.index if y >= first_projection_year]
    last_adj_year = first_projection_year + 13
    out: dict[int, float] = {}
    for t in years:
        total = 0.0
        for s in years:
            if s > t or s > last_adj_year:
                break
            a = adj.loc[s]
            if pd.isna(a):
                continue
            lag = int(t - s)
            total += float(a) * (-assumptions.m * (assumptions.persistence**lag))
        out[int(t)] = total
    return pd.Series(out, dtype=float)


def underlying_growth(
    baseline_growth: pd.Series,
    impact: pd.Series,
    first_projection_year: int,
) -> pd.Series:
    """Underlying growth = pre-projection growth + cumulative impact.

    Excel Realism 2 chart 2 anchors on growth in ``first_projection_year − 1``
    for all projection years.

    Args:
        baseline_growth: Real GDP growth % series.
        impact: Cumulative multiplier impact series.
        first_projection_year: First projection year.

    Returns:
        Underlying growth path under the multiplier.
    """
    anchor_year = first_projection_year - 1
    if anchor_year not in baseline_growth.index:
        raise ValueError(f"missing growth for anchor year {anchor_year}")
    anchor = float(baseline_growth.loc[anchor_year])
    return (anchor + impact.astype(float)).astype(float)
