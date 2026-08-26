"""Public stress DSA with three-way residual financing (``PV_ResFin_pub``)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.residual_pv import (
    PublicResFinOverlay,
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


def _inflation_elasticity(input6: Input6StandardParams) -> float:
    if not input6.interactions_on:
        return 0.0
    return float(input6.inflation_elasticity)


def _growth_pct(level: pd.Series) -> pd.Series:
    prior = pd.Series(level.shift(1), dtype=float)
    return (100.0 * (level / prior.replace(0.0, pd.NA) - 1.0)).astype(float)


def _b1_public_gdp_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    inflation_elasticity: float,
) -> pd.Series:
    """B1_GDP_pub R41: LCU GDP compounded with shocked real × LCU deflator.

    Differs from ``gdp_usd × FX(pa)``: Excel applies the inflation elasticity
    to the LCU deflator (Macro R109) and compounds in LCU, not USD.
    """
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    base_lcu = _align(baseline_macro.gdp_lcu(), years)
    base_const = _align(baseline_macro.gdp_constant(), years).replace(0.0, pd.NA)
    shock_const = _align(shocked_macro.gdp_constant(), years).replace(0.0, pd.NA)
    real_s = _growth_pct(shock_const)
    real_b = _growth_pct(base_const)
    defl_b = _growth_pct(base_lcu / base_const)
    defl_s = defl_b - (real_b - real_s) * inflation_elasticity
    out = base_lcu.copy()
    for year in years:
        if year <= first:
            continue
        prior = year - 1
        if prior not in out.index:
            continue
        rg = float(real_s.loc[year]) if pd.notna(real_s.loc[year]) else 0.0
        dg = float(defl_s.loc[year]) if pd.notna(defl_s.loc[year]) else 0.0
        out.loc[year] = float(out.loc[prior]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
    return out.astype(float)


def _b1_other_identified_flows_lcu(baseline_macro: MacroDebtBook) -> pd.Series:
    """B1 R89: other identified debt-creating flows at baseline LCU.

    Matches Baseline R33/100 × GDP_LCU: contingent + other flows −
    privatization − debt relief.
    """
    years = baseline_macro.inputs.years
    return (
        _align(baseline_macro.inputs.contingent_liabilities, years).fillna(0.0)
        + _align(baseline_macro.inputs.other_debt_creating_flows, years).fillna(0.0)
        - _align(baseline_macro.inputs.privatization, years).fillna(0.0)
        - _align(baseline_macro.inputs.debt_relief, years).fillna(0.0)
    )


def _b1_primary_deficit_lcu(
    baseline_macro: MacroDebtBook,
    shocked_gdp_lcu: pd.Series,
) -> pd.Series:
    """B1 R88: primary deficit LCU under a real-GDP shock.

    Primary expenditure and grants stay at baseline LCU. Non-grant revenue
    scales with shocked GDP (B1 holds rev/GDP from the first shock year).
    """
    years = baseline_macro.inputs.years
    gdp_s = _align(shocked_gdp_lcu, years).replace(0.0, pd.NA)
    gdp_b = _align(baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
    prim_exp = _align(baseline_macro.inputs.primary_expenditure, years).fillna(0.0)
    grants = _align(baseline_macro.grants(), years).fillna(0.0)
    rev_excl = _align(baseline_macro.revenues_incl_grants(), years).fillna(0.0) - grants
    return (prim_exp - rev_excl * (gdp_s / gdp_b) - grants).astype(float)


def estimate_b1_public_gfn(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay | None = None,
    *,
    inflation_elasticity: float = 0.0,
    gdp_lcu: pd.Series | None = None,
) -> pd.Series:
    """B1_GDP_pub R90 public GFN (LCU).

    Identity: primary deficit + existing interest + existing amort + prior
    domestic ST + other identified flows. Debt service is not scaled with
    GDP. Residual-financing service and prior ResFin ST are added when
    ``resfin`` is provided (R84–R87 / prior R81).

    Args:
        baseline_macro: Unshocked Macro book (fiscal LCU and baseline GFN).
        shocked_macro: B1-shocked Macro book (existing debt service).
        resfin: Public ResFin overlay from a prior iteration, if any.
        inflation_elasticity: Input 6 elasticity applied to the LCU deflator
            when reconstructing B1 R41 (0 when interactions are off).
        gdp_lcu: Optional precomputed B1 R41 path; computed from the books
            when omitted.
    """
    years = shocked_macro.inputs.years
    shocked_gdp = (
        gdp_lcu
        if gdp_lcu is not None
        else _b1_public_gdp_lcu(baseline_macro, shocked_macro, inflation_elasticity)
    )
    fx = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    interest = _align(shocked_macro.interest_expenditure(), years).fillna(0.0)
    amort = (
        _align(shocked_macro.ppg_amortization(), years).fillna(0.0)
        + _align(shocked_macro.domestic_amortization(), years).fillna(0.0)
    ) * fx
    prior_st = _align(shocked_macro.domestic_st(), years).shift(1).fillna(0.0)
    gfn = (
        _b1_primary_deficit_lcu(baseline_macro, shocked_gdp)
        + interest
        + amort
        + prior_st
        + _b1_other_identified_flows_lcu(baseline_macro)
    ).astype(float)

    if resfin is None:
        return gfn

    first = shocked_macro.inputs.first_projection_year
    extra = pd.Series(0.0, index=list(years), dtype=float)
    for year in years:
        if year < first:
            continue
        extra.loc[year] = (
            float(resfin.dom_mlt.interest.reindex([year]).fillna(0.0).loc[year])
            + float(resfin.dom_st.interest.reindex([year]).fillna(0.0).loc[year])
            + float(resfin.ext.interest.reindex([year]).fillna(0.0).loc[year])
            * float(fx.loc[year])
            + float(resfin.ext.amortization.reindex([year]).fillna(0.0).loc[year])
            * float(fx.loc[year])
            + float(resfin.dom_mlt.amortization.reindex([year]).fillna(0.0).loc[year])
        )
    prior_resfin_st = resfin.dom_st.stock.shift(1).fillna(0.0)
    for year in years:
        if year < first:
            continue
        extra.loc[year] = float(extra.loc[year]) + float(
            prior_resfin_st.reindex([year]).fillna(0.0).loc[year]
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
    inflation_elasticity: float = 0.0

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked Macro book."""
        return self.macro.inputs.years

    def gdp_lcu(self) -> pd.Series:
        """B1 R41 shocked GDP in LCU (real × LCU deflator compounding)."""
        return _b1_public_gdp_lcu(
            self.baseline_macro, self.macro, self.inflation_elasticity
        )

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

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """PV of public debt / revenue+grants (Output 3-2 middle block).

        B1 holds fiscal ratios as percent of GDP, so the revenue/GDP
        denominator is the baseline path. Do not divide unshocked LCU
        revenue by shocked GDP.
        """
        base_rev_to_gdp = _pct(
            self.baseline_macro.revenues_incl_grants(),
            self.baseline_macro.gdp_lcu(),
        )
        return (
            self.pv_public_debt_to_gdp() / base_rev_to_gdp.replace(0.0, pd.NA) * 100.0
        ).astype(float)

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
        """B1 R90 public GFN (LCU)."""
        return estimate_b1_public_gfn(
            self.baseline_macro,
            self.macro,
            self.resfin,
            inflation_elasticity=self.inflation_elasticity,
        )

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP including ResFin service."""
        rev_to_gdp = _pct(
            self.baseline_macro.revenues_incl_grants(),
            self.baseline_macro.gdp_lcu(),
        )
        return (self.debt_service_to_revenue_grants() * rev_to_gdp / 100.0).astype(
            float
        )


def _run_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    shocked_macro: MacroDebtBook,
    scenario_id: str,
    *,
    inflation_elasticity: float = 0.0,
    iterations: int = 25,
    tol: float = 1e-6,
    public_gap: pd.Series | None = None,
    ext_r86: pd.Series | None = None,
) -> StressPublicBook:
    """Shocked Macro + three-way public ResFin fixed point."""
    years = shocked_macro.inputs.years
    shocked_gdp_lcu = _b1_public_gdp_lcu(macro, shocked_macro, inflation_elasticity)
    r86 = (
        ext_r86.reindex(list(years)).fillna(0.0).astype(float)
        if ext_r86 is not None
        else pd.Series(0.0, index=list(years), dtype=float)
    )
    deflator = gdp_deflator_growth(macro.gdp_lcu(), macro.gdp_constant())
    fx = shocked_macro.fx_pa()
    baseline_gfn = macro.public_gfn()

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
            scenario_id=scenario_id,
            inflation_elasticity=inflation_elasticity,
        )

    overlay: PublicResFinOverlay | None = None
    prev_gap: pd.Series | None = None
    for _ in range(max(iterations, 1)):
        stressed_gfn = estimate_b1_public_gfn(
            macro,
            shocked_macro,
            overlay,
            inflation_elasticity=inflation_elasticity,
            gdp_lcu=shocked_gdp_lcu,
        )
        gap = public_residual_gap(stressed_gfn, baseline_gfn, years)
        for year in years:
            if year < shocked_macro.inputs.first_projection_year:
                gap.loc[year] = 0.0
        fill = split_residual_financing(
            gap, r86, residual_params, fx, modality="capped", years=years
        )
        overlay = build_public_resfin_overlay(
            fill, residual_params, deflator=deflator, years=years
        )
        if prev_gap is not None and float((gap - prev_gap).abs().max()) < tol:
            break
        prev_gap = gap

    assert overlay is not None
    return StressPublicBook(
        macro=shocked_macro,
        external=external,
        baseline_macro=macro,
        resfin=overlay,
        scenario_id=scenario_id,
        inflation_elasticity=inflation_elasticity,
    )


def run_b1_gdp_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    iterations: int = 25,
    tol: float = 1e-6,
    public_gap: pd.Series | None = None,
    ext_r86: pd.Series | None = None,
) -> StressPublicBook:
    """Run B1 real-GDP public stress with three-way residual financing.

    Args:
        macro: Baseline Macro book.
        external: Baseline Ext book.
        input6: Input 6 standard shock params.
        residual_params: Input 7 value-used params (public J shares + terms).
        iterations: Max fixed-point iterations for GFN ↔ ResFin feedback
            (stops early when ``max(|Δ gap|) < tol``).
        tol: Convergence tolerance on successive public residual gaps (LCU).
        public_gap: Optional precomputed public ΔGFN (LCU); skips GFN iteration.
        ext_r86: Optional external residual gap (USD); defaults to zeros (B1).

    Returns:
        ``StressPublicBook`` with ResFin fill and overlays.
    """
    shocked_inputs = apply_real_gdp_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B1_GDP_pub",
        inflation_elasticity=_inflation_elasticity(input6),
        iterations=iterations,
        tol=tol,
        public_gap=public_gap,
        ext_r86=ext_r86,
    )


def run_a1_historical_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public A1: key variables at 10-year historical averages."""
    from lic_dsf.stress.shocks import apply_historical_averages_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_historical_averages_shock(macro.inputs), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "A1_Historical_pub"
    )


def run_b2_pb_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B2 primary-balance stress."""
    from lic_dsf.stress.shocks import apply_primary_balance_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_primary_balance_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "B2_PrimaryBalance_pub"
    )


def run_b3_exports_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B3 exports stress."""
    from lic_dsf.stress.shocks import apply_exports_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_exports_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "B3_Exports_pub"
    )


def run_b4_other_flows_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B4 other-flows stress."""
    from lic_dsf.stress.shocks import apply_other_flows_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_other_flows_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "B4_OtherFlows_pub"
    )


def run_b5_fx_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B5 FX-depreciation stress."""
    from lic_dsf.stress.shocks import apply_fx_depreciation_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_fx_depreciation_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B5_FX_pub",
        inflation_elasticity=_inflation_elasticity(input6),
    )


def run_b6_combo_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B6 combination stress."""
    from lic_dsf.stress.shocks import apply_combo_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_combo_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B6_Combo_pub",
        inflation_elasticity=_inflation_elasticity(input6),
    )


def run_standard_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> dict[str, StressPublicBook]:
    """Run public A1 / B1–B6 and return them by scenario id."""
    return {
        "A1_Historical": run_a1_historical_public(macro, external, residual_params),
        "B1_GDP": run_b1_gdp_public(macro, external, input6, residual_params),
        "B2_PrimaryBalance": run_b2_pb_public(
            macro, external, input6, residual_params
        ),
        "B3_Exports": run_b3_exports_public(macro, external, input6, residual_params),
        "B4_OtherFlows": run_b4_other_flows_public(
            macro, external, input6, residual_params
        ),
        "B5_FX": run_b5_fx_public(macro, external, input6, residual_params),
        "B6_Combo": run_b6_combo_public(macro, external, input6, residual_params),
    }
