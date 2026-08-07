"""CI score, debt-carrying capacity, and applicable thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DebtCarryingCapacity(str, Enum):
    """Debt-carrying capacity classification (Weak / Medium / Strong)."""

    WEAK = "Weak"
    MEDIUM = "Medium"
    STRONG = "Strong"


# Standard LIC-DSF cut-offs (CI Summary).
CI_WEAK_CUTOFF = 2.69
CI_STRONG_CUTOFF = 3.05

# External + public threshold matrices by DCC (CI Summary reference table).
_EXTERNAL_THRESHOLDS: dict[DebtCarryingCapacity, dict[str, float]] = {
    DebtCarryingCapacity.WEAK: {
        "pv_debt_to_exports": 140.0,
        "pv_debt_to_gdp": 30.0,
        "debt_service_to_exports": 10.0,
        "debt_service_to_revenue": 14.0,
    },
    DebtCarryingCapacity.MEDIUM: {
        "pv_debt_to_exports": 180.0,
        "pv_debt_to_gdp": 40.0,
        "debt_service_to_exports": 15.0,
        "debt_service_to_revenue": 18.0,
    },
    DebtCarryingCapacity.STRONG: {
        "pv_debt_to_exports": 240.0,
        "pv_debt_to_gdp": 55.0,
        "debt_service_to_exports": 21.0,
        "debt_service_to_revenue": 23.0,
    },
}

_PUBLIC_PV_GDP: dict[DebtCarryingCapacity, float] = {
    DebtCarryingCapacity.WEAK: 35.0,
    DebtCarryingCapacity.MEDIUM: 55.0,
    DebtCarryingCapacity.STRONG: 70.0,
}


@dataclass(frozen=True, slots=True)
class ApplicableThresholds:
    """Applicable external + public thresholds for a DCC class."""

    dcc: DebtCarryingCapacity
    pv_debt_to_exports: float
    pv_debt_to_gdp: float
    debt_service_to_exports: float
    debt_service_to_revenue: float
    public_pv_debt_to_gdp: float

    def as_dict(self) -> dict[str, float]:
        """Return thresholds keyed by indicator id."""
        return {
            "pv_debt_to_exports": self.pv_debt_to_exports,
            "pv_debt_to_gdp": self.pv_debt_to_gdp,
            "debt_service_to_exports": self.debt_service_to_exports,
            "debt_service_to_revenue": self.debt_service_to_revenue,
            "public_pv_debt_to_gdp": self.public_pv_debt_to_gdp,
        }


def classify_ci(
    ci_score: float,
    *,
    weak_cutoff: float = CI_WEAK_CUTOFF,
    strong_cutoff: float = CI_STRONG_CUTOFF,
) -> DebtCarryingCapacity:
    """Map a CI score to Weak / Medium / Strong.

    Excel rule: ``CI < 2.69`` → Weak; ``2.69 ≤ CI ≤ 3.05`` → Medium;
    ``CI > 3.05`` → Strong.

    Args:
        ci_score: Composite indicator score.
        weak_cutoff: Upper bound for Weak (exclusive).
        strong_cutoff: Lower bound for Strong (exclusive).

    Returns:
        Debt-carrying capacity class.
    """
    if ci_score < weak_cutoff:
        return DebtCarryingCapacity.WEAK
    if ci_score > strong_cutoff:
        return DebtCarryingCapacity.STRONG
    return DebtCarryingCapacity.MEDIUM


def thresholds_for(
    dcc: DebtCarryingCapacity | str,
) -> ApplicableThresholds:
    """Return applicable thresholds for a DCC classification.

    Args:
        dcc: Debt-carrying capacity (enum or ``Weak``/``Medium``/``Strong``).

    Returns:
        Applicable external + public threshold set.
    """
    if isinstance(dcc, str):
        dcc = DebtCarryingCapacity(dcc)
    ext = _EXTERNAL_THRESHOLDS[dcc]
    return ApplicableThresholds(
        dcc=dcc,
        pv_debt_to_exports=ext["pv_debt_to_exports"],
        pv_debt_to_gdp=ext["pv_debt_to_gdp"],
        debt_service_to_exports=ext["debt_service_to_exports"],
        debt_service_to_revenue=ext["debt_service_to_revenue"],
        public_pv_debt_to_gdp=_PUBLIC_PV_GDP[dcc],
    )


def thresholds_from_ci(ci_score: float) -> ApplicableThresholds:
    """Classify CI then return applicable thresholds."""
    return thresholds_for(classify_ci(ci_score))
