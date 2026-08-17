"""Tests for Realism 3 Excel vs Python side-by-side comparison."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.realism.compare_realism3 import (
    REALISM3_SHEET,
    build_realism3_comparison,
    write_realism3_comparison_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def test_comparison_has_sheet_and_computed_columns() -> None:
    frame = build_realism3_comparison(WORKBOOK)
    for col in (
        "sheet",
        "row",
        "col",
        "year",
        "section",
        "series_code",
        "label",
        "excel_value",
        "computed_value",
        "abs_diff",
    ):
        assert col in frame.columns
    assert (frame["sheet"] == REALISM3_SHEET).all()
    assert frame["excel_value"].notna().any()
    assert frame["computed_value"].notna().any()


def test_current_real_growth_2024_matches_excel() -> None:
    frame = build_realism3_comparison(WORKBOOK)
    row = frame[
        (frame["section"] == "Chart series")
        & (frame["label"] == "Real GDP growth - Curr. DSA")
        & (frame["year"] == 2024)
    ]
    assert len(row) == 1
    excel = float(row["excel_value"].iloc[0])
    computed = float(row["computed_value"].iloc[0])
    assert computed == pytest.approx(excel, rel=1e-6)


def test_write_csv_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "realism3.csv"
    written = write_realism3_comparison_csv(WORKBOOK, out)
    assert written == out
    loaded = pd.read_csv(out)
    assert "excel_value" in loaded.columns
    assert len(loaded) > 10
