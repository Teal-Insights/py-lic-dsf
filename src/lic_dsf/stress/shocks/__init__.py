"""Concrete ``MacroShock`` adapters.

Logic is re-exported from ``lic_dsf.stress.macro_shocks``; adapters wrap those
helpers into the path / metadata objects used by scenario runners.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import lic_dsf.stress.macro_shocks as _legacy
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.pv.macro_debt.types import MacroDebtInputs
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.path import (
    ShockedMacroPath,
    ShockMetadata,
    projection_shock_window,
)
from lic_dsf.stress.spec import ScenarioSpec, ShockKind


def _metadata(
    ctx: StressContext,
    *,
    fx_depreciation_pct: float = 0.0,
    exports_shocked_in_levels: bool = False,
) -> ShockMetadata:
    window = projection_shock_window(
        ctx.macro.inputs.years, ctx.macro.inputs.first_projection_year
    )
    return ShockMetadata(
        shock_window_years=window,
        fx_depreciation_pct=float(fx_depreciation_pct),
        threshold_rule=ctx.input6.threshold_rule,
        interactions_on=bool(ctx.input6.interactions_on),
        exports_shocked_in_levels=exports_shocked_in_levels,
    )


def _path(
    ctx: StressContext,
    shocked_inputs: MacroDebtInputs,
    metadata: ShockMetadata,
) -> ShockedMacroPath:
    shocked = MacroDebtBook(inputs=shocked_inputs, external=ctx.external)
    return ShockedMacroPath(baseline=ctx.macro, shocked=shocked, metadata=metadata)


@dataclass(frozen=True, slots=True)
class HistoricalShock:
    """A1 historical-averages path."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_historical_averages_shock(ctx.macro.inputs)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class GdpShock:
    """B1 real GDP growth shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_real_gdp_shock(ctx.macro.inputs, ctx.input6)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class PrimaryBalanceShock:
    """B2 primary balance shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_primary_balance_shock(ctx.macro.inputs, ctx.input6)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class ExportsShock:
    """B3 exports shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_exports_shock(ctx.macro.inputs, ctx.input6)
        return _path(
            ctx,
            inputs,
            _metadata(ctx, exports_shocked_in_levels=True),
        )


@dataclass(frozen=True, slots=True)
class OtherFlowsShock:
    """B4 other flows (transfers / FDI) shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_other_flows_shock(ctx.macro.inputs, ctx.input6)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class FxShock:
    """B5 FX depreciation shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_fx_depreciation_shock(ctx.macro.inputs, ctx.input6)
        return _path(
            ctx,
            inputs,
            _metadata(ctx, fx_depreciation_pct=ctx.input6.fx_depreciation_pct),
        )


@dataclass(frozen=True, slots=True)
class ComboShock:
    """B6 half-size combined shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        inputs = _legacy.apply_combo_shock(ctx.macro.inputs, ctx.input6)
        return _path(
            ctx,
            inputs,
            _metadata(
                ctx,
                fx_depreciation_pct=ctx.input6.combo_fx_depreciation_pct,
                exports_shocked_in_levels=True,
            ),
        )


class MacroShockFactory:
    """Build a :class:`~lic_dsf.stress.path.MacroShock` from a scenario recipe."""

    _BY_KIND: ClassVar[dict[ShockKind, type]] = {
        ShockKind.HISTORICAL: HistoricalShock,
        ShockKind.GDP: GdpShock,
        ShockKind.PRIMARY_BALANCE: PrimaryBalanceShock,
        ShockKind.EXPORTS: ExportsShock,
        ShockKind.OTHER_FLOWS: OtherFlowsShock,
        ShockKind.FX: FxShock,
        ShockKind.COMBO: ComboShock,
    }

    @classmethod
    def from_spec(cls, spec: ScenarioSpec) -> object:
        """Return the concrete shock adapter for ``spec.shock_kind``."""
        adapter = cls._BY_KIND.get(spec.shock_kind)
        if adapter is None:
            from lic_dsf.stress.tailored import TAILORED_SHOCKS

            adapter = TAILORED_SHOCKS.get(spec.shock_kind)
        if adapter is None:
            raise NotImplementedError(
                f"no MacroShock adapter for shock kind {spec.shock_kind!r}"
            )
        return adapter()


# Re-export shock helpers used by tests and package __init__.
apply_real_gdp_shock = _legacy.apply_real_gdp_shock
apply_primary_balance_shock = _legacy.apply_primary_balance_shock
apply_exports_shock = _legacy.apply_exports_shock
apply_other_flows_shock = _legacy.apply_other_flows_shock
apply_fx_depreciation_shock = _legacy.apply_fx_depreciation_shock
apply_combo_shock = _legacy.apply_combo_shock
apply_historical_averages_shock = _legacy.apply_historical_averages_shock
real_depreciation_pct = _legacy.real_depreciation_pct
depreciation_of_nc_pct = _legacy.depreciation_of_nc_pct

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
