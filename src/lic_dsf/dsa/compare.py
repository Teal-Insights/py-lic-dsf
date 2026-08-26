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
from lic_dsf.realism.compare import _a1, _as_year, _year_int

OUTPUT11_SHEET = "Output 1-1 - External DSA"
OUTPUT12_SHEET = "Output 1-2 - Public DSA"

_CSV_COLS = [
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
]

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


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _abs_diff(excel: object, computed: object) -> float | None:
    if excel is None or computed is None:
        return None
    if isinstance(excel, float) and pd.isna(excel):
        return None
    if isinstance(computed, float) and pd.isna(computed):
        return None
    if (
        isinstance(excel, (int, float))
        and not isinstance(excel, bool)
        and isinstance(computed, (int, float))
        and not isinstance(computed, bool)
    ):
        return abs(float(excel) - float(computed))
    return None


def _lookup(
    computed: dict[tuple[str, str], pd.Series],
    section: object,
    match_key: object,
    year: object,
) -> object | None:
    series = computed.get((str(section), str(match_key)))
    if series is None:
        return None
    if year is None or (isinstance(year, float) and pd.isna(year)):
        raw = series.iloc[0] if len(series) else None
    else:
        year_i = _year_int(year)
        raw = series.loc[year_i] if year_i in series.index else None
    if raw is None:
        return None
    if not isinstance(raw, str) and pd.isna(raw):
        return None
    return raw


def pair_frame(
    excel: pd.DataFrame,
    computed: dict[tuple[str, str], pd.Series],
) -> pd.DataFrame:
    """Attach Python values to Excel rows."""
    computed_values: list[object] = []
    diffs: list[float | None] = []
    for section, match_key, year, excel_value in zip(
        excel["section"].tolist(),
        excel["match_key"].tolist(),
        excel["year"].tolist(),
        excel["excel_value"].tolist(),
        strict=True,
    ):
        value = _lookup(computed, section, match_key, year)
        computed_values.append(value if value is not None else pd.NA)
        diffs.append(_abs_diff(excel_value, value))
    excel = excel.copy()
    excel["computed_value"] = computed_values
    excel["abs_diff"] = diffs
    return excel.sort_values(
        ["row", "col", "section", "year"], na_position="last"
    ).reset_index(drop=True)


def write_comparison_csv(frame: pd.DataFrame, output: str | Path) -> Path:
    """Write `frame` comparison columns to `output`."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, _CSV_COLS].to_csv(output, index=False)
    return output


def record_cell(
    *,
    sheet: str,
    row: int,
    col: int,
    year: int | None,
    section: str,
    series_code: str,
    label: str,
    match_key: str,
    value: object,
) -> dict[str, Any]:
    """Build one Excel-side comparison row."""
    return {
        "sheet": sheet,
        "cell": _a1(row, col),
        "row": row,
        "col": col,
        "year": year,
        "section": section,
        "series_code": series_code,
        "label": label,
        "match_key": match_key,
        "excel_value": value,
    }


def year_cols(ws: Any, year_row: int, first_col: int) -> dict[int, int]:
    """Map calendar year to column index from a header row."""
    cols: dict[int, int] = {}
    for col in range(first_col, (ws.max_column or first_col) + 1):
        year = _as_year(ws.cell(year_row, col).value)
        if year is not None:
            cols[year] = col
    return cols


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
