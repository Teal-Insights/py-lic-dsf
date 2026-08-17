"""Probability approach (borderline / Output 6)."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt

import pandas as pd


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via ``erf`` (Excel ``NORMDIST`` / ``NORMSDIST``)."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


@dataclass(frozen=True, slots=True)
class ProbabilityAssumptions:
    """Probit-style coefficients for the probability approach.

    Attributes:
        intercept: Constant term.
        slope: Coefficient on (threshold − ratio) distance.
        bandwidth: Borderline bandwidth as a share of the threshold.
    """

    intercept: float = 0.0
    slope: float = 1.0
    bandwidth: float = 0.1


def borderline_bands(
    threshold: float,
    bandwidth: float = 0.1,
) -> tuple[float, float]:
    """Lower/upper borderline bands around a threshold.

    Excel Probability approach: ``lower = (1 − bw/2) × T``,
    ``upper = (1 + bw/2) × T``.

    Args:
        threshold: Applicable threshold.
        bandwidth: Relative bandwidth (default 0.1).

    Returns:
        ``(lower, upper)`` band edges.
    """
    half = bandwidth / 2.0
    return (1.0 - half) * threshold, (1.0 + half) * threshold


def breach_probability(
    ratio: float,
    threshold: float,
    assumptions: ProbabilityAssumptions | None = None,
) -> float:
    """Probability of distress given ratio vs threshold (probit / NORMDIST).

    ``P = Φ(intercept + slope × (ratio − threshold) / threshold)``.

    Args:
        ratio: Debt burden ratio.
        threshold: Applicable threshold.
        assumptions: Probit coefficients.

    Returns:
        Probability in ``[0, 1]``.
    """
    assumptions = assumptions or ProbabilityAssumptions()
    if threshold == 0:
        return 1.0 if ratio > 0 else 0.0
    z = assumptions.intercept + assumptions.slope * ((ratio - threshold) / threshold)
    return float(_norm_cdf(z))


def path_breach_probabilities(
    values: pd.Series,
    threshold: float,
    assumptions: ProbabilityAssumptions | None = None,
) -> pd.Series:
    """Year-by-year breach probabilities along a ratio path."""
    assumptions = assumptions or ProbabilityAssumptions()
    return pd.Series(
        {
            int(y): breach_probability(float(v), threshold, assumptions)
            for y, v in values.dropna().items()
        },
        dtype=float,
    )


def max_path_probability(
    values: pd.Series,
    threshold: float,
    assumptions: ProbabilityAssumptions | None = None,
) -> float:
    """Maximum breach probability over the path."""
    probs = path_breach_probabilities(values, threshold, assumptions)
    return float(probs.max()) if len(probs) else 0.0


@dataclass(frozen=True, slots=True)
class DistressCoefficients:
    """Excel Probability approach regression coefficients (one indicator).

    Template block ``I64:I74`` / ``J65:J74`` / ``K66:K74`` / ``L67:L74``.
    ``ratio`` multiplies the burden ratio / 100; ``cpia`` is not rescaled.
    """

    ratio: float
    cpia: float
    growth: float
    reserves_imports: float
    reserves_imports_sq: float
    remittances_gdp: float
    world_growth: float
    intercept: float


@dataclass(frozen=True, slots=True)
class DistressCovariates:
    """Period-average regressors (5-year history + 11-year projection).

    Excel ``H77:H81``: CPIA, real GDP growth, reserves/imports, remittances/GDP,
    world real growth. Growth / reserve / remittance / world series are percent.
    """

    cpia: float
    real_gdp_growth: float
    reserves_imports: float
    remittances_gdp: float
    world_growth: float


# Cached template coefficients (Probability approach I/J/K/L 64–74).
EXCEL_DISTRESS_COEFFICIENTS: dict[str, DistressCoefficients] = {
    "pv_debt_to_gdp": DistressCoefficients(
        ratio=1.541,
        cpia=-0.4,
        growth=-3.081,
        reserves_imports=-4.223,
        reserves_imports_sq=3.953,
        remittances_gdp=-2.235,
        world_growth=-12.4,
        intercept=1.31,
    ),
    "pv_debt_to_exports": DistressCoefficients(
        ratio=0.359,
        cpia=-0.381,
        growth=-2.853,
        reserves_imports=-4.591,
        reserves_imports_sq=4.582,
        remittances_gdp=-2.282,
        world_growth=-14.09,
        intercept=1.331,
    ),
    "debt_service_to_exports": DistressCoefficients(
        ratio=3.541,
        cpia=-0.395,
        growth=-1.942,
        reserves_imports=-3.699,
        reserves_imports_sq=3.683,
        remittances_gdp=-1.934,
        world_growth=-13.75,
        intercept=1.148,
    ),
    "debt_service_to_revenue": DistressCoefficients(
        ratio=3.745,
        cpia=-0.362,
        growth=-3.001,
        reserves_imports=-3.696,
        reserves_imports_sq=3.743,
        remittances_gdp=-1.635,
        world_growth=-13.84,
        intercept=0.979,
    ),
}


def distress_index(
    ratio_pct: float,
    covariates: DistressCovariates,
    coefficients: DistressCoefficients,
) -> float:
    """Linear index inside Excel ``NORMDIST(..., 0, 1, TRUE)``.

    Args:
        ratio_pct: Debt-burden ratio in percent (e.g. PV/GDP = 44.88).
        covariates: Period-average macro regressors.
        coefficients: Indicator-specific template coefficients.

    Returns:
        Standard-normal index ``z``.
    """
    res = covariates.reserves_imports / 100.0
    return (
        coefficients.ratio * ratio_pct / 100.0
        + coefficients.cpia * covariates.cpia
        + coefficients.growth * covariates.real_gdp_growth / 100.0
        + coefficients.reserves_imports * res
        + coefficients.reserves_imports_sq * res * res
        + coefficients.remittances_gdp * covariates.remittances_gdp / 100.0
        + coefficients.world_growth * covariates.world_growth / 100.0
        + coefficients.intercept
    )


def distress_probability(
    ratio_pct: float,
    covariates: DistressCovariates,
    coefficients: DistressCoefficients | None = None,
    *,
    indicator: str = "pv_debt_to_gdp",
) -> float:
    """Excel Probability approach ``NORMDIST`` distress probability.

    ``P = Φ(z)`` with ``z`` from `distress_index`. Excel displays ``P × 100``.

    Args:
        ratio_pct: Burden ratio in percent.
        covariates: Period-average regressors (``H77:H81``).
        coefficients: Indicator coefficients; default from `indicator`.
        indicator: Key into `EXCEL_DISTRESS_COEFFICIENTS`.

    Returns:
        Probability in ``[0, 1]``.
    """
    coeffs = coefficients or EXCEL_DISTRESS_COEFFICIENTS[indicator]
    return float(_norm_cdf(distress_index(ratio_pct, covariates, coeffs)))


def path_distress_probabilities(
    values: pd.Series,
    covariates: DistressCovariates,
    coefficients: DistressCoefficients | None = None,
    *,
    indicator: str = "pv_debt_to_gdp",
) -> pd.Series:
    """Year-by-year Excel ``NORMDIST`` probabilities along a ratio path."""
    coeffs = coefficients or EXCEL_DISTRESS_COEFFICIENTS[indicator]
    return pd.Series(
        {
            int(y): distress_probability(float(v), covariates, coeffs)
            for y, v in values.dropna().items()
        },
        dtype=float,
    )
