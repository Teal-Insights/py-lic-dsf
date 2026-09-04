"""Probe catalog for ``Realism 4 - Fiscal adjustment`` numeric outputs."""

from __future__ import annotations

from pathlib import Path

from lic_dsf.realism.compare_realism4 import (
    REALISM4_SHEET,
    year_cols as _year_cols,
)
from tests.parity.probes import Probe, probes_for_years

PRIMARY_DEFICIT_ROW = 9
THREE_YEAR_ADJ_ROW = 10
PLACEMENT_ROW = 14
HISTOGRAM_FIRST_ROW = 23
HISTOGRAM_LAST_ROW = 50
THREE_YEAR_ADJ_FIRST_YEAR = 2024

_PD_LABEL = "Primary deficit"
_ADJ_LABEL = "3-yr Fiscal adjustment"

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


def year_cols(workbook: str | Path) -> dict[int, int]:
    """Map calendar year → column on Realism 4 (row 8 headers)."""
    return _year_cols(workbook)


def realism4_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """All numeric Realism 4 probes (R9 / R10 / R14 / R23–R50)."""
    from fastpyxl import load_workbook

    path = Path(workbook)
    years = year_cols(path)
    probes: list[Probe] = []

    probes.extend(
        probes_for_years(
            sheet=REALISM4_SHEET,
            row=PRIMARY_DEFICIT_ROW,
            sut_key=("primary_deficit",),
            year_cols=years,
            label=_PD_LABEL,
            section="Projections",
        )
    )

    adj_years = {y: c for y, c in years.items() if y >= THREE_YEAR_ADJ_FIRST_YEAR}
    probes.extend(
        probes_for_years(
            sheet=REALISM4_SHEET,
            row=THREE_YEAR_ADJ_ROW,
            sut_key=("three_year_adjustment",),
            year_cols=adj_years,
            label=_ADJ_LABEL,
            section="Projections",
        )
    )

    for col, field, label in _PLACEMENT_CELLS:
        probes.append(
            Probe(
                sheet=REALISM4_SHEET,
                row=PLACEMENT_ROW,
                col=col,
                year=None,
                sut_key=("placement", field),
                label=label,
                section="Placement",
            )
        )

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[REALISM4_SHEET]
        for row in range(HISTOGRAM_FIRST_ROW, HISTOGRAM_LAST_ROW + 1):
            for col, field in _HIST_COLS:
                value = ws.cell(row, col).value
                if value is None or isinstance(value, bool):
                    continue
                if not isinstance(value, (int, float, str)):
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                probes.append(
                    Probe(
                        sheet=REALISM4_SHEET,
                        row=row,
                        col=col,
                        year=None,
                        sut_key=("histogram", row, field),
                        label=f"histogram {field}",
                        section="Histogram",
                    )
                )
    finally:
        wb.close()

    return tuple(probes)
