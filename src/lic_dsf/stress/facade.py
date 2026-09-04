"""Stable public runners over the stress package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.scenario.customized import CustomizedScenarioSpec
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.output_map import (
    result_as_legacy_external_book,
    result_as_legacy_public_book,
)
from lic_dsf.stress.result import StressScenarioResult
from lic_dsf.stress.runner.coupled import CoupledScenarioRunner
from lic_dsf.stress.runner.external import ExternalScenarioRunner
from lic_dsf.stress.runner.public import PublicScenarioRunner
from lic_dsf.stress.spec import ScenarioRegistry
from lic_dsf.stress.suite import StressSuite
from lic_dsf.stress.tailored_params import TailoredParams
from lic_dsf.stress.types import Input6StandardParams, StressScenarioId


def neutral_input6() -> Input6StandardParams:
    """Placeholder Input 6 for A1-only callers that omit the object."""
    return Input6StandardParams(
        threshold_rule="baseline_projection",
        interactions_on=False,
        gdp_shock_sd=0.0,
        inflation_elasticity=0.0,
        primary_balance_shock_sd=0.0,
        domestic_borrowing_cost_bps=0.0,
        exports_shock_sd=0.0,
        exports_gdp_elasticity=0.0,
        transfers_shock_sd=0.0,
        fdi_shock_sd=0.0,
        fx_depreciation_pct=0.0,
        fx_passthrough=0.0,
        net_exports_elasticity=0.0,
        combo_gdp_shock_sd=0.0,
        combo_exports_shock_sd=0.0,
        combo_primary_balance_shock_sd=0.0,
        combo_transfers_shock_sd=0.0,
        combo_fdi_shock_sd=0.0,
        combo_fx_depreciation_pct=0.0,
    )


# Back-compat alias used by stress.tailored wrappers.
_neutral_input6 = neutral_input6


def _ctx(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual: ResidualFinancingParams,
    *,
    market_access: bool = False,
    tailored: TailoredParams | None = None,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> StressContext:
    return StressContext.from_parts(
        macro,
        external,
        input6,
        residual,
        market_access=market_access,
        tailored=tailored,
        custom_spec=custom_spec,
    )


def run_external_scenario(
    scenario_id: StressScenarioId | str,
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual: ResidualFinancingParams,
    *,
    market_access: bool = False,
    tailored: TailoredParams | None = None,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> Any:
    """Run an external scenario and return a legacy ``StressExternalBook``."""
    ctx = _ctx(
        macro,
        external,
        input6,
        residual,
        market_access=market_access,
        tailored=tailored,
        custom_spec=custom_spec,
    )
    result = ExternalScenarioRunner(context=ctx).run(ScenarioRegistry.get(scenario_id))
    return result_as_legacy_external_book(result)


def run_public_scenario(
    scenario_id: StressScenarioId | str,
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual: ResidualFinancingParams,
    *,
    market_access: bool = False,
    tailored: TailoredParams | None = None,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> Any:
    """Run a public scenario and return a legacy ``StressPublicBook``."""
    ctx = _ctx(
        macro,
        external,
        input6,
        residual,
        market_access=market_access,
        tailored=tailored,
        custom_spec=custom_spec,
    )
    result = PublicScenarioRunner(context=ctx).run(ScenarioRegistry.get(scenario_id))
    return result_as_legacy_public_book(result)


def run_scenario(
    scenario_id: StressScenarioId | str,
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual: ResidualFinancingParams,
    *,
    market_access: bool = False,
    tailored: TailoredParams | None = None,
    custom_spec: CustomizedScenarioSpec | None = None,
    public: bool = False,
) -> StressScenarioResult:
    """Run one scenario through the stress pipeline (raw result)."""
    ctx = _ctx(
        macro,
        external,
        input6,
        residual,
        market_access=market_access,
        tailored=tailored,
        custom_spec=custom_spec,
    )
    spec = ScenarioRegistry.get(scenario_id)
    if public or spec.output_binding.output_31_source == "public_external_methods":
        if spec.couple_ext_r86:
            return CoupledScenarioRunner(context=ctx).run(spec)
        return PublicScenarioRunner(context=ctx).run(spec)
    return ExternalScenarioRunner(context=ctx).run(spec)


def run_standard_external_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual: ResidualFinancingParams,
    *,
    workbook_path: str | Path | None = None,
) -> dict[str, Any]:
    """Standard B1–B6 external books (``workbook_path`` ignored)."""
    del workbook_path
    ctx = _ctx(macro, external, input6, residual)
    suite = StressSuite(context=ctx)
    results = suite.run_external_standard()
    b2 = ExternalScenarioRunner(context=ctx).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    )
    results["B2_PrimaryBalance"] = b2
    return {
        sid: result_as_legacy_external_book(result)
        for sid, result in results.items()
        if sid != "A1_Historical" and result.external_ratios is not None
    }


def run_standard_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> dict[str, Any]:
    """Standard A1 + B1–B6 public books."""
    ctx = _ctx(macro, external, input6, residual, market_access=market_access)
    results = StressSuite(context=ctx).run_public_standard()
    return {
        sid: result_as_legacy_public_book(result) for sid, result in results.items()
    }


def run_tailored_external_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual: ResidualFinancingParams,
    params: TailoredParams,
    input6: Input6StandardParams,
    *,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> dict[str, Any]:
    """A2 + C* external books (respects Input 6 applicability)."""
    ctx = _ctx(
        macro,
        external,
        input6,
        residual,
        tailored=params,
        custom_spec=custom_spec,
    )
    results = StressSuite(context=ctx).run_tailored_external(custom_spec=custom_spec)
    return {
        sid: result_as_legacy_external_book(result) for sid, result in results.items()
    }


def run_tailored_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual: ResidualFinancingParams,
    params: TailoredParams,
    input6: Input6StandardParams,
    *,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> dict[str, Any]:
    """A2 + C* public books (respects Input 6 applicability)."""
    ctx = _ctx(
        macro,
        external,
        input6,
        residual,
        tailored=params,
        custom_spec=custom_spec,
    )
    results = StressSuite(context=ctx).run_tailored_public(custom_spec=custom_spec)
    return {
        sid: result_as_legacy_public_book(result) for sid, result in results.items()
    }


def run_a1_historical_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> Any:
    """A1 historical external scenario."""
    return run_external_scenario(
        "A1_Historical", macro, external, _neutral_input6(), residual_params
    )


def run_a1_historical_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> Any:
    """A1 historical public scenario."""
    return run_public_scenario(
        "A1_Historical", macro, external, _neutral_input6(), residual_params
    )


__all__ = [
    "run_a1_historical_external",
    "run_a1_historical_public",
    "run_external_scenario",
    "run_public_scenario",
    "run_scenario",
    "run_standard_external_stress",
    "run_standard_public_stress",
    "run_tailored_external_stress",
    "run_tailored_public_stress",
]
