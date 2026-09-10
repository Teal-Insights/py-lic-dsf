"""Input 6 / tailored shock construction.

``MacroShockFactory`` and adapters live in :mod:`lic_dsf.stress.shocks.adapters`
so importing ``tailored_params`` / ``macro`` does not pull ``StressContext``
(avoids a circular import with :mod:`lic_dsf.stress.context`).
"""

from __future__ import annotations

from typing import Any

from lic_dsf.stress.shocks.macro import (
    apply_combo_shock,
    apply_exports_shock,
    apply_fx_depreciation_shock,
    apply_historical_averages_shock,
    apply_other_flows_shock,
    apply_primary_balance_shock,
    apply_real_gdp_shock,
    depreciation_of_nc_pct,
    real_depreciation_pct,
)

__all__ = [
    "ComboShock",
    "ExportsShock",
    "FxShock",
    "GdpShock",
    "HistoricalShock",
    "MacroShockFactory",
    "OtherFlowsShock",
    "PrimaryBalanceShock",
    "apply_combo_shock",
    "apply_exports_shock",
    "apply_fx_depreciation_shock",
    "apply_historical_averages_shock",
    "apply_other_flows_shock",
    "apply_primary_balance_shock",
    "apply_real_gdp_shock",
    "depreciation_of_nc_pct",
    "real_depreciation_pct",
]

_ADAPTER_EXPORTS = frozenset(
    {
        "ComboShock",
        "ExportsShock",
        "FxShock",
        "GdpShock",
        "HistoricalShock",
        "MacroShockFactory",
        "OtherFlowsShock",
        "PrimaryBalanceShock",
    }
)


def __getattr__(name: str) -> Any:
    if name in _ADAPTER_EXPORTS:
        from lic_dsf.stress.shocks import adapters

        return getattr(adapters, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
