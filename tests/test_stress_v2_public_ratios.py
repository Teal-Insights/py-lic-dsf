"""Phase 6 public GFN identity + public ratios + Output 3-2 / Output 3-1 B2."""

from __future__ import annotations

import pytest

from lic_dsf.stress import run_b1_gdp_public, run_b2_pb_public
from lic_dsf.stress import (
    PublicGFNIdentity,
    PublicScenarioRunner,
    ScenarioRegistry,
    StressContext,
    StressPublicRatios,
)
from lic_dsf.stress.output_map import (
    EXT_SCENARIO_LABELS,
    build_output32_table,
    to_output31_rows,
)
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.bsheet_public import PUBLIC_SHEETS, bsheet_public_probes
from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes

WORKBOOK = WORKBOOK_XLSX

_PUB_ROWS: tuple[tuple[int, str], ...] = (
    (41, "gdp_lcu"),
    (90, "public_gfn"),
    (13, "pv_public_to_gdp"),
    (95, "pv_public_to_revenue"),
    (93, "ds_to_revenue"),
)

# Phase 12: pub B-sheets green through PR-5 (B2 market-access add.int).
_PHASE12_BSHEET = ("B1_GDP", "B2_PrimaryBalance", "B5_FX", "B6_Combo")
# Output 3-2 standard public (B3/B4 = external ResFin overlay; PR-4).
_PHASE12_OUTPUT32 = (
    "A1_Historical",
    "B1_GDP",
    "B2_PrimaryBalance",
    "B3_Exports",
    "B4_OtherFlows",
    "B5_FX",
    "B6_Combo",
)
_OUTPUT32_EXT_OVERLAY = frozenset({"B3_Exports", "B4_OtherFlows", "C4_Market"})
# B3/B4 are Excel-green for 2024–2034; C4 overlay still misses shortened ResFin PV.
_OUTPUT32_EXT_OVERLAY_EXCEL_GREEN = frozenset({"B3_Exports", "B4_OtherFlows"})


@pytest.fixture(scope="module")
def stress_context() -> StressContext:
    return StressContext.from_workbook(WORKBOOK)


def _run_public(ctx: StressContext, scenario_id: str):
    return PublicScenarioRunner(context=ctx).run(
        ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
    )


def _run_for_output32(ctx: StressContext, scenario_id: str):
    """B3/B4/C4 Output 3-2 needs external ResFin; other ids use the public runner."""
    if scenario_id in _OUTPUT32_EXT_OVERLAY:
        from lic_dsf.stress import ExternalScenarioRunner

        return ExternalScenarioRunner(context=ctx).run(
            ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
        )
    return _run_public(ctx, scenario_id)


def test_public_gfn_identity_gdp_and_gap(stress_context: StressContext) -> None:
    result = _run_public(stress_context, "B1_GDP")
    assert result.public_ratios is not None
    gfn = PublicGFNIdentity.from_path(
        result.path,
        inflation_elasticity=result.public_ratios.inflation_elasticity,
    )
    assert float(gfn.gdp_lcu().loc[2025]) == pytest.approx(
        float(result.public_ratios.gdp_lcu().loc[2025]), abs=1e-9
    )
    assert result.resfin.public_gap is not None
    assert float(result.resfin.public_gap.loc[2025]) > 0.0


def _assert_public_bsheet(ctx: StressContext, scenario_id: str) -> None:
    result = _run_public(ctx, scenario_id)
    assert result.public_ratios is not None
    ratios = result.public_ratios
    first = result.path.first_projection_year
    series_map = {
        41: ratios.gdp_lcu(),
        90: ratios.public_gfn(),
        13: ratios.pv_public_debt_to_gdp(),
        95: ratios.pv_public_debt_to_revenue_grants(),
        93: ratios.debt_service_to_revenue_grants(),
    }
    year_set = {y for y in ctx.macro.inputs.years if y >= first}
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=PUBLIC_SHEETS[scenario_id],
        year_row=7,
        first_col=3,
        scenario_id=scenario_id,
        rows=_PUB_ROWS,
    )
    probes = tuple(
        p for p in probes if p.year is not None and int(p.year) in year_set
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        (scenario_id, row, int(year)): float(series.loc[year])
        for row, series in series_map.items()
        for year in year_set
        if year in series.index
    }
    assert_all_passed(compare_probes(excel, sut))


@pytest.mark.parametrize("scenario_id", _PHASE12_BSHEET)
def test_public_bsheet_matches_excel(
    stress_context: StressContext, scenario_id: str
) -> None:
    """Public R41/R90/R13/R95/R93 vs Excel at global tol (Phase 10/12)."""
    _assert_public_bsheet(stress_context, scenario_id)


def test_b1_public_matches_legacy(stress_context: StressContext) -> None:
    result = _run_public(stress_context, "B1_GDP")
    legacy = run_b1_gdp_public(
        stress_context.macro,
        stress_context.external,
        stress_context.input6,
        stress_context.residual,
    )
    assert result.public_ratios is not None
    for year in (2025, 2026):
        assert float(result.public_ratios.public_gfn().loc[year]) == pytest.approx(
            float(legacy.public_gfn().loc[year]), abs=1e-9, rel=1e-12
        )
        assert float(result.public_ratios.pv_public_debt_to_gdp().loc[year]) == (
            pytest.approx(
                float(legacy.pv_public_debt_to_gdp().loc[year]), abs=1e-9, rel=1e-12
            )
        )


def test_output_32_standard_public(stress_context: StressContext) -> None:
    """Output 3-2: Excel Baseline / A1 / B1–B6 at global tol (PR-5)."""
    results = {
        sid: _run_for_output32(stress_context, sid) for sid in _PHASE12_OUTPUT32
    }
    sut = build_output32_table(stress_context.pub_base, results)
    years = set(int(y) for y in stress_context.macro.inputs.years)
    first = stress_context.macro.inputs.first_projection_year
    labels = {EXT_SCENARIO_LABELS[sid] for sid in _PHASE12_OUTPUT32} | {"Baseline"}
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] in labels
        and p.year is not None
        and int(p.year) in years
        and int(p.year) >= first
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


@pytest.mark.parametrize("scenario_id", sorted(_OUTPUT32_EXT_OVERLAY_EXCEL_GREEN))
def test_output_32_b3_b4_external_resfin_overlay(
    stress_context: StressContext, scenario_id: str
) -> None:
    """B3/B4 Output 3-2 = baseline public + external ResFin (Excel R91/R92)."""
    result = _run_for_output32(stress_context, scenario_id)
    assert result.resfin.external is not None
    sut = build_output32_table(stress_context.pub_base, {scenario_id: result})
    label = EXT_SCENARIO_LABELS[scenario_id]
    years = set(int(y) for y in stress_context.macro.inputs.years)
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and int(p.year) in years
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


def test_output_32_c4_market_overlay_2025(stress_context: StressContext) -> None:
    """C4 Output 3-2 @ 2025 = baseline public (Excel R77/R89 are 0)."""
    result = _run_for_output32(stress_context, "C4_Market")
    assert result.resfin.external is not None
    sut = build_output32_table(stress_context.pub_base, {"C4_Market": result})
    label = EXT_SCENARIO_LABELS["C4_Market"]
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year == 2025
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))


def test_output_31_b2_early_years(stress_context: StressContext) -> None:
    """Output 3-1 B2 PV catalog at 1e-6 (full years covered in coupling tests)."""
    result = _run_public(stress_context, "B2_PrimaryBalance")
    assert result.public_ratios is not None
    assert isinstance(result.public_ratios, StressPublicRatios)
    rows = to_output31_rows(
        result.public_ratios, scenario_id="B2_PrimaryBalance"
    )
    label = EXT_SCENARIO_LABELS["B2_PrimaryBalance"]
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.sut_key[0] == "PV of debt-to GDP ratio"
        and p.year in (2024, 2025, 2026)
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        key: series
        for key, series in rows.items()
        if key[0] == "PV of debt-to GDP ratio"
    }
    assert_all_passed(compare_probes(excel, sut))


def test_b2_uses_absolute_policy(stress_context: StressContext) -> None:
    spec = ScenarioRegistry.get("B2_PrimaryBalance")
    from lic_dsf.stress.resfin import AbsoluteResidualPolicy, policy_from_spec

    assert isinstance(policy_from_spec(spec), AbsoluteResidualPolicy)
    result = _run_public(stress_context, "B2_PrimaryBalance")
    assert result.public_ratios is not None
    # Absolute may differ from legacy capped; still produces a positive fill.
    assert result.resfin.fill is not None
    assert float(result.resfin.fill.external_mlt_usd.loc[2025]) >= 0.0


def test_b2_legacy_still_runs(stress_context: StressContext) -> None:
    legacy = run_b2_pb_public(
        stress_context.macro,
        stress_context.external,
        stress_context.input6,
        stress_context.residual,
        market_access=stress_context.market_access,
    )
    assert float(legacy.pv_ppg_external_to_gdp().loc[2025]) >= 0.0


def test_bsheet_public_catalog_covers_phase6_rows() -> None:
    probes = bsheet_public_probes(WORKBOOK, "B1_GDP")
    rows = {p.row for p in probes}
    assert {41, 90, 13, 95, 93} <= rows
