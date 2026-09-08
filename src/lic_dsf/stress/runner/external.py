"""External scenario runner: macro → gap → ResFin → ratios."""

from __future__ import annotations

from dataclasses import dataclass

from lic_dsf.stress.context import StressContext
from lic_dsf.stress.external_dynamics import ExternalDebtDynamics
from lic_dsf.stress.external_portfolio import ExternalPortfolioAdjuster
from lic_dsf.stress.market_access import ComboMarketCost, MarketFinancingCost
from lic_dsf.stress.ratios.external import StressExternalRatios
from lic_dsf.stress.resfin import (
    ResidualFinancingEngine,
    ResidualFinancingResult,
    policy_from_spec,
)
from lic_dsf.stress.result import StressScenarioResult
from lic_dsf.stress.shocks import MacroShockFactory
from lic_dsf.stress.spec import ScenarioSpec, ShockKind

_PUBLIC_RESFIN_SHOCKS = frozenset({ShockKind.GDP, ShockKind.PRIMARY_BALANCE})


@dataclass(slots=True)
class ExternalScenarioRunner:
    """Compose macro path → external dynamics → ResFin → external ratios."""

    context: StressContext

    def run(self, spec: ScenarioSpec) -> StressScenarioResult:
        """Run one external-capable scenario end-to-end."""
        if (
            spec.couple_ext_r86
            and spec.output_binding.output_31_source == "public_external_methods"
        ):
            from lic_dsf.stress.runner.coupled import CoupledScenarioRunner

            return CoupledScenarioRunner(context=self.context).run(spec)

        shock = MacroShockFactory.from_spec(spec)
        path = shock.apply(self.context, spec)

        external = self.context.external
        if spec.fx_revalue_portfolio:
            external = ExternalPortfolioAdjuster().adjust(external, path)

        add_int = None
        residual = self.context.residual
        commercial_pv_delta = None
        commercial_ds_delta = None
        c4_pv_stress = None
        c4_ds_stress = None
        if spec.shock_kind is ShockKind.COMBO:
            add_int = ComboMarketCost().compute_from_context(
                self.context, path, external=external
            )
        elif spec.shock_kind is ShockKind.TAILORED_MARKET:
            tailored = self.context.tailored
            if tailored is not None:
                from lic_dsf.stress.market_terms import (
                    apply_c4_residual_overrides,
                    commercial_pv_delta_usd,
                    compute_c4_pv_stress_usd,
                )

                residual = apply_c4_residual_overrides(
                    self.context.residual,
                    external,
                    tailored,
                    years=path.years,
                    first_projection_year=path.first_projection_year,
                )
                commercial_pv_delta, commercial_ds_delta = commercial_pv_delta_usd(
                    external,
                    tailored,
                    years=path.years,
                    first_projection_year=path.first_projection_year,
                )
            bps = float(tailored.market_cost_bps) if tailored is not None else 0.0
            add_int = MarketFinancingCost(bps=bps).compute_from_context(
                self.context, path, external=external
            )
            if tailored is not None and add_int is not None and commercial_ds_delta is not None:
                from lic_dsf.stress.market_terms import (
                    commercial_weighted_interest_rate,
                    commercial_weighted_resfin_terms,
                )
                _mat1, _grace1, mat_r1, grace_r1 = commercial_weighted_resfin_terms(
                    external,
                    tailored,
                    years=path.years,
                    first_projection_year=path.first_projection_year,
                )
                rate1 = commercial_weighted_interest_rate(
                    external,
                    years=path.years,
                    first_projection_year=path.first_projection_year,
                ) + bps / 10_000.0
                rate2 = float(self.context.residual.avg_interest_rate) / 100.0
                mat_r2 = int(self.context.residual.avg_maturity_rounded)
                grace_r2 = int(self.context.residual.avg_grace_rounded)
                c4_pv_stress, c4_ds_stress = compute_c4_pv_stress_usd(
                    path.years,
                    path.first_projection_year,
                    commercial_ds_delta,
                    add_int,
                    rate1=rate1,
                    rate2=rate2,
                    grace1=grace_r1,
                    maturity1=mat_r1,
                    grace2=grace_r2,
                    maturity2=mat_r2,
                )

        dynamics = ExternalDebtDynamics.from_context(
            self.context,
            path,
            spec,
            additional_borrowing_interest=add_int,
            residual=residual,
        )
        if external is not self.context.external:
            dynamics.external = external
        gap = dynamics.compute_gap_converged()

        ext_engine = ResidualFinancingEngine.for_external(
            residual,
            path.years,
            external=external,
        )
        external_overlay = ext_engine.build_external_overlay(gap.gap)

        public_overlay = None
        fill = None
        public_gap = None
        converged = True
        iterations = gap.iterations

        if spec.shock_kind in _PUBLIC_RESFIN_SHOCKS:
            input6 = self.context.input6
            interactions = bool(input6.interactions_on)
            inflation = (
                float(input6.inflation_elasticity) if interactions else 0.0
            )
            market = (
                bool(self.context.market_access)
                if spec.market_access is None
                else bool(spec.market_access)
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
                external_gap=gap.gap if spec.couple_ext_r86 else None,
                input6=input6,
                inflation_elasticity=inflation,
                market_access=market,
            )
            public_overlay = pub.public
            fill = pub.fill
            public_gap = pub.public_gap
            converged = pub.converged
            iterations = pub.iterations

        resfin = ResidualFinancingResult(
            external=external_overlay,
            public=public_overlay,
            fill=fill,
            converged=converged,
            iterations=iterations,
            public_gap=public_gap,
        )
        ratios = StressExternalRatios.from_path(
            path,
            external,
            external_overlay,
            additional_borrowing_interest=add_int,
            commercial_pv_delta=commercial_pv_delta,
            commercial_ds_delta=commercial_ds_delta,
            c4_pv_stress=c4_pv_stress,
            c4_ds_stress=c4_ds_stress,
        )
        return StressScenarioResult(
            scenario_id=spec.id,
            path=path,
            external_gap=gap,
            resfin=resfin,
            external_ratios=ratios,
        )


# Alias kept for existing imports.
StressScenarioRunner = ExternalScenarioRunner

__all__ = [
    "ExternalScenarioRunner",
    "StressScenarioRunner",
]
