"""Python implementation of the IMF/World Bank LIC-DSF Excel template.

``lic_dsf.pv`` covers present-value instruments, Ext/Dom/Macro debt books, and
workbook loaders. ``lic_dsf.dsa`` covers Baseline DSA sustainability ratios.
``lic_dsf.stress`` covers Input 6 standard stress tests and residual financing.
``lic_dsf.realism`` covers Realism 1–4 / Output 4 panels.
``lic_dsf.rating`` covers CI thresholds, Chart Data breaches, and Output 5/7.
``lic_dsf.scenario`` covers Customized Scenario and Probability / Output 6.
"""

from __future__ import annotations

from lic_dsf import dsa, pv, rating, realism, scenario, stress

__version__ = "0.1.0"

__all__ = [
    "dsa",
    "pv",
    "rating",
    "realism",
    "scenario",
    "stress",
]
