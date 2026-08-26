"""Probe catalogs for Output 3-1 / 3-2 Excel-shaped tables."""

from __future__ import annotations

from pathlib import Path

from fastpyxl import load_workbook

from lic_dsf.output.stress import OUTPUT31_SHEET, OUTPUT32_SHEET
from tests.parity.probes import Probe, as_year, probes_for_years

_EXT_INDICATORS = (
    "PV of debt-to GDP ratio",
    "PV of debt-to-exports ratio",
    "Debt service-to-exports ratio",
    "Debt service-to-revenue ratio",
)
_PUB_INDICATORS = (
    "PV of Debt-to-GDP Ratio",
    "PV of Debt-to-Revenue Ratio",
    "Debt Service-to-Revenue Ratio",
    "Debt Service-to-GDP Ratio",
)


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


def _scenario_row_map(
    path: Path,
    *,
    sheet: str,
    label_col: int,
    sections: tuple[str, ...],
) -> dict[tuple[str, str], int]:
    """Map ``(indicator, scenario-label)`` to Excel row from Output 3-x."""
    from lic_dsf.stress.compare import _EXT_SECTIONS, _PUB_SECTIONS, _SCENARIO_KEYS, _norm

    section_map = _EXT_SECTIONS if sheet == OUTPUT31_SHEET else _PUB_SECTIONS
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        section = ""
        out: dict[tuple[str, str], int] = {}
        for row in range(1, (ws.max_row or 0) + 1):
            raw = ws.cell(row, label_col).value
            header = _norm(raw)
            if header in section_map:
                section = section_map[header]
                continue
            key = _SCENARIO_KEYS.get(header)
            if key is None or not section or section not in sections:
                continue
            out[(section, key)] = row
        return out
    finally:
        wb.close()


def output_31_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """Probes for Output 3-1 rows that exist in the SUT (by indicator/scenario)."""
    path = Path(workbook)
    years = _year_cols(path, OUTPUT31_SHEET, 6, 3)
    rows = _scenario_row_map(
        path, sheet=OUTPUT31_SHEET, label_col=1, sections=_EXT_INDICATORS
    )
    probes: list[Probe] = []
    for (indicator, scenario), row in rows.items():
        probes.extend(
            probes_for_years(
                sheet=OUTPUT31_SHEET,
                row=row,
                sut_key=(indicator, scenario),
                year_cols=years,
                section=indicator,
                label=scenario,
            )
        )
    return tuple(probes)


def output_32_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """Probes for Output 3-2 rows that exist in the SUT."""
    path = Path(workbook)
    years = _year_cols(path, OUTPUT32_SHEET, 8, 4)
    rows = _scenario_row_map(
        path, sheet=OUTPUT32_SHEET, label_col=2, sections=_PUB_INDICATORS
    )
    probes: list[Probe] = []
    for (indicator, scenario), row in rows.items():
        probes.extend(
            probes_for_years(
                sheet=OUTPUT32_SHEET,
                row=row,
                sut_key=(indicator, scenario),
                year_cols=years,
                section=indicator,
                label=scenario,
            )
        )
    return tuple(probes)
