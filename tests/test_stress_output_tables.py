"""Excel-shaped Output 3-x tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from lic_dsf.dsa import load_core
from lic_dsf.output import (
    output_31_table,
    output_32_table,
    stress_external_panel,
    stress_public_panel,
)
from lic_dsf.pv import load_input7_residual_params
from lic_dsf.stress import (
    load_input6_standard,
    run_a1_historical_external,
    run_b1_gdp_public,
    run_b2_pb_public,
    run_standard_external_stress,
)
from tests.parity import (
    assert_all_passed,
    compare_probes,
    excel_available,
    read_cached_output,
    read_live_output,
)
from tests.parity.catalogs import output_31_probes

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"
WORKBOOK_XLSM = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsm"

_CORE = None
_EXT_STRESS = None


def _bundle():
    global _CORE, _EXT_STRESS
    if _CORE is None:
        _CORE = load_core(WORKBOOK)
        macro, external, _ext_base, _pub = _CORE
        input6 = load_input6_standard(WORKBOOK)
        residual = load_input7_residual_params(WORKBOOK)
        _EXT_STRESS = (
            run_standard_external_stress(macro, external, input6, residual),
            run_a1_historical_external(macro, external, residual),
            input6,
            residual,
        )
    return _CORE, _EXT_STRESS


def test_output_31_table_includes_baseline_and_b2() -> None:
    (_macro, _ext, ext_base, _pub), (suite, historical, _i6, _res) = _bundle()
    table = output_31_table(
        ext_base, historical=historical, external_stress=suite
    )
    assert ("PV of debt-to GDP ratio", "Baseline") in table.index
    assert ("PV of debt-to GDP ratio", "B2. Primary balance") in table.index
    assert ("PV of debt-to GDP ratio", "B1. Real GDP growth") in table.index
    thin = stress_external_panel(suite["B1_GDP"])
    assert "PV of PPG external debt / GDP" in thin.index


def test_output_32_table_includes_public_stack() -> None:
    (macro, external, _ext_base, pub_base), (_suite, _hist, input6, residual) = (
        _bundle()
    )
    public = {
        "B1_GDP": run_b1_gdp_public(macro, external, input6, residual),
        "B2_PrimaryBalance": run_b2_pb_public(macro, external, input6, residual),
    }
    table = output_32_table(pub_base, public_stress=public)
    assert ("PV of Debt-to-GDP Ratio", "Baseline") in table.index
    assert ("PV of Debt-to-GDP Ratio", "B1. Real GDP growth") in table.index
    assert ("PV of Debt-to-GDP Ratio", "B2. Primary balance") in table.index
    thin = stress_public_panel(public["B1_GDP"])
    assert "Public sector debt / GDP" in thin.index


def test_output_31_cached_baseline_matches_excel() -> None:
    (_macro, _ext, ext_base, _pub), (suite, historical, _i6, _res) = _bundle()
    sut = output_31_table(
        ext_base, historical=historical, external_stress=suite
    )
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if p.sut_key == ("PV of debt-to GDP ratio", "Baseline")
        and p.year in {2024, 2025, 2026}
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


@pytest.mark.live_excel
def test_output_31_live_excel_baseline() -> None:
    if not excel_available():
        pytest.skip("live Excel not available")
    (_macro, _ext, ext_base, _pub), (suite, historical, _i6, _res) = _bundle()
    sut = output_31_table(
        ext_base, historical=historical, external_stress=suite
    )
    path = WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK
    probes = tuple(
        p
        for p in output_31_probes(path)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] in {"Baseline", "B1. Real GDP growth", "B2. Primary balance"}
    )
    excel = read_live_output(path, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))
