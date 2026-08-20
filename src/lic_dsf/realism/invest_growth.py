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
    first = True
    for year in ig.index:
        if first:
            out[int(year)] = 100.0 * prev
            first = False
            continue
        growth = float(g.loc[year]) if pd.notna(g.loc[year]) else 0.0
        denom = 1.0 + growth
        if denom == 0.0:
            denom = 1.0
        stock = prev * (1.0 - d) / denom + phi * float(ig.loc[year])
        out[int(year)] = 100.0 * stock
        prev = stock
    return pd.Series(out, dtype=float)


def capital_stock_level(
    investment_to_gdp: pd.Series,
    real_gdp_growth: pd.Series,
    assumptions: CapitalAssumptions,
    fad_levels: pd.Series | None = None,
) -> pd.Series:
    """Build the capital stock *level* index (Excel R75).

    Excel builds ``G_t = G_{t-1}(1-d) + (Ig/Y)_t × Y_index_t × φ`` where
    ``Y_index`` is real GDP rebased to 100 at the first year. FAD actual
    levels override the recursion for years where data exists.

    Args:
        investment_to_gdp: Government investment / GDP (percent).
        real_gdp_growth: Real GDP growth (percent).
        assumptions: Capital stock assumptions.
        fad_levels: Optional FAD actual G levels (R71). Where provided,
            the recursion is replaced by the actual value.

    Returns:
        Capital stock level index series.
    """
    ig = investment_to_gdp.astype(float).sort_index() / 100.0
    g = real_gdp_growth.astype(float).reindex(ig.index) / 100.0
    d = assumptions.depreciation
    phi = assumptions.efficiency

    # Build GDP level index (base year = 100)
    gdp_idx: dict[int, float] = {}
    years = list(ig.index)
    gdp_idx[int(years[0])] = 100.0
    for i in range(1, len(years)):
        yr = int(years[i])
        gr = float(g.loc[yr]) if pd.notna(g.loc[yr]) else 0.0
        gdp_idx[yr] = gdp_idx[int(years[i - 1])] * (1.0 + gr)

    out: dict[int, float] = {}
    prev_level: float | None = None

    for year in years:
        yr = int(year)
        if fad_levels is not None and yr in fad_levels.index and pd.notna(
            fad_levels.loc[yr]
        ):
            level = float(fad_levels.loc[yr])
        elif prev_level is None:
            level = assumptions.initial_capital_to_gdp * gdp_idx[yr]
        else:
            level = prev_level * (1.0 - d) + float(ig.loc[yr]) * gdp_idx[yr] * phi
        out[yr] = level
        prev_level = level

    return pd.Series(out, dtype=float)


def capital_growth_contribution(
    capital_to_gdp: pd.Series,
    real_gdp_growth: pd.Series,
    assumptions: CapitalAssumptions,
    *,
    level_index: pd.Series | None = None,
) -> pd.Series:
    """Contribution of government capital to growth: ``100 × β × Ĝ``.

    When `level_index` is given (Excel R75), growth is simply
    ``G_t/G_{t-1} − 1``. Otherwise it is derived from the G/Y ratio and
    real GDP growth: ``Ĝ = (k_t / k_{t-1}) × (1 + g_t) − 1``.

    Args:
        capital_to_gdp: Capital stock / GDP (percent) — used only when
            `level_index` is not provided.
        real_gdp_growth: Real GDP growth (percent) — used only when
            `level_index` is not provided.
        assumptions: Includes output elasticity ``β``.
        level_index: Capital stock level series (from `capital_stock_level`).

    Returns:
        Contribution series in percentage points.
    """
    if level_index is not None:
        lvl = level_index.astype(float).sort_index()
        g_stock = lvl / lvl.shift(1).replace(0.0, pd.NA) - 1.0
    else:
        k = capital_to_gdp.astype(float).sort_index()
        g = real_gdp_growth.astype(float).reindex(k.index) / 100.0
        prior = k.shift(1)
        ratio = k / prior.replace(0.0, pd.NA)
        g_stock = ratio * (1.0 + g) - 1.0
    return (100.0 * assumptions.beta * g_stock).astype(float)


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
