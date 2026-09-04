"""Public stress DSA facade: legacy ``StressPublicBook`` + run_* re-exports."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.market_access import (
    _amortizing_stock_from_disbursements,
    _market_add_int_interest_lcu,
    _market_add_int_interest_parts,
    _market_add_int_rates,
    _shock_window_years,
)
from lic_dsf.stress.public_gfn import (
    _a1_primary_deficit_lcu,
    _a1_public_gdp_lcu,
    _align,
    _b1_other_identified_flows_lcu,
    _b1_primary_deficit_lcu,
    _b1_public_gdp_lcu,
    _clamp_nonnegative,
    _extra_fx_depreciation_ppt,
    _fx_shock_projection_year,
    _growth_pct,
    _inflation_elasticity,
    _pct,
    _public_real_and_lcu_deflator,
    _shocked_real_and_lcu_deflator,
    estimate_b1_public_gfn,
)
from lic_dsf.stress.ratios.public_paths import (
    _b1_scenario_debt_service_lcu,
    _b5_avg_fx_pa,
    _b5_fx_face_uplift_factor,
    _b5_ppg_amort_fx_factor,
    _b5_ppg_interest_fx_factor,
    _b5_public_debt_service_parts_lcu,
    _b5_public_fx_eop_for_debt_service,
    _combo_primary_deficit_lcu,
    _combo_public_debt_service_parts_lcu,
    _macro_debt_service_parts_lcu,
    _macro_debt_service_total_lcu,
    _public_domestic_st_lcu_path,
    _public_existing_debt_service_lcu,
    _public_existing_debt_service_parts_lcu,
    _public_external_face_lcu_path,
    _public_external_pv_lcu_path,
)
from lic_dsf.stress.residual_pv import PublicResFinOverlay
from lic_dsf.stress.types import Input6StandardParams


@dataclass(slots=True)
class StressPublicBook:
    """Legacy public DSA book; ratio math lives on ``StressPublicRatios``."""

    macro: MacroDebtBook
    external: ExternalDebtBook
    baseline_macro: MacroDebtBook
    resfin: PublicResFinOverlay
    scenario_id: str = "B1_GDP_pub"
    inflation_elasticity: float = 0.0
    market_access: bool = False
    fx_passthrough: float = 0.0
    fx_depreciation_pct: float = 0.0
    combo_primary: bool = False
    input6: Input6StandardParams | None = None
    gdp_lcu_override: pd.Series | None = None
    resfin_external_ds: PublicResFinOverlay | None = None
    external_dsa_borrowing_usd: pd.Series | None = None
    primary_exp_gdp_denominator: pd.Series | None = None
    lcu_deflator_growth: pd.Series | None = None
    _ratios: object | None = None

    @classmethod
    def from_ratios(cls, ratios: object) -> StressPublicBook:
        """Wrap ``StressPublicRatios`` for legacy Output / rating APIs."""
        from lic_dsf.stress.ratios.public import StressPublicRatios

        assert isinstance(ratios, StressPublicRatios)
        book = cls(
            macro=ratios.macro,
            external=ratios.external,
            baseline_macro=ratios.baseline_macro,
            resfin=ratios.resfin,
            scenario_id=ratios.scenario_id,
            inflation_elasticity=ratios.inflation_elasticity,
            market_access=ratios.market_access,
            fx_passthrough=ratios.fx_passthrough,
            fx_depreciation_pct=ratios.fx_depreciation_pct,
            combo_primary=ratios.combo_primary,
            input6=ratios.input6,
            gdp_lcu_override=ratios.gdp_lcu_override,
            resfin_external_ds=ratios.resfin_external_ds,
            external_dsa_borrowing_usd=ratios.external_dsa_borrowing_usd,
            primary_exp_gdp_denominator=ratios.primary_exp_gdp_denominator,
            lcu_deflator_growth=ratios.lcu_deflator_growth,
            _ratios=ratios,
        )
        return book

    def _impl(self):
        """Underlying ``StressPublicRatios`` (built lazily from legacy fields)."""
        if self._ratios is not None:
            return self._ratios
        from lic_dsf.stress.ratios.public import StressPublicRatios

        self._ratios = StressPublicRatios.from_legacy_fields(
            macro=self.macro,
            external=self.external,
            baseline_macro=self.baseline_macro,
            resfin=self.resfin,
            scenario_id=self.scenario_id,
            inflation_elasticity=self.inflation_elasticity,
            market_access=self.market_access,
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
            combo_primary=self.combo_primary,
            input6=self.input6,
            gdp_lcu_override=self.gdp_lcu_override,
            resfin_external_ds=self.resfin_external_ds,
            external_dsa_borrowing_usd=self.external_dsa_borrowing_usd,
            primary_exp_gdp_denominator=self.primary_exp_gdp_denominator,
            lcu_deflator_growth=self.lcu_deflator_growth,
        )
        return self._ratios

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked Macro book."""
        return self.macro.inputs.years

    def gdp_lcu(self) -> pd.Series:
        """Public B-sheet R41 shocked GDP in LCU."""
        return self._impl().gdp_lcu()

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet external PV / GDP (R101)."""
        return self._impl().pv_ppg_external_to_gdp()

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet external PV / exports (R102)."""
        return self._impl().pv_ppg_external_to_exports()

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet PPG DS / exports (R103)."""
        return self._impl().ppg_debt_service_to_exports()

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet PPG DS / revenue excl. grants (R104)."""
        return self._impl().ppg_debt_service_to_revenue()

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Public debt / GDP (B-sheet R11 debt-dynamics path)."""
        return self._impl().public_sector_debt_to_gdp()

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """PV of public debt / GDP (B-sheet R13)."""
        return self._impl().pv_public_debt_to_gdp()

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """PV of public debt / revenue+grants (B-sheet R95)."""
        return self._impl().pv_public_debt_to_revenue_grants()

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Debt service / revenue+grants (B-sheet R93)."""
        return self._impl().debt_service_to_revenue_grants()

    def public_gfn(self) -> pd.Series:
        """B1 R90 public GFN (LCU)."""
        return self._impl().public_gfn()

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP (B-sheet R94)."""
        return self._impl().debt_service_to_gdp()


def run_b1_gdp_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run B1 real-GDP public stress with three-way residual financing."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B1_GDP", macro, external, input6, residual_params
    )


def run_a1_historical_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the A1 historical-averages public scenario."""
    from lic_dsf.stress.facade import run_a1_historical_public as _run

    return _run(macro, external, residual_params)


def run_b2_pb_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> StressPublicBook:
    """Run the B2 primary-balance public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B2_PrimaryBalance",
        macro,
        external,
        input6,
        residual_params,
        market_access=market_access,
    )


def run_b3_exports_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B3 exports public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B3_Exports", macro, external, input6, residual_params
    )


def run_b4_other_flows_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B4 other-flows public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B4_OtherFlows", macro, external, input6, residual_params
    )


def run_b5_fx_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B5 FX public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario("B5_FX", macro, external, input6, residual_params)


def run_b6_combo_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B6 combo public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B6_Combo", macro, external, input6, residual_params
    )


def run_standard_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> dict[str, StressPublicBook]:
    """Run public A1 / B1–B6 stress scenarios."""
    from lic_dsf.stress.facade import run_standard_public_stress as _run

    return _run(
        macro, external, input6, residual_params, market_access=market_access
    )


__all__ = [
    "StressPublicBook",
    "_a1_primary_deficit_lcu",
    "_a1_public_gdp_lcu",
    "_align",
    "_amortizing_stock_from_disbursements",
    "_b1_other_identified_flows_lcu",
    "_b1_primary_deficit_lcu",
    "_b1_public_gdp_lcu",
    "_b1_scenario_debt_service_lcu",
    "_b5_avg_fx_pa",
    "_b5_fx_face_uplift_factor",
    "_b5_ppg_amort_fx_factor",
    "_b5_ppg_interest_fx_factor",
    "_b5_public_debt_service_parts_lcu",
    "_b5_public_fx_eop_for_debt_service",
    "_clamp_nonnegative",
    "_combo_primary_deficit_lcu",
    "_combo_public_debt_service_parts_lcu",
    "_extra_fx_depreciation_ppt",
    "_fx_shock_projection_year",
    "_growth_pct",
    "_inflation_elasticity",
    "_macro_debt_service_parts_lcu",
    "_macro_debt_service_total_lcu",
    "_market_add_int_interest_lcu",
    "_market_add_int_interest_parts",
    "_market_add_int_rates",
    "_pct",
    "_public_domestic_st_lcu_path",
    "_public_existing_debt_service_lcu",
    "_public_existing_debt_service_parts_lcu",
    "_public_external_face_lcu_path",
    "_public_external_pv_lcu_path",
    "_public_real_and_lcu_deflator",
    "_shock_window_years",
    "_shocked_real_and_lcu_deflator",
    "estimate_b1_public_gfn",
    "run_a1_historical_public",
    "run_b1_gdp_public",
    "run_b2_pb_public",
    "run_b3_exports_public",
    "run_b4_other_flows_public",
    "run_b5_fx_public",
    "run_b6_combo_public",
    "run_standard_public_stress",
]
