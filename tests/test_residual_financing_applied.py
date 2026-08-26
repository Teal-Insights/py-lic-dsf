"""Tests for applied residual financing (gap → ST / ext MLT / dom MLT)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.load import (
    load_external_debt_inputs,
    load_input6_standard,
    load_input7_residual_params,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)
from lic_dsf.output import stress_public_panel
from lic_dsf.pv import ExternalDebtBook, MacroDebtBook, PVPortfolio
from lic_dsf.stress import (
    build_public_resfin_overlay,
    dom_mlt_resfin_series,
    dom_st_resfin_series,
    external_residual_gap,
    public_residual_gap,
    run_b1_gdp_public,
    run_b3_exports_external,
    run_b5_fx_external,
    split_residual_financing,
    stressed_external_stock_from_shortfall,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

_CACHE: tuple[MacroDebtBook, ExternalDebtBook] | None = None


def _workbook_books() -> tuple[MacroDebtBook, ExternalDebtBook]:
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
        _CACHE = (macro, external)
    return _CACHE


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


def test_public_and_external_residual_gap_helpers() -> None:
    years = (2024, 2025, 2026)
    base_gfn = pd.Series({2024: 100.0, 2025: 110.0, 2026: 120.0})
    stress_gfn = pd.Series({2024: 100.0, 2025: 150.0, 2026: 180.0})
    gap = public_residual_gap(stress_gfn, base_gfn, years)
    assert gap.loc[2025] == pytest.approx(40.0)
    assert gap.loc[2026] == pytest.approx(60.0)

    base_stock = pd.Series({2024: 1000.0, 2025: 1100.0, 2026: 1200.0})
    stress_stock = pd.Series({2024: 1000.0, 2025: 1300.0, 2026: 1600.0})
    ext_gap = external_residual_gap(base_stock, stress_stock, years)
    assert ext_gap.loc[2025] == pytest.approx(200.0)
    assert ext_gap.loc[2026] == pytest.approx(200.0)


def test_stressed_stock_from_shortfall_identity() -> None:
    years = (2024, 2025, 2026)
    base = pd.Series({2024: 100.0, 2025: 110.0, 2026: 120.0})
    shortfall = pd.Series({2024: 0.0, 2025: 50.0, 2026: 30.0})
    stressed = stressed_external_stock_from_shortfall(base, shortfall, years)
    gap = external_residual_gap(base, stressed, years)
    assert gap.loc[2025] == pytest.approx(50.0)
    assert gap.loc[2026] == pytest.approx(30.0)


def test_split_residual_financing_capped_modality_synthetic() -> None:
    years = (2024, 2025)
    params = load_input7_residual_params(WORKBOOK)
    gap = pd.Series({2024: 0.0, 2025: 3430.0732593620123})
    r86 = pd.Series({2024: 0.0, 2025: 0.0})
    fx = pd.Series({2024: 4.45, 2025: 4.9069027418011})
    fill = split_residual_financing(
        gap, r86, params, fx, modality="capped", years=years
    )
    assert fill.external_mlt_usd.loc[2025] == pytest.approx(303.6535436541075, rel=1e-6)
    assert fill.domestic_mlt_lcu.loc[2025] == pytest.approx(780.5664859321987, rel=1e-6)
    assert fill.domestic_st_lcu.loc[2025] == pytest.approx(1159.5083675158533, rel=1e-6)


def test_split_absolute_modality() -> None:
    years = (2025,)
    params = load_input7_residual_params(WORKBOOK)
    gap = pd.Series({2025: 1000.0})
    r86 = pd.Series({2025: 9999.0})
    fx = pd.Series({2025: 5.0})
    fill = split_residual_financing(
        gap, r86, params, fx, modality="absolute", years=years
    )
    assert fill.external_mlt_usd.loc[2025] == pytest.approx(
        1000.0 * params.external_mlt_share / 5.0
    )
    assert fill.domestic_mlt_lcu.loc[2025] == pytest.approx(
        1000.0 * params.domestic_mlt_share
    )
    assert fill.domestic_st_lcu.loc[2025] == pytest.approx(
        1000.0 * params.domestic_st_share
    )


def test_dom_mlt_and_st_series_synthetic() -> None:
    years = (2024, 2025, 2026)
    disb = pd.Series({2024: 0.0, 2025: 100.0, 2026: 50.0})
    deflator = pd.Series({2024: 0.0, 2025: 0.05, 2026: 0.05})
    mlt = dom_mlt_resfin_series(
        disb,
        real_rate=0.03,
        grace=1,
        maturity=3,
        deflator=deflator,
        years=years,
    )
    assert mlt.stock.loc[2025] == pytest.approx(100.0)
    assert mlt.interest.loc[2025] == pytest.approx(0.0)
    assert mlt.interest.loc[2026] == pytest.approx(100.0 * (0.03 + 0.05))
    st = dom_st_resfin_series(disb, real_rate=0.04, deflator=deflator, years=years)
    assert st.stock.loc[2025] == pytest.approx(100.0)
    assert st.interest.loc[2026] == pytest.approx(100.0 * (0.04 + 0.05))


def test_dom_mlt_amort_starts_after_grace_full_years() -> None:
    """Excel R91: vintage t amortizes from t+grace+1 through t+maturity."""
    years = (2024, 2025, 2026, 2027, 2028, 2029)
    disb = pd.Series(0.0, index=list(years), dtype=float)
    disb.loc[2025] = 100.0
    deflator = pd.Series(0.05, index=list(years), dtype=float)
    mlt = dom_mlt_resfin_series(
        disb,
        real_rate=0.03,
        grace=2,
        maturity=3,
        deflator=deflator,
        years=years,
    )
    assert mlt.amortization.loc[2026] == pytest.approx(0.0)
    assert mlt.amortization.loc[2027] == pytest.approx(0.0)
    assert mlt.amortization.loc[2028] == pytest.approx(100.0)
    assert mlt.amortization.loc[2029] == pytest.approx(0.0)


def test_pv_resfin_pub_b1_fill_parity_with_excel_gap() -> None:
    """Given Excel public gap, split + overlays match PV_ResFin_pub B1 block."""
    years = [2024, 2025, 2026]
    params = load_input7_residual_params(WORKBOOK)
    gap = _sheet_row("PV_ResFin_pub", 2, 4, 67, years)
    r86 = _sheet_row("PV_ResFin_pub", 2, 4, 69, years)
    fx = _sheet_row("PV_ResFin_pub", 2, 4, 27, years)
    fill = split_residual_financing(
        gap, r86, params, fx, modality="capped", years=tuple(years)
    )
    expected_ext = _sheet_row("PV_ResFin_pub", 2, 4, 72, years)
    expected_dom = _sheet_row("PV_ResFin_pub", 2, 4, 85, years)
    expected_st = _sheet_row("PV_ResFin_pub", 2, 4, 98, years)
    for year in (2025, 2026):
        assert fill.external_mlt_usd.loc[year] == pytest.approx(
            float(expected_ext.loc[year]), rel=1e-6, abs=1e-4
        ), f"ext {year}"
        assert fill.domestic_mlt_lcu.loc[year] == pytest.approx(
            float(expected_dom.loc[year]), rel=1e-6, abs=1e-4
        ), f"dom {year}"
        assert fill.domestic_st_lcu.loc[year] == pytest.approx(
            float(expected_st.loc[year]), rel=1e-6, abs=1e-4
        ), f"st {year}"

    deflator = pd.Series(
        {2024: 0.0, 2025: 0.09635590457446706, 2026: 0.09149720587972766}
    )
    overlay = build_public_resfin_overlay(
        fill, params, deflator=deflator, years=tuple(years)
    )
    expected_pv = _sheet_row("PV_ResFin_pub", 2, 4, 75, years)
    assert overlay.ext.pv.loc[2025] == pytest.approx(
        float(expected_pv.loc[2025]), rel=1e-6, abs=1e-3
    )


def test_run_b1_gdp_public_with_excel_gap() -> None:
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    years = [2024, 2025, 2026]
    gap = _sheet_row("PV_ResFin_pub", 2, 4, 67, years)
    book = run_b1_gdp_public(macro, external, input6, params, public_gap=gap)
    assert book.scenario_id == "B1_GDP_pub"
    assert book.resfin.fill.external_mlt_usd.loc[2025] == pytest.approx(
        303.6535436541075, rel=1e-5
    )
    panel = stress_public_panel(book)
    assert "PV of public debt / GDP" in panel.index
    # Shocked GDP lowers path; debt/GDP rises vs baseline-ish first proj year.
    assert book.macro.gdp_usd().loc[2025] < macro.gdp_usd().loc[2025]


def test_b1_public_gfn_matches_excel_r90_given_excel_gap() -> None:
    """B1 R90 is a fiscal+DS identity, not baseline GFN scaled by inverse GDP."""
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    years = list(range(2024, 2035))
    gap = _sheet_row("PV_ResFin_pub", 2, 4, 67, years)
    book = run_b1_gdp_public(macro, external, input6, params, public_gap=gap)
    expected = _sheet_row("B1_GDP_pub", 7, 3, 90, years)
    expected_gdp = _sheet_row("B1_GDP_pub", 7, 3, 41, years)
    got = book.public_gfn()
    got_gdp = book.gdp_lcu()
    for year in years:
        assert float(got_gdp.loc[year]) == pytest.approx(
            float(expected_gdp.loc[year]), rel=1e-6, abs=0.1
        ), f"B1 R41 GDP LCU {year}"
        assert float(got.loc[year]) == pytest.approx(
            float(expected.loc[year]), rel=1e-4, abs=1.0
        ), f"B1 R90 GFN {year}"


def test_b1_public_pv_to_revenue_uses_baseline_rev_to_gdp() -> None:
    """B1 holds rev/GDP; PV/rev must not use unshocked LCU revenue / shocked GDP."""
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    book = run_b1_gdp_public(macro, external, input6, params, iterations=4)

    base_rev_to_gdp = 100.0 * macro.revenues_incl_grants() / macro.gdp_lcu()
    expected = book.pv_public_debt_to_gdp() / base_rev_to_gdp * 100.0
    got = book.pv_public_debt_to_revenue_grants()
    assert float(got.loc[2025]) == pytest.approx(float(expected.loc[2025]), rel=1e-9)

    naive = (
        book.pv_public_debt_to_gdp()
        / (100.0 * book.macro.revenues_incl_grants() / book.gdp_lcu())
        * 100.0
    )
    # Shocked GDP vs baseline rev/GDP must not coincide with the B1 identity.
    assert float(got.loc[2025]) != pytest.approx(float(naive.loc[2025]), rel=1e-6, abs=0.05)
    assert float(got.loc[2024]) == pytest.approx(float(naive.loc[2024]), rel=1e-9)
    panel = stress_public_panel(book)
    assert "PV of public debt / revenue+grants" in panel.index


def test_run_b1_gdp_public_iterative_produces_positive_fill() -> None:
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    book = run_b1_gdp_public(macro, external, input6, params)
    assert float(book.resfin.fill.external_mlt_usd.loc[2025]) > 0.0
    assert float(book.resfin.fill.domestic_mlt_lcu.loc[2025]) > 0.0
    assert float(book.resfin.fill.domestic_st_lcu.loc[2025]) > 0.0
    years = list(range(2024, 2029))
    fill_years = [2025, 2026]
    expected_gfn = _sheet_row("B1_GDP_pub", 7, 3, 90, years)
    expected_gap = _sheet_row("PV_ResFin_pub", 2, 4, 67, years)
    expected_ext = _sheet_row("PV_ResFin_pub", 2, 4, 72, fill_years)
    expected_dom = _sheet_row("PV_ResFin_pub", 2, 4, 85, fill_years)
    expected_st = _sheet_row("PV_ResFin_pub", 2, 4, 98, fill_years)
    expected_ext_int = _sheet_row("PV_ResFin_pub", 2, 4, 77, fill_years)
    expected_dom_int = _sheet_row("PV_ResFin_pub", 2, 4, 90, fill_years)
    expected_st_int = _sheet_row("PV_ResFin_pub", 2, 4, 99, fill_years)
    got_gfn = book.public_gfn()
    got_gap = public_residual_gap(got_gfn, macro.public_gfn(), tuple(years))
    for year in years:
        assert float(got_gfn.loc[year]) == pytest.approx(
            float(expected_gfn.loc[year]), rel=1e-4, abs=1.0
        ), f"iterative B1 R90 {year}"
        assert float(got_gap.loc[year]) == pytest.approx(
            float(expected_gap.loc[year]), rel=1e-4, abs=1.0
        ), f"iterative R67 {year}"
    for year in fill_years:
        assert float(book.resfin.fill.external_mlt_usd.loc[year]) == pytest.approx(
            float(expected_ext.loc[year]), rel=1e-5, abs=1e-3
        ), f"iterative R72 {year}"
        assert float(book.resfin.fill.domestic_mlt_lcu.loc[year]) == pytest.approx(
            float(expected_dom.loc[year]), rel=1e-5, abs=1e-3
        ), f"iterative R85 {year}"
        assert float(book.resfin.fill.domestic_st_lcu.loc[year]) == pytest.approx(
            float(expected_st.loc[year]), rel=1e-5, abs=1e-3
        ), f"iterative R98 {year}"
        assert float(book.resfin.ext.interest.loc[year]) == pytest.approx(
            float(expected_ext_int.loc[year]), rel=1e-5, abs=1e-3
        ), f"iterative R77 {year}"
        assert float(book.resfin.dom_mlt.interest.loc[year]) == pytest.approx(
            float(expected_dom_int.loc[year]), rel=1e-5, abs=1e-3
        ), f"iterative ResFin R90 {year}"
        assert float(book.resfin.dom_st.interest.loc[year]) == pytest.approx(
            float(expected_st_int.loc[year]), rel=1e-5, abs=1e-3
        ), f"iterative R99 {year}"
    assert book.resfin.fill.external_mlt_usd.loc[2025] == pytest.approx(
        303.6535436541075, rel=1e-5
    )


def test_macro_public_gfn_matches_baseline_public_r78() -> None:
    """Gap subtract uses macro.public_gfn ≡ Baseline - public R78."""
    macro, _external = _workbook_books()
    years = list(range(2024, 2029))
    # Baseline R7 holds calendar years starting at col 15 (2024).
    expected = _sheet_row("Baseline - public", 7, 15, 78, years)
    got = macro.public_gfn()
    for year in years:
        assert float(got.loc[year]) == pytest.approx(
            float(expected.loc[year]), rel=1e-9, abs=1e-6
        ), f"Baseline R78 {year}"


def test_b3_external_gap_r86_r89_parity() -> None:
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    book = run_b3_exports_external(macro, external, input6, params)
    years = [2024, 2025, 2026, 2027, 2028]
    expected_r86 = _sheet_row("B3_Exports_ext", 8, 3, 86, years)
    expected_r89 = _sheet_row("B3_Exports_ext", 8, 3, 89, years)
    borrowing = book.residual_borrowing
    for year in years:
        if year < macro.inputs.first_projection_year:
            continue
        assert float(borrowing.loc[year]) == pytest.approx(
            float(expected_r86.loc[year]), rel=1e-5, abs=1e-3
        ), f"residual borrowing {year}"
        assert book.resfin_pv.loc[year] == pytest.approx(
            float(expected_r89.loc[year]), rel=1e-5, abs=1e-3
        ), f"ResFin PV {year}"


def test_b5_fx_gap_r87_parity() -> None:
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    book = run_b5_fx_external(macro, external, input6, params)
    years = [2024, 2025, 2026, 2027, 2028]
    expected = _sheet_row("B5_depreciation_ext", 8, 3, 87, years)
    for year in years:
        if year < macro.inputs.first_projection_year:
            continue
        assert float(book.residual_borrowing.loc[year]) == pytest.approx(
            float(expected.loc[year]), rel=1e-5, abs=1e-3
        ), f"B5 residual borrowing {year}"
