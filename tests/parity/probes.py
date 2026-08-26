"""Probe catalog types for Output-panel differential tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Hashable

import pandas as pd


@dataclass(frozen=True, slots=True)
class Probe:
    """One Output-sheet cell (or year-cell) compared to a SUT key.

    Attributes:
        sheet: Excel sheet name.
        row: 1-based Excel row.
        col: 1-based Excel column (optional when ``year`` is set and a year
            header map is supplied at read time).
        year: Calendar year for time-series probes.
        label: Human-readable Excel label.
        sut_key: Key into the SUT table (row number, MultiIndex tuple, or
            cell address). Missing keys fail the run as a missing-SUT error.
        section: Optional section header (Output 3-x indicator name).
    """

    sheet: str
    row: int
    sut_key: Hashable
    label: str = ""
    col: int | None = None
    year: int | None = None
    section: str = ""


def a1(row: int, col: int) -> str:
    """Return A1 notation for a 1-based ``(row, col)``."""
    letters = ""
    n = col
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row}"


def as_year(value: Any) -> int | None:
    """Parse a year header cell."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    year = int(value)
    if 1990 <= year <= 2100:
        return year
    return None


def year_columns(headers: pd.Series | dict[int, int], *, first_col: int = 1) -> dict[int, int]:
    """Map calendar year to 1-based column index.

    Args:
        headers: Either a ``{year: col}`` map or a 1-based Series of header
            values keyed by column index.
        first_col: First column to scan when ``headers`` is a Series.
    """
    if isinstance(headers, dict):
        return {int(year): int(col) for year, col in headers.items()}
    cols: dict[int, int] = {}
    for col, value in headers.items():
        if int(col) < first_col:
            continue
        year = as_year(value)
        if year is not None:
            cols[year] = int(col)
    return cols


def probes_for_years(
    *,
    sheet: str,
    row: int,
    sut_key: Hashable,
    year_cols: dict[int, int],
    label: str = "",
    section: str = "",
) -> tuple[Probe, ...]:
    """Build one probe per year column for a time-series Excel row."""
    return tuple(
        Probe(
            sheet=sheet,
            row=row,
            col=col,
            year=year,
            sut_key=sut_key,
            label=label,
            section=section,
        )
        for year, col in sorted(year_cols.items())
    )
