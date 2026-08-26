"""Python implementation of the IMF/World Bank LIC-DSF Excel template.

``lic_dsf.pv`` covers present-value instruments, Ext/Dom/Macro debt books, and
workbook loaders. ``lic_dsf.dsa`` covers Baseline DSA sustainability ratios.
``lic_dsf.stress`` covers Input 6 standard stress tests and residual financing.
``lic_dsf.realism`` covers Realism 1–4 math. ``lic_dsf.output`` assembles Output
sheet DataFrames. ``lic_dsf.rating`` covers CI thresholds, Chart Data breaches,
and Output 5/7 ratings. ``lic_dsf.scenario`` covers Customized Scenario and
Probability math.
"""

from __future__ import annotations

from lic_dsf import dsa, output, pv, rating, realism, scenario, stress

__version__ = "0.1.0"

__all__ = [
    "dsa",
    "output",
    "pv",
    "rating",
    "realism",
    "scenario",
    "stress",
]
