"""Python implementation of the IMF/World Bank LIC-DSF Excel template.

``lic_dsf.pv`` covers present-value instruments / portfolios.
``lic_dsf.books`` covers Ext / Dom / Macro debt books.
``lic_dsf.resfin`` covers Input 7 residual financing (params, overlays, engine).
``lic_dsf.load`` parses LIC-DSF Input / CI / Realism sheets into those types.
``lic_dsf.dsa`` covers Baseline DSA sustainability ratios.
``lic_dsf.stress`` covers Input 6 standard stress tests (uses ``resfin``).
``lic_dsf.realism`` covers Realism 1–4 math. ``lic_dsf.output`` assembles Output
sheet DataFrames. ``lic_dsf.rating`` covers CI thresholds, Chart Data breaches,
and Output 5/7 ratings. ``lic_dsf.scenario`` covers Customized Scenario and
Probability math.
"""

from __future__ import annotations

from lic_dsf import (
    books,
    dsa,
    load,
    output,
    pv,
    rating,
    realism,
    resfin,
    scenario,
    stress,
)

__version__ = "0.1.0"

__all__ = [
    "books",
    "dsa",
    "load",
    "output",
    "pv",
    "rating",
    "realism",
    "resfin",
    "scenario",
    "stress",
]
