"""Excel-shaped Output 1-1 / 1-2 tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from lic_dsf.dsa import load_core
from lic_dsf.output import (
    external_dsa_panel,
    output_11_table,
    output_12_table,
    public_dsa_panel,
)
from tests.parity import (
    assert_all_passed,
    compare_probes,
    excel_available,
    read_cached_output,
    read_live_output,
)
from tests.parity.catalogs import output_11_probes, output_12_probes

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"
WORKBOOK_XLSM = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsm"

_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        _CORE = load_core(WORKBOOK)
    return _CORE


def test_output_11_table_shape_and_thin_panel_unchanged() -> None:
    _macro, _ext, ext_base, _pub = _core()
    table = output_11_table(ext_base)
    assert 30 in table.index
    assert 8 in table.index
    assert 2024 in table.columns
    thin = external_dsa_panel(ext_base)
    assert "PV of PPG external debt / GDP" in thin.index
    assert list(thin.columns) == list(ext_base.years)


def test_output_12_table_shape_and_thin_panel_unchanged() -> None:
    _macro, _ext, _ext_base, pub_base = _core()
    table = output_12_table(pub_base)
    assert 8 in table.index
    assert 31 in table.index
    thin = public_dsa_panel(pub_base)
    assert "Public sector debt / GDP" in thin.index


def test_output_11_cached_parity_headline_rows() -> None:
    _macro, _ext, ext_base, _pub = _core()
    sut = output_11_table(ext_base)
    probes = tuple(p for p in output_11_probes(WORKBOOK) if p.row in {8, 9, 15, 30, 33, 35, 38, 50})
    excel = read_cached_output(WORKBOOK, probes)
    # Skip blank Excel cells (``...`` / None) so history holes do not fail.
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    frame = compare_probes(excel, sut)
    assert_all_passed(frame)


def test_output_12_cached_parity_headline_rows() -> None:
    _macro, _ext, _ext_base, pub_base = _core()
    sut = output_12_table(pub_base)
    probes = tuple(p for p in output_12_probes(WORKBOOK) if p.row in {8, 9, 13, 31, 35, 37, 42})
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    frame = compare_probes(excel, sut)
    assert_all_passed(frame)


@pytest.mark.live_excel
def test_output_11_live_excel() -> None:
    if not excel_available():
        pytest.skip("live Excel not available")
    _macro, _ext, ext_base, _pub = _core()
    sut = output_11_table(ext_base)
    probes = output_11_probes(WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK)
    excel = read_live_output(WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


@pytest.mark.live_excel
def test_output_12_live_excel() -> None:
    if not excel_available():
        pytest.skip("live Excel not available")
    _macro, _ext, _ext_base, pub_base = _core()
    sut = output_12_table(pub_base)
    probes = output_12_probes(WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK)
    excel = read_live_output(WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))
