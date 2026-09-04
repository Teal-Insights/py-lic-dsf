"""Unified scenario run result."""

from __future__ import annotations

from dataclasses import dataclass

from lic_dsf.stress.external_dynamics import ExternalGapResult
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.ratios.external import StressExternalRatios
from lic_dsf.stress.ratios.public import StressPublicRatios
from lic_dsf.stress.resfin import ResidualFinancingResult
from lic_dsf.stress.types import StressScenarioId


@dataclass(frozen=True, slots=True)
class StressScenarioResult:
    """Full pipeline output for one stress scenario."""

    scenario_id: StressScenarioId
    path: ShockedMacroPath
    external_gap: ExternalGapResult
    resfin: ResidualFinancingResult
    external_ratios: StressExternalRatios | None = None
    public_ratios: StressPublicRatios | None = None


# Alias kept for existing imports.
ScenarioRunResult = StressScenarioResult

__all__ = ["ScenarioRunResult", "StressScenarioResult"]
