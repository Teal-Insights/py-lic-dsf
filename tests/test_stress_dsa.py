"""Tests for standard stress DSA (``lic_dsf.stress``)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.pv import (
    ExternalDebtBook,
    ExternalDebtInputs,
    MacroDebtBook,
    MacroDebtInputs,
    PresentValueInstrument,
    PVPortfolio,
    ResidualFinancingParams,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)
from lic_dsf.output import stress_external_panel
from lic_dsf.stress import (
    Input6StandardParams,
    StressExternalBook,
    apply_historical_averages_shock,
    apply_real_gdp_shock,
    load_input6_standard,
    real_depreciation_pct,
    resfin_instrument,
    resfin_overlay_series,
    run_a1_historical_external,
    run_b1_gdp_external,
    run_standard_external_stress,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

_CACHE: tuple[MacroDebtBook, ExternalDebtBook, Input6StandardParams] | None = None


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_macro_ext() -> tuple[MacroDebtBook, ExternalDebtBook]:
    years = (2023, 2024, 2025, 2026)
    z = _zero(years)
    instrument = PresentValueInstrument(
        name="NewLoan",
        grace=1,
        maturity=3,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[100.0, 0.0, 0.0, 0.0],
        years=years,
    )
    ext_inputs = ExternalDebtInputs(
        years=years,
        existing_debt_service=pd.DataFrame(
            {2023: [10.0], 2024: [10.0], 2025: [10.0], 2026: [10.0]},
            index=["IMF"],
        ),
        existing_principal=pd.Series({2023: 5.0, 2024: 5.0, 2025: 5.0, 2026: 5.0}),
        existing_discount_rates={"IMF": 0.05},
        arrears=z.copy(),
        short_term_external=pd.Series({2023: 50.0, 2024: 40.0, 2025: 0.0, 2026: 0.0}),
        sdr_pv=z.copy(),
        sdr_interest=z.copy(),
        macro_ppg_external=pd.Series(
            {2023: 1100.0, 2024: 1200.0, 2025: 1300.0, 2026: 1400.0}
        ),
        macro_mlt_external=pd.Series(
            {2023: 1050.0, 2024: 1160.0, 2025: 1300.0, 2026: 1400.0}
        ),
        fx_eop=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5, 2026: 2.5}),
        fx_pa=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5, 2026: 2.5}),
        locally_issued_debt_stock=pd.Series(
            {2023: 100.0, 2024: 80.0, 2025: 60.0, 2026: 40.0}
        ),
        locally_issued_principal=pd.Series(
            {2023: 5.0, 2024: 5.0, 2025: 5.0, 2026: 5.0}
        ),
        locally_issued_interest=pd.Series({2023: 2.0, 2024: 2.0, 2025: 2.0, 2026: 2.0}),
        locally_issued_st=z.copy(),
        locally_issued_st_principal=z.copy(),
        locally_issued_st_interest=z.copy(),
        domestic_mlt_disbursements_usd=z.copy(),
        domestic_st_disbursements_usd=z.copy(),
        short_term_interest_rate=0.10,
        residual_interest_rates={},
        grant_element_weight_names=frozenset(),
    )
    external = ExternalDebtBook(
        portfolio=PVPortfolio(instruments=(instrument,)), inputs=ext_inputs
    )
    # Constant real growth ~5% hist; strong 2025 baseline growth for shock contrast.
    gdp_c = pd.Series({2023: 1000.0, 2024: 1050.0, 2025: 1200.0, 2026: 1260.0})
    gdp_u = pd.Series({2023: 2000.0, 2024: 2200.0, 2025: 2600.0, 2026: 2800.0})
    macro_inputs = MacroDebtInputs(
        years=years,
        first_projection_year=2024,
        gdp_usd=gdp_u,
        gdp_constant=gdp_c,
        fx_eop=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5, 2026: 2.5}),
        fx_pa=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5, 2026: 2.5}),
        current_account=z.copy(),
        exports=pd.Series({2023: 400.0, 2024: 440.0, 2025: 480.0, 2026: 520.0}),
        imports=z.copy(),
        current_transfers_net=z.copy(),
        current_transfers_official=z.copy(),
        fdi=z.copy(),
        exceptional_financing=z.copy(),
        reserves_flow=z.copy(),
        revenues_incl_grants=pd.Series(
            {2023: 200.0, 2024: 220.0, 2025: 240.0, 2026: 260.0}
        ),
        grants=pd.Series({2023: 20.0, 2024: 22.0, 2025: 24.0, 2026: 26.0}),
        privatization=z.copy(),
        primary_expenditure=pd.Series(
            {2023: 150.0, 2024: 160.0, 2025: 170.0, 2026: 180.0}
        ),
        public_assets=z.copy(),
        contingent_liabilities=z.copy(),
        other_debt_creating_flows=z.copy(),
        debt_relief=z.copy(),
        mlt_external=pd.Series({2023: 500.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        short_term_external=pd.Series({2023: 50.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        private_mlt_external=z.copy(),
        private_st_external=pd.Series({2023: 10.0, 2024: 10.0, 2025: 10.0, 2026: 10.0}),
        domestic_mlt=pd.Series({2023: 200.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        domestic_st=pd.Series({2023: 20.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        ppg_interest=pd.Series({2023: 10.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        private_interest=z.copy(),
        domestic_interest=pd.Series({2023: 5.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        ppg_amortization=pd.Series({2023: 15.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        private_amortization=z.copy(),
        domestic_amortization=pd.Series({2023: 4.0, 2024: 0.0, 2025: 0.0, 2026: 0.0}),
        concessional_loans=z.copy(),
        domestic_mlt_input5=pd.Series(
            {2023: 0.0, 2024: 210.0, 2025: 220.0, 2026: 230.0}
        ),
        domestic_st_input5=pd.Series({2023: 0.0, 2024: 22.0, 2025: 24.0, 2026: 26.0}),
        domestic_interest_lcu_input5=pd.Series(
            {2023: 0.0, 2024: 12.5, 2025: 12.5, 2026: 12.5}
        ),
        domestic_principal_lcu_input5=pd.Series(
            {2023: 0.0, 2024: 30.0, 2025: 32.0, 2026: 34.0}
        ),
        public_gfn_input5=pd.Series({2023: 0.0, 2024: 80.0, 2025: 85.0, 2026: 90.0}),
    )
    macro = MacroDebtBook(inputs=macro_inputs, external=external)
    return macro, external


def _workbook_bundle() -> tuple[MacroDebtBook, ExternalDebtBook, Input6StandardParams]:
    global _CACHE
    if _CACHE is None:
        instruments = load_instruments_from_workbook(
            WORKBOOK, include_zero_disbursement=True
        )
        lc_nr = load_lc_nr_instruments_from_workbook(
            WORKBOOK, include_zero_disbursement=True
        )
        portfolio = PVPortfolio(instruments=tuple(instruments) + tuple(lc_nr))
        external = ExternalDebtBook(
            portfolio=portfolio, inputs=load_external_debt_inputs(WORKBOOK)
        )
        macro = MacroDebtBook(
            inputs=load_macro_debt_inputs(WORKBOOK), external=external
        )
        params = load_input6_standard(WORKBOOK)
        _CACHE = (macro, external, params)
    return _CACHE


def _sheet_cached(
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
        missing: list[int] = []
        for year in years:
            cell_col = year_cols.get(year)
            if cell_col is None:
                missing.append(year)
                continue
            value = ws.cell(row, cell_col).value
            if not isinstance(value, (int, float)):
                missing.append(year)
                continue
            out[year] = float(value)
        if missing:
            pytest.skip(f"{sheet} R{row} missing cached values for {missing}")
        return pd.Series(out, dtype=float)
    finally:
        wb.close()


def test_input6_synthetic_dataclass() -> None:
    params = Input6StandardParams(
        threshold_rule="whichever_lower",
        interactions_on=True,
        gdp_shock_sd=1.0,
        inflation_elasticity=0.6,
        primary_balance_shock_sd=1.0,
        domestic_borrowing_cost_bps=25.0,
        exports_shock_sd=1.0,
        exports_gdp_elasticity=0.8,
        transfers_shock_sd=1.0,
        fdi_shock_sd=1.0,
        fx_depreciation_pct=30.0,
        fx_passthrough=0.3,
        net_exports_elasticity=0.15,
        combo_gdp_shock_sd=0.5,
        combo_exports_shock_sd=0.5,
        combo_primary_balance_shock_sd=0.5,
        combo_transfers_shock_sd=0.5,
        combo_fdi_shock_sd=0.5,
        combo_fx_depreciation_pct=15.0,
    )
    assert params.gdp_shock_sd == 1.0
    assert params.interactions_on is True


def test_load_input6_standard_workbook() -> None:
    params = load_input6_standard(WORKBOOK)
    assert params.threshold_rule == "whichever_lower"
    assert params.interactions_on is True
    assert params.gdp_shock_sd == pytest.approx(1.0)
    assert params.inflation_elasticity == pytest.approx(0.6)
    assert params.exports_shock_sd == pytest.approx(1.0)
    assert params.exports_gdp_elasticity == pytest.approx(0.8)
    assert params.fx_depreciation_pct == pytest.approx(30.0)
    assert params.combo_gdp_shock_sd == pytest.approx(0.5)


def test_apply_real_gdp_shock_synthetic() -> None:
    macro, _ = _synthetic_macro_ext()
    params = Input6StandardParams(
        threshold_rule="whichever_lower",
        interactions_on=True,
        gdp_shock_sd=1.0,
        inflation_elasticity=0.6,
        primary_balance_shock_sd=1.0,
        domestic_borrowing_cost_bps=25.0,
        exports_shock_sd=1.0,
        exports_gdp_elasticity=0.8,
        transfers_shock_sd=1.0,
        fdi_shock_sd=1.0,
        fx_depreciation_pct=30.0,
        fx_passthrough=0.3,
        net_exports_elasticity=0.15,
        combo_gdp_shock_sd=0.5,
        combo_exports_shock_sd=0.5,
        combo_primary_balance_shock_sd=0.5,
        combo_transfers_shock_sd=0.5,
        combo_fdi_shock_sd=0.5,
        combo_fx_depreciation_pct=15.0,
    )
    shocked = apply_real_gdp_shock(macro.inputs, params)
    # Year-1 projection unchanged; years 2–3 shocked lower.
    assert shocked.gdp_constant.loc[2024] == pytest.approx(
        macro.inputs.gdp_constant.loc[2024]
    )
    assert shocked.gdp_constant.loc[2025] < macro.inputs.gdp_constant.loc[2025]
    assert shocked.gdp_usd.loc[2025] < macro.inputs.gdp_usd.loc[2025]
    # Absolute exports unchanged under B1.
    assert shocked.exports.loc[2025] == pytest.approx(macro.inputs.exports.loc[2025])


def test_b1_growth_gdp_parity() -> None:
    macro, _external, params = _workbook_bundle()
    shocked_inputs = apply_real_gdp_shock(macro.inputs, params)
    years = [2024, 2025, 2026, 2027]
    expected_gdp = _sheet_cached("B1_GDP_ext", 8, 3, 46, years)
    expected_growth = _sheet_cached("B1_GDP_ext", 8, 3, 50, years)
    # Reconstruct real growth from shocked constant GDP.
    const = shocked_inputs.gdp_constant
    for year in years:
        prior = const.loc[year - 1]
        got_g = (const.loc[year] / prior - 1.0) * 100.0
        assert got_g == pytest.approx(
            float(expected_growth.loc[year]), rel=1e-7, abs=1e-5
        ), f"growth {year}"
        assert shocked_inputs.gdp_usd.loc[year] == pytest.approx(
            float(expected_gdp.loc[year]), rel=1e-7, abs=1e-4
        ), f"gdp {year}"


def test_a1_growth_gdp_parity() -> None:
    macro, _external, _params = _workbook_bundle()
    shocked = apply_historical_averages_shock(macro.inputs)
    years = [2024, 2025, 2026, 2027]
    expected_gdp = _sheet_cached("A1_historical_ext", 8, 3, 46, years)
    expected_growth = _sheet_cached("A1_historical_ext", 8, 3, 50, years)
    const = shocked.gdp_constant
    for year in years:
        prior = const.loc[year - 1]
        got_g = (const.loc[year] / prior - 1.0) * 100.0
        assert got_g == pytest.approx(
            float(expected_growth.loc[year]), rel=1e-7, abs=1e-5
        ), f"growth {year}"
        assert shocked.gdp_usd.loc[year] == pytest.approx(
            float(expected_gdp.loc[year]), rel=1e-7, abs=1e-4
        ), f"gdp {year}"


def test_a1_pv_gdp_parity() -> None:
    years = [2024, 2025, 2026, 2027]
    macro, external, _params = _workbook_bundle()
    residual = external.residual_params()
    book = run_a1_historical_external(macro, external, residual)
    got = book.pv_ppg_external_to_gdp().reindex(years)
    expected = _sheet_cached("A1_historical_ext", 8, 3, 35, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-7, abs=1e-3
        ), f"A1 pv/gdp {year}"


def test_resfin_instrument_and_overlay() -> None:
    years = (2024, 2025, 2026)
    gap = pd.Series({2024: 0.0, 2025: 100.0, 2026: 50.0})
    params = ResidualFinancingParams(
        external_mlt_share=1.0,
        domestic_mlt_share=0.0,
        domestic_st_share=0.0,
        avg_interest_rate=8.0,
        avg_grace=2.0,
        avg_maturity=5.0,
        avg_grace_rounded=2,
        avg_maturity_rounded=5,
    )
    instrument = resfin_instrument(gap, params, discount_rate=0.05, years=years)
    assert instrument.grace == 2
    assert instrument.maturity == 5
    assert instrument.interest_rate == pytest.approx(0.08)
    assert list(instrument.disbursements) == pytest.approx([0.0, 100.0, 50.0])
    overlay = resfin_overlay_series(instrument, years)
    assert overlay.pv.loc[2025] > 0.0
    assert overlay.debt_service.loc[2025] >= 0.0


def test_stress_external_book_overlay_raises_pv_ratio() -> None:
    macro, external = _synthetic_macro_ext()
    years = macro.inputs.years
    z = _zero(years)
    overlay_pv = pd.Series({2023: 0.0, 2024: 0.0, 2025: 200.0, 2026: 180.0})
    book = StressExternalBook(
        macro=macro,
        external=external,
        resfin_pv=overlay_pv,
        resfin_interest=z,
        resfin_amortization=z,
        residual_borrowing=z,
        scenario_id="B1_GDP",
    )
    base_pv_gdp = (
        100.0
        * float(external.total_pv_of_debt().loc[2025])
        / float(macro.gdp_usd().loc[2025])
    )
    assert book.pv_ppg_external_to_gdp().loc[2025] == pytest.approx(
        base_pv_gdp + 100.0 * 200.0 / 2600.0
    )


def test_run_b1_and_panel_synthetic() -> None:
    macro, external = _synthetic_macro_ext()
    params = Input6StandardParams(
        threshold_rule="whichever_lower",
        interactions_on=True,
        gdp_shock_sd=1.0,
        inflation_elasticity=0.6,
        primary_balance_shock_sd=1.0,
        domestic_borrowing_cost_bps=25.0,
        exports_shock_sd=1.0,
        exports_gdp_elasticity=0.8,
        transfers_shock_sd=1.0,
        fdi_shock_sd=1.0,
        fx_depreciation_pct=30.0,
        fx_passthrough=0.3,
        net_exports_elasticity=0.15,
        combo_gdp_shock_sd=0.5,
        combo_exports_shock_sd=0.5,
        combo_primary_balance_shock_sd=0.5,
        combo_transfers_shock_sd=0.5,
        combo_fdi_shock_sd=0.5,
        combo_fx_depreciation_pct=15.0,
    )
    residual = ResidualFinancingParams(
        external_mlt_share=1.0,
        domestic_mlt_share=0.0,
        domestic_st_share=0.0,
        avg_interest_rate=8.0,
        avg_grace=2.0,
        avg_maturity=5.0,
        avg_grace_rounded=2,
        avg_maturity_rounded=5,
    )
    book = run_b1_gdp_external(macro, external, params, residual)
    assert isinstance(book, StressExternalBook)
    assert book.scenario_id == "B1_GDP"
    panel = stress_external_panel(book)
    assert "PV of PPG external debt / GDP" in panel.index
    assert book.macro.gdp_usd().loc[2025] < macro.gdp_usd().loc[2025]


@pytest.mark.parametrize(
    ("method", "row"),
    [
        ("pv_ppg_external_to_gdp", 35),
        ("pv_ppg_external_to_exports", 36),
        ("ppg_debt_service_to_exports", 39),
    ],
)
def test_b1_gdp_external_parity(method: str, row: int) -> None:
    years = [2024, 2025, 2026, 2027]
    macro, external, params = _workbook_bundle()
    residual = external.residual_params()
    book = run_b1_gdp_external(macro, external, params, residual)
    got = getattr(book, method)().reindex(years)
    expected = _sheet_cached("B1_GDP_ext", 8, 3, row, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-7, abs=1e-4
        ), f"{method} {year}"


def test_run_standard_external_stress_registry() -> None:
    macro, external, params = _workbook_bundle()
    residual = external.residual_params()
    results = run_standard_external_stress(macro, external, params, residual)
    assert set(results) >= {
        "B1_GDP",
        "B3_Exports",
        "B4_OtherFlows",
        "B5_FX",
        "B6_Combo",
    }
    assert results["B1_GDP"].scenario_id == "B1_GDP"
    # Export shock should cut exports in shock years.
    b3 = results["B3_Exports"]
    assert b3.macro.exports().loc[2025] < macro.exports().loc[2025]


@pytest.mark.parametrize(
    ("scenario_id", "sheet"),
    [
        ("B3_Exports", "B3_Exports_ext"),
        ("B4_OtherFlows", "B4_other flows_ext"),
        ("B5_FX", "B5_depreciation_ext"),
        ("B6_Combo", "B6_Combo_mkt_ext"),
    ],
)
@pytest.mark.parametrize(
    ("method", "row"),
    [
        ("pv_ppg_external_to_gdp", 35),
        ("pv_ppg_external_to_exports", 36),
        ("ppg_debt_service_to_exports", 39),
    ],
)
def test_standard_external_ratio_parity(
    scenario_id: str, sheet: str, method: str, row: int
) -> None:
    years = [2024, 2025, 2026, 2027, 2028]
    macro, external, params = _workbook_bundle()
    residual = external.residual_params()
    book = run_standard_external_stress(macro, external, params, residual)[scenario_id]
    got = getattr(book, method)().reindex(years)
    expected = _sheet_cached(sheet, 8, 3, row, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-7, abs=1e-4
        ), f"{scenario_id} {method} {year}"


def test_real_depreciation_pct_matches_b5_b6_e43() -> None:
    """B5/B6 E43: real dep uses foreign deflator growth, not the nominal shock."""
    foreign_g = 1.8475197751998351
    lcu_g = 9.635590457446707
    assert real_depreciation_pct(
        nominal_dep=30.0,
        foreign_deflator_growth=foreign_g,
        lcu_deflator_growth=lcu_g,
        passthrough=0.3,
    ) == pytest.approx(11.603756678103139, abs=1e-9)
    assert real_depreciation_pct(
        nominal_dep=15.0,
        foreign_deflator_growth=foreign_g,
        lcu_deflator_growth=lcu_g,
        passthrough=0.3,
        real_growth_gap=8.859360587787224 - 5.124091583320329,
        inflation_elasticity=0.6,
    ) == pytest.approx(4.674244044941062, abs=1e-9)


def test_b5_fx_gdp_and_baseline_year_parity() -> None:
    years = [2024, 2025]
    macro, external, params = _workbook_bundle()
    residual = external.residual_params()
    book = run_standard_external_stress(macro, external, params, residual)["B5_FX"]
    expected_gdp = _sheet_cached("B5_depreciation_ext", 8, 3, 46, years)
    for year in years:
        assert book.macro.gdp_usd().loc[year] == pytest.approx(
            float(expected_gdp.loc[year]), rel=1e-7, abs=1e-4
        ), f"B5 GDP {year}"
    # First projection year stays on baseline ratios (no residual overlay yet).
    expected_r35 = _sheet_cached("B5_depreciation_ext", 8, 3, 35, [2024])
    assert book.pv_ppg_external_to_gdp().loc[2024] == pytest.approx(
        float(expected_r35.loc[2024]), rel=1e-7, abs=1e-4
    )
    assert (
        book.pv_ppg_external_to_gdp().loc[2025]
        > book.pv_ppg_external_to_gdp().loc[2024]
    )
