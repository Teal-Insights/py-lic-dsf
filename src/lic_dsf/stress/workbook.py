"""Load cached A2 / tailored C* external ratios from Excel stress sheets.

Debug dump only — not an Input parser. Standard Input 6 loaders live in
``lic_dsf.load``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.load._cells import _tailored_applicability

if TYPE_CHECKING:
    from lic_dsf.stress.scenario import CachedStressExternalBook

_TAILORED_SHEET = "Input 6 - Tailored Tests"
_CUSTOMIZED_EXTERNAL_SHEET = "Customized Scenario-External"

_RATIO_METHODS = (
    "pv_ppg_external_to_gdp",
    "pv_ppg_external_to_exports",
    "ppg_debt_service_to_exports",
    "ppg_debt_service_to_revenue",
)

_CACHED_SHEETS: dict[str, tuple[str, tuple[int, int, int, int], str]] = {
    "A2_Custom": (
        _CUSTOMIZED_EXTERNAL_SHEET,
        (82, 83, 86, 87),
        "A2_Custom",
    ),
    "C1_CombinedCL": (
        "C1_Combined CL",
        (101, 102, 103, 104),
        "C1_CombinedCL",
    ),
    "C3_Commodity": (
        "C3_Commodity prices_ext",
        (35, 36, 39, 40),
        "C3_Commodity",
    ),
    "C4_Market": (
        "C4_Market_financing",
        (82, 83, 96, 99),
        "C4_Market",
    ),
}


def _year_columns(ws: Any, *, scan_rows: range = range(6, 10)) -> dict[int, int]:
    """Map projection year → column on a B-sheet-style stress tab."""
    for row in scan_rows:
        cols: dict[int, int] = {}
        for col in range(3, 45):
            value = ws.cell(row, col).value
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                year = int(value)
                if 1900 < year < 2200:
                    cols[year] = col
        if cols:
            return cols
    return {}


def _read_ratio_series(
    ws: Any,
    row: int,
    year_cols: dict[int, int],
) -> pd.Series:
    return pd.Series(
        {
            year: float(ws.cell(row, col).value)
            for year, col in year_cols.items()
            if isinstance(ws.cell(row, col).value, (int, float))
            and not isinstance(ws.cell(row, col).value, bool)
        },
        dtype=float,
    )


def load_cached_external_stress(path: str | Path) -> dict[str, CachedStressExternalBook]:
    """Load A2 / tailored C* external ratios from Excel stress sheets.

    Debug dump only — not an Output 3-x SUT input. Use
    ``run_tailored_external_stress`` for Python-computed A2/C* paths. This
    loader still reads materialized B-sheet ratios for side-by-side debugging
    (and skips C2/C3/C4 when Input 6 marks them inapplicable).

    Args:
        path: Path to a LIC-DSF workbook.

    Returns:
        Scenario id → cached ratio book.
    """
    from lic_dsf.stress.scenario import CachedStressExternalBook

    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        tailored_flags = _tailored_applicability(workbook[_TAILORED_SHEET])
        customized_on = (
            str(workbook[_CUSTOMIZED_EXTERNAL_SHEET].cell(3, 4).value or "")
            .strip()
            .lower()
            == "yes"
        )
        books: dict[str, CachedStressExternalBook] = {}
        for key, (sheet_name, rows, scenario_id) in _CACHED_SHEETS.items():
            if key == "A2_Custom" and not customized_on:
                continue
            if key == "C3_Commodity" and not tailored_flags["C3_Commodity"]:
                continue
            if key == "C4_Market" and not tailored_flags["C4_Market"]:
                continue
            if sheet_name not in workbook.sheetnames:
                continue
            ws = workbook[sheet_name]
            year_cols = _year_columns(ws)
            if not year_cols:
                continue
            series = {
                method: _read_ratio_series(ws, row, year_cols)
                for method, row in zip(_RATIO_METHODS, rows, strict=True)
            }
            books[key] = CachedStressExternalBook(
                scenario_id=scenario_id,  # type: ignore[arg-type]
                _pv_ppg_external_to_gdp=series["pv_ppg_external_to_gdp"],
                _pv_ppg_external_to_exports=series["pv_ppg_external_to_exports"],
                _ppg_debt_service_to_exports=series["ppg_debt_service_to_exports"],
                _ppg_debt_service_to_revenue=series["ppg_debt_service_to_revenue"],
            )
        return books
    finally:
        workbook.close()
