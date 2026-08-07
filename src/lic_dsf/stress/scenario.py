"""Stress scenario books and runners (external standard tests)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.residual_pv import (
    external_dsa_residual_params,
    external_residual_gap,
    flow_shortfall_gap,
    resfin_instrument,
    resfin_overlay_series,
    stressed_external_stock_from_shortfall,
)
from lic_dsf.stress.shocks import (
    apply_combo_shock,
    apply_exports_shock,
    apply_fx_depreciation_shock,
    apply_other_flows_shock,
    apply_real_gdp_shock,
)
from lic_dsf.stress.types import Input6StandardParams, StressScenarioId


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def _discount_rate(external: ExternalDebtBook) -> float:
    for instrument in external.portfolio.instruments:
        rate = getattr(instrument, "discount_rate", None)
        if rate is not None:
            return float(rate)
    return 0.05


@dataclass(slots=True)
class StressExternalBook:
    """External DSA ratios under a stress scenario (B-sheet engine).

    Numerators are baseline Ext PPG PV / service plus the ResFin overlay
    (Excel ``PV Stress``). Denominators come from the shocked ``MacroDebtBook``.
    """

    macro: MacroDebtBook
    external: ExternalDebtBook
    resfin_pv: pd.Series
    resfin_interest: pd.Series
    resfin_amortization: pd.Series
    scenario_id: StressScenarioId

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked Macro book."""
        return self.macro.inputs.years

    def pv_ppg_usd(self) -> pd.Series:
        """Stressed PPG external PV (Ext R391 + ResFin PV)."""
        return (
            _align(self.external.total_pv_of_debt(), self.years)
            + _align(self.resfin_pv, self.years).fillna(0.0)
        ).astype(float)

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """B-sheet R35."""
        return _clamp_nonnegative(_pct(self.pv_ppg_usd(), self.macro.gdp_usd()))

    def exports_to_gdp(self) -> pd.Series:
        """Exports / GDP × 100 under the shocked Macro path."""
        return _pct(self.macro.exports(), self.macro.gdp_usd())

    def revenues_to_gdp(self) -> pd.Series:
        """Revenues excl. grants / GDP × 100."""
        return _pct(self.macro.revenues_excl_grants(), self.macro.gdp_usd())

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """B-sheet R36."""
        return (self.pv_ppg_external_to_gdp() / self.exports_to_gdp() * 100.0).astype(
            float
        )

    def pv_ppg_external_to_revenue(self) -> pd.Series:
        """B-sheet R37."""
        return (self.pv_ppg_external_to_gdp() / self.revenues_to_gdp() * 100.0).astype(
            float
        )

    def total_external_debt_service_to_exports(self) -> pd.Series:
        """Total external DS / exports including ResFin service."""
        prior_priv_st = pd.Series(
            self.macro.private_st_external().shift(1), dtype=float
        ).fillna(0.0)
        numer = (
            prior_priv_st
            + self.macro.external_interest()
            + self.macro.external_amortization()
            + _align(self.resfin_interest, self.years).fillna(0.0)
            + _align(self.resfin_amortization, self.years).fillna(0.0)
        )
        return _pct(numer, self.macro.exports())

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """B-sheet R39."""
        return _clamp_nonnegative(
            self.total_external_debt_service_to_exports()
            - self.macro.private_debt_service_to_exports()
        )

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """B-sheet R40."""
        raw = (
            self.ppg_debt_service_to_exports()
            * self.macro.exports()
            / self.macro.revenues_excl_grants().replace(0.0, pd.NA)
        )
        return _clamp_nonnegative(
            raw.replace([float("inf"), float("-inf")], pd.NA).astype(float)
        )

    def external_gfn_usd(self) -> pd.Series:
        """Macro external GFN under the shocked path."""
        return self.macro.external_gfn()


def _zero_overlay(years: tuple[int, ...]) -> tuple[pd.Series, pd.Series, pd.Series]:
    z = pd.Series(0.0, index=list(years), dtype=float)
    return z.copy(), z.copy(), z.copy()


def _build_book(
    *,
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    gap: pd.Series,
    scenario_id: StressScenarioId,
) -> StressExternalBook:
    years = shocked_macro.inputs.years
    params = external_dsa_residual_params(residual_params)
    if float(gap.fillna(0.0).clip(lower=0.0).sum()) == 0.0:
        pv, interest, amort = _zero_overlay(years)
    else:
        instrument = resfin_instrument(
            gap,
            params,
            discount_rate=params.discount_rate or _discount_rate(external),
            years=years,
        )
        overlay = resfin_overlay_series(instrument, years)
        pv, interest, amort = overlay.pv, overlay.interest, overlay.amortization
    return StressExternalBook(
        macro=shocked_macro,
        external=external,
        resfin_pv=pv,
        resfin_interest=interest,
        resfin_amortization=amort,
        scenario_id=scenario_id,
    )


def run_b1_gdp_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B1 real-GDP external stress test.

    GDP-only shocks in the LIC-DSF template leave the B1 debt-identity residual
    (R86) at ~0, so the ResFin overlay is zero and ratios move with the shocked
    GDP denominator (exports held absolute).
    """
    shocked_inputs = apply_real_gdp_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    years = shocked_macro.inputs.years
    gap = pd.Series(0.0, index=list(years), dtype=float)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked_macro,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id="B1_GDP",
    )


def _external_gap_from_shortfall(
    macro: MacroDebtBook,
    shortfall: pd.Series,
) -> pd.Series:
    """Debt-identity residual from baseline PPG stock + cumulative shortfall."""
    years = macro.inputs.years
    baseline_stock = _align(macro.ppg_external(), years).fillna(0.0)
    stressed_stock = stressed_external_stock_from_shortfall(
        baseline_stock, shortfall, years
    )
    return external_residual_gap(baseline_stock, stressed_stock, years)


def run_b3_exports_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B3 exports external stress test."""
    shocked_inputs = apply_exports_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    years = shocked_macro.inputs.years
    shortfall = flow_shortfall_gap(macro.exports(), shocked_macro.exports(), years)
    gap = _external_gap_from_shortfall(macro, shortfall)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked_macro,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id="B3_Exports",
    )


def run_b4_other_flows_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B4 other-flows (transfers + FDI) external stress test."""
    shocked_inputs = apply_other_flows_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    years = shocked_macro.inputs.years
    shortfall = flow_shortfall_gap(
        macro.inputs.current_transfers_net,
        shocked_macro.inputs.current_transfers_net,
        years,
    ) + flow_shortfall_gap(macro.inputs.fdi, shocked_macro.inputs.fdi, years)
    gap = _external_gap_from_shortfall(macro, shortfall)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked_macro,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id="B4_OtherFlows",
    )


def run_b5_fx_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B5 FX-depreciation external stress test."""
    shocked_inputs = apply_fx_depreciation_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    # Full B5 debt-identity residual (revaluation) is deferred; GDP-deflator
    # pass-through alone drives the first-order PV/GDP move.
    years = shocked_macro.inputs.years
    gap = pd.Series(0.0, index=list(years), dtype=float)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked_macro,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id="B5_FX",
    )


def run_b6_combo_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B6 half-size combination external stress test."""
    shocked_inputs = apply_combo_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    years = shocked_macro.inputs.years
    shortfall = (
        flow_shortfall_gap(macro.exports(), shocked_macro.exports(), years)
        + flow_shortfall_gap(
            macro.inputs.current_transfers_net,
            shocked_macro.inputs.current_transfers_net,
            years,
        )
        + flow_shortfall_gap(macro.inputs.fdi, shocked_macro.inputs.fdi, years)
    )
    gap = _external_gap_from_shortfall(macro, shortfall)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked_macro,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id="B6_Combo",
    )


def run_standard_external_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> dict[str, StressExternalBook]:
    """Run the standard external B-tests and return them by scenario id."""
    runners = (
        ("B1_GDP", run_b1_gdp_external),
        ("B3_Exports", run_b3_exports_external),
        ("B4_OtherFlows", run_b4_other_flows_external),
        ("B5_FX", run_b5_fx_external),
        ("B6_Combo", run_b6_combo_external),
    )
    return {
        key: runner(macro, external, input6, residual_params) for key, runner in runners
    }
