"""Derived Macro-Debt_Data metrics (GFN, residual gap, public debt, rates)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from lic_dsf.pv.macro_debt import stocks as _stocks

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.types import MacroDebtInputs


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).fillna(0.0).astype(float)


def _safe_rate(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def primary_balance(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R44 = revenues − primary expenditure."""
    years = inputs.years
    return _align(inputs.revenues_incl_grants, years) - _align(
        inputs.primary_expenditure, years
    )


def interest_expenditure(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R49 = (PPG interest + domestic interest) × FX(pa)."""
    years = inputs.years
    return (
        _stocks.ppg_interest(inputs, external) + _stocks.domestic_interest(inputs)
    ) * _align(inputs.fx_pa, years)


def external_gfn(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R74 = -CA - FDI + ext amort + prior total ST."""
    years = inputs.years
    ca = _align(inputs.current_account, years)
    fdi = _align(inputs.fdi, years)
    amort = _stocks.external_amortization(inputs, external)
    st = _stocks.total_short_term_external(inputs, external)
    prior_st = st.shift(1).fillna(0.0)
    return (-ca - fdi + amort + prior_st).astype(float)


def private_financing_covered(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R75 = Δ private MLT + private amort + private ST."""
    private_mlt = _stocks.private_mlt_external(inputs)
    private_st = _stocks.private_st_external(inputs)
    delta_mlt = private_mlt - private_mlt.shift(1).fillna(0.0)
    amort = _stocks.private_amortization(inputs)
    return (delta_mlt + amort + private_st).astype(float)


def public_financing_covered(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R76 = external GFN − private covered."""
    return external_gfn(inputs, external) - private_financing_covered(inputs)


def residual_financing_gap(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R77 = R76 − R10 − Ext R122 (projection identity; hist may be blank)."""
    years = inputs.years
    gap = (
        public_financing_covered(inputs, external)
        - _stocks.short_term_external(inputs, external)
        - _stocks.new_public_external_mlt_disbursements(external, years)
    )
    # Excel only fills R77 from first projection year.
    out = gap.copy()
    for year in years:
        if year < inputs.first_projection_year:
            out.loc[year] = pd.NA
    return out.astype(float)


def public_external_debt_lcu(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R81 = PPG external × FX(eop)."""
    return _stocks.ppg_external(inputs, external) * _align(inputs.fx_eop, inputs.years)


def public_domestic_debt(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R82 = R14."""
    return _stocks.domestic_debt(inputs)


def total_public_debt(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R80 = R81 + R82."""
    return public_external_debt_lcu(inputs, external) + public_domestic_debt(inputs)


def interest_rate_external(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R86 = PPG interest / prior PPG external × 100."""
    interest = _stocks.ppg_interest(inputs, external)
    prior = pd.Series(_stocks.ppg_external(inputs, external).shift(1), dtype=float)
    return _safe_rate(interest, prior)


def interest_rate_domestic(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R87 = domestic interest / prior domestic × FX(pa) × 100."""
    years = inputs.years
    interest = _stocks.domestic_interest(inputs)
    prior = pd.Series(_stocks.domestic_debt(inputs).shift(1), dtype=float)
    fx = _align(inputs.fx_pa, years)
    out = 100.0 * interest / prior.replace(0.0, pd.NA) * fx
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def public_gfn(inputs: MacroDebtInputs, external: ExternalDebtBook | None) -> pd.Series:
    """Macro R101: hist identity; Input 5 R56 from first projection year."""
    years = inputs.years
    # Hist: -PB + (interest+dom amort+prior ST+ppg amort)*FX + prior dom ST
    #       + contingent + other - privatization - debt relief
    pb = primary_balance(inputs)
    interest_ppg = _stocks.ppg_interest(inputs, external)
    interest_dom = _stocks.domestic_interest(inputs)
    dom_amort = _stocks.domestic_amortization(inputs)
    ppg_amort = _stocks.ppg_amortization(inputs, external)
    prior_st = _stocks.short_term_external(inputs, external).shift(1).fillna(0.0)
    prior_dom_st = _stocks.domestic_st(inputs).shift(1).fillna(0.0)
    fx = _align(inputs.fx_pa, years)
    hist = (
        -pb
        + (interest_ppg + interest_dom + dom_amort + prior_st + ppg_amort) * fx
        + prior_dom_st
        + _align(inputs.contingent_liabilities, years)
        + _align(inputs.other_debt_creating_flows, years)
        - _align(inputs.privatization, years)
        - _align(inputs.debt_relief, years)
    )
    return _stocks.hist_proj(
        hist,
        inputs.public_gfn_input5,
        years,
        inputs.first_projection_year,
    )


def real_gdp_growth(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R107 = (GDP_const / prior − 1) × 100."""
    gdp = _align(inputs.gdp_constant, inputs.years)
    prior = pd.Series(gdp.shift(1), dtype=float)
    return _safe_rate(gdp - prior, prior)


def exchange_rate_dollar_per_nc(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R113 = 1 / FX(pa)."""
    fx = _align(inputs.fx_pa, inputs.years)
    return (1.0 / fx.replace(0.0, pd.NA)).fillna(0.0).astype(float)


def depreciation_of_nc(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R114 = -100 × (R113 / prior R113 − 1)."""
    rate = exchange_rate_dollar_per_nc(inputs)
    prior = pd.Series(rate.shift(1), dtype=float)
    return (-_safe_rate(rate - prior, prior)).astype(float)
