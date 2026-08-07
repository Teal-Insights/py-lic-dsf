"""Hist / projection debt stock and service stitch for Macro-Debt_Data."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.types import MacroDebtInputs


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).fillna(0.0).astype(float)


def hist_proj(
    hist: pd.Series,
    proj: pd.Series,
    years: tuple[int, ...],
    first_projection_year: int,
) -> pd.Series:
    """Use ``hist`` before first projection year, ``proj`` from then on."""
    hist_a = _align(hist, years)
    proj_a = _align(proj, years)
    out = hist_a.copy()
    for year in years:
        if year >= first_projection_year:
            out.loc[year] = float(proj_a.loc[year])
    return out.astype(float)


def mlt_external(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R9: Input 3 hist; Ext R67+R65+R329 in projection."""
    if external is None:
        return _align(inputs.mlt_external, inputs.years)
    years = list(external.inputs.years)
    proj = (
        external.existing_mlt_nominal().reindex(years).fillna(0.0)
        + external.inputs.arrears.reindex(years).fillna(0.0)
        + external.new_mlt_nominal().reindex(years).fillna(0.0)
    )
    return hist_proj(
        inputs.mlt_external, proj, inputs.years, inputs.first_projection_year
    )


def short_term_external(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R10: Input 3 hist; Ext R386 in projection."""
    if external is None:
        return _align(inputs.short_term_external, inputs.years)
    proj = external.total_st_external()
    return hist_proj(
        inputs.short_term_external, proj, inputs.years, inputs.first_projection_year
    )


def private_mlt_external(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R12 (Input 3 through horizon)."""
    return _align(inputs.private_mlt_external, inputs.years)


def private_st_external(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R13 (Input 3 through horizon)."""
    return _align(inputs.private_st_external, inputs.years)


def ppg_external(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R8 = R9 + R10."""
    return mlt_external(inputs, external) + short_term_external(inputs, external)


def private_external(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R11 = R12 + R13."""
    return private_mlt_external(inputs) + private_st_external(inputs)


def total_external(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R6 = R8 + R11."""
    return ppg_external(inputs, external) + private_external(inputs)


def total_mlt(inputs: MacroDebtInputs, external: ExternalDebtBook | None) -> pd.Series:
    """Macro R7 = R12 + R9."""
    return private_mlt_external(inputs) + mlt_external(inputs, external)


def domestic_mlt(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R15: Input 3 hist; Input 5 R212 in projection."""
    return hist_proj(
        inputs.domestic_mlt,
        inputs.domestic_mlt_input5,
        inputs.years,
        inputs.first_projection_year,
    )


def domestic_st(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R16: Input 3 hist; Input 5 R213 in projection."""
    return hist_proj(
        inputs.domestic_st,
        inputs.domestic_st_input5,
        inputs.years,
        inputs.first_projection_year,
    )


def domestic_debt(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R14 = R15 + R16."""
    return domestic_mlt(inputs) + domestic_st(inputs)


def ppg_interest(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R19: Input 3 hist; Ext R396 in projection."""
    if external is None:
        return _align(inputs.ppg_interest, inputs.years)
    proj = external.total_public_debt_service().loc["    of which: interest"]
    return hist_proj(
        inputs.ppg_interest, proj, inputs.years, inputs.first_projection_year
    )


def private_interest(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R20 (Input 3)."""
    return _align(inputs.private_interest, inputs.years)


def domestic_interest(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R21: Input 3 interest / FX(pa) hist; Input 5 LCU / FX in projection."""
    years = inputs.years
    fx = _align(inputs.fx_pa, years)
    hist = _align(inputs.domestic_interest, years) / fx.replace(0.0, pd.NA)
    hist = hist.fillna(0.0)
    interest_lcu = _align(inputs.domestic_interest_lcu_input5, years)
    proj = interest_lcu / fx.replace(0.0, pd.NA)
    proj = proj.fillna(0.0)
    return hist_proj(hist, proj, years, inputs.first_projection_year)


def domestic_amortization(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R26: Input 3 amort / FX hist; ``(I215 - prior R16) / FX`` in projection."""
    years = inputs.years
    fx = _align(inputs.fx_pa, years)
    hist = _align(inputs.domestic_amortization, years) / fx.replace(0.0, pd.NA)
    hist = hist.fillna(0.0)
    principal_lcu = _align(inputs.domestic_principal_lcu_input5, years)
    dom_st = domestic_st(inputs)
    prior_st = dom_st.shift(1).fillna(0.0)
    proj = (principal_lcu - prior_st) / fx.replace(0.0, pd.NA)
    proj = proj.fillna(0.0)
    return hist_proj(hist, proj, years, inputs.first_projection_year)


def external_interest(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R18 = R19 + R20."""
    return ppg_interest(inputs, external) + private_interest(inputs)


def ppg_amortization(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R24: Input 3 hist; Ext R395 in projection."""
    if external is None:
        return _align(inputs.ppg_amortization, inputs.years)
    proj = external.total_public_debt_service().loc["    of which: principal"]
    return hist_proj(
        inputs.ppg_amortization, proj, inputs.years, inputs.first_projection_year
    )


def private_amortization(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R25 (Input 3)."""
    return _align(inputs.private_amortization, inputs.years)


def external_amortization(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R23 = R24 + R25."""
    return ppg_amortization(inputs, external) + private_amortization(inputs)


def total_short_term_external(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R89 = R10 + R13."""
    return short_term_external(inputs, external) + private_st_external(inputs)


def pv_external_lcu(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R92: Ext R391 × FX(eop); 0 without Ext."""
    years = inputs.years
    fx = _align(inputs.fx_eop, years)
    if external is None:
        return pd.Series(0.0, index=list(years), dtype=float)
    pv = external.total_pv_of_debt()
    # Excel uses Ext for all years on R92 (including hist). Prefer Ext where
    # available; fall back to 0 outside Ext horizon.
    return _align(pv, years) * fx


def grant_element_percent(
    inputs: MacroDebtInputs, external: ExternalDebtBook | None
) -> pd.Series:
    """Macro R90 projection: Ext R408; hist blank/ellipsis → 0."""
    years = inputs.years
    if external is None:
        return pd.Series(0.0, index=list(years), dtype=float)
    ge = external.grant_element_percent()
    return hist_proj(
        pd.Series(0.0, index=list(years), dtype=float),
        ge,
        years,
        inputs.first_projection_year,
    )


def new_public_external_mlt_disbursements(
    external: ExternalDebtBook | None,
    years: tuple[int, ...],
) -> pd.Series:
    """Ext R122 — total new public external MLT disbursements."""
    if external is None:
        return pd.Series(0.0, index=list(years), dtype=float)
    borrowing = external.portfolio.aggregate_external().loc[
        "New forex borrowing (gross, USD)"
    ]
    return _align(borrowing, years)
