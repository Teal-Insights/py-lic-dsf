"""Tests for Realism 3 Excel vs Python side-by-side comparison."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.realism.compare_realism3 import (
    REALISM3_SHEET,
    _CURR_DSA_LABEL,
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
        & (frame["label"] == _CURR_DSA_LABEL)
        & (frame["year"] == 2024)
    ]
    assert len(row) == 1
    assert str(row["cell"].iloc[0]) == "I27"
    excel = float(row["excel_value"].iloc[0])
    computed = float(row["computed_value"].iloc[0])
    assert computed == pytest.approx(excel, rel=1e-6)


def test_current_real_growth_chart_block_matches_excel() -> None:
    """Curr.DSA real GDP growth matches Excel for the chart-block years."""
    frame = build_realism3_comparison(WORKBOOK)
    rows = frame[
        (frame["section"] == "Chart series")
        & (frame["label"] == _CURR_DSA_LABEL)
        & frame["year"].between(2018, 2029)
    ]
    assert set(int(y) for y in rows["year"]) == set(range(2018, 2030))
    for _, row in rows.iterrows():
        assert float(row["computed_value"]) == pytest.approx(
            float(row["excel_value"]), rel=1e-6, abs=1e-9
        ), f"year={row['year']}"


def test_comparison_excludes_prev_dsa_growth() -> None:
    frame = build_realism3_comparison(WORKBOOK)
    assert not frame["series_code"].str.contains("Prev", case=False, na=False).any()
    assert (frame["label"] == _CURR_DSA_LABEL).all()
    assert (frame["series_code"] == _CURR_DSA_LABEL).all()


def test_write_csv_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "realism3.csv"
    written = write_realism3_comparison_csv(WORKBOOK, out)
    assert written == out
    loaded = pd.read_csv(out)
    assert "excel_value" in loaded.columns
    assert len(loaded) > 10
