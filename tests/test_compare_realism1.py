"""Tests for Realism 1 Excel vs Python side-by-side comparison."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.realism.compare import (
    REALISM1_SHEET,
    build_realism1_comparison,
    write_realism1_comparison_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def test_comparison_has_sheet_and_computed_columns() -> None:
    frame = build_realism1_comparison(WORKBOOK)
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
    assert (frame["sheet"] == REALISM1_SHEET).all()
    assert frame["excel_value"].notna().any()
    assert frame["computed_value"].notna().any()


def test_current_ppg_debt_to_gdp_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Current vintage", "D_PPG_GDP", 2024)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-8
    )


def test_current_total_external_d_gdp_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Current vintage", "D_GDP", 2024)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_current_d_lch_gdp_2019_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Current vintage", "D_LCH_GDP", 2019)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_chart_usd_current_dsa_2029_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Chart (level)", "Current DSA", 2029)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def _cell(frame: pd.DataFrame, section: str, key: str, year: int) -> pd.Series:
    row = frame[
        (frame["section"] == section)
        & ((frame["series_code"] == key) | (frame["label"] == key))
        & (frame["year"] == year)
    ]
    assert len(row) == 1, f"{section} {key} {year}: {len(row)} rows"
    return row.iloc[0]


def test_chart_usd_dsa2019_2029_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Chart (level)", "DSA-2019", 2029)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_chart_usd_previous_dsa_2029_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Chart (level)", "Previous DSA", 2029)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_last_vintage_rebased_ngdp_2034_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "Public / Last vintage (re-based)", "NGDP", 2034)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_last_vintage_rebased_du_gdp_2021_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "Public / Last vintage (re-based)", "DU_GDP", 2021)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_last_vintage_rebased_d_ppg_gdp_2020_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "External / Last vintage (re-based)", "D_PPG_GDP", 2020)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_five_years_ago_rebased_still_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "Public / 5 years ago (re-based)", "NGDP", 2034)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_current_ducir_2021_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "Public / Current vintage", "DUCIR_GDP", 2021)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_current_residual_2021_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "Public / Current vintage", "Residual", 2021)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_five_years_ago_rebased_residual_2028_matches_excel() -> None:
    frame = build_realism1_comparison(WORKBOOK)
    row = _cell(frame, "Public / 5 years ago (re-based)", "Residual", 2028)
    assert float(row["computed_value"]) == pytest.approx(
        float(row["excel_value"]), rel=1e-6
    )


def test_write_csv_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "realism1.csv"
    written = write_realism1_comparison_csv(WORKBOOK, out)
    assert written == out
    loaded = pd.read_csv(out)
    assert "excel_value" in loaded.columns
    assert "computed_value" in loaded.columns
    assert len(loaded) > 10
