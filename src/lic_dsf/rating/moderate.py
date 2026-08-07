"""Output 5-1 moderate-risk granularity helpers."""

from __future__ import annotations

from enum import Enum

import pandas as pd

from lic_dsf.rating.chart_data import RiskRating


class ModerateSpace(str, Enum):
    """Space-to-absorb-shocks granularity for moderate-risk countries."""

    SUBSTANTIAL = "Substantial space"
    SOME = "Some space"
    LIMITED = "Limited space"
    NOT_APPLICABLE = "n.a."


def moderate_space_from_headroom(
    baseline_max: float,
    threshold: float,
    *,
    substantial_pct: float = 0.20,
    some_pct: float = 0.10,
) -> ModerateSpace:
    """Classify moderate-risk space from baseline headroom to threshold.

    Args:
        baseline_max: Peak baseline ratio over the rating horizon.
        threshold: Applicable threshold.
        substantial_pct: Headroom share of threshold for substantial space.
        some_pct: Headroom share for some space.

    Returns:
        Moderate-space category.
    """
    if threshold <= 0:
        return ModerateSpace.NOT_APPLICABLE
    headroom = (threshold - baseline_max) / threshold
    if headroom >= substantial_pct:
        return ModerateSpace.SUBSTANTIAL
    if headroom >= some_pct:
        return ModerateSpace.SOME
    return ModerateSpace.LIMITED


def moderate_panel(
    *,
    mechanical_external: RiskRating,
    baseline_pv_gdp: pd.Series,
    threshold_pv_gdp: float,
    rating_years: list[int] | None = None,
) -> pd.DataFrame:
    """Output 5-1 moderate granularity panel.

    Only meaningful when mechanical external rating is Moderate; otherwise
    returns ``n.a.``.

    Args:
        mechanical_external: Mechanical external rating.
        baseline_pv_gdp: Baseline PV/GDP path.
        threshold_pv_gdp: Applicable PV/GDP threshold.
        rating_years: Optional horizon.

    Returns:
        Single-column summary DataFrame.
    """
    series = baseline_pv_gdp.astype(float)
    if rating_years is not None:
        series = series.reindex(rating_years).dropna()
    peak = float(series.max()) if len(series) else float("nan")
    if mechanical_external != RiskRating.MODERATE:
        space = ModerateSpace.NOT_APPLICABLE
    else:
        space = moderate_space_from_headroom(peak, threshold_pv_gdp)
    return pd.Series(
        {
            "Mechanical external": mechanical_external.label,
            "Baseline peak PV/GDP": peak,
            "Threshold PV/GDP": threshold_pv_gdp,
            "Space to absorb shock": space.value,
        },
        name="Output 5-1",
    ).to_frame()
