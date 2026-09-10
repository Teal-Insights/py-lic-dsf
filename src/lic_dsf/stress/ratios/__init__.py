"""Stress ratio projection packages.

Contract: stress ratios combine baseline Ext / public numerators with ResFin
overlays over shocked Macro denominators (Input 6 path). They are not a second
copy of ``lic_dsf.dsa`` baseline books — they project the shocked path.
"""

from __future__ import annotations

from lic_dsf.stress.ratios.external import StressExternalRatios
from lic_dsf.stress.ratios.public import StressPublicRatios

__all__ = ["StressExternalRatios", "StressPublicRatios"]
