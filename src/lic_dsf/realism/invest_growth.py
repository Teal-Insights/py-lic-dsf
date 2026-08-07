"""Realism 3 — investment-growth and government capital contribution."""

from __future__ import annotations

import pandas as pd

from lic_dsf.realism.types import CapitalAssumptions


def capital_stock_to_gdp(
    investment_to_gdp: pd.Series,
    real_gdp_growth: pd.Series,
    assumptions: CapitalAssumptions,
) -> pd.Series:
    """Recurse government capital stock / GDP.

    ``G_t/Y_t = G_{t−1}/Y_{t−1} × (1−d) / (1+g_t) + φ × (Ig/Y)_t``
    where ``g_t`` is real growth as a decimal.

    Args:
        investment_to_gdp: Government investment / GDP (percent).
        real_gdp_growth: Real GDP growth (percent).
        assumptions: Depreciation, efficiency, initial ``G/Y``.

    Returns:
        Capital stock / GDP series (percent).
    """
    ig = investment_to_gdp.astype(float).sort_index() / 100.0
    g = real_gdp_growth.astype(float).reindex(ig.index) / 100.0
    d = assumptions.depreciation
    phi = assumptions.efficiency
    out: dict[int, float] = {}
    prev = assumptions.initial_capital_to_gdp
    for year in ig.index:
        growth = float(g.loc[year]) if pd.notna(g.loc[year]) else 0.0
        denom = 1.0 + growth
        if denom == 0.0:
            denom = 1.0
        stock = prev * (1.0 - d) / denom + phi * float(ig.loc[year])
        out[int(year)] = 100.0 * stock
        prev = stock
    return pd.Series(out, dtype=float)


def capital_growth_contribution(
    capital_to_gdp: pd.Series,
    assumptions: CapitalAssumptions,
) -> pd.Series:
    """Contribution of government capital to growth: ``β × Ĝ``.

    ``Ĝ_t = (G_t − G_{t−1}) / G_{t−1}`` using capital/GDP levels as proxy for
    capital growth when GDP units cancel in ratios used by Realism 3 charts.
    Excel uses the capital stock recursion in levels; callers may pass
    level-based capital and obtain ``β × ΔG/G``.

    Args:
        capital_to_gdp: Capital stock / GDP (percent) from
            `capital_stock_to_gdp`.
        assumptions: Includes output elasticity ``β``.

    Returns:
        Contribution series in percentage points.
    """
    k = capital_to_gdp.astype(float).sort_index()
    prior = k.shift(1)
    growth = (k - prior) / prior.replace(0.0, pd.NA)
    return (100.0 * assumptions.beta * growth).astype(float)


def residual_growth_contribution(
    real_gdp_growth: pd.Series,
    government_contribution: pd.Series,
) -> pd.Series:
    """Residual = real growth − government capital contribution.

    Args:
        real_gdp_growth: Real GDP growth (percent).
        government_contribution: ``β × Ĝ`` contribution (ppt).

    Returns:
        Residual contribution of other factors.
    """
    return (
        real_gdp_growth.astype(float) - government_contribution.astype(float)
    ).astype(float)
