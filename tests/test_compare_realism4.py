"""Tests for Realism 4 Excel vs Python side-by-side comparison."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.output import realism4_sheet_table
from lic_dsf.realism.compare_realism4 import (
    REALISM4_SHEET,
    build_realism4_comparison,
    write_realism4_comparison_csv,
    year_cols,
)
from tests.parity.catalogs.realism4 import realism4_probes
from tests.parity.equality import ABS_TOL

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def test_comparison_has_sheet_and_computed_columns() -> None:
    frame = build_realism4_comparison(WORKBOOK)
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
        "passed",
        "missing_sut",
    ):
        assert col in frame.columns
    assert (frame["sheet"] == REALISM4_SHEET).all()
    assert frame["excel_value"].notna().any()
    assert frame["computed_value"].notna().any()


def test_probe_catalog_covers_2035() -> None:
    years = year_cols(WORKBOOK)
    assert max(years) == 2035
    assert min(years) == 2021
    probes = realism4_probes(WORKBOOK)
    adj_years = {p.year for p in probes if p.sut_key == ("three_year_adjustment",)}
    pd_years = {p.year for p in probes if p.sut_key == ("primary_deficit",)}
    assert 2035 in adj_years
    assert 2021 in pd_years
    assert 2023 not in adj_years  # Excel R10 blank before 2024


def test_full_sheet_parity_at_1e_6() -> None:
    frame = build_realism4_comparison(WORKBOOK)
    assert len(frame) > 0
    assert int(frame["missing_sut"].sum()) == 0
    failed = frame.loc[~frame["passed"].astype(bool)]
    assert failed.empty, failed[["cell", "label", "excel_value", "computed_value", "abs_diff"]].to_string()
    numeric_diffs = frame["abs_diff"].dropna()
    assert float(numeric_diffs.max()) <= ABS_TOL


def test_sections_include_projections_placement_histogram() -> None:
    frame = build_realism4_comparison(WORKBOOK)
    sections = set(frame["section"].unique())
    assert sections == {"Projections", "Placement", "Histogram"}
    assert (frame["section"] == "Projections").sum() == 15 + 12  # R9 2021–2035 + R10 2024–2035
    assert (frame["section"] == "Placement").sum() == 4


def test_realism4_sheet_table_matches_excel_paths() -> None:
    table = realism4_sheet_table(WORKBOOK)
    assert list(table.index) == ["Primary deficit", "3-yr Fiscal adjustment"]
    assert 2021 in table.columns and 2035 in table.columns
    assert pd.isna(table.loc["3-yr Fiscal adjustment", 2021])
    assert pd.isna(table.loc["3-yr Fiscal adjustment", 2023])
    assert pd.notna(table.loc["3-yr Fiscal adjustment", 2024])
    assert pd.notna(table.loc["3-yr Fiscal adjustment", 2035])
    placement = table.attrs["placement"]
    assert placement.category == 20
    assert "histogram" in table.attrs

    frame = build_realism4_comparison(WORKBOOK)
    for year in range(2021, 2036):
        row = frame[
            (frame["label"] == "Primary deficit") & (frame["year"] == year)
        ]
        assert len(row) == 1
        assert float(table.loc["Primary deficit", year]) == pytest.approx(
            float(row["excel_value"].iloc[0]), abs=ABS_TOL
        )
    for year in range(2024, 2036):
        row = frame[
            (frame["label"] == "3-yr Fiscal adjustment") & (frame["year"] == year)
        ]
        assert len(row) == 1
        assert float(table.loc["3-yr Fiscal adjustment", year]) == pytest.approx(
            float(row["excel_value"].iloc[0]), abs=ABS_TOL
        )


def test_write_csv_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "realism4.csv"
    written = write_realism4_comparison_csv(WORKBOOK, out)
    assert written == out
    loaded = pd.read_csv(out)
    assert "excel_value" in loaded.columns
    assert "missing_sut" in loaded.columns
    assert len(loaded) > 10
    assert loaded["missing_sut"].sum() == 0
