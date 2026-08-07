"""Public stress DSA with three-way residual financing (``PV_ResFin_pub``)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.residual_pv import (
    PublicResFinOverlay,
    ResidualFill,
    build_public_resfin_overlay,
    gdp_deflator_growth,
    public_residual_gap,
    split_residual_financing,
)
from lic_dsf.stress.shocks import apply_real_gdp_shock
from lic_dsf.stress.types import Input6StandardParams


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def _zero_fill(years: tuple[int, ...]) -> ResidualFill:
    z = pd.Series(0.0, index=list(years), dtype=float)
    return ResidualFill(
        external_mlt_usd=z.copy(),
        domestic_mlt_lcu=z.copy(),
        domestic_st_lcu=z.copy(),
    )


def estimate_b1_public_gfn(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay | None = None,
) -> pd.Series:
    """Estimate B1_GDP_pub R90-style public GFN (LCU).

    First-order term scales baseline GFN by the inverse GDP ratio (financing
    need rises when GDP falls). Residual-financing interest / ST from a prior
    iteration are added when ``resfin`` is provided.
    """
    years = shocked_macro.inputs.years
    base_gfn = _align(baseline_macro.public_gfn(), years).fillna(0.0)
    base_gdp = _align(baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
    shock_gdp = _align(shocked_macro.gdp_lcu(), years).replace(0.0, pd.NA)
    gfn = (base_gfn * base_gdp / shock_gdp).fillna(base_gfn).astype(float)

    if resfin is None:
        return gfn

    fx = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    first = shocked_macro.inputs.first_projection_year
    extra = pd.Series(0.0, index=list(years), dtype=float)
    for year in years:
        if year < first:
            continue
        # ResFin domestic interest + ST interest + ext interest×FX + amort×FX
        # + prior ST stock (feeds next-year GFN like B1 R81).
        extra.loc[year] = (
            float(resfin.dom_mlt.interest.reindex([year]).fillna(0.0).loc[year])
            + float(resfin.dom_st.interest.reindex([year]).fillna(0.0).loc[year])
            + float(resfin.ext.interest.reindex([year]).fillna(0.0).loc[year])
            * float(fx.loc[year])
            + float(resfin.ext.amortization.reindex([year]).fillna(0.0).loc[year])
            * float(fx.loc[year])
            + float(resfin.dom_mlt.amortization.reindex([year]).fillna(0.0).loc[year])
        )
    # Prior-year ResFin ST enters GFN (B1 R90 uses prior R81).
    prior_st = resfin.dom_st.stock.shift(1).fillna(0.0)
    for year in years:
        if year < first:
            continue
        extra.loc[year] = float(extra.loc[year]) + float(
            prior_st.reindex([year]).fillna(0.0).loc[year]
        )
    return (gfn + extra).astype(float)


@dataclass(slots=True)
class StressPublicBook:
    """Public DSA ratios under stress with three-way ResFin overlays."""

    macro: MacroDebtBook
    external: ExternalDebtBook
    baseline_macro: MacroDebtBook
    resfin: PublicResFinOverlay
    scenario_id: str = "B1_GDP_pub"

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked Macro book."""
        return self.macro.inputs.years

    def gdp_lcu(self) -> pd.Series:
        """Shocked GDP in LCU."""
        return self.macro.gdp_lcu()

    def _resfin_external_lcu(self) -> pd.Series:
        fx = self.macro.fx_pa()
        return _align(self.resfin.ext.pv, self.years).fillna(0.0) * _align(
            fx, self.years
        ).fillna(1.0)

    def _resfin_domestic_debt(self) -> pd.Series:
        return _align(self.resfin.dom_mlt.stock, self.years).fillna(0.0) + _align(
            self.resfin.dom_st.stock, self.years
        ).fillna(0.0)

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Public debt / GDP including ResFin stocks."""
        numer = (
            self.macro.total_public_debt()
            + self._resfin_external_lcu()
            + self._resfin_domestic_debt()
        )
        return _pct(numer, self.gdp_lcu())

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """PV of public debt / GDP including ResFin PV."""
        numer = (
            self.macro.pv_external_lcu()
            + self.macro.public_domestic_debt()
            + self._resfin_external_lcu()
            + _align(self.resfin.dom_mlt.pv, self.years).fillna(0.0)
            + _align(self.resfin.dom_st.stock, self.years).fillna(0.0)
        )
        return _clamp_nonnegative(_pct(numer, self.gdp_lcu()))

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Debt service / revenue+grants including ResFin service."""
        fx = self.macro.fx_pa()
        prior_dom_st = pd.Series(self.macro.domestic_st().shift(1), dtype=float).fillna(
            0.0
        )
        prior_resfin_st = (
            _align(self.resfin.dom_st.stock, self.years).shift(1).fillna(0.0)
        )
        numer = (
            self.macro.interest_expenditure()
            + prior_dom_st
            + prior_resfin_st
            + (self.macro.domestic_amortization() + self.macro.ppg_amortization()) * fx
            + _align(self.resfin.dom_mlt.interest, self.years).fillna(0.0)
            + _align(self.resfin.dom_st.interest, self.years).fillna(0.0)
            + _align(self.resfin.dom_mlt.amortization, self.years).fillna(0.0)
            + _align(self.resfin.ext.interest, self.years).fillna(0.0) * fx
            + _align(self.resfin.ext.amortization, self.years).fillna(0.0) * fx
        )
        return _clamp_nonnegative(_pct(numer, self.macro.revenues_incl_grants()))

    def public_gfn(self) -> pd.Series:
        """Stressed public GFN estimate (LCU)."""
        return estimate_b1_public_gfn(self.baseline_macro, self.macro, self.resfin)


def run_b1_gdp_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    iterations: int = 4,
    public_gap: pd.Series | None = None,
    ext_r86: pd.Series | None = None,
) -> StressPublicBook:
    """Run B1 real-GDP public stress with three-way residual financing.

    Args:
        macro: Baseline Macro book.
        external: Baseline Ext book.
        input6: Input 6 standard shock params.
        residual_params: Input 7 value-used params (public J shares + terms).
        iterations: Fixed-point iterations for GFN ↔ ResFin feedback.
        public_gap: Optional precomputed public ΔGFN (LCU); skips estimation.
        ext_r86: Optional external residual gap (USD); defaults to zeros (B1).

    Returns:
        ``StressPublicBook`` with ResFin fill and overlays.
    """
    shocked_inputs = apply_real_gdp_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    years = shocked_macro.inputs.years
    r86 = (
        ext_r86.reindex(list(years)).fillna(0.0).astype(float)
        if ext_r86 is not None
        else pd.Series(0.0, index=list(years), dtype=float)
    )
    deflator = gdp_deflator_growth(
        shocked_macro.inputs.gdp_usd, shocked_macro.inputs.gdp_constant
    )
    fx = shocked_macro.fx_pa()

    if public_gap is not None:
        gap = public_gap.reindex(list(years)).fillna(0.0).astype(float)
        fill = split_residual_financing(
            gap, r86, residual_params, fx, modality="capped", years=years
        )
        overlay = build_public_resfin_overlay(
            fill, residual_params, deflator=deflator, years=years
        )
        return StressPublicBook(
            macro=shocked_macro,
            external=external,
            baseline_macro=macro,
            resfin=overlay,
            scenario_id="B1_GDP_pub",
        )

    overlay: PublicResFinOverlay | None = None
    fill = _zero_fill(years)
    for _ in range(max(iterations, 1)):
        stressed_gfn = estimate_b1_public_gfn(macro, shocked_macro, overlay)
        gap = public_residual_gap(stressed_gfn, macro.public_gfn(), years)
        # Zero gap before first projection year.
        for year in years:
            if year < shocked_macro.inputs.first_projection_year:
                gap.loc[year] = 0.0
        fill = split_residual_financing(
            gap, r86, residual_params, fx, modality="capped", years=years
        )
        overlay = build_public_resfin_overlay(
            fill, residual_params, deflator=deflator, years=years
        )

    assert overlay is not None
    return StressPublicBook(
        macro=shocked_macro,
        external=external,
        baseline_macro=macro,
        resfin=overlay,
        scenario_id="B1_GDP_pub",
    )


def stress_public_panel(book: StressPublicBook) -> pd.DataFrame:
    """Output 1-2-shaped public stress sustainability rows."""
    return pd.DataFrame(
        {
            "Public sector debt / GDP": book.public_sector_debt_to_gdp(),
            "PV of public debt / GDP": book.pv_public_debt_to_gdp(),
            "Debt service / revenue+grants": book.debt_service_to_revenue_grants(),
            "Public GFN (LCU)": book.public_gfn(),
        }
    ).T
