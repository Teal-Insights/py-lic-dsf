"""Output 7 risk rating summary (mechanical + judgement API)."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from lic_dsf.rating.chart_data import MechanicalRatingResult, RiskRating
from lic_dsf.rating.classification import (
    ApplicableThresholds,
    DebtCarryingCapacity,
)


@dataclass(slots=True)
class RiskRatingSummary:
    """Output 7 mechanical ratings plus optional judgement overrides.

    Attributes:
        mechanical: Chart Data mechanical ratings.
        thresholds: Applicable CI thresholds echo.
        dcc: Debt-carrying capacity.
        ci_score: Optional CI score.
        final_external: Final external rating (defaults to mechanical).
        final_overall: Final overall rating (defaults to mechanical).
        judgement_applied: Whether judgement overrides were set.
        judgement_note: Free-text judgement description.
        moderate_granularity: Optional Output 5-1 granularity label.
    """

    mechanical: MechanicalRatingResult
    thresholds: ApplicableThresholds
    dcc: DebtCarryingCapacity
    ci_score: float | None = None
    final_external: RiskRating | None = None
    final_overall: RiskRating | None = None
    judgement_applied: bool = False
    judgement_note: str = ""
    moderate_granularity: str | None = None

    def __post_init__(self) -> None:
        if self.final_external is None:
            self.final_external = self.mechanical.external
        if self.final_overall is None:
            self.final_overall = self.mechanical.overall

    def apply_judgement(
        self,
        *,
        final_external: RiskRating | None = None,
        final_overall: RiskRating | None = None,
        note: str = "",
    ) -> RiskRatingSummary:
        """Return a copy with judgement overrides (yellow-cell API).

        Args:
            final_external: Override for final external rating.
            final_overall: Override for final overall rating.
            note: Judgement description for the write-up.

        Returns:
            Updated summary.
        """
        return replace(
            self,
            final_external=final_external or self.final_external,
            final_overall=final_overall or self.final_overall,
            judgement_applied=True,
            judgement_note=note or self.judgement_note,
        )


def risk_summary_panel(summary: RiskRatingSummary) -> pd.DataFrame:
    """Output 7 shaped summary table (no i18n chrome)."""
    mech = summary.mechanical
    rows = {
        "Mechanical external": mech.external.label,
        "Final external": summary.final_external.label
        if summary.final_external
        else mech.external.label,
        "Mechanical fiscal": mech.fiscal.label,
        "Mechanical overall": mech.overall.label,
        "Final overall": summary.final_overall.label
        if summary.final_overall
        else mech.overall.label,
        "Judgement applied": "Yes" if summary.judgement_applied else "No",
        "Debt carrying capacity": summary.dcc.value,
        "CI score": summary.ci_score,
        "Threshold PV/GDP": summary.thresholds.pv_debt_to_gdp,
        "Threshold PV/exports": summary.thresholds.pv_debt_to_exports,
        "Threshold DS/exports": summary.thresholds.debt_service_to_exports,
        "Threshold DS/revenue": summary.thresholds.debt_service_to_revenue,
        "Threshold public PV/GDP": summary.thresholds.public_pv_debt_to_gdp,
        "Moderate granularity": summary.moderate_granularity,
        "Judgement note": summary.judgement_note or None,
    }
    return pd.Series(rows, name="Output 7").to_frame()
