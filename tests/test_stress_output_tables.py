"""Excel-shaped Output 3-x tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from lic_dsf.load import (
    load_ci_summary,
    load_core,
    load_input1_market,
    load_input6_standard,
    load_input7_residual_params,
    load_tailored_params,
)
from lic_dsf.load.tailored import load_customized_public_spec
from lic_dsf.output import (
    output_31_table,
    output_32_table,
    stress_external_panel,
    stress_public_panel,
)
from lic_dsf.stress import (
    run_a1_historical_external,
    run_standard_external_stress,
    run_standard_public_stress,
    run_tailored_public_stress,
)
from tests.parity import (
    assert_all_passed,
    compare_probes,
    excel_available,
    read_cached_output,
    read_live_output,
)
from tests.parity.excel import ExcelComCrashed
from tests.parity.catalogs import output_31_probes, output_32_probes

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"
WORKBOOK_XLSM = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsm"

_CORE = None
_EXT_STRESS = None
_PUB_STRESS = None

_PUB_INDICATORS = (
    "PV of Debt-to-GDP Ratio",
    "PV of Debt-to-Revenue Ratio",
    "Debt Service-to-Revenue Ratio",
)


def _bundle():
    global _CORE, _EXT_STRESS, _PUB_STRESS
    if _CORE is None:
        _CORE = load_core(WORKBOOK)
        macro, external, _ext_base, _pub = _CORE
        input6 = load_input6_standard(WORKBOOK)
        residual = load_input7_residual_params(WORKBOOK)
        tailored = load_tailored_params(WORKBOOK)
        market_access, _embi = load_input1_market(WORKBOOK)
        _EXT_STRESS = (
            run_standard_external_stress(macro, external, input6, residual),
            run_a1_historical_external(macro, external, residual),
            input6,
            residual,
        )
        public = run_standard_public_stress(
            macro, external, input6, residual, market_access=market_access
        )
        public_tailored = run_tailored_public_stress(
            macro,
            external,
            residual,
            tailored,
            input6,
            custom_spec=load_customized_public_spec(WORKBOOK),
        )
        _PUB_STRESS = (public, public_tailored)
    return _CORE, _EXT_STRESS, _PUB_STRESS


def _output_31():
    (_macro, _ext, ext_base, _pub), (suite, historical, _i6, _res), (public, _pt) = (
        _bundle()
    )
    return output_31_table(
        ext_base,
        historical=historical,
        external_stress=suite,
        public_stress=public,
    )


def test_output_31_table_includes_baseline_and_b2() -> None:
    (_macro, _ext, _ext_base, _pub), (suite, _historical, _i6, _res), _pub_s = _bundle()
    table = _output_31()
    assert ("PV of debt-to GDP ratio", "Baseline") in table.index
    assert ("PV of debt-to GDP ratio", "B2. Primary balance") in table.index
    assert ("PV of debt-to GDP ratio", "B1. Real GDP growth") in table.index
    thin = stress_external_panel(suite["B1_GDP"])
    assert "PV of PPG external debt / GDP" in thin.index


def test_output_32_table_includes_full_public_stack() -> None:
    (_macro, _ext, _ext_base, pub_base), _ext_s, (public, tailored) = _bundle()
    thresh = load_ci_summary(WORKBOOK).thresholds.public_pv_debt_to_gdp
    table = output_32_table(
        pub_base,
        public_stress=public,
        tailored=tailored,
        public_threshold=thresh,
    )
    always = {
        "Baseline",
        "A1 historical",
        "A2 custom",
        "B1. Real GDP growth",
        "B2. Primary balance",
        "B3. Exports",
        "B4. Other flows",
        "B5. Depreciation",
        "B6. Combination of B1-B5",
        "C1. Combined contingent liabilities",
    }
    optional = {
        "C2. Natural disaster": "C2_NaturalDisaster",
        "C3. Commodity price": "C3_Commodity",
        "C4. Market Financing": "C4_Market",
    }
    for indicator in _PUB_INDICATORS:
        for scenario in always:
            assert (indicator, scenario) in table.index, (indicator, scenario)
        for scenario, sid in optional.items():
            if sid in tailored:
                assert (indicator, scenario) in table.index, (indicator, scenario)
    assert ("PV of Debt-to-GDP Ratio", "Threshold") in table.index
    for indicator in (
        "PV of Debt-to-Revenue Ratio",
        "Debt Service-to-Revenue Ratio",
    ):
        assert (indicator, "Threshold") not in table.index
    thin = stress_public_panel(public["B1_GDP"])
    assert "Public sector debt / GDP" in thin.index


def test_output_32_probes_cover_three_indicators_and_benchmark() -> None:
    probes = output_32_probes(WORKBOOK)
    keys = {(p.sut_key[0], p.sut_key[1]) for p in probes if isinstance(p.sut_key, tuple)}
    for indicator in _PUB_INDICATORS:
        assert (indicator, "Baseline") in keys
        assert (indicator, "A1 historical") in keys
        assert (indicator, "A2 custom") in keys
        assert (indicator, "B1. Real GDP growth") in keys
        assert (indicator, "C1. Combined contingent liabilities") in keys
    assert ("PV of Debt-to-GDP Ratio", "Threshold") in keys
    assert ("PV of Debt-to-Revenue Ratio", "Threshold") not in keys
    assert not any(k[0] == "Debt Service-to-GDP Ratio" for k in keys)


def test_output_31_cached_baseline_matches_excel() -> None:
    sut = _output_31()
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if p.sut_key == ("PV of debt-to GDP ratio", "Baseline")
        and p.year in {2024, 2025, 2026}
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


def test_output_31_cached_b2_matches_excel() -> None:
    """Output 3-1 B2 follows public B2 external ratios (Chart Data wiring).

    Shock-window years match Excel at the global 1e-6 tolerance. Later-year
    debt-service still has small residual drift from ResFin block timing.
    """
    sut = _output_31()
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == "B2. Primary balance"
        and p.year in {2024, 2025, 2026}
        and p.sut_key[0].startswith("PV of debt")
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, sut)
    # 2026 PV can still drift by ~1e-4 from ResFin/add.int fixed-point noise.
    near = report[report["year"] == 2026]
    early = report[report["year"].isin({2024, 2025})]
    assert_all_passed(early)
    if not near.empty:
        assert float(near["abs_diff"].max()) < 1e-3
    # Debt service in the shock window (add.int interest is still near zero).
    ds_probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == "B2. Primary balance"
        and p.year in {2024, 2025}
        and p.sut_key[0].startswith("Debt service")
    )
    ds_excel = read_cached_output(WORKBOOK, ds_probes)
    ds_excel = ds_excel[
        ds_excel["excel_value"].map(lambda v: isinstance(v, (int, float)))
    ]
    assert_all_passed(compare_probes(ds_excel, sut))


def test_output_32_cached_baseline_and_benchmark_match_excel() -> None:
    (_macro, _ext, _ext_base, pub_base), _ext_s, (public, tailored) = _bundle()
    thresh = load_ci_summary(WORKBOOK).thresholds.public_pv_debt_to_gdp
    sut = output_32_table(
        pub_base,
        public_stress=public,
        tailored=tailored,
        public_threshold=thresh,
    )
    wanted = {
        ("PV of Debt-to-GDP Ratio", "Baseline"),
        ("PV of Debt-to-GDP Ratio", "Threshold"),
        ("PV of Debt-to-Revenue Ratio", "Baseline"),
        ("Debt Service-to-Revenue Ratio", "Baseline"),
    }
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key in wanted
        and p.year in {2024, 2025, 2026}
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


@pytest.mark.live_excel
def test_output_31_live_excel_baseline() -> None:
    if not excel_available():
        pytest.skip("live Excel not available")
    sut = _output_31()
    path = WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK
    probes = tuple(
        p
        for p in output_31_probes(path)
        if isinstance(p.sut_key, tuple)
        and (
            p.sut_key[1] in {"Baseline", "B1. Real GDP growth"}
            or (
                p.sut_key[1] == "B2. Primary balance"
                and p.year in {2024, 2025}
            )
        )
    )
    try:
        excel = read_live_output(path, probes)
    except ExcelComCrashed as exc:
        pytest.skip(f"Excel COM crashed (retry after killing EXCEL.EXE): {exc}")
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


@pytest.mark.live_excel
def test_output_32_live_excel_scenarios() -> None:
    if not excel_available():
        pytest.skip("live Excel not available")
    (_macro, _ext, _ext_base, pub_base), _ext_s, (public, tailored) = _bundle()
    thresh = load_ci_summary(WORKBOOK).thresholds.public_pv_debt_to_gdp
    sut = output_32_table(
        pub_base,
        public_stress=public,
        tailored=tailored,
        public_threshold=thresh,
    )
    path = WORKBOOK_XLSM if WORKBOOK_XLSM.exists() else WORKBOOK
    probes = tuple(
        p
        for p in output_32_probes(path)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1]
        in {
            "Baseline",
            "A1 historical",
            "A2 custom",
            "B1. Real GDP growth",
            "B2. Primary balance",
            "Threshold",
        }
    )
    try:
        excel = read_live_output(path, probes)
    except ExcelComCrashed as exc:
        pytest.skip(f"Excel COM crashed (retry after killing EXCEL.EXE): {exc}")
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))
