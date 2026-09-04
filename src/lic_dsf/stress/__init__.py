"""LIC-DSF stress tests (Input 6 → shocked Macro → ResFin → ratios).

Sibling of ``lic_dsf.pv`` and ``lic_dsf.dsa``. Baseline ratios live in
``lic_dsf.dsa``; this package applies Input 6 shocks and residual-financing PV
overlays (external and public three-way fill) to produce B-sheet paths.
"""

from __future__ import annotations

from lic_dsf.stress.bound import (
    bsheet_exports_to_gdp,
    external_residual_borrowing,
    historical_identity_pins,
)
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.external_dynamics import ExternalDebtDynamics, ExternalGapResult
from lic_dsf.stress.external_portfolio import ExternalPortfolioAdjuster
from lic_dsf.stress.facade import (
    run_external_scenario,
    run_public_scenario,
    run_scenario,
)
from lic_dsf.stress.macro_shocks import (
    apply_combo_shock,
    apply_exports_shock,
    apply_fx_depreciation_shock,
    apply_historical_averages_shock,
    apply_other_flows_shock,
    apply_primary_balance_shock,
    apply_real_gdp_shock,
    real_depreciation_pct,
)
from lic_dsf.stress.market_access import ComboMarketCost, MarketAccessAddon
from lic_dsf.stress.path import ShockedMacroPath, ShockMetadata
from lic_dsf.stress.public import (
    StressPublicBook,
    estimate_b1_public_gfn,
    run_a1_historical_public,
    run_b1_gdp_public,
    run_b2_pb_public,
    run_b3_exports_public,
    run_b4_other_flows_public,
    run_b5_fx_public,
    run_b6_combo_public,
    run_standard_public_stress,
)
from lic_dsf.stress.public_gfn import PublicGFNIdentity
from lic_dsf.stress.ratios import StressExternalRatios, StressPublicRatios
from lic_dsf.stress.resfin import (
    AbsoluteResidualPolicy,
    CappedResidualPolicy,
    ResidualFinancingEngine,
    ResidualFinancingResult,
    ResidualPolicy,
)
from lic_dsf.stress.residual_pv import (
    DomMltOverlay,
    DomStOverlay,
    PublicResFinOverlay,
    ResFinOverlay,
    ResidualFill,
    build_public_resfin_overlay,
    dom_mlt_resfin_series,
    dom_st_resfin_series,
    external_dsa_residual_params,
    external_residual_gap,
    flow_shortfall_gap,
    public_dsa_residual_params,
    public_residual_gap,
    resfin_instrument,
    resfin_overlay_series,
    split_residual_financing,
    stressed_external_stock_from_shortfall,
)
from lic_dsf.stress.result import ScenarioRunResult, StressScenarioResult
from lic_dsf.stress.runner import (
    CoupledScenarioRunner,
    ExternalScenarioRunner,
    PublicScenarioRunner,
    StressScenarioRunner,
)
from lic_dsf.stress.scenario import (
    StressExternalBook,
    rebuild_external_with_fx,
    run_a1_historical_external,
    run_b1_gdp_external,
    run_b2_pb_external,
    run_b3_exports_external,
    run_b4_other_flows_external,
    run_b5_fx_external,
    run_b6_combo_external,
    run_standard_external_stress,
)
from lic_dsf.stress.shocks import MacroShockFactory
from lic_dsf.stress.spec import (
    OutputBinding,
    ResidualPolicyKind,
    ScenarioRegistry,
    ScenarioSpec,
    ShockKind,
)
from lic_dsf.stress.suite import (
    StressSuite,
    build_output31_from_suite,
    build_output32_from_suite,
)
from lic_dsf.stress.tailored_params import (
    TailoredParams,
    run_tailored_external_stress,
    run_tailored_public_stress,
)
from lic_dsf.stress.types import Input6StandardParams, StressScenarioId, ThresholdRule

__all__ = [
    "AbsoluteResidualPolicy",
    "CappedResidualPolicy",
    "ComboMarketCost",
    "CoupledScenarioRunner",
    "DomMltOverlay",
    "DomStOverlay",
    "ExternalDebtDynamics",
    "ExternalGapResult",
    "ExternalPortfolioAdjuster",
    "ExternalScenarioRunner",
    "Input6StandardParams",
    "MacroShockFactory",
    "MarketAccessAddon",
    "OutputBinding",
    "PublicGFNIdentity",
    "PublicResFinOverlay",
    "PublicScenarioRunner",
    "ResFinOverlay",
    "ResidualFill",
    "ResidualFinancingEngine",
    "ResidualFinancingResult",
    "ResidualPolicy",
    "ResidualPolicyKind",
    "ScenarioRegistry",
    "ScenarioRunResult",
    "ScenarioSpec",
    "ShockKind",
    "ShockMetadata",
    "ShockedMacroPath",
    "StressContext",
    "StressExternalBook",
    "StressExternalRatios",
    "StressPublicBook",
    "StressPublicRatios",
    "StressScenarioId",
    "StressScenarioResult",
    "StressScenarioRunner",
    "StressSuite",
    "TailoredParams",
    "ThresholdRule",
    "apply_combo_shock",
    "apply_exports_shock",
    "apply_fx_depreciation_shock",
    "apply_historical_averages_shock",
    "apply_other_flows_shock",
    "apply_primary_balance_shock",
    "apply_real_gdp_shock",
    "bsheet_exports_to_gdp",
    "build_output31_from_suite",
    "build_output32_from_suite",
    "build_public_resfin_overlay",
    "dom_mlt_resfin_series",
    "dom_st_resfin_series",
    "estimate_b1_public_gfn",
    "external_dsa_residual_params",
    "external_residual_borrowing",
    "external_residual_gap",
    "flow_shortfall_gap",
    "historical_identity_pins",
    "public_dsa_residual_params",
    "public_residual_gap",
    "real_depreciation_pct",
    "rebuild_external_with_fx",
    "resfin_instrument",
    "resfin_overlay_series",
    "run_a1_historical_external",
    "run_a1_historical_public",
    "run_b1_gdp_external",
    "run_b1_gdp_public",
    "run_b2_pb_external",
    "run_b2_pb_public",
    "run_b3_exports_external",
    "run_b3_exports_public",
    "run_b4_other_flows_external",
    "run_b4_other_flows_public",
    "run_b5_fx_external",
    "run_b5_fx_public",
    "run_b6_combo_external",
    "run_b6_combo_public",
    "run_external_scenario",
    "run_public_scenario",
    "run_scenario",
    "run_standard_external_stress",
    "run_standard_public_stress",
    "run_tailored_external_stress",
    "run_tailored_public_stress",
    "split_residual_financing",
    "stressed_external_stock_from_shortfall",
]
