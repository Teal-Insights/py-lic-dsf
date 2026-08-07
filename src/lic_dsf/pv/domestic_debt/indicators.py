"""Pure Dom_Debt_Data derived-indicator math."""

from __future__ import annotations

import pandas as pd

from lic_dsf.pv.domestic_debt.types import DomesticDebtInputs


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    """Match Excel ``IF(x<0,0,x)`` while preserving NA."""
    out = series.copy()
    mask = out.notna() & (out < 0)
    out = out.where(~mask, 0.0)
    return out


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Element-wise divide; zero / non-finite denominators become NA."""
    out = numerator / denominator
    out = out.mask(denominator.isna() | (denominator == 0))
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def domestic_debt_to_gdp(inputs: DomesticDebtInputs) -> pd.Series:
    """Domestic debt / GDP (Dom R10): ``max(0, public − PPG external)``."""
    years = inputs.years
    public = _align(inputs.public_sector_debt_pct_gdp, years)
    ppg = _align(inputs.ppg_external_debt_pct_gdp, years)
    return _clamp_nonnegative(public - ppg)


def domestic_ds_to_revenues(inputs: DomesticDebtInputs) -> pd.Series:
    """Domestic DS / revenues incl. grants (Dom R16).

    ``pub_ds − ppg_ds × (rev − grants) / rev``, clamped at 0.
    """
    years = inputs.years
    pub_ds = _align(inputs.public_ds_to_revenue_grants, years)
    ppg_ds = _align(inputs.ppg_ds_to_revenue, years)
    rev = _align(inputs.revenues_incl_grants, years)
    grants = _align(inputs.grants, years)
    share = _safe_divide(rev - grants, rev)
    raw = pub_ds - ppg_ds * share
    return _clamp_nonnegative(raw)


def gdp_lcu(inputs: DomesticDebtInputs) -> pd.Series:
    """Nominal GDP in LCU (Dom R33): ``gdp_usd × fx_pa``."""
    years = inputs.years
    return _align(inputs.gdp_usd, years) * _align(inputs.fx_pa, years)


def domestic_interest_lcu(inputs: DomesticDebtInputs) -> pd.Series:
    """Domestic interest in LCU (Dom R29): Macro interest × FX(pa)."""
    years = inputs.years
    return _align(inputs.domestic_interest_due, years) * _align(inputs.fx_pa, years)


def change_in_domestic_debt(inputs: DomesticDebtInputs) -> pd.Series:
    """Change in domestic debt (Dom R28); first year is NA."""
    years = inputs.years
    stock = _align(inputs.domestic_debt_stock, years) + _align(
        inputs.fx_denominated_domestic_stock, years
    )
    change = stock - stock.shift(1)
    change.iloc[0] = pd.NA
    return change.astype(float)


def net_issuance_to_gdp(inputs: DomesticDebtInputs) -> pd.Series:
    """Net domestic debt issuance / GDP (Dom R25); first year is NA."""
    years = inputs.years
    delta = change_in_domestic_debt(inputs)
    interest = domestic_interest_lcu(inputs) + _align(
        inputs.fx_denominated_domestic_interest, years
    )
    gdp = gdp_lcu(inputs)
    raw = _safe_divide(100.0 * (delta - interest), gdp)
    raw.iloc[0] = pd.NA
    return raw.astype(float)


def net_issuance_to_prior_dom_debt(inputs: DomesticDebtInputs) -> pd.Series:
    """Net issuance / prior domestic debt-to-GDP (Dom R34); first year NA."""
    net = net_issuance_to_gdp(inputs)
    prior_ratio = pd.Series(domestic_debt_to_gdp(inputs).shift(1), dtype=float)
    raw = _safe_divide(100.0 * net, prior_ratio)
    raw.iloc[0] = pd.NA
    return raw.astype(float)


def peer_median_debt_to_gdp(inputs: DomesticDebtInputs) -> pd.Series:
    """Constant peer-median band (Dom R14)."""
    return pd.Series(
        float(inputs.peer_median_debt_to_gdp),
        index=list(inputs.years),
        dtype=float,
    )


def peer_median_ds_to_revenues(inputs: DomesticDebtInputs) -> pd.Series:
    """Constant peer-median band (Dom R22)."""
    return pd.Series(
        float(inputs.peer_median_ds_to_revenues),
        index=list(inputs.years),
        dtype=float,
    )


def summary_averages(
    series: pd.Series,
    *,
    first_projection_year: int,
    years: tuple[int, ...],
) -> pd.Series:
    """Excel Dom summary averages AL / AM / AN / AP.

    * ``hist_10`` — average of the 10 years ending the year before projection
      (Excel ``AVERAGE(E:N)`` when O is first projection).
    * ``proj_1_5`` — first five projection years.
    * ``proj_6_20`` — projection years 6–20.
    * ``proj_all`` — all projection years through the horizon.
    """
    year_list = list(years)
    try:
        proj_idx = year_list.index(first_projection_year)
    except ValueError as exc:
        raise ValueError(
            f"first_projection_year {first_projection_year} not in years"
        ) from exc

    hist = year_list[max(0, proj_idx - 10) : proj_idx]
    proj = year_list[proj_idx:]
    proj_1_5 = proj[:5]
    proj_6_20 = proj[5:20]

    def _avg(subset: list[int]) -> float:
        if not subset:
            return float("nan")
        values = series.reindex(subset).dropna()
        if values.empty:
            return float("nan")
        return float(values.mean())

    return pd.Series(
        {
            "hist_10": _avg(hist),
            "proj_1_5": _avg(proj_1_5),
            "proj_6_20": _avg(proj_6_20),
            "proj_all": _avg(proj),
        },
        dtype=float,
    )
