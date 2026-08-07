"""Output 4-1 / 4-2 shaped realism panels (no i18n chrome)."""

from __future__ import annotations

import pandas as pd

from lic_dsf.realism.fiscal_adjustment import (
    DEFAULT_LIC_PROGRAM_DISTRIBUTION,
    FiscalAdjustmentPlacement,
    place_in_lic_histogram,
    projected_three_year_adjustment,
    three_year_fiscal_adjustment,
)
from lic_dsf.realism.fiscal_multiplier import (
    cumulative_multiplier_impact,
    fiscal_adjustment_from_primary_balance,
    underlying_growth,
)
from lic_dsf.realism.invest_growth import (
    capital_growth_contribution,
    capital_stock_to_gdp,
    residual_growth_contribution,
)
from lic_dsf.realism.types import CapitalAssumptions, MultiplierAssumptions


def fiscal_adjustment_panel(
    primary_deficit_pct: pd.Series,
    first_projection_year: int,
) -> pd.DataFrame:
    """Output 4-2 histogram panel for planned 3-year fiscal adjustment.

    Args:
        primary_deficit_pct: Baseline public primary deficit / GDP.
        first_projection_year: First projection year.

    Returns:
        DataFrame with histogram bins plus projected adjustment placement.
    """
    dist = DEFAULT_LIC_PROGRAM_DISTRIBUTION
    hist = dist.as_frame()
    adj_series = three_year_fiscal_adjustment(primary_deficit_pct)
    projected = projected_three_year_adjustment(
        primary_deficit_pct, first_projection_year
    )
    placement = place_in_lic_histogram(projected)
    hist = hist.copy()
    hist["projected_adjustment"] = float("nan")
    hist.loc[placement.bin_index, "projected_adjustment"] = projected
    hist.attrs["placement"] = placement
    hist.attrs["adjustment_series"] = adj_series
    return hist


def fiscal_multiplier_panel(
    primary_balance_pct: pd.Series,
    real_gdp_growth: pd.Series,
    first_projection_year: int,
    multipliers: list[MultiplierAssumptions] | None = None,
) -> pd.DataFrame:
    """Output 4-2 chart-0 panel: impact and underlying growth by ``m``.

    Args:
        primary_balance_pct: Macro primary balance / GDP (%).
        real_gdp_growth: Real GDP growth (%).
        first_projection_year: First projection year.
        multipliers: Multiplier grid; defaults to ``m ∈ {0.2,…,1}``, ``p=0.6``.

    Returns:
        Multi-index columns ``(metric, m)`` over projection years.
    """
    if multipliers is None:
        multipliers = [
            MultiplierAssumptions(m=m, persistence=0.6)
            for m in (0.2, 0.4, 0.6, 0.8, 1.0)
        ]
    adj = fiscal_adjustment_from_primary_balance(primary_balance_pct)
    frames: dict[tuple[str, float], pd.Series] = {}
    for a in multipliers:
        impact = cumulative_multiplier_impact(adj, a, first_projection_year)
        under = underlying_growth(real_gdp_growth, impact, first_projection_year)
        frames[("impact", a.m)] = impact
        frames[("underlying_growth", a.m)] = under
    return pd.DataFrame(frames)


def invest_growth_panel(
    investment_to_gdp: pd.Series,
    real_gdp_growth: pd.Series,
    assumptions: CapitalAssumptions | None = None,
) -> pd.DataFrame:
    """Output 4-2 invest / growth-contribution panel.

    Args:
        investment_to_gdp: Government investment / GDP (%).
        real_gdp_growth: Real GDP growth (%).
        assumptions: Capital stock assumptions.

    Returns:
        Panel with capital stock, G contribution, and residual.
    """
    assumptions = assumptions or CapitalAssumptions()
    stock = capital_stock_to_gdp(investment_to_gdp, real_gdp_growth, assumptions)
    contrib = capital_growth_contribution(stock, assumptions)
    residual = residual_growth_contribution(real_gdp_growth, contrib)
    return pd.DataFrame(
        {
            "Gov investment / GDP": investment_to_gdp.astype(float),
            "Capital stock / GDP": stock,
            "Contribution of government capital": contrib,
            "Contribution of other factors": residual,
            "Real GDP growth": real_gdp_growth.astype(float),
        }
    ).T


def forecast_error_panel(
    current_debt_pct: pd.Series,
    prior_debt_pct: pd.Series,
    errors: pd.Series | None = None,
) -> pd.DataFrame:
    """Output 4-1 vintage debt-path / forecast-error panel.

    Args:
        current_debt_pct: Current DSA debt / GDP.
        prior_debt_pct: Prior (rebased) DSA debt / GDP.
        errors: Optional precomputed forecast errors.

    Returns:
        Panel comparing vintages and errors.
    """
    from lic_dsf.realism.forecast_error import forecast_error as fe

    err = errors if errors is not None else fe(prior_debt_pct, current_debt_pct)
    return pd.DataFrame(
        {
            "Current DSA debt / GDP": current_debt_pct.astype(float),
            "Prior DSA debt / GDP": prior_debt_pct.astype(float),
            "Forecast error (prior − current)": err.astype(float),
        }
    ).T


def placement_summary(placement: FiscalAdjustmentPlacement) -> pd.Series:
    """Scalar summary of Realism 4 histogram placement."""
    return pd.Series(
        {
            "projected_3yr_adjustment": placement.adjustment,
            "bin_edge": placement.bin_edge,
            "category": placement.category,
            "percent_of_sample": placement.percent_of_sample,
            "cumulative_percent": placement.cumulative_percent,
        }
    )
