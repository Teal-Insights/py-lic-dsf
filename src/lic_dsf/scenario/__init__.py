"""Optional scenario modules: Customized Scenario and Probability approach.

Registers custom paths into ``lic_dsf.rating`` Chart Data; Output 6 panels.
Input 8 SDR remains in ``lic_dsf.pv`` (already loaded into Ext).
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
from lic_dsf.scenario.workbook import load_distress_covariates

__all__ = [
    "EXCEL_DISTRESS_COEFFICIENTS",
    "EXCEL_PROBABILITY_THRESHOLDS",
    "CustomizedScenarioSpec",
    "DistressCoefficients",
    "DistressCovariates",
    "ProbabilityAssumptions",
    "apply_customized_deltas",
    "borderline_bands",
    "breach_probability",
    "distress_probability",
    "load_distress_covariates",
    "max_path_probability",
    "path_breach_probabilities",
    "path_distress_probabilities",
    "register_custom_path",
]
