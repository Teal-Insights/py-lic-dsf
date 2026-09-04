"""Excel vs Python comparison for Realism 4 (fiscal adjustment histogram)."""

from __future__ import annotations

from pathlib import Path
from typing import Hashable

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.realism.compare import _a1, _as_year, _books
from lic_dsf.realism.fiscal_adjustment import (
    DEFAULT_LIC_PROGRAM_DISTRIBUTION,
    place_in_lic_histogram,
    projected_three_year_adjustment,
    three_year_fiscal_adjustment,
)

REALISM4_SHEET = "Realism 4 - Fiscal adjustment"
_ADJ_LABEL = "3-yr Fiscal adjustment"
_PD_LABEL = "Primary deficit"
_YEAR_HEADER_ROW = 8
_FIRST_YEAR_COL = 6
_THREE_YEAR_ADJ_FIRST_YEAR = 2024
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
    "passed",
    "missing_sut",
)

_PLACEMENT_CELLS: tuple[tuple[int, str, str], ...] = (
    (4, "adjustment", "Projected 3-yr adjustment"),
    (5, "bin_edge", "bin edge"),
    (6, "category", "category"),
    (7, "percent_of_sample", "percent of sample"),
)

_HIST_COLS: tuple[tuple[int, str], ...] = (
    (1, "bin"),
    (2, "frequency"),
    (3, "category"),
    (4, "percent_of_sample"),
    (5, "cumulative_percent"),
)


def year_cols(path: str | Path) -> dict[int, int]:
    """Map calendar year → column on Realism 4 (row 8 headers)."""
    wb = load_workbook(Path(path), data_only=True, read_only=True)
    try:
        ws = wb[REALISM4_SHEET]
        cols: dict[int, int] = {}
        for col in range(_FIRST_YEAR_COL, (ws.max_column or _FIRST_YEAR_COL) + 1):
            year = _as_year(ws.cell(_YEAR_HEADER_ROW, col).value)
            if year is not None:
                cols[year] = col
        return cols
    finally:
        wb.close()


def compute_realism4_sut(path: str | Path) -> dict[Hashable, object]:
    """SUT map keyed by Realism 4 probe ``sut_key`` values."""
    path = Path(path)
    _macro, _ext, _eb, pub = _books(str(path))
    first_proj = pub.macro.inputs.first_projection_year
    pd_pct = pub.primary_deficit_to_gdp()
    adj = three_year_fiscal_adjustment(pd_pct)
    projected = projected_three_year_adjustment(pd_pct, first_proj)
    placement = place_in_lic_histogram(projected)
    dist = DEFAULT_LIC_PROGRAM_DISTRIBUTION

    sut: dict[Hashable, object] = {
        ("primary_deficit",): pd_pct.astype(float),
        ("three_year_adjustment",): adj.astype(float),
        ("placement", "adjustment"): float(placement.adjustment),
        ("placement", "bin_edge"): placement.bin_edge,
        ("placement", "category"): float(placement.category),
        ("placement", "percent_of_sample"): float(placement.percent_of_sample),
    }
    for i, excel_row in enumerate(range(23, 51)):
        if i >= len(dist.bins):
            break
        sut[("histogram", excel_row, "bin")] = dist.bins[i]
        sut[("histogram", excel_row, "frequency")] = float(dist.frequencies[i])
        sut[("histogram", excel_row, "category")] = float(i + 1)
        sut[("histogram", excel_row, "percent_of_sample")] = float(
            dist.percent_of_sample[i]
        )
        sut[("histogram", excel_row, "cumulative_percent")] = float(
            dist.cumulative_percent[i]
        )
    return sut


def compute_realism4_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Three-year fiscal adjustment series (legacy helper)."""
    path = Path(path)
    _macro, _ext, _eb, pub = _books(str(path))
    adj = three_year_fiscal_adjustment(pub.primary_deficit_to_gdp())
    return {("Projections", _ADJ_LABEL): adj}


def _lookup_sut(
    sut: dict[Hashable, object], key: Hashable, year: int | None
) -> object | None:
    if key not in sut:
        return None
    value = sut[key]
    if isinstance(value, pd.Series) and year is not None:
        if year not in value.index or pd.isna(value.loc[year]):
            return None
        return float(value.loc[year])
    return value


def _excel_cell_value(value: object) -> object:
    if isinstance(value, bool):
        return pd.NA
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        return text if text else pd.NA
    return pd.NA


def _abs_diff(excel_value: object, computed: object | None) -> float | None:
    if computed is None or pd.isna(excel_value) is True:
        return None
    if isinstance(excel_value, str) or isinstance(computed, str):
        return 0.0 if str(excel_value) == str(computed) else None
    if not isinstance(excel_value, (int, float)) or not isinstance(
        computed, (int, float)
    ):
        return None
    return abs(float(excel_value) - float(computed))


def _passes(excel_value: object, computed: object | None) -> bool:
    if computed is None:
        return False
    if isinstance(excel_value, str) or isinstance(computed, str):
        return str(excel_value) == str(computed)
    if not isinstance(excel_value, (int, float)) or not isinstance(
        computed, (int, float)
    ):
        return excel_value == computed
    delta = abs(float(excel_value) - float(computed))
    if delta <= 1e-6:
        return True
    scale = max(abs(float(excel_value)), abs(float(computed)))
    return scale > 0.0 and delta / scale <= 1e-12


def build_realism4_comparison(path: str | Path) -> pd.DataFrame:
    """Build Excel vs Python table for all Realism 4 numeric outputs."""
    path = Path(path)
    years = year_cols(path)
    sut = compute_realism4_sut(path)
    records: list[dict[object, object]] = []

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[REALISM4_SHEET]

        for year, col in sorted(years.items()):
            excel_value = _excel_cell_value(ws.cell(9, col).value)
            if pd.isna(excel_value) is True:
                continue
            key: Hashable = ("primary_deficit",)
            computed = _lookup_sut(sut, key, year)
            records.append(
                {
                    "sheet": REALISM4_SHEET,
                    "cell": _a1(9, col),
                    "row": 9,
                    "col": col,
                    "year": year,
                    "section": "Projections",
                    "series_code": _PD_LABEL,
                    "label": _PD_LABEL,
                    "sut_key": key,
                    "excel_value": excel_value,
                    "computed_value": computed if computed is not None else pd.NA,
                    "abs_diff": _abs_diff(excel_value, computed),
                    "missing_sut": computed is None,
                    "passed": _passes(excel_value, computed),
                }
            )

        for year, col in sorted(years.items()):
            if year < _THREE_YEAR_ADJ_FIRST_YEAR:
                continue
            excel_value = _excel_cell_value(ws.cell(10, col).value)
            if pd.isna(excel_value) is True:
                continue
            key = ("three_year_adjustment",)
            computed = _lookup_sut(sut, key, year)
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
                    "sut_key": key,
                    "excel_value": excel_value,
                    "computed_value": computed if computed is not None else pd.NA,
                    "abs_diff": _abs_diff(excel_value, computed),
                    "missing_sut": computed is None,
                    "passed": _passes(excel_value, computed),
                }
            )

        for col, field, label in _PLACEMENT_CELLS:
            excel_value = _excel_cell_value(ws.cell(14, col).value)
            if pd.isna(excel_value) is True:
                continue
            key = ("placement", field)
            computed = _lookup_sut(sut, key, None)
            records.append(
                {
                    "sheet": REALISM4_SHEET,
                    "cell": _a1(14, col),
                    "row": 14,
                    "col": col,
                    "year": pd.NA,
                    "section": "Placement",
                    "series_code": label,
                    "label": label,
                    "sut_key": key,
                    "excel_value": excel_value,
                    "computed_value": computed if computed is not None else pd.NA,
                    "abs_diff": _abs_diff(excel_value, computed),
                    "missing_sut": computed is None,
                    "passed": _passes(excel_value, computed),
                }
            )

        for row in range(23, 51):
            for col, field in _HIST_COLS:
                raw = ws.cell(row, col).value
                if raw is None:
                    continue
                excel_value = _excel_cell_value(raw)
                if pd.isna(excel_value) is True:
                    continue
                key = ("histogram", row, field)
                computed = _lookup_sut(sut, key, None)
                records.append(
                    {
                        "sheet": REALISM4_SHEET,
                        "cell": _a1(row, col),
                        "row": row,
                        "col": col,
                        "year": pd.NA,
                        "section": "Histogram",
                        "series_code": f"histogram {field}",
                        "label": f"histogram {field}",
                        "sut_key": key,
                        "excel_value": excel_value,
                        "computed_value": computed if computed is not None else pd.NA,
                        "abs_diff": _abs_diff(excel_value, computed),
                        "missing_sut": computed is None,
                        "passed": _passes(excel_value, computed),
                    }
                )
    finally:
        wb.close()

    return pd.DataFrame.from_records(records)


def write_realism4_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Realism 4 comparison table."""
    frame = build_realism4_comparison(workbook)
    cols = [c for c in _CSV_COLS if c in frame.columns]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, cols].to_csv(output, index=False)
    return output
