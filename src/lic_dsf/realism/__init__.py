"""Realism tools (Excel Realism 1–4 / Output 4-1 / 4-2).

Consumes Baseline public / Macro series; does not own Chart Data or ratings.
"""

from lic_dsf.realism.fiscal_adjustment import (
    DEFAULT_LIC_PROGRAM_DISTRIBUTION,
    FiscalAdjustmentPlacement,
    place_in_lic_histogram,
    projected_three_year_adjustment,
    three_year_fiscal_adjustment,
)
from lic_dsf.realism.fiscal_multiplier import (
    cumulative_multiplier_impact,
    fiscal_adjustment_from_primary_balance,
    underlying_growth,
    unit_impulse,
)
from lic_dsf.realism.forecast_error import (
    QuartileBand,
    compare_to_quartiles,
    debt_creating_flow_panel,
    debt_stock_from_ratio,
    forecast_error,
    gdp_rebase_scale,
    other_identified_flows_to_gdp,
    public_automatic_debt_dynamics,
    rebase_ratio_to_outturn_gdp,
    total_external_to_gdp,
)
from lic_dsf.realism.imported import ImportedDataCatalog, load_imported_data
from lic_dsf.realism.invest_growth import (
    capital_growth_contribution,
    capital_stock_to_gdp,
    residual_growth_contribution,
)
from lic_dsf.realism.panels import (
    fiscal_adjustment_panel,
    fiscal_multiplier_panel,
    forecast_error_panel,
    invest_growth_panel,
    placement_summary,
)
from lic_dsf.realism.types import (
    CapitalAssumptions,
    LicProgramDistribution,
    MultiplierAssumptions,
)
from lic_dsf.realism.workbook import (
    load_capital_assumptions,
    load_lic_program_distribution,
    load_multiplier_grid,
)

__all__ = [
    "DEFAULT_LIC_PROGRAM_DISTRIBUTION",
    "CapitalAssumptions",
    "FiscalAdjustmentPlacement",
    "ImportedDataCatalog",
    "LicProgramDistribution",
    "MultiplierAssumptions",
    "QuartileBand",
    "capital_growth_contribution",
    "capital_stock_to_gdp",
    "compare_to_quartiles",
    "cumulative_multiplier_impact",
    "debt_creating_flow_panel",
    "debt_stock_from_ratio",
    "fiscal_adjustment_from_primary_balance",
    "fiscal_adjustment_panel",
    "fiscal_multiplier_panel",
    "forecast_error",
    "forecast_error_panel",
    "gdp_rebase_scale",
    "invest_growth_panel",
    "load_capital_assumptions",
    "load_imported_data",
    "load_lic_program_distribution",
    "load_multiplier_grid",
    "other_identified_flows_to_gdp",
    "place_in_lic_histogram",
    "placement_summary",
    "projected_three_year_adjustment",
    "public_automatic_debt_dynamics",
    "rebase_ratio_to_outturn_gdp",
    "residual_growth_contribution",
    "three_year_fiscal_adjustment",
    "total_external_to_gdp",
    "underlying_growth",
    "unit_impulse",
]
