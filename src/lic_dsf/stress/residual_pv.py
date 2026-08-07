"""Residual-financing PV overlays (``PV Stress`` / ``PV_ResFin_pub``)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import pandas as pd

from lic_dsf.pv import PresentValueInstrument
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams


@dataclass(slots=True)
class ResFinOverlay:
    """PV / debt-service series for residual external MLT under stress."""

    pv: pd.Series
    interest: pd.Series
    amortization: pd.Series
    debt_service: pd.Series
    instrument: PresentValueInstrument


@dataclass(slots=True)
class ResidualFill:
    """Three-way residual financing disbursements (public DSA)."""

    external_mlt_usd: pd.Series
    domestic_mlt_lcu: pd.Series
    domestic_st_lcu: pd.Series


@dataclass(slots=True)
class DomMltOverlay:
    """Domestic MLT residual schedule in LCU (``PV_ResFin_pub`` R85–R91)."""

    stock: pd.Series
    interest: pd.Series
    amortization: pd.Series
    debt_service: pd.Series
    pv: pd.Series
    disbursements: pd.Series


@dataclass(slots=True)
class DomStOverlay:
    """Domestic ST residual rollover in LCU (``PV_ResFin_pub`` R98–R99)."""

    stock: pd.Series
    interest: pd.Series
    disbursements: pd.Series


@dataclass(slots=True)
class PublicResFinOverlay:
    """Bundled public residual financing overlays."""

    fill: ResidualFill
    ext: ResFinOverlay
    dom_mlt: DomMltOverlay
    dom_st: DomStOverlay


def external_dsa_residual_params(
    params: ResidualFinancingParams,
) -> ResidualFinancingParams:
    """Return Input 7 *external DSA* terms (100% external PPG MLT fill)."""
    return replace(
        params,
        external_mlt_share=1.0,
        domestic_mlt_share=0.0,
        domestic_st_share=0.0,
    )


def public_dsa_residual_params(
    params: ResidualFinancingParams,
) -> ResidualFinancingParams:
    """Return params for public DSA residual fill (keep J-column shares)."""
    return replace(params)


def resfin_instrument(
    gap: pd.Series,
    params: ResidualFinancingParams,
    *,
    discount_rate: float | None = None,
    years: tuple[int, ...],
    apply_share: bool = True,
) -> PresentValueInstrument:
    """Build a ``PresentValueInstrument`` for residual external MLT fill.

    Args:
        gap: Residual borrowing need by year (USD). When ``apply_share`` is
            True, disbursements are ``max(gap, 0) × external_mlt_share``;
            otherwise ``gap`` is treated as already-split ext MLT USD.
        params: Input 7 residual financing terms.
        discount_rate: DSA discount rate; defaults to ``params.discount_rate``.
        years: Calendar years aligned with ``gap``.
        apply_share: Whether to multiply by ``external_mlt_share``.

    Returns:
        Instrument whose ``external()`` block mirrors a PV Stress / ResFin loan.
    """
    year_list = list(years)
    aligned = gap.reindex(year_list).fillna(0.0).astype(float)
    share = params.external_mlt_share if apply_share else 1.0
    disbursements = [max(float(aligned.loc[y]), 0.0) * share for y in year_list]
    grace = max(int(params.avg_grace_rounded), 0)
    maturity = max(int(params.avg_maturity_rounded), grace + 1)
    rate = (
        float(discount_rate)
        if discount_rate is not None
        else float(params.discount_rate)
    )
    return PresentValueInstrument(
        name="ResFin",
        grace=grace,
        maturity=maturity,
        interest_rate=float(params.avg_interest_rate) / 100.0,
        discount_rate=rate,
        disbursements=disbursements,
        years=year_list,
    )


def resfin_overlay_series(
    instrument: PresentValueInstrument,
    years: tuple[int, ...],
) -> ResFinOverlay:
    """Extract PV / interest / amortization overlays aligned to ``years``."""
    external = instrument.external()
    pv_key = f"PV of debt   {instrument.name}"
    year_list = list(years)

    def _row(name: str) -> pd.Series:
        if name not in external.index:
            return pd.Series(0.0, index=year_list, dtype=float)
        values = {}
        for year in year_list:
            if year in external.columns:
                values[year] = float(external.loc[name, year])
            else:
                values[year] = 0.0
        return pd.Series(values, dtype=float)

    interest = _row("Interest")
    amortization = _row("Amortization")
    debt_service = _row("Total debt service (in USD)")
    if debt_service.sum() == 0.0:
        debt_service = (interest + amortization).astype(float)
    return ResFinOverlay(
        pv=_row(pv_key),
        interest=interest,
        amortization=amortization,
        debt_service=debt_service,
        instrument=instrument,
    )


def flow_shortfall_gap(
    baseline: pd.Series,
    shocked: pd.Series,
    years: tuple[int, ...],
) -> pd.Series:
    """``max(0, baseline − shocked)`` financing gap from a flow shortfall."""
    base = baseline.reindex(list(years)).fillna(0.0).astype(float)
    shock = shocked.reindex(list(years)).fillna(0.0).astype(float)
    return (base - shock).clip(lower=0.0).astype(float)


def public_residual_gap(
    stressed_gfn_lcu: pd.Series,
    baseline_gfn_lcu: pd.Series,
    years: tuple[int, ...] | None = None,
) -> pd.Series:
    """Public DSA residual gap: stressed GFN − baseline GFN (LCU).

    Mirrors ``PV_ResFin_pub`` B1 ``R67`` = ``B*_pub!R90 − Baseline - public!R78``.
    """
    if years is None:
        years = tuple(sorted(set(stressed_gfn_lcu.index).union(baseline_gfn_lcu.index)))
    stress = stressed_gfn_lcu.reindex(list(years)).fillna(0.0).astype(float)
    base = baseline_gfn_lcu.reindex(list(years)).fillna(0.0).astype(float)
    return (stress - base).astype(float)


def external_residual_gap(
    baseline_stock_usd: pd.Series,
    stressed_stock_usd: pd.Series,
    years: tuple[int, ...] | None = None,
) -> pd.Series:
    """External DSA residual gap: Δstressed stock − Δbaseline stock (USD).

    Mirrors ``B*_ext!R86`` = ``R85 − R83``.
    """
    if years is None:
        years = tuple(
            sorted(set(baseline_stock_usd.index).union(stressed_stock_usd.index))
        )
    year_list = list(years)
    base = baseline_stock_usd.reindex(year_list).fillna(0.0).astype(float)
    stress = stressed_stock_usd.reindex(year_list).fillna(0.0).astype(float)
    d_base = base.diff().fillna(0.0)
    d_stress = stress.diff().fillna(0.0)
    return (d_stress - d_base).astype(float)


def stressed_external_stock_from_shortfall(
    baseline_stock_usd: pd.Series,
    flow_shortfall_usd: pd.Series,
    years: tuple[int, ...],
) -> pd.Series:
    """Approximate stressed PPG stock as baseline + cumulative flow shortfall.

    Matches B3 year-1 identity when the residual equals the export shortfall;
    later years may diverge from full B-sheet debt dynamics.
    """
    year_list = list(years)
    base = baseline_stock_usd.reindex(year_list).fillna(0.0).astype(float)
    shortfall = flow_shortfall_usd.reindex(year_list).fillna(0.0).astype(float)
    return (base + shortfall.cumsum()).astype(float)


def split_residual_financing(
    public_gap_lcu: pd.Series,
    ext_r86_usd: pd.Series,
    params: ResidualFinancingParams,
    fx_pa: pd.Series,
    *,
    modality: Literal["capped", "absolute"] = "capped",
    years: tuple[int, ...] | None = None,
) -> ResidualFill:
    """Split public residual gap into ext MLT / dom MLT / ST.

    Args:
        public_gap_lcu: Public ΔGFN (LCU).
        ext_r86_usd: External DSA residual gross borrowing (USD).
        params: Public Input 7 shares (J9–J11).
        fx_pa: Period-average FX (LCU per USD).
        modality: ``capped`` (B1/B5/B6) or ``absolute`` (B2 PB).
        years: Optional year horizon.

    Returns:
        Disbursement series for the three residual legs.
    """
    if years is None:
        years = tuple(sorted(set(public_gap_lcu.index).union(ext_r86_usd.index)))
    year_list = list(years)
    gap = public_gap_lcu.reindex(year_list).fillna(0.0).astype(float)
    ext86 = ext_r86_usd.reindex(year_list).fillna(0.0).astype(float)
    fx = (
        fx_pa.reindex(year_list)
        .fillna(1.0)
        .astype(float)
        .replace(0.0, pd.NA)
        .fillna(1.0)
    )

    j9 = float(params.external_mlt_share)
    j10 = float(params.domestic_mlt_share)
    j11 = float(params.domestic_st_share)
    dom_share_sum = j10 + j11
    if dom_share_sum <= 0.0:
        dom_share_sum = 1.0

    ext_usd: dict[int, float] = {}
    dom_mlt: dict[int, float] = {}
    dom_st: dict[int, float] = {}

    for year in year_list:
        g = float(gap.loc[year])
        fx_y = float(fx.loc[year])
        r86 = float(ext86.loc[year])
        if g <= 0.0 and modality == "capped":
            # Negative / zero public gap: no additional public residual fill.
            ext_usd[year] = 0.0
            dom_mlt[year] = 0.0
            dom_st[year] = 0.0
            continue

        if modality == "absolute":
            ext_usd[year] = max(g, 0.0) * j9 / fx_y
            dom_mlt[year] = max(g, 0.0) * j10
            dom_st[year] = max(g, 0.0) * j11
            continue

        # Capped (B1/B5/B6): modality 1 if external residual exceeds public
        # share × gap / FX; else modality 2 share split.
        threshold = (g * j9 / fx_y) if fx_y else 0.0
        if r86 > threshold >= 0.0:
            # Modality 1: cover with external up to public gap / FX.
            ext_usd[year] = max(g, 0.0) / fx_y if fx_y else 0.0
            dom_mlt[year] = 0.0
            dom_st[year] = 0.0
        else:
            # Modality 2.
            ext_u = max(g, 0.0) * j9 / fx_y if fx_y else 0.0
            remainder = max(g - ext_u * fx_y, 0.0)
            ext_usd[year] = ext_u
            dom_mlt[year] = remainder * j10 / dom_share_sum
            dom_st[year] = remainder * j11 / dom_share_sum

    return ResidualFill(
        external_mlt_usd=pd.Series(ext_usd, dtype=float),
        domestic_mlt_lcu=pd.Series(dom_mlt, dtype=float),
        domestic_st_lcu=pd.Series(dom_st, dtype=float),
    )


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).fillna(0.0).astype(float)


def dom_mlt_resfin_series(
    disbursements_lcu: pd.Series,
    *,
    real_rate: float,
    grace: int,
    maturity: int,
    deflator: pd.Series,
    years: tuple[int, ...],
    discount_rate: float = 0.05,
) -> DomMltOverlay:
    """Domestic MLT residual schedule in LCU (``PV_ResFin_pub`` R85–R91).

    Interest uses ``real_rate + deflator`` each year. When the nominal rate is
    at or above ``discount_rate``, PV tracks face stock (same rule as Ext
    ResFin when i ≥ d).
    """
    year_list = list(years)
    disb = _align(disbursements_lcu, years)
    defl = _align(deflator, years)
    grace = max(int(grace), 0)
    maturity = max(int(maturity), grace + 1)
    span = float(maturity - grace)

    amort = pd.Series(0.0, index=year_list, dtype=float)
    # Cohort amortization: each disbursement amortizes evenly after grace.
    for i, year in enumerate(year_list):
        amount = float(disb.loc[year])
        if amount <= 0.0:
            continue
        for j in range(grace, maturity):
            target_i = i + j
            if target_i >= len(year_list):
                break
            amort.loc[year_list[target_i]] += amount / span

    stock = pd.Series(0.0, index=year_list, dtype=float)
    interest = pd.Series(0.0, index=year_list, dtype=float)
    for i, year in enumerate(year_list):
        if i == 0:
            stock.loc[year] = float(disb.loc[year]) - float(amort.loc[year])
            interest.loc[year] = 0.0
        else:
            prior = year_list[i - 1]
            stock.loc[year] = (
                float(stock.loc[prior]) + float(disb.loc[year]) - float(amort.loc[year])
            )
            nom_rate = float(real_rate) + float(defl.loc[year])
            interest.loc[year] = float(stock.loc[prior]) * nom_rate

    debt_service = (interest + amort).astype(float)
    pv = pd.Series(0.0, index=year_list, dtype=float)
    for i, year in enumerate(year_list):
        nom_rate = float(real_rate) + float(defl.loc[year])
        if nom_rate >= discount_rate:
            if i == 0:
                pv.loc[year] = float(disb.loc[year])
            else:
                pv.loc[year] = (
                    float(pv.loc[year_list[i - 1]])
                    - float(amort.loc[year])
                    + float(disb.loc[year])
                )
        else:
            # Simple face approximation when concessional; unit NPV not needed
            # for public overlay first cut.
            if i == 0:
                pv.loc[year] = float(disb.loc[year])
            else:
                pv.loc[year] = (
                    float(pv.loc[year_list[i - 1]]) * (1.0 + discount_rate)
                    - float(debt_service.loc[year])
                    + float(disb.loc[year])
                )

    return DomMltOverlay(
        stock=stock.astype(float),
        interest=interest.astype(float),
        amortization=amort.astype(float),
        debt_service=debt_service,
        pv=pv.astype(float),
        disbursements=disb,
    )


def dom_st_resfin_series(
    disbursements_lcu: pd.Series,
    *,
    real_rate: float,
    deflator: pd.Series,
    years: tuple[int, ...],
) -> DomStOverlay:
    """Domestic ST residual rollover (stock = disbursement; interest on prior)."""
    year_list = list(years)
    disb = _align(disbursements_lcu, years)
    defl = _align(deflator, years)
    stock = disb.copy()
    interest = pd.Series(0.0, index=year_list, dtype=float)
    for i, year in enumerate(year_list):
        if i == 0:
            interest.loc[year] = 0.0
        else:
            prior = year_list[i - 1]
            nom_rate = float(real_rate) + float(defl.loc[year])
            interest.loc[year] = float(stock.loc[prior]) * nom_rate
    return DomStOverlay(
        stock=stock.astype(float),
        interest=interest.astype(float),
        disbursements=disb,
    )


def build_public_resfin_overlay(
    fill: ResidualFill,
    params: ResidualFinancingParams,
    *,
    deflator: pd.Series,
    years: tuple[int, ...],
) -> PublicResFinOverlay:
    """Build ext MLT + dom MLT + dom ST overlays from a residual fill."""
    instrument = resfin_instrument(
        fill.external_mlt_usd,
        params,
        years=years,
        apply_share=False,
    )
    ext = resfin_overlay_series(instrument, years)
    dom_mlt = dom_mlt_resfin_series(
        fill.domestic_mlt_lcu,
        real_rate=params.domestic_mlt_real_rate,
        grace=params.domestic_mlt_grace,
        maturity=params.domestic_mlt_maturity,
        deflator=deflator,
        years=years,
        discount_rate=params.discount_rate,
    )
    dom_st = dom_st_resfin_series(
        fill.domestic_st_lcu,
        real_rate=params.domestic_st_real_rate,
        deflator=deflator,
        years=years,
    )
    return PublicResFinOverlay(fill=fill, ext=ext, dom_mlt=dom_mlt, dom_st=dom_st)


def gdp_deflator_growth(gdp_usd: pd.Series, gdp_constant: pd.Series) -> pd.Series:
    """GDP deflator growth rate (decimal) from USD / constant GDP paths."""
    years = tuple(gdp_usd.index)
    usd = gdp_usd.reindex(list(years)).astype(float)
    const = gdp_constant.reindex(list(years)).astype(float)
    idx = usd / const.replace(0.0, pd.NA)
    growth = idx / idx.shift(1) - 1.0
    return growth.fillna(0.0).astype(float)
