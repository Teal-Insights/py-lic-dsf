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

    Excel Probability approach: ``lower = (1 − bw) × T``, ``upper = (1 + bw) × T``.

    Args:
        threshold: Applicable threshold.
        bandwidth: Relative bandwidth (default 0.1).

    Returns:
        ``(lower, upper)`` band edges.
    """
    return (1.0 - bandwidth) * threshold, (1.0 + bandwidth) * threshold


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
