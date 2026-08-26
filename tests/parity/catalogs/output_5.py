"""Probe catalogs for cell-keyed Output 5 / 7 tables."""

from __future__ import annotations

from lic_dsf.output.rating import _OUTPUT51_CELLS, _OUTPUT52_CELLS, _OUTPUT7_CELLS
from tests.parity.probes import Probe


def _parse_a1(cell: str) -> tuple[int, int]:
    i = 0
    while i < len(cell) and cell[i].isalpha():
        i += 1
    letters, digits = cell[:i], cell[i:]
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch.upper()) - 64)
    return int(digits), col


def _cell_probes(sheet: str, cells: dict[str, tuple[str, str]]) -> tuple[Probe, ...]:
    probes: list[Probe] = []
    for cell, (section, label) in cells.items():
        row, col = _parse_a1(cell)
        probes.append(
            Probe(
                sheet=sheet,
                row=row,
                col=col,
                sut_key=cell,
                section=section,
                label=label,
            )
        )
    return tuple(probes)


def output_51_probes() -> tuple[Probe, ...]:
    """Cell probes for Output 5-1 / Chart Data values the library computes."""
    chart = _cell_probes(
        "Chart Data",
        {k: v for k, v in _OUTPUT51_CELLS.items() if k != "E73"},
    )
    space = Probe(
        sheet="Output 7 - Risk rating summary",
        row=73,
        col=5,
        sut_key="E73",
        section="Output 5-1",
        label="Space to absorb shock",
    )
    return chart + (space,)


def output_52_probes() -> tuple[Probe, ...]:
    """Cell probes for Output 5-2 market-module values."""
    return _cell_probes("Output 5-2 Market module", _OUTPUT52_CELLS)


def output_7_probes() -> tuple[Probe, ...]:
    """Cell probes for Output 7 summary values the library computes."""
    return _cell_probes("Output 7 - Risk rating summary", _OUTPUT7_CELLS)
