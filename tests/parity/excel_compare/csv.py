"""Shared CSV write / pair helpers for legacy Excel comparisons."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from tests.parity.excel_compare.cells import a1, year_int

CSV_COLS = [
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


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def abs_diff(excel: object, computed: object) -> float | None:
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


def lookup(
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
        year_i = year_int(year)
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
        value = lookup(computed, section, match_key, year)
        computed_values.append(value if value is not None else pd.NA)
        diffs.append(abs_diff(excel_value, value))
    excel = excel.copy()
    excel["computed_value"] = computed_values
    excel["abs_diff"] = diffs
    return excel.sort_values(
        ["row", "col", "section", "year"], na_position="last"
    ).reset_index(drop=True)


def write_comparison_csv(frame: pd.DataFrame, output: str | Path) -> Path:
    """Write ``frame`` comparison columns to ``output``."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cols = [c for c in CSV_COLS if c in frame.columns]
    frame.loc[:, cols].to_csv(output, index=False)
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
        "cell": a1(row, col),
        "row": row,
        "col": col,
        "year": year,
        "section": section,
        "series_code": series_code,
        "label": label,
        "match_key": match_key,
        "excel_value": value,
    }


# Re-export cell helpers used by leaf modules.
__all__ = [
    "CSV_COLS",
    "a1",
    "abs_diff",
    "as_year",
    "is_number",
    "lookup",
    "pair_frame",
    "record_cell",
    "write_comparison_csv",
    "year_int",
]
