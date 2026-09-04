"""Coupled external↔public scenario runner."""

from __future__ import annotations

from dataclasses import dataclass

from lic_dsf.stress.context import StressContext
from lic_dsf.stress.external_dynamics import ExternalDebtDynamics
from lic_dsf.stress.external_portfolio import ExternalPortfolioAdjuster
from lic_dsf.stress.market_access import ComboMarketCost, MarketAccessAddon
from lic_dsf.stress.public_gfn import PublicGFNIdentity
from lic_dsf.stress.ratios.external import StressExternalRatios
from lic_dsf.stress.ratios.public import StressPublicRatios
from lic_dsf.stress.resfin import (
    ResidualFinancingEngine,
    ResidualFinancingResult,
    policy_from_spec,
)
from lic_dsf.stress.result import StressScenarioResult
from lic_dsf.stress.shocks import MacroShockFactory
from lic_dsf.stress.spec import ScenarioRegistry, ScenarioSpec, ShockKind

# Input 6 interactions: inflation elasticity applies only to these shocks.
_INFLATION_SHOCKS = frozenset({ShockKind.GDP, ShockKind.FX, ShockKind.COMBO})
_FX_PASSTHROUGH_SHOCKS = frozenset(
    {ShockKind.FX, ShockKind.COMBO, ShockKind.TAILORED_MARKET}
)


@dataclass(slots=True)
class CoupledScenarioRunner:
    """Run external gap then public GFN↔ResFin with optional R86 coupling.

    Used for B2 (``couple_ext_r86``) and any scenario that needs both external
    and public ratio surfaces from one pass.
    """

    context: StressContext

    def run(self, spec: ScenarioSpec) -> StressScenarioResult:
        """Run one coupled scenario end-to-end."""
        ctx = self.context
        shock = MacroShockFactory.from_spec(spec)
        path = shock.apply(ctx, spec)

        external = ctx.external
        if spec.fx_revalue_portfolio:
            external = ExternalPortfolioAdjuster().adjust(external, path)

        add_int = None
        if spec.shock_kind is ShockKind.COMBO:
            add_int = ComboMarketCost().compute_from_context(
                ctx, path, external=external
            )

        dynamics = ExternalDebtDynamics.from_context(
            ctx,
            path,
            spec,
            additional_borrowing_interest=add_int,
        )
        # Dynamics keep baseline Ext on the dataclass; swap if FX-revalued.
        if external is not ctx.external:
            dynamics.external = external
        gap = dynamics.compute_gap_converged()

        ext_engine = ResidualFinancingEngine.for_external(
            ctx.residual,
            path.years,
            external=external,
        )
        external_overlay = ext_engine.build_external_overlay(gap.gap)
        external_ratios = StressExternalRatios.from_path(
            path,
            external,
            external_overlay,
            additional_borrowing_interest=add_int,
        )

        market = ScenarioRegistry.resolve_market_access(
            spec, context_market_access=ctx.market_access
        )
        input6 = ctx.input6
        interactions = bool(input6.interactions_on)
        inflation = (
            float(input6.inflation_elasticity)
            if interactions and spec.shock_kind in _INFLATION_SHOCKS
            else 0.0
        )
        fx_passthrough = (
            float(input6.fx_passthrough)
            if interactions and spec.shock_kind in _FX_PASSTHROUGH_SHOCKS
            else 0.0
        )

        from lic_dsf.stress.public import _a1_public_gdp_lcu

        historical = spec.shock_kind is ShockKind.HISTORICAL
        gdp_lcu = _a1_public_gdp_lcu(path.baseline) if historical else None
        gfn = PublicGFNIdentity.from_path(
            path,
            input6=input6,
            inflation_elasticity=inflation,
            fx_passthrough=fx_passthrough,
            market_access=market,
            gdp_lcu=gdp_lcu,
            historical=historical,
        )
        pub_engine = ResidualFinancingEngine.for_public(
            ctx.residual,
            path.years,
            policy=policy_from_spec(spec),
            external=external,
        )
        external_gap_series = gap.gap if spec.couple_ext_r86 else None
        pub = pub_engine.solve_public_with_gfn_feedback(
            path.baseline,
            path.shocked,
            gfn=gfn,
            external_gap=external_gap_series,
            inflation_elasticity=inflation,
            market_access=market,
        )

        resfin_external_ds = None
        if market and pub.public is not None:
            pub_ds = pub_engine.solve_public_with_gfn_feedback(
                path.baseline,
                path.shocked,
                gfn=PublicGFNIdentity.from_path(
                    path,
                    input6=input6,
                    inflation_elasticity=inflation,
                    fx_passthrough=fx_passthrough,
                    market_access=True,
                    include_external_add_int=False,
                    gdp_lcu=gfn.gdp_lcu(),
                    historical=historical,
                    external=external,
                ),
                external_gap=external_gap_series,
                inflation_elasticity=inflation,
                market_access=True,
                include_external_add_int=False,
            )
            resfin_external_ds = pub_ds.public

        assert pub.public is not None
        # MarketAccessAddon documents the B2 add.int surface; ratios already
        # consume market_access + resfin_external_ds via StressPublicBook.
        _addon = MarketAccessAddon.from_path(path, pub.public, enabled=market)

        resfin = ResidualFinancingResult(
            external=external_overlay,
            public=pub.public,
            fill=pub.fill,
            converged=pub.converged,
            iterations=pub.iterations,
            public_gap=pub.public_gap,
        )
        public_ratios = StressPublicRatios.from_path(
            path,
            external,
            pub.public,
            inflation_elasticity=inflation,
            fx_passthrough=fx_passthrough,
            market_access=_addon.enabled,
            resfin_external_ds=resfin_external_ds,
            gfn=gfn,
            scenario_id=f"{spec.id}_pub",
        )
        return StressScenarioResult(
            scenario_id=spec.id,
            path=path,
            external_gap=gap,
            resfin=resfin,
            external_ratios=external_ratios,
            public_ratios=public_ratios,
        )


__all__ = ["CoupledScenarioRunner"]
