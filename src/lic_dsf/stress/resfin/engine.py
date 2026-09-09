"""Compatibility shim — import from ``lic_dsf.resfin`` instead."""

from __future__ import annotations

from lic_dsf.resfin import (
    EXTERNAL_INTEREST_TOL,
    PUBLIC_GAP_TOL,
    ResidualFinancingEngine,
    ResidualFinancingResult,
)

__all__ = [
    "EXTERNAL_INTEREST_TOL",
    "PUBLIC_GAP_TOL",
    "ResidualFinancingEngine",
    "ResidualFinancingResult",
]
