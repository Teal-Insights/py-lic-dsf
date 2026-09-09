"""Excel vs Python comparison for Output 1-1 / 1-2 (baseline DSA).

Headline CSV helpers. Prefer ``tests.parity.compare_probes`` against
``lic_dsf.output.output_11_table`` / ``output_12_table`` for full Output-panel
catalogs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.load.core import load_core
from lic_dsf.output.baseline import external_dsa_panel, public_dsa_panel
from tests.parity.excel_compare.cells import year_cols
from tests.parity.excel_compare.csv import (
    is_number as _is_number,
    pair_frame,
    record_cell,
    write_comparison_csv,
)

OUTPUT11_SHEET = "Output 1-1 - External DSA"
OUTPUT12_SHEET = "Output 1-2 - Public DSA"

_OUTPUT11_ROWS: tuple[tuple[int, str], ...] = (
    (30, "PV of PPG external debt / GDP"),
    (31, "PV of PPG external debt / exports"),
    (32, "PV of PPG external debt / revenue"),
    (33, "PPG debt service / exports"),
    (34, "PPG debt service / revenue"),
    (35, "External GFN (USD)"),
)

_OUTPUT12_ROWS: tuple[tuple[int, str], ...] = (
    (8, "Public sector debt / GDP"),
    (9, "PPG external debt / GDP"),
    (31, "PV of public debt / GDP"),
    (32, "PV of public debt / revenue+grants"),
    (35, "Debt service / revenue+grants"),
    (37, "Public GFN / GDP"),
)

_YEAR_ROW = 6
_FIRST_YEAR_COL = 3
_SECTION = "Sustainability indicators"


@lru_cache(maxsize=4)
def _dsa_panels(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    _macro, _external, ext_base, pub_base = load_core(path)
    return external_dsa_panel(ext_base), public_dsa_panel(pub_base)


def _read_panel_rows(
    path: Path,
    *,
    sheet: str,
    rows: tuple[tuple[int, str], ...],
) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        cols = year_cols(ws, _YEAR_ROW, _FIRST_YEAR_COL)
        records: list[dict[str, Any]] = []
        for row, key in rows:
            label = str(ws.cell(row, 2).value or "").strip()
            for year, col in cols.items():
                value = ws.cell(row, col).value
                if not _is_number(value):
                    continue
                records.append(
                    record_cell(
                        sheet=sheet,
                        row=row,
                        col=col,
                        year=year,
                        section=_SECTION,
                        series_code=key,
                        label=label,
                        match_key=key,
                        value=float(value),
                    )
                )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


def compute_output11_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 1-1 panel rows keyed by `(section, match_key)`."""
    panel, _pub = _dsa_panels(str(Path(path)))
    return {(_SECTION, str(name)): panel.loc[name] for name in panel.index}


def compute_output12_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 1-2 panel rows keyed by `(section, match_key)`."""
    _ext, panel = _dsa_panels(str(Path(path)))
    return {(_SECTION, str(name)): panel.loc[name] for name in panel.index}


def build_output11_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Output 1-1."""
    path = Path(path)
    return pair_frame(
        _read_panel_rows(path, sheet=OUTPUT11_SHEET, rows=_OUTPUT11_ROWS),
        compute_output11_outputs(path),
    )


def build_output12_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Output 1-2."""
    path = Path(path)
    return pair_frame(
        _read_panel_rows(path, sheet=OUTPUT12_SHEET, rows=_OUTPUT12_ROWS),
        compute_output12_outputs(path),
    )


def write_output11_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 1-1 comparison table to `output`."""
    return write_comparison_csv(build_output11_comparison(workbook), output)


def write_output12_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 1-2 comparison table to `output`."""
    return write_comparison_csv(build_output12_comparison(workbook), output)
