"""Realism 1 — forecast-error / debt-creating-flow decomposition helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from lic_dsf.dsa.dynamics import public_automatic_debt_dynamics

GdpRebaseMode = Literal["constant", "last_vintage"]


def gdp_rebase_scale(
    old_gdp: pd.Series,
    new_gdp: pd.Series,
    *,
    mode: GdpRebaseMode = "constant",
    first_projection_year: int | None = None,
) -> pd.Series:
    """Return Excel Realism 1 ``r = old GDP / new GDP`` by vintage mode.

    ``constant`` (5-years-ago, ``R48`` / ``R126``): one ``r`` from the first
    overlapping year, copied across the horizon.

    ``last_vintage`` (``R73`` / ``R147``): year-specific ``r_t`` through
    ``first_projection_year - 2``, then that value is held for
    ``t >= first_projection_year - 1``.

    Args:
        old_gdp: Vintage nominal GDP.
        new_gdp: Current/outturn nominal GDP.
        mode: ``constant`` or ``last_vintage``.
        first_projection_year: Required when ``mode`` is ``last_vintage``.

    Returns:
        Scale series ``r`` aligned to ``old_gdp``.

    Raises:
        ValueError: If ``last_vintage`` is used without ``first_projection_year``.
    """
    old = old_gdp.astype(float)
    new = new_gdp.astype(float).reindex(old.index)
    scale = (old / new.replace(0.0, pd.NA)).astype(float)
    if mode == "constant":
        first = next((y for y in scale.index if pd.notna(scale.loc[y])), None)
        if first is not None and pd.notna(scale.loc[first]):
            return pd.Series(float(scale.loc[first]), index=scale.index, dtype=float)
        return scale
    if first_projection_year is None:
        raise ValueError("first_projection_year is required for last_vintage rebase")
    freeze_from = int(first_projection_year) - 1
    last_vary = int(first_projection_year) - 2
    out = scale.copy()
    frozen: float
    if last_vary in out.index and pd.notna(out.loc[last_vary]):
        frozen = float(out.loc[last_vary])
    else:
        prior = [y for y in out.index if int(y) < freeze_from and pd.notna(out.loc[y])]
        frozen = float(out.loc[prior[-1]]) if prior else float("nan")
    for year in out.index:
        if int(year) >= freeze_from:
            out.loc[year] = frozen
    return out.astype(float)


def rebase_ratio_to_outturn_gdp(
    old_gdp: pd.Series,
    new_gdp: pd.Series,
    old_ratio_pct: pd.Series,
    *,
    mode: GdpRebaseMode = "constant",
    first_projection_year: int | None = None,
) -> pd.Series:
    """Rebase a % of GDP ratio onto the outturn GDP path.

    ``rebased_% = old_% × r`` where ``r`` comes from `gdp_rebase_scale`.
    Default ``mode="constant"`` is the 5-years-ago identity.

    Args:
        old_gdp: Vintage nominal GDP.
        new_gdp: Current/outturn nominal GDP.
        old_ratio_pct: Vintage ratio in percent of (old) GDP.
        mode: ``constant`` or ``last_vintage``.
        first_projection_year: Required when ``mode`` is ``last_vintage``.

    Returns:
        Rebased ratio in percent of new GDP.
    """
    scale = gdp_rebase_scale(
        old_gdp,
        new_gdp,
        mode=mode,
        first_projection_year=first_projection_year,
    )
    ratio = old_ratio_pct.astype(float).reindex(scale.index)
    return (ratio * scale).astype(float)


def total_external_to_gdp(
    ppg_external_to_gdp: pd.Series,
    private_external: pd.Series,
    gdp_usd: pd.Series,
) -> pd.Series:
    """Excel Realism 1 ``D_GDP``: PPG % plus private external / USD GDP.

    ``D_PPG_GDP`` already values PPG at eop FX over LCU GDP. Excel then adds
    ``100 × private_external / GDP_USD`` rather than converting the whole
    external stock at eop FX.

    Args:
        ppg_external_to_gdp: PPG external / GDP (percent), Excel ``D_PPG_GDP``.
        private_external: Private external debt stock (same units as ``gdp_usd``).
        gdp_usd: Nominal GDP in USD.

    Returns:
        Total external debt / GDP (percent).
    """
    priv_pct = (
        100.0
        * private_external.astype(float).reindex(ppg_external_to_gdp.index)
        / gdp_usd.astype(float).reindex(ppg_external_to_gdp.index).replace(0.0, pd.NA)
    )
    return (ppg_external_to_gdp.astype(float) + priv_pct).astype(float)


def debt_stock_from_ratio(ratio_pct: pd.Series, gdp: pd.Series) -> pd.Series:
    """Convert a % of GDP ratio into a stock in GDP units.

    Excel Realism 1 vintage USD/LCU levels are ``ratio / 100 × vintage GDP``,
    not rebased % × current GDP.

    Args:
        ratio_pct: Debt / GDP in percent.
        gdp: Nominal GDP in the stock's units (e.g. billions of USD).

    Returns:
        Debt stock series.
    """
    gdp_a = gdp.astype(float).reindex(ratio_pct.index)
    return (ratio_pct.astype(float) / 100.0 * gdp_a).astype(float)


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


def other_identified_flows_to_gdp(
    contingent: pd.Series,
    other: pd.Series,
    privatization: pd.Series,
    debt_relief: pd.Series,
    gdp_lcu: pd.Series,
) -> pd.Series:
    """Baseline R33 / Realism `DU_OF_GDP`: other identified flows / GDP.

    ``100 × (contingent + other − privatization − debt relief) / GDP_LCU``.

    Args:
        contingent: Contingent liabilities (same units as `gdp_lcu`).
        other: Other debt-creating flows.
        privatization: Privatization receipts (enter positive; subtracted).
        debt_relief: Debt relief (enter positive; subtracted).
        gdp_lcu: Nominal GDP in local currency.

    Returns:
        Other identified debt-creating flows in percent of GDP.
    """
    gdp = gdp_lcu.astype(float)
    numer = (
        contingent.astype(float).reindex(gdp.index).fillna(0.0)
        + other.astype(float).reindex(gdp.index).fillna(0.0)
        - privatization.astype(float).reindex(gdp.index).fillna(0.0)
        - debt_relief.astype(float).reindex(gdp.index).fillna(0.0)
    )
    return (100.0 * numer / gdp.replace(0.0, pd.NA)).astype(float)


def debt_creating_flow_panel(
    change_in_debt: pd.Series,
    primary_deficit: pd.Series,
    other_flows: pd.Series,
    residual: pd.Series | None = None,
    *,
    real_interest: pd.Series | None = None,
    real_gdp_growth: pd.Series | None = None,
    real_exchange_rate: pd.Series | None = None,
) -> pd.DataFrame:
    """Debt-creating flow decomposition panel (Output 4-1 shape).

    Excel residual is the leftover after the identified stack: primary deficit,
    other identified flows, and automatic dynamics (real interest, real GDP
    growth, real exchange-rate depreciation). Omitting those contribution
    series keeps the older 3-term identity.

    Args:
        change_in_debt: Change in debt / GDP.
        primary_deficit: Primary deficit / GDP.
        other_flows: Other identified debt-creating flows / GDP.
        residual: Optional residual / GDP (computed if omitted).
        real_interest: Contribution from average real interest / GDP.
        real_gdp_growth: Contribution from real GDP growth / GDP.
        real_exchange_rate: Contribution from real FX depreciation / GDP.

    Returns:
        DataFrame with flow rows over years.
    """
    change = change_in_debt.astype(float)
    pd_pct = primary_deficit.astype(float).reindex(change.index)
    other = other_flows.astype(float).reindex(change.index)

    def _term(series: pd.Series | None) -> pd.Series:
        if series is None:
            return pd.Series(0.0, index=change.index, dtype=float)
        return series.astype(float).reindex(change.index).fillna(0.0)

    if residual is None:
        residual = (
            change
            - pd_pct.fillna(0.0)
            - other.fillna(0.0)
            - _term(real_interest)
            - _term(real_gdp_growth)
            - _term(real_exchange_rate)
        )
    return pd.DataFrame(
        {
            "Change in debt / GDP": change,
            "Primary deficit / GDP": pd_pct,
            "Other debt-creating flows / GDP": other,
            "Residual / GDP": residual.astype(float),
        }
    ).T
