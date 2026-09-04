"""External debt-dynamics parity: R86 gap + R19 exports/GDP."""

from __future__ import annotations

import pytest

from lic_dsf.stress import ScenarioRegistry, StressContext, StressScenarioRunner
from lic_dsf.stress.external_dynamics import ExternalDebtDynamics
from lic_dsf.stress.runner import ScenarioRunResult
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.layout import probes_for_metric_rows

WORKBOOK = WORKBOOK_XLSX

_EXCEL_GAP_SHEETS: dict[str, tuple[str, int]] = {
    "A1_Historical": ("A1_historical_ext", 86),
    "B1_GDP": ("B1_GDP_ext", 86),
    "B3_Exports": ("B3_Exports_ext", 86),
    "B4_OtherFlows": ("B4_other flows_ext", 86),
    "B5_FX": ("B5_depreciation_ext", 87),
    "B6_Combo": ("B6_Combo_mkt_ext", 86),
}

_EXPORTS_SHEETS: dict[str, str] = {
    "B1_GDP": "B1_GDP_ext",
    "B3_Exports": "B3_Exports_ext",
}


def _run(ctx: StressContext, scenario_id: str) -> ScenarioRunResult:
    return StressScenarioRunner(context=ctx).run(
        ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("scenario_id", tuple(_EXCEL_GAP_SHEETS))
def test_external_gap_matches_bsheet(
    scenario_id: str, stress_context: StressContext
) -> None:
    sheet, row = _EXCEL_GAP_SHEETS[scenario_id]
    result = _run(stress_context, scenario_id)
    assert isinstance(result, ScenarioRunResult)
    gap = result.external_gap.gap
    first = result.path.first_projection_year
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=sheet,
        year_row=8,
        first_col=3,
        scenario_id=scenario_id,
        rows=((row, "residual_gross_borrowing"),),
    )
    probes = tuple(p for p in probes if p.year is not None and p.year > first)
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        (scenario_id, row, int(year)): float(gap.loc[year])
        for year in gap.index
        if int(year) > first
    }
    assert_all_passed(compare_probes(excel, sut))


def test_b1_gap_is_near_zero(stress_context: StressContext) -> None:
    result = _run(stress_context, "B1_GDP")
    assert result.external_gap.iterations == 0
    assert float(result.external_gap.gap.fillna(0.0).abs().max()) < 1e-6


@pytest.mark.parametrize("scenario_id", ("B3_Exports", "B5_FX"))
def test_converged_loop_terminates(
    scenario_id: str, stress_context: StressContext
) -> None:
    result = _run(stress_context, scenario_id)
    assert 1 <= result.external_gap.iterations <= 25


@pytest.mark.parametrize("scenario_id", tuple(_EXPORTS_SHEETS))
def test_exports_to_gdp_matches_r19(
    scenario_id: str, stress_context: StressContext
) -> None:
    result = _run(stress_context, scenario_id)
    dynamics = ExternalDebtDynamics.from_context(
        stress_context,
        result.path,
        ScenarioRegistry.get(scenario_id),  # type: ignore[arg-type]
    )
    series = dynamics.exports_to_gdp()
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=_EXPORTS_SHEETS[scenario_id],
        year_row=8,
        first_col=3,
        scenario_id=scenario_id,
        rows=((19, "exports_to_gdp"),),
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        (scenario_id, 19, int(year)): float(series.loc[year]) for year in series.index
    }
    assert_all_passed(compare_probes(excel, sut))
