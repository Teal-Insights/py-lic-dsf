"""Inventory numeric cells on LIC-DSF Output sheets (class D vs data rows).

Run from the repo root::

    uv run python -m tests.parity.inventory
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from tests.parity.equality import error_class
from tests.parity.probes import a1, as_year

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"
OUTPUT = REPO_ROOT / "data" / "parity" / "output_inventory.csv"

_SHEETS: tuple[tuple[str, int, int, int], ...] = (
    ("Output 1-1 - External DSA", 2, 6, 3),
    ("Output 1-2 - Public DSA", 2, 6, 3),
    ("Output 3-1 Stress-external", 1, 6, 3),
    ("Output 3-2 Stress-public", 2, 8, 4),
    ("Output 4-1 - Forecast Error", 2, 6, 3),
    ("Output 4-2 - Realism", 2, 6, 3),
    ("Output 5-1 Moderate risk", 2, 1, 1),
    ("Output 5-2 Market module", 2, 1, 1),
    ("Output 6 - Prob (if applicable)", 2, 1, 1),
    ("Output 7 - Risk rating summary", 2, 1, 1),
)

_CLASS_D_PREFIXES = (
    "sources:",
    "table ",
    "go to ",
    "1/",
    "2/",
    "3/",
    "4/",
    "5/",
    "6/",
    "7/",
    "8/",
    "hide",
    "(in percent",
)


def _classify(label: object, nums: int) -> str:
    text = str(label or "").strip().lower()
    if not text and nums == 0:
        return "empty"
    if any(text.startswith(p) for p in _CLASS_D_PREFIXES):
        return "D_exclude"
    if nums == 0:
        return "header"
    return "numeric"


def main() -> None:
    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    records: list[dict[str, object]] = []
    try:
        for sheet, label_col, year_row, first_col in _SHEETS:
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            year_cols: dict[int, int] = {}
            for col in range(first_col, (ws.max_column or first_col) + 1):
                year = as_year(ws.cell(year_row, col).value)
                if year is not None:
                    year_cols[year] = col
            scan_cols = list(year_cols.values()) or list(
                range(1, min((ws.max_column or 1), 60) + 1)
            )
            for row in range(1, (ws.max_row or 0) + 1):
                label = ws.cell(row, label_col).value
                nums = 0
                first_cell = ""
                for col in scan_cols:
                    value = ws.cell(row, col).value
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        nums += 1
                        if not first_cell:
                            first_cell = a1(row, col)
                    elif error_class(value) is not None:
                        nums += 1
                if label or nums:
                    records.append(
                        {
                            "sheet": sheet,
                            "row": row,
                            "label": str(label).replace("\n", " ") if label else "",
                            "numeric_cells": nums,
                            "class": _classify(label, nums),
                            "sample_cell": first_cell,
                        }
                    )
    finally:
        wb.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_records(records).to_csv(OUTPUT, index=False)
    print(f"wrote {OUTPUT} ({len(records)} rows)")
    _write_probe_catalogs()


def _write_probe_catalogs() -> None:
    """Write typed probe catalogs as CSV for skeptic coverage."""
    from tests.parity.catalogs import (
        output_11_probes,
        output_12_probes,
        output_31_probes,
        output_32_probes,
    )

    dest = OUTPUT.parent / "probe_catalog.csv"
    rows: list[dict[str, object]] = []
    for name, probes in (
        ("output_11", output_11_probes(WORKBOOK)),
        ("output_12", output_12_probes(WORKBOOK)),
        ("output_31", output_31_probes(WORKBOOK)),
        ("output_32", output_32_probes(WORKBOOK)),
    ):
        for p in probes:
            rows.append(
                {
                    "catalog": name,
                    "sheet": p.sheet,
                    "row": p.row,
                    "col": p.col,
                    "year": p.year,
                    "sut_key": str(p.sut_key),
                    "section": p.section,
                    "label": p.label,
                }
            )
    dest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_records(rows).to_csv(dest, index=False)
    print(f"wrote {dest} ({len(rows)} probes)")


if __name__ == "__main__":
    main()
