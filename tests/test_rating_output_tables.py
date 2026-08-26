"""Cell-keyed Output 5 / 7 tables (no live Excel required)."""

from __future__ import annotations

from pathlib import Path

from lic_dsf.output import output_51_table, output_52_table, output_7_table

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def test_output_51_table_has_mechanical_and_threshold() -> None:
    table = output_51_table(WORKBOOK)
    assert "D10" in table.index
    assert "D66" in table.index
    assert str(table.loc["D10", "value"]) == "High"
    assert float(table.loc["D66", "value"]) == 40.0


def test_output_52_table_has_gfn_benchmark() -> None:
    table = output_52_table(WORKBOOK)
    assert "AB8" in table.index
    assert float(table.loc["AB8", "value"]) == 14.0


def test_output_7_table_has_mechanical_external() -> None:
    table = output_7_table(WORKBOOK)
    assert "E48" in table.index
    assert str(table.loc["E48", "value"]) == "High"
