"""Excel vs Python comparison for Realism 4 (fiscal adjustment histogram)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.dsa.compare import write_comparison_csv
from lic_dsf.realism.compare import _a1, _as_year, _books, _year_int
from lic_dsf.realism.fiscal_adjustment import three_year_fiscal_adjustment

REALISM4_SHEET = "Realism 4 - Fiscal adjustment"
_ADJ_LABEL = "3-yr Fiscal adjustment"
_CSV_COLS = (
    "sheet",
    "cell",
    "row",
    "col",
    "year",
    "section",
    "series_code",
    "label",
    "excel_value",
    "computed_value",
    "abs_diff",
)


def _year_cols(ws) -> dict[int, int]:
    cols: dict[int, int] = {}
    for header_row in (8, 9, 7, 10, 11, 12):
        for col in range(1, (ws.max_column or 1) + 1):
            year = _as_year(ws.cell(header_row, col).value)
            if year is not None:
                cols[year] = col
        if cols:
            return cols
    return cols


def _read_excel(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[REALISM4_SHEET]
        year_cols = _year_cols(ws)
        records: list[dict[object, object]] = []
        # R10 is the 3-year adjustment path (Excel Realism 4).
        for year, col in year_cols.items():
            value = ws.cell(10, col).value
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            records.append(
                {
                    "sheet": REALISM4_SHEET,
                    "cell": _a1(10, col),
                    "row": 10,
                    "col": col,
                    "year": year,
                    "section": "Projections",
                    "series_code": _ADJ_LABEL,
                    "label": _ADJ_LABEL,
                    "match_key": _ADJ_LABEL,
                    "excel_value": float(value),
                }
            )
        for row in range(1, min((ws.max_row or 0), 80) + 1):
            if row == 10:
                continue
            label = str(ws.cell(row, 2).value or ws.cell(row, 1).value or "").strip()
            if not label:
                continue
            for year, col in year_cols.items():
                value = ws.cell(row, col).value
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                records.append(
                    {
                        "sheet": REALISM4_SHEET,
                        "cell": _a1(row, col),
                        "row": row,
                        "col": col,
                        "year": year,
                        "section": "Projections",
                        "series_code": label,
                        "label": label,
                        "match_key": label,
                        "excel_value": float(value),
                    }
                )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


def compute_realism4_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Three-year fiscal adjustment series."""
    path = Path(path)
    _macro, _ext, _eb, pub = _books(str(path))
    adj = three_year_fiscal_adjustment(pub.primary_deficit_to_gdp())
    return {("Projections", _ADJ_LABEL): adj}


def build_realism4_comparison(path: str | Path) -> pd.DataFrame:
    """Build Excel vs Python table for Realism 4 projections."""
    path = Path(path)
    excel = _read_excel(path)
    computed = compute_realism4_outputs(path)
    series = computed[("Projections", _ADJ_LABEL)]
    values: list[object] = []
    diffs: list[float | None] = []
    for label, year, excel_value in zip(
        excel["label"], excel["year"], excel["excel_value"], strict=True
    ):
        value = None
        year_i = _year_int(year)
        if str(label) == _ADJ_LABEL and year_i in series.index and pd.notna(
            series.loc[year_i]
        ):
            value = float(series.loc[year_i])
        values.append(value if value is not None else pd.NA)
        diffs.append(
            abs(float(excel_value) - float(value)) if value is not None else None
        )
    excel = excel.copy()
    excel["computed_value"] = values
    excel["abs_diff"] = diffs
    return excel


def write_realism4_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Realism 4 comparison table."""
    return write_comparison_csv(build_realism4_comparison(workbook), output)
