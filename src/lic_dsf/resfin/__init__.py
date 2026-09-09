"""Residual financing (Input 7 / PV Stress / PV_ResFin_pub).

Owns params, Ext decade defaults, overlays, split policies, and the
fixed-point engine. Uses ``lic_dsf.pv.PresentValueInstrument`` for the
synthetic external MLT residual loan — does not live inside ``pv``.
"""

from __future__ import annotations

from lic_dsf.resfin.defaults import calculate_residual_defaults
from lic_dsf.resfin.engine import (
    EXTERNAL_INTEREST_TOL,
    PUBLIC_GAP_TOL,
    ResidualFinancingEngine,
    ResidualFinancingResult,
)
from lic_dsf.resfin.overlay import (
    build_public_resfin_overlay,
    dom_mlt_resfin_series,
    dom_st_resfin_series,
    external_residual_gap,
    flow_shortfall_gap,
    gdp_deflator_growth,
    public_residual_gap,
    resfin_instrument,
    resfin_overlay_series,
    split_residual_financing,
    stressed_external_stock_from_shortfall,
)
from lic_dsf.resfin.params import (
    ResidualFinancingOverrides,
    ResidualFinancingParams,
    external_dsa_residual_params,
    public_dsa_residual_params,
    resolve_residual_params,
)
from lic_dsf.resfin.policy import (
    AbsoluteResidualPolicy,
    CappedResidualPolicy,
    ResidualPolicy,
    ResidualPolicyKind,
    policy_from_kind,
)
from lic_dsf.resfin.types import (
    DomMltOverlay,
    DomStOverlay,
    PublicResFinOverlay,
    ResFinOverlay,
    ResidualFill,
)

__all__ = [
    "EXTERNAL_INTEREST_TOL",
    "PUBLIC_GAP_TOL",
    "AbsoluteResidualPolicy",
    "CappedResidualPolicy",
    "DomMltOverlay",
    "DomStOverlay",
    "PublicResFinOverlay",
    "ResFinOverlay",
    "ResidualFill",
    "ResidualFinancingEngine",
    "ResidualFinancingOverrides",
    "ResidualFinancingParams",
    "ResidualFinancingResult",
    "ResidualPolicy",
    "ResidualPolicyKind",
    "build_public_resfin_overlay",
    "calculate_residual_defaults",
    "dom_mlt_resfin_series",
    "dom_st_resfin_series",
    "external_dsa_residual_params",
    "external_residual_gap",
    "flow_shortfall_gap",
    "gdp_deflator_growth",
    "policy_from_kind",
    "public_dsa_residual_params",
    "public_residual_gap",
    "resfin_instrument",
    "resfin_overlay_series",
    "resolve_residual_params",
    "split_residual_financing",
    "stressed_external_stock_from_shortfall",
]
