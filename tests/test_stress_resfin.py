"""Residual-financing engine: policies, overlays, public GFN loop."""

from __future__ import annotations

import pandas as pd
import pytest

from lic_dsf.load import load_input7_residual_params
from lic_dsf.stress import (
    AbsoluteResidualPolicy,
    CappedResidualPolicy,
    ResidualFinancingEngine,
    ScenarioRegistry,
    StressContext,
    StressScenarioRunner,
    split_residual_financing,
)
from lic_dsf.stress.resfin import policy_from_spec
from lic_dsf.stress.runner.public import PublicScenarioRunner
from lic_dsf.stress.spec import ResidualPolicyKind
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.catalogs.resfin import (
    PV_RESFIN_PUB_SHEET,
    PV_STRESS_B3_ROWS,
    PV_STRESS_SHEET,
    RESFIN_PUB_B1_ROWS,
    RESFIN_PUB_B6_ROWS,
)

WORKBOOK = WORKBOOK_XLSX


def _sheet_row(
    sheet: str, year_row: int, first_col: int, row: int, years: list[int]
) -> pd.Series:
    from fastpyxl import load_workbook

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        year_cols: dict[int, int] = {}
        col = first_col
        while True:
            value = ws.cell(year_row, col).value
            if not isinstance(value, (int, float)):
                break
            year_cols[int(value)] = col
            col += 1
        out: dict[int, float] = {}
        for year in years:
            cell_col = year_cols[year]
            raw = ws.cell(row, cell_col).value
            out[year] = float(raw) if isinstance(raw, (int, float)) else 0.0
        return pd.Series(out, dtype=float)
    finally:
        wb.close()


def test_capped_vs_absolute_policy_synthetic() -> None:
    years = (2025,)
    params = load_input7_residual_params(WORKBOOK)
    gap = pd.Series({2025: 1000.0})
    r86 = pd.Series({2025: 9999.0})
    fx = pd.Series({2025: 5.0})
    capped = CappedResidualPolicy().split(gap, r86, params, fx, years=years)
    absolute = AbsoluteResidualPolicy().split(gap, r86, params, fx, years=years)
    # Large R86 → capped modality 1: full gap / FX on external, no domestic.
    assert capped.external_mlt_usd.loc[2025] == pytest.approx(1000.0 / 5.0)
    assert capped.domestic_mlt_lcu.loc[2025] == pytest.approx(0.0)
    assert absolute.external_mlt_usd.loc[2025] == pytest.approx(
        1000.0 * params.external_mlt_share / 5.0
    )
    assert absolute.domestic_mlt_lcu.loc[2025] == pytest.approx(
        1000.0 * params.domestic_mlt_share
    )
    assert absolute.domestic_st_lcu.loc[2025] == pytest.approx(
        1000.0 * params.domestic_st_share
    )


def test_b2_spec_selects_absolute_policy() -> None:
    spec = ScenarioRegistry.get("B2_PrimaryBalance")
    assert spec.residual_policy is ResidualPolicyKind.ABSOLUTE
    assert isinstance(policy_from_spec(spec), AbsoluteResidualPolicy)


def test_b3_overlay_from_excel_gap_matches_pv_stress(
    stress_context: StressContext,
) -> None:
    """Given Excel R46 gap, engine PV/interest/amort match ``PV Stress`` B3.

    Horizon matches the short projection window used by Excel's CHOOSE-based
    ResFin schedule.
    """
    years = [2024, 2025, 2026, 2027, 2028]
    gap = _sheet_row(PV_STRESS_SHEET, 3, 4, 46, years)
    engine = ResidualFinancingEngine.for_external(
        stress_context.residual,
        tuple(years),
        external=stress_context.external,
    )
    overlay = engine.build_external_overlay(gap)
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=PV_STRESS_SHEET,
        year_row=3,
        first_col=4,
        scenario_id="B3_Exports",
        rows=PV_STRESS_B3_ROWS,
    )
    year_set = set(years)
    probes = tuple(
        p for p in probes if p.year is not None and int(p.year) in year_set
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    series_map = {
        46: gap,
        49: overlay.pv,
        52: overlay.interest,
        53: overlay.amortization,
    }
    sut = {
        ("B3_Exports", row, int(year)): float(series_map[row].loc[year])
        for row in series_map
        for year in years
    }
    assert_all_passed(compare_probes(excel, sut))


def test_b1_public_iterative_fill_matches_excel(
    stress_context: StressContext,
) -> None:
    result = StressScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B1_GDP")
    )
    assert result.resfin.public is not None
    assert result.resfin.converged
    pub = result.resfin.public
    fill_years = [2025, 2026]
    series_map = {
        67: result.resfin.public_gap,
        72: pub.fill.external_mlt_usd,
        75: pub.ext.pv,
        77: pub.ext.interest,
        78: pub.ext.amortization,
        85: pub.fill.domestic_mlt_lcu,
        90: pub.dom_mlt.interest,
        91: pub.dom_mlt.amortization,
        98: pub.fill.domestic_st_lcu,
        99: pub.dom_st.interest,
    }
    rows = tuple((r, lab) for r, lab in RESFIN_PUB_B1_ROWS if r in series_map)
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=PV_RESFIN_PUB_SHEET,
        year_row=2,
        first_col=4,
        scenario_id="B1_GDP",
        rows=rows,
    )
    year_set = set(fill_years)
    probes = tuple(
        p for p in probes if p.year is not None and int(p.year) in year_set
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        ("B1_GDP", row, int(year)): float(series.loc[year])
        for row, series in series_map.items()
        for year in fill_years
        if series is not None
    }
    assert_all_passed(compare_probes(excel, sut))


def test_b6_resfin_pub_split_parity_with_excel_gap() -> None:
    """B6 capped split uses Excel gap + external DSA R86 + baseline FX (R27)."""
    years = [2025, 2026, 2027, 2028]
    params = load_input7_residual_params(WORKBOOK)
    off = 141
    gap = _sheet_row(PV_RESFIN_PUB_SHEET, 2, 4, 67 + off, years)
    r86 = _sheet_row(PV_RESFIN_PUB_SHEET, 2, 4, 69 + off, years)
    fx = _sheet_row(PV_RESFIN_PUB_SHEET, 2, 4, 27, years)
    fill = split_residual_financing(
        gap, r86, params, fx, modality="capped", years=tuple(years)
    )
    expected_ext = _sheet_row(PV_RESFIN_PUB_SHEET, 2, 4, 72 + off, years)
    expected_dom = _sheet_row(PV_RESFIN_PUB_SHEET, 2, 4, 85 + off, years)
    expected_st = _sheet_row(PV_RESFIN_PUB_SHEET, 2, 4, 98 + off, years)
    for year in years:
        assert fill.external_mlt_usd.loc[year] == pytest.approx(
            float(expected_ext.loc[year]), rel=1e-6, abs=1e-4
        ), f"ext {year}"
        assert fill.domestic_mlt_lcu.loc[year] == pytest.approx(
            float(expected_dom.loc[year]), rel=1e-6, abs=1e-4
        ), f"dom {year}"
        assert fill.domestic_st_lcu.loc[year] == pytest.approx(
            float(expected_st.loc[year]), rel=1e-6, abs=1e-4
        ), f"st {year}"


def test_b6_public_iterative_fill_matches_excel_2025(
    stress_context: StressContext,
) -> None:
    """B6 ResFin wiring: converged 2025 three-way fill matches PV_ResFin_pub."""
    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B6_Combo")
    )
    assert result.resfin.public is not None
    assert result.resfin.converged
    pub = result.resfin.public
    fill_years = [2025]
    series_map = {
        208: result.resfin.public_gap,
        213: pub.fill.external_mlt_usd,
        226: pub.fill.domestic_mlt_lcu,
        239: pub.fill.domestic_st_lcu,
    }
    rows = tuple((r, lab) for r, lab in RESFIN_PUB_B6_ROWS if r in series_map)
    probes = probes_for_metric_rows(
        path=WORKBOOK,
        sheet=PV_RESFIN_PUB_SHEET,
        year_row=2,
        first_col=4,
        scenario_id="B6_Combo",
        rows=rows,
    )
    year_set = set(fill_years)
    probes = tuple(
        p for p in probes if p.year is not None and int(p.year) in year_set
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {
        ("B6_Combo", row, int(year)): float(series.loc[year])
        for row, series in series_map.items()
        for year in fill_years
        if series is not None
    }
    assert_all_passed(compare_probes(excel, sut))
