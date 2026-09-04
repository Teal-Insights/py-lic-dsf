"""Stress scenario books and runners (external standard tests)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.pv.portfolio import PVPortfolio
from lic_dsf.stress.bound import bsheet_exports_to_gdp
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
    residual_borrowing: pd.Series
    scenario_id: StressScenarioId
    baseline_macro: MacroDebtBook | None = None
    fx_depreciation_pct: float = 0.0
    additional_borrowing_interest: pd.Series | None = None

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
        """Exports / GDP × 100 (B-sheet R19)."""
        if self.baseline_macro is None:
            return _pct(self.macro.exports(), self.macro.gdp_usd())
        return bsheet_exports_to_gdp(
            self.baseline_macro,
            self.macro,
            fx_depreciation_pct=self.fx_depreciation_pct,
        )

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
        if self.additional_borrowing_interest is not None:
            numer = numer + _align(
                self.additional_borrowing_interest, self.years
            ).fillna(0.0)
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


def rebuild_external_with_fx(
    external: ExternalDebtBook,
    fx_pa: pd.Series,
    fx_eop: pd.Series,
) -> ExternalDebtBook:
    """Rebuild Ext with shocked FX so LC-NR USD PV/stock revalue (B5/B6)."""
    instruments = []
    for inst in external.portfolio.instruments:
        if isinstance(inst, LocalCurrencyNonResidentInstrument) and inst.years:
            years = list(inst.years)
            pa = fx_pa.reindex(years).ffill().bfill()
            eop = fx_eop.reindex(years).ffill().bfill()
            instruments.append(
                replace(
                    inst,
                    fx_pa=[float(pa.loc[y]) for y in years],
                    fx_eop=[float(eop.loc[y]) for y in years],
                )
            )
        else:
            instruments.append(inst)
    return ExternalDebtBook(
        portfolio=PVPortfolio(instruments=tuple(instruments)),
        inputs=replace(external.inputs, fx_pa=fx_pa, fx_eop=fx_eop),
    )


def run_a1_historical_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the A1 historical-averages external scenario."""
    from lic_dsf.stress.facade import run_a1_historical_external as _run

    return _run(macro, external, residual_params)


def run_b2_pb_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B2 primary-balance external stress test."""
    from lic_dsf.stress.facade import run_external_scenario

    return run_external_scenario(
        "B2_PrimaryBalance", macro, external, input6, residual_params
    )


def run_b1_gdp_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B1 real-GDP external stress test."""
    from lic_dsf.stress.facade import run_external_scenario

    return run_external_scenario("B1_GDP", macro, external, input6, residual_params)


def run_b3_exports_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B3 exports external stress test."""
    from lic_dsf.stress.facade import run_external_scenario

    return run_external_scenario(
        "B3_Exports", macro, external, input6, residual_params
    )


def run_b4_other_flows_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B4 other-flows external stress test."""
    from lic_dsf.stress.facade import run_external_scenario

    return run_external_scenario(
        "B4_OtherFlows", macro, external, input6, residual_params
    )


def run_b5_fx_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressExternalBook:
    """Run the B5 FX-depreciation external stress test."""
    from lic_dsf.stress.facade import run_external_scenario

    return run_external_scenario("B5_FX", macro, external, input6, residual_params)


def run_b6_combo_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    workbook_path: str | Path | None = None,
) -> StressExternalBook:
    """Run the B6 combo external stress test (``workbook_path`` unused)."""
    del workbook_path
    from lic_dsf.stress.facade import run_external_scenario

    return run_external_scenario("B6_Combo", macro, external, input6, residual_params)


def run_standard_external_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    workbook_path: str | Path | None = None,
) -> dict[str, StressExternalBook]:
    """Run the standard external B-tests."""
    from lic_dsf.stress.facade import run_standard_external_stress as _run

    return _run(
        macro, external, input6, residual_params, workbook_path=workbook_path
    )
