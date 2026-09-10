"""Cell-keyed Output 5 / 6 / 7 SUT tables and Output 7 summary panel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lic_dsf.rating.summary import RiskRatingSummary
from lic_dsf.rating.sut_outputs import (
    compute_output6_outputs,
    compute_output7_outputs,
    compute_output51_outputs,
    compute_output52_outputs,
)

# Chart Data / Output 7 / Input 1 addresses the library computes.
_OUTPUT51_CELLS: dict[str, tuple[str, str]] = {
    "D10": ("Output 5-1", "Mechanical external"),
    "D61": ("Output 5-1", "Baseline peak PV/GDP"),
    "D66": ("Output 5-1", "Threshold PV/GDP"),
    "E73": ("Output 5-1", "Space to absorb shock"),
    "D23": ("Output 5-1", "Space (unconstrained)"),
}

_OUTPUT52_CELLS: dict[str, tuple[str, str]] = {
    "AB8": ("Output 5-2", "GFN benchmark"),
    "AB9": ("Output 5-2", "Max GFN / GDP"),
    "AB10": ("Output 5-2", "GFN breach"),
    "AX8": ("Output 5-2", "EMBI benchmark"),
    "AX9": ("Output 5-2", "EMBI spread"),
    "AX10": ("Output 5-2", "EMBI breach"),
    "AB12": ("Output 5-2", "Heightened liquidity needs"),
    "C27": ("Output 5-2", "Applicable"),
}

_OUTPUT7_CELLS: dict[str, tuple[str, str]] = {
    "E5": ("Output 7", "Country"),
    "E6": ("Output 7", "Country Code"),
    "E48": ("Output 7", "Mechanical external"),
    "I10": ("Output 7", "Mechanical fiscal"),
    "E54": ("Output 7", "Mechanical overall"),
    "D65": ("Output 7", "Debt carrying capacity"),
    "E66": ("Output 7", "CI score"),
    "D66": ("Output 7", "Threshold PV/GDP"),
    "E73": ("Output 7", "Moderate granularity"),
    "E75": ("Output 7", "Market-Financing Pressures"),
}


def _scalar_frame(
    store: dict[tuple[str, str], pd.Series],
    cells: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    rows: dict[str, object] = {}
    for cell, key in cells.items():
        series = store.get(key)
        if series is None:
            continue
        rows[cell] = series.iloc[0] if len(series) else pd.NA
    return pd.Series(rows, name="value").to_frame()


def risk_summary_panel(summary: RiskRatingSummary) -> pd.DataFrame:
    """Output 7 shaped summary table (canonical panel builder).

    Args:
        summary: Mechanical ratings plus optional judgement overrides.

    Returns:
        One-column DataFrame named ``Output 7``.
    """
    mech = summary.mechanical
    rows = {
        "Mechanical external": mech.external.label,
        "Final external": summary.final_external.label
        if summary.final_external
        else mech.external.label,
        "Mechanical fiscal": mech.fiscal.label,
        "Mechanical overall": mech.overall.label,
        "Final overall": summary.final_overall.label
        if summary.final_overall
        else mech.overall.label,
        "Judgement applied": "Yes" if summary.judgement_applied else "No",
        "Debt carrying capacity": summary.dcc.value,
        "CI score": summary.ci_score,
        "Threshold PV/GDP": summary.thresholds.pv_debt_to_gdp,
        "Threshold PV/exports": summary.thresholds.pv_debt_to_exports,
        "Threshold DS/exports": summary.thresholds.debt_service_to_exports,
        "Threshold DS/revenue": summary.thresholds.debt_service_to_revenue,
        "Threshold public PV/GDP": summary.thresholds.public_pv_debt_to_gdp,
        "Moderate granularity": summary.moderate_granularity,
        "Judgement note": summary.judgement_note or None,
    }
    return pd.Series(rows, name="Output 7").to_frame()


def output_51_table(path: str | Path) -> pd.DataFrame:
    """Output 5-1 cell-keyed SUT (mechanical, peak, threshold, space).

    Args:
        path: LIC-DSF workbook path.

    Returns:
        One-column frame indexed by cell address (``D10``, ``D66``, …).
    """
    return _scalar_frame(compute_output51_outputs(path), _OUTPUT51_CELLS)


def output_52_table(path: str | Path) -> pd.DataFrame:
    """Output 5-2 cell-keyed SUT (GFN / EMBI / applicability).

    Args:
        path: LIC-DSF workbook path.

    Returns:
        One-column frame indexed by cell address.
    """
    return _scalar_frame(compute_output52_outputs(path), _OUTPUT52_CELLS)


def output_6_table(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Output 6 / Probability approach series keyed by section and match_key.

    Args:
        path: LIC-DSF workbook path.

    Returns:
        Mapping ``(indicator, series)`` → year path (plus assumption scalars).
    """
    return compute_output6_outputs(path)


def output_7_table(path: str | Path) -> pd.DataFrame:
    """Output 7 cell-keyed SUT (ratings, CI, judgement).

    Args:
        path: LIC-DSF workbook path.

    Returns:
        One-column frame indexed by cell address.
    """
    return _scalar_frame(compute_output7_outputs(path), _OUTPUT7_CELLS)


def output_51_cell_keys() -> tuple[str, ...]:
    """Cell addresses covered by ``output_51_table``."""
    return tuple(_OUTPUT51_CELLS)
