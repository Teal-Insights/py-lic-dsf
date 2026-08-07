"""Tests for applied residual financing (gap → ST / ext MLT / dom MLT)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.pv import (
    ExternalDebtBook,
    MacroDebtBook,
    PVPortfolio,
    load_external_debt_inputs,
    load_input7_residual_params,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)
from lic_dsf.stress import (
    build_public_resfin_overlay,
    dom_mlt_resfin_series,
    dom_st_resfin_series,
    external_residual_gap,
    load_input6_standard,
    public_residual_gap,
    run_b1_gdp_public,
    run_b3_exports_external,
    split_residual_financing,
    stress_public_panel,
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


def test_run_b1_gdp_public_iterative_produces_positive_fill() -> None:
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    book = run_b1_gdp_public(macro, external, input6, params, iterations=4)
    assert float(book.resfin.fill.external_mlt_usd.loc[2025]) > 0.0
    assert float(book.resfin.fill.domestic_mlt_lcu.loc[2025]) > 0.0
    assert float(book.resfin.fill.domestic_st_lcu.loc[2025]) > 0.0
    # Within ~20% of Excel B1 fill for 2025 (GDP-scaled GFN approx).
    assert book.resfin.fill.external_mlt_usd.loc[2025] == pytest.approx(
        303.65, rel=0.2, abs=50.0
    )


def test_b3_external_gap_r86_r89_parity() -> None:
    macro, external = _workbook_books()
    input6 = load_input6_standard(WORKBOOK)
    params = load_input7_residual_params(WORKBOOK)
    book = run_b3_exports_external(macro, external, input6, params)
    years = [2024, 2025]
    expected_r86 = _sheet_row("B3_Exports_ext", 8, 3, 86, years)
    expected_r89 = _sheet_row("B3_Exports_ext", 8, 3, 89, years)
    # 2025: identity matches export shortfall / ResFin PV.
    assert book.resfin_pv.loc[2025] == pytest.approx(
        float(expected_r89.loc[2025]), rel=1e-5, abs=1e-3
    )
    assert float(expected_r86.loc[2025]) == pytest.approx(
        float(expected_r89.loc[2025]), rel=1e-5, abs=1e-3
    )
