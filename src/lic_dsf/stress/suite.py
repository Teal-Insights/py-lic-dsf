"""Batch stress suite: standard + tailored → Output 3-x tables."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from lic_dsf.scenario.customized import CustomizedScenarioSpec
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.output_map import (
    build_output31_external_table,
    build_output32_table,
)
from lic_dsf.stress.result import StressScenarioResult
from lic_dsf.stress.runner.coupled import CoupledScenarioRunner
from lic_dsf.stress.runner.external import ExternalScenarioRunner
from lic_dsf.stress.runner.public import PublicScenarioRunner
from lic_dsf.stress.spec import ScenarioRegistry
from lic_dsf.stress.tailored import applicable_tailored_ids


@dataclass(slots=True)
class StressSuite:
    """Batch runners over the scenario registry."""

    context: StressContext

    def run_external_standard(self) -> dict[str, StressScenarioResult]:
        """Run all standard scenarios that feed Output 3-1 from external books.

        Skips B2 (``public_external_methods``).
        """
        runner = ExternalScenarioRunner(context=self.context)
        out: dict[str, StressScenarioResult] = {}
        for scenario_id, spec in ScenarioRegistry.STANDARD.items():
            if spec.output_binding.output_31_source != "external":
                continue
            out[scenario_id] = runner.run(spec)
        return out

    def run_public_standard(self) -> dict[str, StressScenarioResult]:
        """Run standard public scenarios that own a public B-sheet path.

        B3/B4 Output 3-2 uses the external ResFin overlay on baseline public
        (Excel ``Baseline - public`` R91/R92); those ids are filled by
        :meth:`build_output32` via the external runner.
        """
        runner = PublicScenarioRunner(context=self.context)
        out: dict[str, StressScenarioResult] = {}
        for scenario_id in (
            "A1_Historical",
            "B1_GDP",
            "B2_PrimaryBalance",
            "B5_FX",
            "B6_Combo",
        ):
            out[scenario_id] = runner.run(ScenarioRegistry.get(scenario_id))
        return out

    def run_tailored_external(
        self,
        *,
        custom_spec: CustomizedScenarioSpec | None = None,
    ) -> dict[str, StressScenarioResult]:
        """A2 + C1 always; C2–C4 when Input 6 marks them applicable."""
        ctx = self.context
        if custom_spec is not None and custom_spec is not ctx.custom_spec:
            ctx = replace(ctx, custom_spec=custom_spec)
        runner = ExternalScenarioRunner(context=ctx)
        out: dict[str, StressScenarioResult] = {}
        for scenario_id in applicable_tailored_ids(ctx.tailored):
            out[scenario_id] = runner.run(ScenarioRegistry.get(scenario_id))
        return out

    def run_tailored_public(
        self,
        *,
        custom_spec: CustomizedScenarioSpec | None = None,
    ) -> dict[str, StressScenarioResult]:
        """A2 + C1 always; C2–C4 when Input 6 marks them applicable."""
        ctx = self.context
        if custom_spec is not None and custom_spec is not ctx.custom_spec:
            ctx = replace(ctx, custom_spec=custom_spec)
        runner = PublicScenarioRunner(context=ctx)
        out: dict[str, StressScenarioResult] = {}
        for scenario_id in applicable_tailored_ids(ctx.tailored):
            out[scenario_id] = runner.run(ScenarioRegistry.get(scenario_id))
        return out

    def run_all(
        self,
        *,
        public_custom_spec: CustomizedScenarioSpec | None = None,
    ) -> dict[str, StressScenarioResult]:
        """Run standard external+public and applicable tailored scenarios.

        B2 uses :class:`CoupledScenarioRunner` via the public runner. Tailored
        public A2 may use a separate ``public_custom_spec`` (Excel public sheet).
        """
        out: dict[str, StressScenarioResult] = {}
        out.update(self.run_external_standard())
        public = self.run_public_standard()
        out.update(public)
        out.update(self.run_tailored_external())
        # Public tailored may need a different A2 spec than external.
        pub_tailored = self.run_tailored_public(custom_spec=public_custom_spec)
        for sid, result in pub_tailored.items():
            # Prefer public ratios when both external+public ran the same id.
            if sid in out and result.public_ratios is not None:
                prior = out[sid]
                out[sid] = StressScenarioResult(
                    scenario_id=result.scenario_id,
                    path=result.path,
                    external_gap=prior.external_gap
                    if prior.external_gap is not None
                    else result.external_gap,
                    resfin=result.resfin,
                    external_ratios=prior.external_ratios,
                    public_ratios=result.public_ratios,
                )
            else:
                out[sid] = result
        return out

    def build_output31(
        self,
        *,
        thresholds: dict[str, float] | None = None,
    ) -> pd.DataFrame:
        """Build Output 3-1 from a full suite run (incl. tailored external)."""
        external = self.run_external_standard()
        tailored = self.run_tailored_external()
        external.update(tailored)
        public_for_o31: dict[str, StressScenarioResult] = {}
        b2 = CoupledScenarioRunner(context=self.context).run(
            ScenarioRegistry.get("B2_PrimaryBalance")
        )
        public_for_o31["B2_PrimaryBalance"] = b2
        # C1 runs via tailored → CoupledScenarioRunner; prefer its public ratios.
        c1 = tailored.get("C1_CombinedCL")
        if c1 is not None and c1.public_ratios is not None:
            public_for_o31["C1_CombinedCL"] = c1
            external.pop("C1_CombinedCL", None)
        return build_output31_external_table(
            self.context.ext_base,
            external,
            public_results=public_for_o31,
            thresholds=thresholds,
        )

    def build_output32(
        self,
        *,
        public_threshold: float | None = None,
        public_custom_spec: CustomizedScenarioSpec | None = None,
    ) -> pd.DataFrame:
        """Build Output 3-2 from standard + tailored public runs.

        B3/B4/C4 are external ResFin overlays on baseline public (Excel
        ``Baseline - public`` R91–R93), so their rows come from
        :class:`ExternalScenarioRunner` after tailored public runs.
        """
        results = self.run_public_standard()
        results.update(self.run_tailored_public(custom_spec=public_custom_spec))
        ext_runner = ExternalScenarioRunner(context=self.context)
        for scenario_id in ("B3_Exports", "B4_OtherFlows", "C4_Market"):
            results[scenario_id] = ext_runner.run(ScenarioRegistry.get(scenario_id))
        return build_output32_table(
            self.context.pub_base,
            results,
            public_threshold=public_threshold,
        )


def build_output31_from_suite(
    workbook: str | Path,
) -> pd.DataFrame:
    """Convenience: workbook → Output 3-1 MultiIndex table via StressSuite."""
    from lic_dsf.load import load_ci_summary

    ctx = StressContext.from_workbook(workbook)
    thresholds = load_ci_summary(workbook).thresholds.as_dict()
    return StressSuite(context=ctx).build_output31(thresholds=thresholds)


def build_output32_from_suite(
    workbook: str | Path,
) -> pd.DataFrame:
    """Convenience: workbook → Output 3-2 MultiIndex table via StressSuite."""
    from lic_dsf.load import load_ci_summary
    from lic_dsf.load.tailored import load_customized_public_spec

    ctx = StressContext.from_workbook(workbook)
    thresh = load_ci_summary(workbook).thresholds.public_pv_debt_to_gdp
    public_spec = load_customized_public_spec(workbook)
    return StressSuite(context=ctx).build_output32(
        public_threshold=float(thresh) if thresh is not None else None,
        public_custom_spec=public_spec,
    )


__all__ = [
    "StressSuite",
    "build_output31_from_suite",
    "build_output32_from_suite",
]
