"""CI Summary / Trigger snapshot types used by rating math."""

from __future__ import annotations

from dataclasses import dataclass

from lic_dsf.rating.classification import ApplicableThresholds, DebtCarryingCapacity


@dataclass(frozen=True, slots=True)
class CiSummarySnapshot:
    """CI Summary snapshot for the template country."""

    country: str
    country_code: int
    ci_score: float
    dcc: DebtCarryingCapacity
    thresholds: ApplicableThresholds
    dcc_current: str
    dcc_previous: str
    dcc_two_previous: str


@dataclass(frozen=True, slots=True)
class TriggerFlags:
    """Sparse Trigger-sheet flags used by rating modules."""

    country_code: int
    isocode: str
    country: str
    market_lic: bool
    disaster_flag: bool
