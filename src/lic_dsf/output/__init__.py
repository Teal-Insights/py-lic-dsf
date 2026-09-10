"""Excel Output-sheet DataFrames assembled from DSA / stress / realism books.

Leaf modules (``lic_dsf.output.baseline``, ``stress_geometry``, …) may be
imported directly. Package ``__init__`` exports are resolved lazily so that
``stress`` / ``rating`` can import geometry helpers without circular imports.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "OUTPUT11_NUMERIC_ROWS",
    "OUTPUT11_SHEET",
    "OUTPUT12_NUMERIC_ROWS",
    "OUTPUT12_SHEET",
    "OUTPUT31_SHEET",
    "OUTPUT32_SHEET",
    "external_dsa_panel",
    "external_debt_scenarios_table",
    "fiscal_adjustment_panel",
    "fiscal_multiplier_panel",
    "forecast_error_panel",
    "invest_growth_panel",
    "output_11_table",
    "output_12_table",
    "output_31_table",
    "output_32_table",
    "output_41_table",
    "output_42_fiscal_adjustment_table",
    "output_42_invest_table",
    "output_42_multiplier_table",
    "output_51_cell_keys",
    "output_51_table",
    "output_52_table",
    "output_6_table",
    "output_7_table",
    "placement_summary",
    "probabilities_table",
    "probability_panel",
    "public_dsa_panel",
    "realism4_sheet_table",
    "risk_summary_panel",
    "stress_external_panel",
    "stress_public_panel",
]

_LAZY: dict[str, tuple[str, str]] = {
    "OUTPUT11_NUMERIC_ROWS": ("lic_dsf.output.baseline", "OUTPUT11_NUMERIC_ROWS"),
    "OUTPUT11_SHEET": ("lic_dsf.output.baseline", "OUTPUT11_SHEET"),
    "OUTPUT12_NUMERIC_ROWS": ("lic_dsf.output.baseline", "OUTPUT12_NUMERIC_ROWS"),
    "OUTPUT12_SHEET": ("lic_dsf.output.baseline", "OUTPUT12_SHEET"),
    "OUTPUT31_SHEET": ("lic_dsf.output.stress", "OUTPUT31_SHEET"),
    "OUTPUT32_SHEET": ("lic_dsf.output.stress", "OUTPUT32_SHEET"),
    "external_dsa_panel": ("lic_dsf.output.baseline", "external_dsa_panel"),
    "external_debt_scenarios_table": (
        "lic_dsf.output.scenario",
        "external_debt_scenarios_table",
    ),
    "fiscal_adjustment_panel": ("lic_dsf.output.realism", "fiscal_adjustment_panel"),
    "fiscal_multiplier_panel": ("lic_dsf.output.realism", "fiscal_multiplier_panel"),
    "forecast_error_panel": ("lic_dsf.output.realism", "forecast_error_panel"),
    "invest_growth_panel": ("lic_dsf.output.realism", "invest_growth_panel"),
    "output_11_table": ("lic_dsf.output.baseline", "output_11_table"),
    "output_12_table": ("lic_dsf.output.baseline", "output_12_table"),
    "output_31_table": ("lic_dsf.output.stress", "output_31_table"),
    "output_32_table": ("lic_dsf.output.stress", "output_32_table"),
    "output_41_table": ("lic_dsf.output.realism", "output_41_table"),
    "output_42_fiscal_adjustment_table": (
        "lic_dsf.output.realism",
        "output_42_fiscal_adjustment_table",
    ),
    "output_42_invest_table": ("lic_dsf.output.realism", "output_42_invest_table"),
    "output_42_multiplier_table": (
        "lic_dsf.output.realism",
        "output_42_multiplier_table",
    ),
    "output_51_cell_keys": ("lic_dsf.output.rating", "output_51_cell_keys"),
    "output_51_table": ("lic_dsf.output.rating", "output_51_table"),
    "output_52_table": ("lic_dsf.output.rating", "output_52_table"),
    "output_6_table": ("lic_dsf.output.rating", "output_6_table"),
    "output_7_table": ("lic_dsf.output.rating", "output_7_table"),
    "placement_summary": ("lic_dsf.output.realism", "placement_summary"),
    "probabilities_table": ("lic_dsf.output.scenario", "probabilities_table"),
    "probability_panel": ("lic_dsf.output.scenario", "probability_panel"),
    "public_dsa_panel": ("lic_dsf.output.baseline", "public_dsa_panel"),
    "realism4_sheet_table": ("lic_dsf.output.realism", "realism4_sheet_table"),
    "risk_summary_panel": ("lic_dsf.output.rating", "risk_summary_panel"),
    "stress_external_panel": ("lic_dsf.output.stress", "stress_external_panel"),
    "stress_public_panel": ("lic_dsf.output.stress", "stress_public_panel"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr = _LAZY[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    from importlib import import_module

    value = getattr(import_module(module_name), attr)
    globals()[name] = value
    return value
