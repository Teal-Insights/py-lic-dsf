"""Public scenario runner: macro → GFN ↔ ResFin → public ratios (Phase 6+7)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.stress.context import StressContext
from lic_dsf.stress.external_dynamics import ExternalDebtDynamics, ExternalGapResult
from lic_dsf.stress.external_portfolio import ExternalPortfolioAdjuster
from lic_dsf.stress.market_access import ComboMarketCost, MarketAccessAddon
from lic_dsf.stress.public_gfn import PublicGFNIdentity
from lic_dsf.stress.ratios.public import StressPublicRatios
from lic_dsf.stress.resfin import (
    ResidualFinancingEngine,
    ResidualFinancingResult,
    policy_from_spec,
)
from lic_dsf.stress.result import StressScenarioResult
from lic_dsf.stress.shocks import MacroShockFactory
from lic_dsf.stress.spec import ScenarioRegistry, ScenarioSpec, ShockKind

# Legacy `_run_public_stress` only passes inflation elasticity for these shocks.
_INFLATION_SHOCKS = frozenset({ShockKind.GDP, ShockKind.FX, ShockKind.COMBO})
_FX_PASSTHROUGH_SHOCKS = frozenset(
    {ShockKind.FX, ShockKind.COMBO, ShockKind.TAILORED_MARKET}
)


def _zero_gap(years: tuple[int, ...]) -> ExternalGapResult:
    z = pd.Series(0.0, index=list(years), dtype=float)
    return ExternalGapResult(
        gap=z, resfin_interest=z.copy(), iterations=0, resfin_pv=z.copy()
    )


def _external_dsa_gap_for_public_split(
    context: StressContext,
    path: object,
    spec: ScenarioSpec,
    external: object,
) -> pd.Series | None:
    """External DSA R86 (USD) for capped public ResFin modality selection.

    Excel ``PV_ResFin_pub`` row 69 / B6 row 210 feeds ``split_residual_financing``
    when modality 1 applies. B1 sets ``ext_r86_zero``; B5/B6/A1-style public runs
    need the converged external gap even when ``couple_ext_r86`` is false.
    """
    if spec.ext_r86_zero:
        return None
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.stress.path import ShockedMacroPath

    assert isinstance(path, ShockedMacroPath)
    assert isinstance(external, ExternalDebtBook)
    add_int = None
    if spec.shock_kind is ShockKind.COMBO:
        add_int = ComboMarketCost().compute_from_context(
            context, path, external=external
        )
    dynamics = ExternalDebtDynamics.from_context(
        context,
        path,
        spec,
        additional_borrowing_interest=add_int,
    )
    if external is not context.external:
        dynamics.external = external
    return dynamics.compute_gap_converged().gap


@dataclass(slots=True)
class PublicScenarioRunner:
    """Compose macro path → public GFN/ResFin fixed-point → public ratios."""

    context: StressContext

    def run(self, spec: ScenarioSpec) -> StressScenarioResult:
        """Run one public-capable scenario end-to-end.

        When ``couple_ext_r86`` is set (B2), delegates to
        :class:`~lic_dsf.stress.runner.coupled.CoupledScenarioRunner` so the
        Absolute public split sees the Phase 3 external gap.
        """
        if not spec.implemented:
            raise NotImplementedError(
                f"scenario {spec.id!r} is a tailored stub; fill in Phase 8"
            )
        if spec.couple_ext_r86:
            from lic_dsf.stress.runner.coupled import CoupledScenarioRunner

            return CoupledScenarioRunner(context=self.context).run(spec)

        shock = MacroShockFactory.from_spec(spec)
        path = shock.apply(self.context, spec)

        # Excel C3_commodity_prices_pub R20 uses B1_GDP_pub R41 as the
        # expenditure denominator (sheet copied from B1 with that ref kept).
        if spec.shock_kind is ShockKind.TAILORED_COMMODITY:
            from dataclasses import replace as _dc_replace

            from lic_dsf.stress.path import ShockedMacroPath

            b1_spec = ScenarioRegistry.get("B1_GDP")
            b1_path = MacroShockFactory.from_spec(b1_spec).apply(
                self.context, b1_spec
            )
            b1_infl = (
                float(self.context.input6.inflation_elasticity)
                if self.context.input6.interactions_on
                else 0.0
            )
            b1_gdp = PublicGFNIdentity.from_path(
                b1_path,
                input6=self.context.input6,
                inflation_elasticity=b1_infl,
            ).gdp_lcu()
            path = ShockedMacroPath(
                baseline=path.baseline,
                shocked=path.shocked,
                metadata=_dc_replace(
                    path.metadata, primary_exp_gdp_denominator=b1_gdp
                ),
            )

        external = self.context.external
        if spec.fx_revalue_portfolio:
            external = ExternalPortfolioAdjuster().adjust(external, path)

        market = ScenarioRegistry.resolve_market_access(
            spec, context_market_access=self.context.market_access
        )
        input6 = self.context.input6
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

        external_dsa_gap = _external_dsa_gap_for_public_split(
            self.context, path, spec, external
        )
        external_gap = _zero_gap(path.years)

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
            external=external,
            external_dsa_borrowing_usd=external_dsa_gap,
        )
        pub_engine = ResidualFinancingEngine.for_public(
            self.context.residual,
            path.years,
            policy=policy_from_spec(spec),
            external=external,
        )
        pub = pub_engine.solve_public_with_gfn_feedback(
            path.baseline,
            path.shocked,
            gfn=gfn,
            external_gap=external_dsa_gap,
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
                    external_dsa_borrowing_usd=external_dsa_gap,
                ),
                external_gap=external_dsa_gap,
                inflation_elasticity=inflation,
                market_access=True,
                include_external_add_int=False,
            )
            resfin_external_ds = pub_ds.public

        assert pub.public is not None
        _addon = MarketAccessAddon.from_path(path, pub.public, enabled=market)
        resfin = ResidualFinancingResult(
            external=None,
            public=pub.public,
            fill=pub.fill,
            converged=pub.converged,
            iterations=pub.iterations,
            public_gap=pub.public_gap,
        )
        ratios = StressPublicRatios.from_path(
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
            external_gap=external_gap,
            resfin=resfin,
            public_ratios=ratios,
        )


__all__ = ["PublicScenarioRunner"]
