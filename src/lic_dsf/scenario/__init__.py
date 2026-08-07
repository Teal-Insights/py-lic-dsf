"""Optional scenario modules: Customized Scenario and Probability approach.

Registers custom paths into ``lic_dsf.rating`` Chart Data; Output 6 panels.
Input 8 SDR remains in ``lic_dsf.pv`` (already loaded into Ext).
"""

from lic_dsf.scenario.customized import (
    CustomizedScenarioSpec,
    apply_customized_deltas,
    register_custom_path,
)
from lic_dsf.scenario.panels import probability_panel
from lic_dsf.scenario.probability import (
    ProbabilityAssumptions,
    borderline_bands,
    breach_probability,
    max_path_probability,
    path_breach_probabilities,
)

__all__ = [
    "CustomizedScenarioSpec",
    "ProbabilityAssumptions",
    "apply_customized_deltas",
    "borderline_bands",
    "breach_probability",
    "max_path_probability",
    "path_breach_probabilities",
    "probability_panel",
    "register_custom_path",
]
