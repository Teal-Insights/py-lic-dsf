"""Workbook layout helpers for B-sheet and ResFin probe catalogs."""

from __future__ import annotations

from pathlib import Path

from fastpyxl import load_workbook

from tests.parity.probes import Probe, as_year


def year_cols(
    path: str | Path,
    sheet: str,
    year_row: int,
    first_col: int,
) -> dict[int, int]:
    """Map calendar year → 1-based column, scanning contiguous year headers."""
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        cols: dict[int, int] = {}
        col = first_col
        while True:
            year = as_year(ws.cell(year_row, col).value)
            if year is None:
                break
            cols[year] = col
            col += 1
        return cols
    finally:
        wb.close()


def probes_for_metric_rows(
    *,
    path: str | Path,
    sheet: str,
    year_row: int,
    first_col: int,
    scenario_id: str,
    rows: tuple[tuple[int, str], ...],
    last_year: int | None = None,
) -> tuple[Probe, ...]:
    """One probe per ``(sheet_row, year)`` with ``sut_key=(scenario_id, row, year)``.

    ``last_year`` drops header years beyond the model horizon (ResFin sheets
    carry amortization columns decades past the projection).
    """
    years = year_cols(path, sheet, year_row, first_col)
    probes: list[Probe] = []
    for row, label in rows:
        for year, col in sorted(years.items()):
            if last_year is not None and year > last_year:
                continue
            probes.append(
                Probe(
                    sheet=sheet,
                    row=row,
                    col=col,
                    year=year,
                    sut_key=(scenario_id, row, year),
                    label=label,
                    section=scenario_id,
                )
            )
    return tuple(probes)
