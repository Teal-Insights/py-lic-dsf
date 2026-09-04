"""External ratios (B-sheet R35/36/39/40) + Output 3-1 parity."""

from __future__ import annotations

import pytest

from lic_dsf.stress import (
    ExternalScenarioRunner,
    ScenarioRegistry,
    StressContext,
    StressExternalRatios,
    StressSuite,
)
from lic_dsf.stress.output_map import build_output31_external_table
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.bsheet_external import (
    EXTERNAL_SHEETS,
    bsheet_external_probes,
)
from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.catalogs.output_3 import output_31_probes

WORKBOOK = WORKBOOK_XLSX

_RATIO_SCENARIOS = ("A1_Historical", "B1_GDP", "B3_Exports", "B5_FX", "B6_Combo")
_RATIO_ROWS: tuple[tuple[int, str], ...] = (
    (35, "pv_ppg_to_gdp"),
    (36, "pv_ppg_to_exports"),
    (39, "ppg_ds_to_exports"),
    (40, "ppg_ds_to_revenue"),
)

_OUTPUT31_EXCEL_LABELS = frozenset(
    {
        "Baseline",
        "A1 historical",
        "B1. Real GDP growth",
        "B3. Exports",
        "B4. Other flows",
        "B5. Depreciation",
        "B6. Combination of B1-B5",
    }
)


def _run(ctx: StressContext, scenario_id: str):
    return ExternalScenarioRunner(context=ctx).run(
        ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("scenario_id", _RATIO_SCENARIOS)
def test_external_ratios_match_bsheet(
    scenario_id: str, stress_context: StressContext
) -> None:
    result = _run(stress_context, scenario_id)
    assert result.external_ratios is not None
    assert isinstance(result.external_ratios, StressExternalRatios)
    ratios = result.external_ratios
    first = result.path.first_projection_year
    series_map = {
        35: ratios.pv_ppg_external_to_gdp(),
        36: ratios.pv_ppg_external_to_exports(),
        39: ratios.ppg_debt_service_to_exports(),
        40: ratios.ppg_debt_service_to_revenue(),
    }

    sheet = EXTERNAL_SHEETS[scenario_id]
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=sheet,
        year_row=8,
        first_col=3,
        scenario_id=scenario_id,
        rows=_RATIO_ROWS,
    )
    probes = tuple(p for p in probes if p.year is not None and p.year > first)
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        (scenario_id, row, int(year)): float(series.loc[year])
        for row, series in series_map.items()
        for year in series.index
        if int(year) > first
    }
    assert_all_passed(compare_probes(excel, sut))


def test_suite_skips_b2(stress_context: StressContext) -> None:
    results = StressSuite(context=stress_context).run_external_standard()
    assert "B2_PrimaryBalance" not in results
    assert "B1_GDP" in results
    assert "A1_Historical" in results
    assert results["B1_GDP"].external_ratios is not None


def test_output_31_external_scenarios(stress_context: StressContext) -> None:
    """Output 3-1 matches Excel for Baseline/A1/B1/B3/B4/B5/B6."""
    runner = ExternalScenarioRunner(context=stress_context)
    results = {
        sid: runner.run(ScenarioRegistry.get(sid))  # type: ignore[arg-type]
        for sid in (
            "A1_Historical",
            "B1_GDP",
            "B3_Exports",
            "B4_OtherFlows",
            "B5_FX",
            "B6_Combo",
        )
    }
    sut = build_output31_external_table(stress_context.ext_base, results)
    years = {int(y) for y in stress_context.macro.inputs.years}
    first = stress_context.macro.inputs.first_projection_year

    excel_probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] in _OUTPUT31_EXCEL_LABELS
        and p.year is not None
        and int(p.year) in years
        and int(p.year) >= first
    )
    excel = read_cached_output(WORKBOOK, excel_probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, sut))

    # B6 must carry Python-computed combo add.int.
    assert results["B6_Combo"].external_ratios is not None
    add_int = results["B6_Combo"].external_ratios.additional_borrowing_interest
    assert add_int is not None
    assert float(add_int.loc[2026]) > 0.0


def test_bsheet_catalog_covers_ratio_scenarios() -> None:
    for scenario_id in _RATIO_SCENARIOS:
        probes = bsheet_external_probes(WORKBOOK, scenario_id)
        rows = {p.row for p in probes}
        assert {35, 36, 39, 40} <= rows
        if scenario_id == "B5_FX":
            assert 87 in rows
        else:
            assert 86 in rows
