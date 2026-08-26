"""Probe catalogs for Output 1-1 / 1-2 Excel-shaped tables."""

from __future__ import annotations

from pathlib import Path

from fastpyxl import load_workbook

from lic_dsf.output.baseline import (
    OUTPUT11_NUMERIC_ROWS,
    OUTPUT11_SHEET,
    OUTPUT12_NUMERIC_ROWS,
    OUTPUT12_SHEET,
)
from tests.parity.probes import Probe, as_year, probes_for_years


def _year_cols(path: Path, sheet: str, year_row: int, first_col: int) -> dict[int, int]:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        cols: dict[int, int] = {}
        for col in range(first_col, (ws.max_column or first_col) + 1):
            year = as_year(ws.cell(year_row, col).value)
            if year is not None:
                cols[year] = col
        return cols
    finally:
        wb.close()


def output_11_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """Probes for every numeric Output 1-1 series row in the SUT table."""
    path = Path(workbook)
    years = _year_cols(path, OUTPUT11_SHEET, 6, 3)
    probes: list[Probe] = []
    for row in OUTPUT11_NUMERIC_ROWS:
        probes.extend(
            probes_for_years(
                sheet=OUTPUT11_SHEET,
                row=row,
                sut_key=row,
                year_cols=years,
            )
        )
    return tuple(probes)


def output_12_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """Probes for every numeric Output 1-2 series row in the SUT table."""
    path = Path(workbook)
    years = _year_cols(path, OUTPUT12_SHEET, 6, 3)
    probes: list[Probe] = []
    for row in OUTPUT12_NUMERIC_ROWS:
        probes.extend(
            probes_for_years(
                sheet=OUTPUT12_SHEET,
                row=row,
                sut_key=row,
                year_cols=years,
            )
        )
    return tuple(probes)
