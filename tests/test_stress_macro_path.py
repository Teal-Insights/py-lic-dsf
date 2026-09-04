"""Macro-path parity: shocked GDP / growth vs external B-sheets."""

from __future__ import annotations

import pytest

from lic_dsf.stress import ScenarioRegistry, StressContext, StressScenarioRunner
from lic_dsf.stress.path import ShockedMacroPath, projection_shock_window
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.probes import Probe

WORKBOOK = WORKBOOK_XLSX

# External B-sheets with Nominal GDP (R46) and real growth (R50).
_MACRO_SHEETS: dict[str, str] = {
    "A1_Historical": "A1_historical_ext",
    "B1_GDP": "B1_GDP_ext",
    "B3_Exports": "B3_Exports_ext",
    "B4_OtherFlows": "B4_other flows_ext",
    "B5_FX": "B5_depreciation_ext",
    "B6_Combo": "B6_Combo_mkt_ext",
}

_MACRO_ROWS: tuple[tuple[int, str], ...] = (
    (46, "gdp_usd"),
    (50, "real_gdp_growth"),
)


def _macro_probes(scenario_id: str) -> tuple[Probe, ...]:
    return probes_for_metric_rows(
        path=WORKBOOK,
        sheet=_MACRO_SHEETS[scenario_id],
        year_row=8,
        first_col=3,
        scenario_id=scenario_id,
        rows=_MACRO_ROWS,
    )


def _macro_sut(path: ShockedMacroPath, scenario_id: str) -> dict:
    out: dict = {}
    gdp = path.gdp_usd()
    growth = path.gdp_growth_pct()
    for year in path.years:
        out[(scenario_id, 46, int(year))] = float(gdp.loc[year])
        out[(scenario_id, 50, int(year))] = float(growth.loc[year])
    return out


@pytest.mark.parametrize("scenario_id", tuple(_MACRO_SHEETS))
def test_shocked_macro_matches_bsheet(
    scenario_id: str, stress_context: StressContext
) -> None:
    spec = ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
    result = StressScenarioRunner(context=stress_context).run(spec)
    path = result.path
    assert isinstance(path, ShockedMacroPath)
    probes = _macro_probes(scenario_id)
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, _macro_sut(path, scenario_id)))


def test_shock_window_is_projection_years_2_and_3(stress_context: StressContext) -> None:
    years = stress_context.macro.inputs.years
    first = stress_context.macro.inputs.first_projection_year
    window = projection_shock_window(years, first)
    proj = [y for y in years if y >= first]
    assert window == (proj[1], proj[2])
    for scenario_id in ("B1_GDP", "B5_FX", "B6_Combo"):
        path = StressScenarioRunner(context=stress_context).run(
            ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
        ).path
        assert path.metadata.shock_window_years == window


def test_b5_metadata_carries_fx_depreciation(stress_context: StressContext) -> None:
    path = StressScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B5_FX")
    ).path
    assert path.metadata.fx_depreciation_pct == pytest.approx(
        stress_context.input6.fx_depreciation_pct
    )
    assert path.metadata.exports_shocked_in_levels is False


def test_b3_exports_shocked_in_levels(stress_context: StressContext) -> None:
    path = StressScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B3_Exports")
    ).path
    assert path.metadata.exports_shocked_in_levels is True
    # Absolute exports fall in the shock window vs baseline.
    y0, y1 = path.metadata.shock_window_years
    assert float(path.exports().loc[y0]) < float(path.baseline.exports().loc[y0])
    assert float(path.exports().loc[y1]) < float(path.baseline.exports().loc[y1])


def test_b2_macro_path_builds_without_bsheet_gdp(stress_context: StressContext) -> None:
    path = StressScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    ).path
    assert isinstance(path, ShockedMacroPath)
    # Primary expenditure rises under a PB deficit shock in the window.
    y0, _y1 = path.metadata.shock_window_years
    assert float(path.shocked.inputs.primary_expenditure.loc[y0]) > float(
        path.baseline.inputs.primary_expenditure.loc[y0]
    )


def test_shocked_macro_path_has_no_ratio_methods() -> None:
    banned = {
        "pv_ppg_external_to_gdp",
        "pv_public_debt_to_gdp",
        "residual_borrowing",
        "resfin",
    }
    for name in banned:
        assert not hasattr(ShockedMacroPath, name)
