"""Unit tests for the Output-panel parity contract (no Excel required)."""

from __future__ import annotations

import pandas as pd

from tests.parity import (
    Probe,
    a1,
    abs_diff,
    close,
    compare_probes,
    error_class,
    excel_available,
    probes_for_years,
)


def test_close_absolute_and_relative() -> None:
    assert close(1.0, 1.0 + 1e-7)
    assert close(1e12, 1e12 + 1.0)  # rel ~ 1e-12
    assert not close(1.0, 1.0 + 1e-5)
    assert close(float("nan"), float("nan"))
    assert close(None, None)
    assert close("...", pd.NA)
    assert close("#DIV/0!", "#DIV/0!")
    assert not close("#DIV/0!", "#N/A")
    assert close("High", "High")
    assert not close("High", "Moderate")


def test_error_class_and_abs_diff() -> None:
    assert error_class("#REF!") == "#REF!"
    assert error_class(1.0) is None
    assert abs_diff(3.0, 1.0) == 2.0
    assert abs_diff("a", 1.0) is None
    assert abs_diff(1.0, 1.0) == 0.0


def test_a1_and_probes_for_years() -> None:
    assert a1(30, 4) == "D30"
    assert a1(1, 28) == "AB1"
    probes = probes_for_years(
        sheet="Output 1-1 - External DSA",
        row=30,
        sut_key=30,
        year_cols={2024: 14, 2025: 15},
        label="PV/GDP",
    )
    assert len(probes) == 2
    assert probes[0].year == 2024
    assert probes[0].col == 14


def test_compare_probes_missing_sut_fails() -> None:
    excel = pd.DataFrame(
        {
            "sheet": ["Output 1-1 - External DSA"],
            "cell": ["D30"],
            "row": [30],
            "col": [4],
            "year": [2024],
            "section": [""],
            "label": ["PV/GDP"],
            "sut_key": [30],
            "excel_value": [10.0],
        }
    )
    sut = pd.DataFrame({2024: [10.0]}, index=[99])
    frame = compare_probes(excel, sut)
    assert bool(frame.loc[0, "missing_sut"])
    assert not bool(frame.loc[0, "passed"])


def test_compare_probes_pass() -> None:
    excel = pd.DataFrame(
        {
            "sheet": ["Output 1-1 - External DSA"],
            "cell": ["D30"],
            "row": [30],
            "col": [4],
            "year": [2024],
            "section": [""],
            "label": ["PV/GDP"],
            "sut_key": [30],
            "excel_value": [10.0],
        }
    )
    sut = pd.DataFrame({2024: [10.0]}, index=[30])
    frame = compare_probes(excel, sut)
    assert bool(frame.loc[0, "passed"])
    assert not bool(frame.loc[0, "missing_sut"])


def test_excel_available_false_without_flag() -> None:
    assert excel_available() is False


def test_probe_is_frozen() -> None:
    probe = Probe(sheet="Output 7 - Risk rating summary", row=48, col=5, sut_key="E48")
    assert probe.sut_key == "E48"
