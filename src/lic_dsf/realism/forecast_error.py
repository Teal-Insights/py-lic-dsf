"""Realism 1 — forecast-error / debt-creating-flow decomposition helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def rebase_ratio_to_outturn_gdp(
    old_gdp: pd.Series,
    new_gdp: pd.Series,
    old_ratio_pct: pd.Series,
) -> pd.Series:
    """Rebase a % of GDP ratio onto the outturn GDP path.

    Excel Realism 1 uses ``r = OldGDP_t0 / NewGDP_t0`` (constant for the
    5-years-ago vintage) then scales debt stocks and rebuilds % GDP on the
    current GDP path. For a simple ratio rebase at a shared year-0 GDP:

    ``rebased_% = old_% × (old_GDP / new_GDP)``.

    Args:
        old_gdp: Vintage nominal GDP.
        new_gdp: Current/outturn nominal GDP.
        old_ratio_pct: Vintage ratio in percent of (old) GDP.

    Returns:
        Rebased ratio in percent of new GDP.
    """
    old = old_gdp.astype(float)
    new = new_gdp.astype(float).reindex(old.index)
    ratio = old_ratio_pct.astype(float).reindex(old.index)
    scale = (old / new.replace(0.0, pd.NA)).astype(float)
    # Prefer a constant scale from the first overlapping year (Excel r).
    first = next((y for y in scale.index if pd.notna(scale.loc[y])), None)
    if first is not None and pd.notna(scale.loc[first]):
        scale = pd.Series(float(scale.loc[first]), index=scale.index, dtype=float)
    return (ratio * scale).astype(float)


def forecast_error(projected: pd.Series, outturn: pd.Series) -> pd.Series:
    """Forecast error = projected − outturn (ppt).

    Args:
        projected: Projected path (e.g. prior vintage, possibly rebased).
        outturn: Realized / current vintage path.

    Returns:
        Error series on the intersection of indexes.
    """
    idx = projected.index.intersection(outturn.index)
    return (
        projected.reindex(idx).astype(float) - outturn.reindex(idx).astype(float)
    ).astype(float)


@dataclass(frozen=True, slots=True)
class QuartileBand:
    """Peer quartile band for forecast-error comparison."""

    p25: float
    p50: float
    p75: float


def compare_to_quartiles(error: float, band: QuartileBand) -> str:
    """Classify a forecast error relative to peer quartiles.

    Args:
        error: Forecast error (ppt).
        band: Peer quartile band.

    Returns:
        One of ``below_p25``, ``p25_p50``, ``p50_p75``, ``above_p75``.
    """
    if error < band.p25:
        return "below_p25"
    if error < band.p50:
        return "p25_p50"
    if error < band.p75:
        return "p50_p75"
    return "above_p75"


def debt_creating_flow_panel(
    change_in_debt: pd.Series,
    primary_deficit: pd.Series,
    other_flows: pd.Series,
    residual: pd.Series | None = None,
) -> pd.DataFrame:
    """Debt-creating flow decomposition panel (Output 4-1 shape).

    Args:
        change_in_debt: Change in debt / GDP.
        primary_deficit: Primary deficit / GDP.
        other_flows: Other identified debt-creating flows / GDP.
        residual: Optional residual / GDP (computed if omitted).

    Returns:
        DataFrame with flow rows over years.
    """
    change = change_in_debt.astype(float)
    pd_pct = primary_deficit.astype(float).reindex(change.index)
    other = other_flows.astype(float).reindex(change.index)
    if residual is None:
        residual = change - pd_pct.fillna(0.0) - other.fillna(0.0)
    return pd.DataFrame(
        {
            "Change in debt / GDP": change,
            "Primary deficit / GDP": pd_pct,
            "Other debt-creating flows / GDP": other,
            "Residual / GDP": residual.astype(float),
        }
    ).T
