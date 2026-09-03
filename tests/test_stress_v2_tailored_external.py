"""Phase 11 tailored external Output 3-1 parity (C1 / C3 / C4)."""

from __future__ import annotations

import pytest

from lic_dsf.stress import ExternalScenarioRunner, ScenarioRegistry, StressContext
from lic_dsf.stress.output_map import build_output31_external_table
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes

WORKBOOK = WORKBOOK_XLSX

_TAILORED = (
    ("C1_CombinedCL", "C1. Combined contingent liabilities"),
    ("C3_Commodity", "C3. Commodity price"),
    ("C4_Market", "C4. Market Financing"),
)

# Excel-green subset for Phase 11 (2024 anchor + early projection years).
_PHASE11_YEARS = range(2024, 2029)


@pytest.fixture(scope="module")
def stress_context() -> StressContext:
    return StressContext.from_workbook(WORKBOOK)


@pytest.fixture(scope="module")
def output31_tailored(stress_context: StressContext):
    runner = ExternalScenarioRunner(context=stress_context)
    results = {
        sid: runner.run(ScenarioRegistry.get(sid))  # type: ignore[arg-type]
        for sid, _ in _TAILORED
    }
    public = {}
    c1 = results.get("C1_CombinedCL")
    if c1 is not None and c1.public_ratios is not None:
        public["C1_CombinedCL"] = c1
        results = {k: v for k, v in results.items() if k != "C1_CombinedCL"}
    return build_output31_external_table(
        stress_context.ext_base, results, public_results=public
    )


@pytest.mark.parametrize(("scenario_id", "label"), _TAILORED)
def test_tailored_output31_2024_matches_excel(
    scenario_id: str,
    label: str,
    stress_context: StressContext,
    output31_tailored,
) -> None:
    """2024 tailored rows match baseline external (Excel anchor)."""
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year == 2024
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output31_tailored, probes=probes))


def test_c3_commodity_pv_to_exports_2025(stress_context: StressContext) -> None:
    """C3 R36 @ 2025 — adj_share² export scale + GDP ε (Phase 11)."""
    result = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C3_Commodity")  # type: ignore[arg-type]
    )
    ratios = result.external_ratios
    assert ratios is not None
    year = 2025
    excel = read_cached_output(
        WORKBOOK,
        tuple(
            p
            for p in output_31_probes(WORKBOOK)
            if p.sut_key
            == ("PV of debt-to-exports ratio", "C3. Commodity price")
            and p.year == year
        ),
    )
    excel_val = float(excel["excel_value"].iloc[0])
    assert float(ratios.pv_ppg_external_to_exports().loc[year]) == pytest.approx(
        excel_val, abs=1e-6
    )


def test_c3_output31_excel_green(output31_tailored) -> None:
    """C3 Output 3-1 @ 1e-6 for 2024–2034 (post-shock R18 % + export-tail growth)."""
    label = "C3. Commodity price"
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output31_tailored, probes=probes))


def test_c1_cl_shock_pct_from_input2(stress_context: StressContext) -> None:
    """C1 uses Input 2 Debt Coverage F25 total (Excel AA60), not a flat 10%."""
    assert stress_context.tailored is not None
    assert float(stress_context.tailored.cl_shock_pct_gdp) == pytest.approx(
        9.375480101740473, abs=1e-9
    )


def test_c1_output32_excel_green(stress_context: StressContext) -> None:
    """C1 Output 3-2 matches Excel at global tol (Input 2 CL%)."""
    result = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C1_CombinedCL")  # type: ignore[arg-type]
    )
    assert result.public_ratios is not None
    from lic_dsf.stress.output_map import build_output32_table
    from tests.parity.catalogs.output_3 import output_32_probes

    sut = build_output32_table(
        stress_context.pub_base, {"C1_CombinedCL": result}
    )
    label = "C1. Combined contingent liabilities"
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut, probes=probes))


def test_c3_output32_excel_green(stress_context: StressContext) -> None:
    """C3 Output 3-2 matches Excel @ 1e-6 for 2024–2026 (pub R41/R88/R13)."""
    from lic_dsf.stress.output_map import build_output32_table
    from lic_dsf.stress.runner.public import PublicScenarioRunner

    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C3_Commodity")  # type: ignore[arg-type]
    )
    assert result.public_ratios is not None
    assert result.path.metadata.lcu_deflator_growth is not None
    assert result.path.metadata.primary_exp_gdp_denominator is not None
    sut = build_output32_table(
        stress_context.pub_base, {"C3_Commodity": result}
    )
    label = "C3. Commodity price"
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2026
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut, probes=probes))


def test_c3_output32_later_years_residual(stress_context: StressContext) -> None:
    """C3 Output 3-2 2027+ within sub-ppt residual (ResFin ST timing)."""
    from lic_dsf.stress.output_map import build_output32_table
    from lic_dsf.stress.runner.public import PublicScenarioRunner

    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C3_Commodity")  # type: ignore[arg-type]
    )
    sut = build_output32_table(
        stress_context.pub_base, {"C3_Commodity": result}
    )
    label = "C3. Commodity price"
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2027 <= int(p.year) <= 2034
        and p.sut_key[0] == "PV of Debt-to-GDP Ratio"
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, sut, probes=probes)
    assert float(report["abs_diff"].max()) < 0.05


def test_c1_cl_external_resfin_2025(stress_context: StressContext) -> None:
    """C1 one-off CL → public ResFin forex path @ 2025 (Phase 13)."""
    result = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C1_CombinedCL")  # type: ignore[arg-type]
    )
    year = 2025
    assert result.public_ratios is not None
    assert result.resfin.public is not None
    # Public three-way fill drives ongoing ext MLT (not one-shot external gap).
    assert float(result.resfin.public.ext.pv.loc[year]) > 0.0
    excel = read_cached_output(
        WORKBOOK,
        tuple(
            p
            for p in output_31_probes(WORKBOOK)
            if p.sut_key
            == ("PV of debt-to GDP ratio", "C1. Combined contingent liabilities")
            and p.year == year
        ),
    )
    excel_val = float(excel["excel_value"].iloc[0])
    assert float(result.public_ratios.pv_ppg_external_to_gdp().loc[year]) == (
        pytest.approx(excel_val, abs=1e-6)
    )
    excel_2028 = read_cached_output(
        WORKBOOK,
        tuple(
            p
            for p in output_31_probes(WORKBOOK)
            if p.sut_key
            == ("PV of debt-to GDP ratio", "C1. Combined contingent liabilities")
            and p.year == 2028
        ),
    )
    excel_2028_val = float(excel_2028["excel_value"].iloc[0])
    assert float(result.public_ratios.pv_ppg_external_to_gdp().loc[2028]) == (
        pytest.approx(excel_2028_val, abs=1e-6)
    )


def test_c3_output32_excel_green_early(stress_context: StressContext) -> None:
    """C3 Output 3-2 @ 2024–2026: AA69 deflator + R20/R18 pub path @ 1e-6."""
    from lic_dsf.stress.output_map import build_output32_table
    from lic_dsf.stress.runner.public import PublicScenarioRunner

    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C3_Commodity")  # type: ignore[arg-type]
    )
    assert result.public_ratios is not None
    assert result.path.metadata.lcu_deflator_growth is not None
    assert result.path.metadata.primary_exp_gdp_denominator is not None
    sut = build_output32_table(
        stress_context.pub_base, {"C3_Commodity": result}
    )
    label = "C3. Commodity price"
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2026
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut, probes=probes))


def test_c3_output32_later_years_bounded(stress_context: StressContext) -> None:
    """C3 Output 3-2 2027–2034: ResFin ST modality residual ≪1 ppt."""
    from lic_dsf.stress.output_map import build_output32_table
    from lic_dsf.stress.runner.public import PublicScenarioRunner

    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C3_Commodity")  # type: ignore[arg-type]
    )
    sut = build_output32_table(
        stress_context.pub_base, {"C3_Commodity": result}
    )
    label = "C3. Commodity price"
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2027 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, sut, probes=probes)
    assert float(report["abs_diff"].max()) < 0.05


@pytest.mark.parametrize(("scenario_id", "label"), _TAILORED)
def test_tailored_output31_early_horizon_improved(
    scenario_id: str,
    label: str,
    output31_tailored,
) -> None:
    """Tailored 2024–2028 max drift ≪ Phase 11 baseline (Phase 13 Track A)."""
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year in _PHASE11_YEARS
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, output31_tailored, probes=probes)
    # C3 O31 hard-green via test_c3_output31_excel_green; C1 closed; C4 early ≪1 ppt.
    limit = 1.0
    assert float(report["abs_diff"].max()) < limit


def test_c4_output31_2025_pv_and_ds_match_excel(
    stress_context: StressContext,
) -> None:
    """C4 Output 3-1 @ 2025: PV/GDP, DS/X, DS/rev (Excel R82/R96/R99)."""
    result = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C4_Market")  # type: ignore[arg-type]
    )
    assert result.external_ratios is not None
    assert result.path.metadata.ds_revenue_uses_baseline is True
    assert float(result.external_gap.gap.loc[2025]) == pytest.approx(0.0, abs=1e-9)
    year = 2025
    checks = (
        ("PV of debt-to GDP ratio", result.external_ratios.pv_ppg_external_to_gdp()),
        (
            "Debt service-to-exports ratio",
            result.external_ratios.ppg_debt_service_to_exports(),
        ),
        (
            "Debt service-to-revenue ratio",
            result.external_ratios.ppg_debt_service_to_revenue(),
        ),
    )
    for indicator, series in checks:
        excel = read_cached_output(
            WORKBOOK,
            tuple(
                p
                for p in output_31_probes(WORKBOOK)
                if p.sut_key == (indicator, "C4. Market Financing")
                and p.year == year
            ),
        )
        excel_val = float(excel["excel_value"].iloc[0])
        assert float(series.loc[year]) == pytest.approx(excel_val, abs=1e-6)


def test_c4_output31_excel_green(output31_tailored) -> None:
    """C4 Output 3-1 @ 1e-6 for 2024–2034 (PV Stress stock = residual PV)."""
    label = "C4. Market Financing"
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output31_tailored, probes=probes))


def test_c4_output32_excel_green(stress_context: StressContext) -> None:
    """C4 Output 3-2 overlay @ 1e-6 for 2024–2034."""
    from lic_dsf.stress.output_map import build_output32_table

    result = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("C4_Market")  # type: ignore[arg-type]
    )
    sut = build_output32_table(
        stress_context.pub_base, {"C4_Market": result}
    )
    label = "C4. Market Financing"
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut, probes=probes))

