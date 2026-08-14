"""LIC-DSF standard stress tests (Input 6 → shocked Macro → ResFin → ratios).

Sibling of ``lic_dsf.pv`` and ``lic_dsf.dsa``. Baseline ratios live in
``lic_dsf.dsa``; this package applies Input 6 shocks and residual-financing PV
overlays (external and public three-way fill) to produce B-sheet paths.
"""

from lic_dsf.stress.bound import external_residual_borrowing
from lic_dsf.stress.panels import stress_external_panel
from lic_dsf.stress.public import (
    StressPublicBook,
    estimate_b1_public_gfn,
    run_b1_gdp_public,
    stress_public_panel,
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
from lic_dsf.stress.scenario import (
    StressExternalBook,
    rebuild_external_with_fx,
    run_b1_gdp_external,
    run_b3_exports_external,
    run_b4_other_flows_external,
    run_b5_fx_external,
    run_b6_combo_external,
    run_standard_external_stress,
)
from lic_dsf.stress.shocks import (
    apply_combo_shock,
    apply_exports_shock,
    apply_fx_depreciation_shock,
    apply_other_flows_shock,
    apply_primary_balance_shock,
    apply_real_gdp_shock,
    real_depreciation_pct,
)
from lic_dsf.stress.types import Input6StandardParams, StressScenarioId, ThresholdRule
from lic_dsf.stress.workbook import load_input6_standard

__all__ = [
    "DomMltOverlay",
    "DomStOverlay",
    "Input6StandardParams",
    "PublicResFinOverlay",
    "ResFinOverlay",
    "ResidualFill",
    "StressExternalBook",
    "StressPublicBook",
    "StressScenarioId",
    "ThresholdRule",
    "apply_combo_shock",
    "apply_exports_shock",
    "apply_fx_depreciation_shock",
    "apply_other_flows_shock",
    "apply_primary_balance_shock",
    "apply_real_gdp_shock",
    "build_public_resfin_overlay",
    "dom_mlt_resfin_series",
    "dom_st_resfin_series",
    "estimate_b1_public_gfn",
    "external_dsa_residual_params",
    "external_residual_borrowing",
    "external_residual_gap",
    "flow_shortfall_gap",
    "load_input6_standard",
    "public_dsa_residual_params",
    "public_residual_gap",
    "real_depreciation_pct",
    "rebuild_external_with_fx",
    "resfin_instrument",
    "resfin_overlay_series",
    "run_b1_gdp_external",
    "run_b1_gdp_public",
    "run_b3_exports_external",
    "run_b4_other_flows_external",
    "run_b5_fx_external",
    "run_b6_combo_external",
    "run_standard_external_stress",
    "split_residual_financing",
    "stress_external_panel",
    "stress_public_panel",
    "stressed_external_stock_from_shortfall",
]
