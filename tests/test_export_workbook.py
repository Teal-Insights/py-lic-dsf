"""Smoke and write round-trip tests for ``lic_dsf.run`` / ``lic_dsf.export``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastpyxl import load_workbook

from lic_dsf.export import sanitize_sheet_title, to_workbook, to_workbook_from_path
from lic_dsf.load import load_invest_growth_series
from lic_dsf.run import (
    OUTPUT_SHEET_ORDER,
    SHEET_1_1,
    SHEET_1_2,
    SHEET_7,
    SHEET_DATABASE,
    compute_outputs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

pytestmark = pytest.mark.skipif(
    not WORKBOOK.is_file(), reason="bundled LIC-DSF template missing"
)


def test_load_invest_growth_series_smoke() -> None:
    series = load_invest_growth_series(WORKBOOK)
    assert isinstance(series, pd.Series)
    assert len(series) >= 4
    assert all(isinstance(y, (int, float)) for y in series.index)


def test_compute_outputs_baseline_subset() -> None:
    book = compute_outputs(WORKBOOK, include={SHEET_1_1, SHEET_1_2})
    assert list(book.sheets) == [SHEET_1_1, SHEET_1_2]
    assert book.sheets[SHEET_1_1].shape[0] == 6
    assert book.sheets[SHEET_1_2].shape[0] == 6
    assert book.meta["first_projection_year"] >= 2000


def test_compute_outputs_rejects_unknown_sheet() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        compute_outputs(WORKBOOK, include={"not-a-sheet"})


def test_to_workbook_roundtrip_baseline(tmp_path: Path) -> None:
    book = compute_outputs(WORKBOOK, include={SHEET_1_1, SHEET_1_2})
    out = tmp_path / "panels.xlsx"
    written = to_workbook(book, out)
    assert written.is_file()

    wb = load_workbook(written, data_only=True, read_only=True)
    try:
        titles = set(wb.sheetnames)
        assert sanitize_sheet_title(SHEET_1_1) in titles
        assert sanitize_sheet_title(SHEET_1_2) in titles
        assert "Engine meta" in titles

        ws = wb[sanitize_sheet_title(SHEET_1_1)]
        # Header row then indicator rows (index in col A, years across).
        assert ws.cell(1, 2).value == 2011 or int(ws.cell(1, 2).value) == 2011
        src = book.sheets[SHEET_1_1]
        # Prefer a cell that is finite in the source panel.
        row_idx, col_idx = None, None
        for i in range(src.shape[0]):
            for j in range(src.shape[1]):
                value = src.iloc[i, j]
                if pd.notna(value):
                    row_idx, col_idx = i, j
                    break
            if row_idx is not None:
                break
        assert row_idx is not None and col_idx is not None
        expected = float(src.iloc[row_idx, col_idx])
        # Excel: row 1 header, data starts row 2; col 1 labels, years from col 2.
        actual = ws.cell(row_idx + 2, col_idx + 2).value
        assert actual is not None
        assert float(actual) == pytest.approx(expected, abs=1e-6, rel=1e-9)
    finally:
        wb.close()


def test_to_workbook_from_path_database(tmp_path: Path) -> None:
    out = tmp_path / "db_only.xlsx"
    to_workbook_from_path(WORKBOOK, out, include=[SHEET_DATABASE])
    wb = load_workbook(out, data_only=True, read_only=True)
    try:
        assert sanitize_sheet_title(SHEET_DATABASE) in wb.sheetnames
        ws = wb[sanitize_sheet_title(SHEET_DATABASE)]
        assert ws.cell(1, 1).value == "Indicator" or ws.cell(1, 2).value == "Indicator"
    finally:
        wb.close()


@pytest.mark.slow
def test_compute_outputs_full_catalog_keys() -> None:
    book = compute_outputs(WORKBOOK)
    assert list(book.sheets.keys()) == list(OUTPUT_SHEET_ORDER)
    assert SHEET_7 in book.sheets
    assert not book.sheets[SHEET_7].empty
    assert book.meta.get("country")
