"""Tests for Output 5-1 / 5-2 / 6 / 7 Excel vs Python comparison CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.rating.compare import (
    build_output6_comparison,
    build_output7_comparison,
    build_output51_comparison,
    build_output52_comparison,
    write_output6_comparison_csv,
    write_output7_comparison_csv,
    write_output51_comparison_csv,
    write_output52_comparison_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

_COLUMNS = (
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
)


def _by_cell(frame: pd.DataFrame, cell: str) -> pd.Series:
    row = frame[frame["cell"] == cell]
    assert len(row) == 1, f"{cell}: {len(row)} rows"
    return row.iloc[0]


def _assert_columns(frame: pd.DataFrame) -> None:
    for col in _COLUMNS:
        assert col in frame.columns
    assert frame["excel_value"].notna().any()
    assert frame["computed_value"].notna().any()


def test_output51_threshold_peak_and_mechanical() -> None:
    frame = build_output51_comparison(WORKBOOK)
    _assert_columns(frame)

    threshold = _by_cell(frame, "D66")
    assert float(threshold["excel_value"]) == pytest.approx(40.0)
    assert float(threshold["computed_value"]) == pytest.approx(40.0)

    peak = _by_cell(frame, "D61")
    assert float(peak["computed_value"]) == pytest.approx(
        float(peak["excel_value"]), rel=1e-6
    )

    mechanical = _by_cell(frame, "D10")
    assert str(mechanical["excel_value"]) == "High"
    assert str(mechanical["computed_value"]) == "High"
    assert float(mechanical["abs_diff"]) == pytest.approx(0.0)


def test_output52_gfn_and_embi_table() -> None:
    frame = build_output52_comparison(WORKBOOK)
    _assert_columns(frame)

    benchmark = _by_cell(frame, "AB8")
    assert float(benchmark["excel_value"]) == pytest.approx(14.0)
    assert float(benchmark["computed_value"]) == pytest.approx(14.0)

    max_gfn = _by_cell(frame, "AB9")
    assert float(max_gfn["computed_value"]) == pytest.approx(
        float(max_gfn["excel_value"]), rel=1e-6
    )

    gfn_breach = _by_cell(frame, "AB10")
    assert str(gfn_breach["excel_value"]) == "Yes"
    assert str(gfn_breach["computed_value"]) == "Yes"

    embi = _by_cell(frame, "AX9")
    assert float(embi["excel_value"]) == pytest.approx(350.0)
    assert float(embi["computed_value"]) == pytest.approx(350.0)

    embi_bench = _by_cell(frame, "AX8")
    assert float(embi_bench["excel_value"]) == pytest.approx(570.0)
    assert float(embi_bench["computed_value"]) == pytest.approx(570.0)

    applicable = _by_cell(frame, "C27")
    assert str(applicable["excel_value"]) == "Yes"
    assert str(applicable["computed_value"]) == "Yes"


def test_output6_baseline_pv_gdp_2024() -> None:
    frame = build_output6_comparison(WORKBOOK)
    _assert_columns(frame)

    baseline = _by_cell(frame, "H27")
    assert int(baseline["year"]) == 2024
    assert float(baseline["computed_value"]) == pytest.approx(
        float(baseline["excel_value"]), rel=1e-6
    )

    threshold = _by_cell(frame, "H30")
    assert float(threshold["excel_value"]) == pytest.approx(40.0)
    assert float(threshold["computed_value"]) == pytest.approx(40.0)

    lower = _by_cell(frame, "H31")
    assert float(lower["excel_value"]) == pytest.approx(38.0)
    assert float(lower["computed_value"]) == pytest.approx(38.0)

    historical = _by_cell(frame, "I28")
    assert int(historical["year"]) == 2025
    assert pd.notna(historical["computed_value"])
    assert float(historical["computed_value"]) == pytest.approx(
        float(historical["excel_value"]), rel=1e-4, abs=0.05
    )

    baseline_prob = _by_cell(frame, "H84")
    assert float(baseline_prob["excel_value"]) == pytest.approx(18.415979429368583)
    assert float(baseline_prob["computed_value"]) == pytest.approx(
        float(baseline_prob["excel_value"]), abs=0.05
    )

    mx_prob = _by_cell(frame, "H86")
    assert float(mx_prob["computed_value"]) == pytest.approx(
        float(mx_prob["excel_value"]), abs=0.05
    )


def test_output7_mechanical_and_ci_score() -> None:
    frame = build_output7_comparison(WORKBOOK)
    _assert_columns(frame)

    mechanical = _by_cell(frame, "E48")
    assert str(mechanical["excel_value"]) == "High"
    assert str(mechanical["computed_value"]) == "High"

    ci_score = _by_cell(frame, "E66")
    assert float(ci_score["computed_value"]) == pytest.approx(
        float(ci_score["excel_value"]), rel=1e-8
    )
    assert frame[frame["cell"].isin(["E49", "E50", "E55"])].empty


def test_write_csv_roundtrips(tmp_path: Path) -> None:
    writers = (
        write_output51_comparison_csv,
        write_output52_comparison_csv,
        write_output6_comparison_csv,
        write_output7_comparison_csv,
    )
    for write in writers:
        out = tmp_path / f"{write.__name__}.csv"
        written = write(WORKBOOK, out)
        assert written == out
        loaded = pd.read_csv(out)
        assert "excel_value" in loaded.columns
        assert "computed_value" in loaded.columns
        assert len(loaded) > 3
