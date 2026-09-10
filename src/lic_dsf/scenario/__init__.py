"""Optional Excel scenario tools (two unrelated products).

This package is a **namespace**, not a single engine:

1. **Customized Scenario** (``scenario.customized``) — user path deltas /
   levels registered into Chart Data for rating.
2. **Probability approach** (``scenario.probability``) — Output 6 / probit
   helpers (Φ, distress covariates, borderline bands).

Stress tailored A2 also consumes :class:`CustomizedScenarioSpec`; that does
not make this package part of ``lic_dsf.stress``. Output 6 frames live in
``lic_dsf.output``. Input 8 SDR remains in Ext via ``lic_dsf.books`` / ``pv``.
"""

from lic_dsf.scenario.customized import (
    CustomizedScenarioSpec,
    apply_customized_deltas,
    register_custom_path,
)
from lic_dsf.scenario.probability import (
    EXCEL_DISTRESS_COEFFICIENTS,
    EXCEL_PROBABILITY_THRESHOLDS,
    DistressCoefficients,
    DistressCovariates,
    ProbabilityAssumptions,
    borderline_bands,
    breach_probability,
    distress_probability,
    max_path_probability,
    path_breach_probabilities,
    path_distress_probabilities,
)

__all__ = [
    # --- Customized Scenario ---
    "CustomizedScenarioSpec",
    "apply_customized_deltas",
    "register_custom_path",
    # --- Probability approach (Output 6) ---
    "EXCEL_DISTRESS_COEFFICIENTS",
    "EXCEL_PROBABILITY_THRESHOLDS",
    "DistressCoefficients",
    "DistressCovariates",
    "ProbabilityAssumptions",
    "borderline_bands",
    "breach_probability",
    "distress_probability",
    "max_path_probability",
    "path_breach_probabilities",
    "path_distress_probabilities",
]
