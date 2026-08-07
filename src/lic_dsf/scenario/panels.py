"""Output 6 probability panels."""

from __future__ import annotations

import pandas as pd

from lic_dsf.scenario.probability import (
    ProbabilityAssumptions,
    borderline_bands,
    path_breach_probabilities,
)


def probability_panel(
    paths: dict[str, pd.Series],
    threshold: float,
    *,
    indicator: str = "pv_debt_to_gdp",
    assumptions: ProbabilityAssumptions | None = None,
) -> pd.DataFrame:
    """Output 6 shaped probability panel for one indicator.

    Args:
        paths: Map of scenario id → ratio series (baseline, MX shock, …).
        threshold: Applicable threshold.
        indicator: Indicator label.
        assumptions: Probability assumptions (incl. bandwidth).

    Returns:
        DataFrame with path levels, bands, and probabilities.
    """
    assumptions = assumptions or ProbabilityAssumptions()
    lower, upper = borderline_bands(threshold, assumptions.bandwidth)
    frames: dict[str, pd.Series] = {}
    for name, series in paths.items():
        frames[f"{name} level"] = series.astype(float)
        frames[f"{name} prob"] = path_breach_probabilities(
            series, threshold, assumptions
        )
    frames["threshold"] = pd.Series(threshold, index=next(iter(paths.values())).index)
    frames["lower_band"] = pd.Series(lower, index=frames["threshold"].index)
    frames["upper_band"] = pd.Series(upper, index=frames["threshold"].index)
    out = pd.DataFrame(frames).T
    out.attrs["indicator"] = indicator
    return out
