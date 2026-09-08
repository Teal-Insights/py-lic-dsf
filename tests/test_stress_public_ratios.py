"""Public GFN identity + public ratios + Output 3-2 parity."""

from __future__ import annotations

import pytest

from lic_dsf.stress import (
    ExternalScenarioRunner,
    PublicGFNIdentity,
    PublicScenarioRunner,
    ScenarioRegistry,
    StressContext,
)
from lic_dsf.stress.output_map import EXT_SCENARIO_LABELS, build_output32_table
from lic_dsf.stress.resfin import AbsoluteResidualPolicy, policy_from_spec
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.bsheet_public import PUBLIC_SHEETS, bsheet_public_probes
from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.catalogs.output_3 import output_32_probes

WORKBOOK = WORKBOOK_XLSX

_PUB_ROWS: tuple[tuple[int, str], ...] = (
    (41, "gdp_lcu"),
    (90, "public_gfn"),
    (13, "pv_public_to_gdp"),
    (95, "pv_public_to_revenue"),
    (93, "ds_to_revenue"),
)

# Scenarios with a dedicated ``*_pub`` B-sheet driven by the public runner.
_BSHEET_SCENARIOS = ("B1_GDP", "B2_PrimaryBalance", "B5_FX", "B6_Combo")
_OUTPUT32_STANDARD = (
    "A1_Historical",
    "B1_GDP",
    "B2_PrimaryBalance",
    "B3_Exports",
    "B4_OtherFlows",
    "B5_FX",
    "B6_Combo",
)
# Output 3-2 for these ids is baseline public + the external ResFin overlay
# (Excel R91/R92), so they run through the external runner.
_OUTPUT32_EXT_OVERLAY = frozenset({"B3_Exports", "B4_OtherFlows", "C4_Market"})


def _run_public(ctx: StressContext, scenario_id: str):
    return PublicScenarioRunner(context=ctx).run(
        ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
    )


def _run_for_output32(ctx: StressContext, scenario_id: str):
    if scenario_id in _OUTPUT32_EXT_OVERLAY:
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


@pytest.mark.parametrize("scenario_id", _BSHEET_SCENARIOS)
def test_public_bsheet_matches_excel(
    stress_context: StressContext, scenario_id: str
) -> None:
    """Public R41/R90/R13/R95/R93 match Excel at global tolerance."""
    result = _run_public(stress_context, scenario_id)
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
    year_set = {y for y in stress_context.macro.inputs.years if y >= first}
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


def test_output_32_standard_public(stress_context: StressContext) -> None:
    """Output 3-2 Baseline / A1 / B1–B6 match Excel at global tolerance."""
    results = {
        sid: _run_for_output32(stress_context, sid) for sid in _OUTPUT32_STANDARD
    }
    sut = build_output32_table(stress_context.pub_base, results)
    years = {int(y) for y in stress_context.macro.inputs.years}
    first = stress_context.macro.inputs.first_projection_year
    labels = {EXT_SCENARIO_LABELS[sid] for sid in _OUTPUT32_STANDARD} | {"Baseline"}
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


@pytest.mark.parametrize("scenario_id", sorted(_OUTPUT32_EXT_OVERLAY))
def test_output_32_external_resfin_overlay(
    stress_context: StressContext, scenario_id: str
) -> None:
    """B3/B4/C4 Output 3-2 = baseline public + external ResFin (Excel R91/R92)."""
    result = _run_for_output32(stress_context, scenario_id)
    assert result.resfin.external is not None
    sut = build_output32_table(stress_context.pub_base, {scenario_id: result})
    label = EXT_SCENARIO_LABELS[scenario_id]
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
    assert_all_passed(compare_probes(excel, sut))


def test_b2_uses_absolute_policy(stress_context: StressContext) -> None:
    spec = ScenarioRegistry.get("B2_PrimaryBalance")
    assert isinstance(policy_from_spec(spec), AbsoluteResidualPolicy)
    result = _run_public(stress_context, "B2_PrimaryBalance")
    assert result.public_ratios is not None
    assert result.resfin.fill is not None
    assert float(result.resfin.fill.external_mlt_usd.loc[2025]) >= 0.0


def test_bsheet_public_catalog_covers_metric_rows() -> None:
    probes = bsheet_public_probes(WORKBOOK, "B1_GDP")
    rows = {p.row for p in probes}
    assert {41, 90, 13, 95, 93} <= rows
