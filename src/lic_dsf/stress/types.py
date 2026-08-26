"""Input 6 standard-test shock parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ThresholdRule = Literal[
    "historical_average",
    "baseline_projection",
    "whichever_lower",
]

StressScenarioId = Literal[
    "A1_Historical",
    "A2_Custom",
    "B1_GDP",
    "B2_PrimaryBalance",
    "B3_Exports",
    "B4_OtherFlows",
    "B5_FX",
    "B6_Combo",
    "C1_CombinedCL",
    "C2_NaturalDisaster",
    "C3_Commodity",
    "C4_Market",
]


@dataclass(slots=True)
class Input6StandardParams:
    """Resolved ``Input 6(optional)-Standard Test`` sizes and interactions.

    User-defined columns (D / H) are preferred when loading from Excel; combo
    magnitudes are stored explicitly (Excel halves of the individual shocks).
    """

    threshold_rule: ThresholdRule
    interactions_on: bool

    gdp_shock_sd: float
    inflation_elasticity: float

    primary_balance_shock_sd: float
    domestic_borrowing_cost_bps: float

    exports_shock_sd: float
    exports_gdp_elasticity: float

    transfers_shock_sd: float
    fdi_shock_sd: float

    fx_depreciation_pct: float
    fx_passthrough: float
    net_exports_elasticity: float

    combo_gdp_shock_sd: float
    combo_exports_shock_sd: float
    combo_primary_balance_shock_sd: float
    combo_transfers_shock_sd: float
    combo_fdi_shock_sd: float
    combo_fx_depreciation_pct: float
