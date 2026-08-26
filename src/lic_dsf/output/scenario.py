"""Output 6 probability panels."""

from __future__ import annotations

import pandas as pd

from lic_dsf.scenario.probability import (
    EXCEL_PROBABILITY_THRESHOLDS,
    DistressCoefficients,
    DistressCovariates,
    ProbabilityAssumptions,
    borderline_bands,
    path_breach_probabilities,
    path_distress_probabilities,
)

_EXTERNAL_DEBT_SCENARIO_ROWS: dict[str, str] = {
    "baseline level": "Baseline",
    "historical level": "Historical scenario",
    "mx_shock level": "MX shock Standard&Tailored",
    "threshold": "Threshold",
    "lower_band": "Lower Band",
    "upper_band": "Upper Band",
}

_PROBABILITY_ROWS: dict[str, str] = {
    "baseline prob": "Baseline",
    "historical prob": "Historical scenario",
    "mx_shock prob": "MX shock Standard&Tailored",
}


def probability_panel(
    paths: dict[str, pd.Series],
    threshold: float,
    *,
    indicator: str = "pv_debt_to_gdp",
    assumptions: ProbabilityAssumptions | None = None,
    covariates: DistressCovariates | None = None,
    coefficients: DistressCoefficients | None = None,
) -> pd.DataFrame:
    """Output 6 shaped probability panel for one indicator.

    When `covariates` is set, probabilities use the Excel ``NORMDIST``
    regression (CPIA, growth, reserves/imports, remittances, world growth).
    Otherwise they use the simple ``Φ((ratio − T) / T)`` helper.

    Args:
        paths: Map of scenario id → ratio series (baseline, MX shock, …).
        threshold: Applicable threshold.
        indicator: Indicator label.
        assumptions: Probability assumptions (incl. bandwidth).
        covariates: Excel Probability approach period averages.
        coefficients: Indicator-specific ``NORMDIST`` coefficients.

    Returns:
        DataFrame with path levels, bands, and probabilities.
    """
    assumptions = assumptions or ProbabilityAssumptions()
    lower, upper = borderline_bands(threshold, assumptions.bandwidth)
    frames: dict[str, pd.Series] = {}
    for name, series in paths.items():
        frames[f"{name} level"] = series.astype(float)
        if covariates is not None:
            frames[f"{name} prob"] = path_distress_probabilities(
                series,
                covariates,
                coefficients,
                indicator=indicator,
            )
        else:
            frames[f"{name} prob"] = path_breach_probabilities(
                series, threshold, assumptions
            )
    frames["threshold"] = pd.Series(threshold, index=next(iter(paths.values())).index)
    frames["lower_band"] = pd.Series(lower, index=frames["threshold"].index)
    frames["upper_band"] = pd.Series(upper, index=frames["threshold"].index)
    out = pd.DataFrame(frames).T
    out.attrs["indicator"] = indicator
    return out


def external_debt_scenarios_table(panel: pd.DataFrame) -> pd.DataFrame:
    """External debt scenario levels from a `probability_panel` (Excel rows 27–32).

    Args:
        panel: Full Output 6 panel for one indicator.

    Returns:
        Ratio paths, CI threshold, and borderline bands with Excel row labels.
    """
    rows = [row for row in _EXTERNAL_DEBT_SCENARIO_ROWS if row in panel.index]
    out = panel.loc[rows].copy()
    out.index = [_EXTERNAL_DEBT_SCENARIO_ROWS[row] for row in rows]
    return out


def probabilities_table(
    panel: pd.DataFrame,
    *,
    indicator: str | None = None,
) -> pd.DataFrame:
    """Distress probabilities from a `probability_panel` (Excel rows 84–87).

    Probabilities are scaled to percent to match the Probability approach sheet.
    The trailing ``Threshold`` row is the template cutoff in ``O64:O67`` (constant
    across years), not the debt-burden threshold.

    Args:
        panel: Full Output 6 panel for one indicator.
        indicator: Indicator key for the probability cutoff; defaults to
            ``panel.attrs["indicator"]``.

    Returns:
        Scenario probabilities (percent) plus the probability threshold row.
    """
    indicator = indicator or str(panel.attrs.get("indicator", "pv_debt_to_gdp"))
    prob_rows = [row for row in _PROBABILITY_ROWS if row in panel.index]
    out = panel.loc[prob_rows].astype(float) * 100.0
    out.index = [_PROBABILITY_ROWS[row] for row in prob_rows]
    cutoff = EXCEL_PROBABILITY_THRESHOLDS[indicator]
    out.loc["Threshold"] = pd.Series(cutoff, index=out.columns, dtype=float)
    return out
