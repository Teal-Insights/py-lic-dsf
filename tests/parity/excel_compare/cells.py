"""Shared Excel cell / year helpers for legacy CSV compare modules."""

from __future__ import annotations

from typing import Any


def a1(row: int, col: int) -> str:
    """Return A1 notation for a 1-based ``(row, col)``."""
    letters = ""
    n = col
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row}"


def year_int(value: object) -> int:
    """Coerce a year cell to ``int`` (raises on bool / bad types)."""
    if isinstance(value, bool):
        raise TypeError(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value))


def as_year(value: object) -> int | None:
    """Parse a calendar year from a header cell, or ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    year = int(value)
    if 1990 <= year <= 2100:
        return year
    return None


def year_cols(ws: Any, year_row: int, first_col: int) -> dict[int, int]:
    """Map calendar year to column index from a header row."""
    cols: dict[int, int] = {}
    for col in range(first_col, (ws.max_column or first_col) + 1):
        year = as_year(ws.cell(year_row, col).value)
        if year is not None:
            cols[year] = col
    return cols
