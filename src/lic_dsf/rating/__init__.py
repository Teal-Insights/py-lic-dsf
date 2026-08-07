"""Risk rating layer: CI thresholds, Chart Data breaches, Output 5/7.

Consumes Baseline / stress ratio paths; does not own DSA ratio math.
"""

from lic_dsf.rating.chart_data import (
    ChartDataRegistry,
    MechanicalRatingResult,
    RatioPath,
    RiskRating,
    annual_breaches,
    compute_mechanical_ratings,
    mechanical_rating_from_breaches,
    multi_year_breach,
)
from lic_dsf.rating.classification import (
    CI_STRONG_CUTOFF,
    CI_WEAK_CUTOFF,
    ApplicableThresholds,
    DebtCarryingCapacity,
    classify_ci,
    thresholds_for,
    thresholds_from_ci,
)
from lic_dsf.rating.market import (
    MarketFinancingInputs,
    MarketFinancingResult,
    assess_market_financing,
    market_panel,
)
from lic_dsf.rating.moderate import (
    ModerateSpace,
    moderate_panel,
    moderate_space_from_headroom,
)
from lic_dsf.rating.summary import RiskRatingSummary, risk_summary_panel
from lic_dsf.rating.workbook import (
    CiSummarySnapshot,
    TriggerFlags,
    load_ci_summary,
    load_trigger_flags,
)

__all__ = [
    "CI_STRONG_CUTOFF",
    "CI_WEAK_CUTOFF",
    "ApplicableThresholds",
    "ChartDataRegistry",
    "CiSummarySnapshot",
    "DebtCarryingCapacity",
    "MarketFinancingInputs",
    "MarketFinancingResult",
    "MechanicalRatingResult",
    "ModerateSpace",
    "RatioPath",
    "RiskRating",
    "RiskRatingSummary",
    "TriggerFlags",
    "annual_breaches",
    "assess_market_financing",
    "classify_ci",
    "compute_mechanical_ratings",
    "load_ci_summary",
    "load_trigger_flags",
    "market_panel",
    "mechanical_rating_from_breaches",
    "moderate_panel",
    "moderate_space_from_headroom",
    "multi_year_breach",
    "risk_summary_panel",
    "thresholds_for",
    "thresholds_from_ci",
]
