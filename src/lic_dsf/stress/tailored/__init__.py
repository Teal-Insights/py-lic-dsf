"""Tailored A2/C* shock adapters and applicability helpers (Phase 8)."""

from __future__ import annotations

from dataclasses import dataclass

from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.pv.macro_debt.types import MacroDebtInputs
from lic_dsf.scenario.customized import apply_customized_deltas
from lic_dsf.stress.tailored_params import TailoredParams
import lic_dsf.stress.tailored_params as _legacy
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
    ds_revenue_uses_baseline: bool = False,
    lcu_deflator_growth=None,
    primary_exp_gdp_denominator=None,
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
        ds_revenue_uses_baseline=ds_revenue_uses_baseline,
        lcu_deflator_growth=lcu_deflator_growth,
        primary_exp_gdp_denominator=primary_exp_gdp_denominator,
    )


def _path(
    ctx: StressContext,
    shocked_inputs: MacroDebtInputs,
    metadata: ShockMetadata,
) -> ShockedMacroPath:
    shocked = MacroDebtBook(inputs=shocked_inputs, external=ctx.external)
    return ShockedMacroPath(baseline=ctx.macro, shocked=shocked, metadata=metadata)


def applicable_tailored_ids(params: TailoredParams | None) -> tuple[str, ...]:
    """Return tailored scenario ids that should run for ``params``.

    A2 and C1 always run. C2–C4 follow Input 6 On/Off flags (Excel ``n.a.``).
    """
    out: list[str] = ["A2_Custom", "C1_CombinedCL"]
    if params is None:
        return tuple(out)
    if params.natural_disaster:
        out.append("C2_NaturalDisaster")
    if params.commodity:
        out.append("C3_Commodity")
    if params.market:
        out.append("C4_Market")
    return tuple(out)


def _require_params(ctx: StressContext) -> TailoredParams:
    if ctx.tailored is None:
        raise ValueError("StressContext.tailored is required for tailored shocks")
    return ctx.tailored


@dataclass(frozen=True, slots=True)
class CustomScenarioShock:
    """A2 customized scenario; baseline path when ``custom_spec`` is None."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        if ctx.custom_spec is None:
            return ShockedMacroPath(
                baseline=ctx.macro,
                shocked=ctx.macro,
                metadata=_metadata(ctx),
            )
        inputs = apply_customized_deltas(ctx.macro.inputs, ctx.custom_spec)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class CombinedCLShock:
    """C1 combined contingent-liability shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        params = _require_params(ctx)
        inputs = _legacy.apply_combined_cl_shock(ctx.macro.inputs, params)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class NaturalDisasterShock:
    """C2 natural-disaster shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        params = _require_params(ctx)
        inputs = _legacy.apply_natural_disaster_shock(ctx.macro.inputs, params)
        return _path(ctx, inputs, _metadata(ctx))


@dataclass(frozen=True, slots=True)
class CommodityShock:
    """C3 commodity-price export shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        params = _require_params(ctx)
        inputs = _legacy.apply_commodity_price_shock(
            ctx.macro.inputs, params, ctx.input6
        )
        deflator = _legacy.commodity_public_lcu_deflator_growth(ctx.macro, params)
        return _path(
            ctx,
            inputs,
            _metadata(
                ctx,
                exports_shocked_in_levels=True,
                lcu_deflator_growth=deflator,
            ),
        )


@dataclass(frozen=True, slots=True)
class MarketFinancingShock:
    """C4 market-financing FX shock."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        del spec
        params = _require_params(ctx)
        inputs = _legacy.apply_market_financing_shock(
            ctx.macro.inputs, params, ctx.input6
        )
        return _path(
            ctx,
            inputs,
            _metadata(
                ctx,
                fx_depreciation_pct=params.market_fx_depreciation_pct,
                # Match Excel C4 R94 / R99 (baseline USD revenue denominator).
                ds_revenue_uses_baseline=True,
            ),
        )


TAILORED_SHOCKS: dict[ShockKind, type] = {
    ShockKind.TAILORED_CUSTOM: CustomScenarioShock,
    ShockKind.TAILORED_COMBINED_CL: CombinedCLShock,
    ShockKind.TAILORED_NATURAL_DISASTER: NaturalDisasterShock,
    ShockKind.TAILORED_COMMODITY: CommodityShock,
    ShockKind.TAILORED_MARKET: MarketFinancingShock,
}

__all__ = [
    "CombinedCLShock",
    "CommodityShock",
    "CustomScenarioShock",
    "MarketFinancingShock",
    "NaturalDisasterShock",
    "TAILORED_SHOCKS",
    "TailoredParams",
    "applicable_tailored_ids",
]
