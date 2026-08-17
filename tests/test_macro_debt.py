"""Tests for Macro-Debt_Data bridge (pass-through, stitch, derived)."""

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
    load_domestic_debt_inputs,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

_WORKBOOK_MACRO_BOOK: MacroDebtBook | None = None


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_inputs() -> MacroDebtInputs:
    years = (2022, 2023, 2024, 2025)
    z = _zero(years)
    return MacroDebtInputs(
        years=years,
        first_projection_year=2024,
        gdp_usd=pd.Series({2022: 100.0, 2023: 110.0, 2024: 120.0, 2025: 130.0}),
        gdp_constant=pd.Series({2022: 90.0, 2023: 95.0, 2024: 100.0, 2025: 105.0}),
        fx_eop=pd.Series({2022: 2.0, 2023: 2.0, 2024: 2.5, 2025: 2.5}),
        fx_pa=pd.Series({2022: 2.0, 2023: 2.0, 2024: 2.5, 2025: 2.5}),
        current_account=pd.Series({2022: -10.0, 2023: -12.0, 2024: -15.0, 2025: -18.0}),
        exports=pd.Series({2022: 50.0, 2023: 55.0, 2024: 60.0, 2025: 65.0}),
        imports=pd.Series({2022: 60.0, 2023: 65.0, 2024: 70.0, 2025: 75.0}),
        current_transfers_net=z.copy(),
        current_transfers_official=z.copy(),
        fdi=pd.Series({2022: 5.0, 2023: 5.0, 2024: 6.0, 2025: 6.0}),
        exceptional_financing=z.copy(),
        reserves_flow=z.copy(),
        revenues_incl_grants=pd.Series(
            {2022: 40.0, 2023: 42.0, 2024: 45.0, 2025: 48.0}
        ),
        grants=pd.Series({2022: 4.0, 2023: 4.0, 2024: 5.0, 2025: 5.0}),
        privatization=z.copy(),
        primary_expenditure=pd.Series({2022: 35.0, 2023: 36.0, 2024: 38.0, 2025: 40.0}),
        public_assets=z.copy(),
        contingent_liabilities=z.copy(),
        other_debt_creating_flows=z.copy(),
        debt_relief=z.copy(),
        mlt_external=pd.Series({2022: 200.0, 2023: 210.0, 2024: 999.0, 2025: 999.0}),
        short_term_external=pd.Series(
            {2022: 20.0, 2023: 25.0, 2024: 999.0, 2025: 999.0}
        ),
        private_mlt_external=pd.Series(
            {2022: 50.0, 2023: 55.0, 2024: 60.0, 2025: 65.0}
        ),
        private_st_external=pd.Series({2022: 5.0, 2023: 5.0, 2024: 5.0, 2025: 5.0}),
        domestic_mlt=pd.Series({2022: 80.0, 2023: 85.0, 2024: 0.0, 2025: 0.0}),
        domestic_st=pd.Series({2022: 10.0, 2023: 12.0, 2024: 0.0, 2025: 0.0}),
        ppg_interest=pd.Series({2022: 8.0, 2023: 9.0, 2024: 0.0, 2025: 0.0}),
        private_interest=z.copy(),
        domestic_interest=pd.Series({2022: 3.0, 2023: 3.0, 2024: 0.0, 2025: 0.0}),
        ppg_amortization=pd.Series({2022: 15.0, 2023: 16.0, 2024: 0.0, 2025: 0.0}),
        private_amortization=pd.Series({2022: 2.0, 2023: 2.0, 2024: 2.0, 2025: 2.0}),
        domestic_amortization=pd.Series({2022: 4.0, 2023: 4.0, 2024: 0.0, 2025: 0.0}),
        concessional_loans=z.copy(),
        domestic_mlt_input5=pd.Series({2022: 0.0, 2023: 0.0, 2024: 90.0, 2025: 95.0}),
        domestic_st_input5=pd.Series({2022: 0.0, 2023: 0.0, 2024: 14.0, 2025: 15.0}),
        domestic_interest_lcu_input5=pd.Series(
            {2022: 0.0, 2023: 0.0, 2024: 10.0, 2025: 12.5}
        ),
        domestic_principal_lcu_input5=pd.Series(
            {2022: 0.0, 2023: 0.0, 2024: 20.0, 2025: 22.0}
        ),
        public_gfn_input5=pd.Series({2022: 0.0, 2023: 0.0, 2024: 70.0, 2025: 75.0}),
    )


def _tiny_ext_book() -> ExternalDebtBook:
    years = (2023, 2024, 2025)
    z = _zero(years)
    instrument = PresentValueInstrument(
        name="NewLoan",
        grace=1,
        maturity=3,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[100.0, 0.0, 0.0],
        years=years,
    )
    ext_inputs = ExternalDebtInputs(
        years=years,
        existing_debt_service=pd.DataFrame(
            {2023: [10.0], 2024: [10.0], 2025: [10.0]}, index=["IMF"]
        ),
        existing_principal=pd.Series({2023: 5.0, 2024: 5.0, 2025: 5.0}),
        existing_discount_rates={"IMF": 0.05},
        arrears=z.copy(),
        short_term_external=pd.Series({2023: 50.0, 2024: 40.0, 2025: 0.0}),
        sdr_pv=z.copy(),
        sdr_interest=z.copy(),
        macro_ppg_external=pd.Series({2023: 1100.0, 2024: 1200.0, 2025: 1300.0}),
        macro_mlt_external=pd.Series({2023: 1050.0, 2024: 1160.0, 2025: 1300.0}),
        fx_eop=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5}),
        fx_pa=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5}),
        locally_issued_debt_stock=pd.Series({2023: 100.0, 2024: 80.0, 2025: 60.0}),
        locally_issued_principal=pd.Series({2023: 5.0, 2024: 5.0, 2025: 5.0}),
        locally_issued_interest=pd.Series({2023: 2.0, 2024: 2.0, 2025: 2.0}),
        locally_issued_st=z.copy(),
        locally_issued_st_principal=z.copy(),
        locally_issued_st_interest=z.copy(),
        domestic_mlt_disbursements_usd=z.copy(),
        domestic_st_disbursements_usd=z.copy(),
        short_term_interest_rate=0.10,
        residual_interest_rates={},
        grant_element_weight_names=frozenset(),
    )
    return ExternalDebtBook(
        portfolio=PVPortfolio(instruments=(instrument,)), inputs=ext_inputs
    )


def test_passthrough_without_external() -> None:
    book = MacroDebtBook(inputs=_synthetic_inputs())
    assert book.gdp_usd().loc[2023] == pytest.approx(110.0)
    assert book.mlt_external().loc[2023] == pytest.approx(210.0)
    # Without Ext, projection still uses Input 3 seed (not overwritten).
    assert book.mlt_external().loc[2024] == pytest.approx(999.0)
    assert book.primary_balance().loc[2024] == pytest.approx(45.0 - 38.0)


def test_stitch_uses_ext_in_projection() -> None:
    macro_inputs = _synthetic_inputs()
    ext = _tiny_ext_book()
    book = MacroDebtBook(inputs=macro_inputs, external=ext)

    # Hist unchanged.
    assert book.mlt_external().loc[2023] == pytest.approx(210.0)
    # Projection from Ext: existing + arrears + new.
    years = list(ext.inputs.years)
    expected = (
        float(ext.existing_mlt_nominal().loc[2024])
        + float(ext.inputs.arrears.loc[2024])
        + float(ext.new_mlt_nominal().loc[2024])
    )
    assert 2024 in years
    assert book.mlt_external().loc[2024] == pytest.approx(expected)
    assert book.short_term_external().loc[2024] == pytest.approx(
        float(ext.total_st_external().loc[2024])
    )
    assert book.ppg_external().loc[2024] == pytest.approx(
        book.mlt_external().loc[2024] + book.short_term_external().loc[2024]
    )
    assert book.total_external().loc[2024] == pytest.approx(
        book.ppg_external().loc[2024] + book.private_external().loc[2024]
    )


def test_domestic_proj_and_public_debt() -> None:
    book = MacroDebtBook(inputs=_synthetic_inputs())
    assert book.domestic_mlt().loc[2023] == pytest.approx(85.0)
    assert book.domestic_mlt().loc[2024] == pytest.approx(90.0)
    assert book.domestic_debt().loc[2024] == pytest.approx(90.0 + 14.0)
    # R21 proj = LCU interest / FX
    assert book.domestic_interest().loc[2024] == pytest.approx(10.0 / 2.5)
    # R80 = PPG*FX + domestic
    book_ext = MacroDebtBook(inputs=_synthetic_inputs(), external=_tiny_ext_book())
    ppg = book_ext.ppg_external().loc[2024]
    fx = 2.5
    assert book_ext.total_public_debt().loc[2024] == pytest.approx(
        ppg * fx + 90.0 + 14.0
    )


def test_load_macro_debt_inputs_smoke() -> None:
    inputs = load_macro_debt_inputs(WORKBOOK)
    assert inputs.first_projection_year == 2024
    assert 2011 in inputs.years
    assert 2024 in inputs.years
    assert float(inputs.gdp_usd.loc[2023]) > 0.0
    assert float(inputs.fx_pa.loc[2024]) > 0.0


def _macro_cached(row: int, years: list[int]) -> pd.Series:
    from fastpyxl import load_workbook

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ws = wb["Macro-Debt_Data"]
        year_cols: dict[int, int] = {}
        col = 8
        while True:
            value = ws.cell(5, col).value
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
            pytest.skip(f"Macro-Debt_Data R{row} missing cached values for {missing}")
        return pd.Series(out, dtype=float)
    finally:
        wb.close()


def _workbook_macro_book() -> MacroDebtBook:
    global _WORKBOOK_MACRO_BOOK
    if _WORKBOOK_MACRO_BOOK is None:
        instruments = load_instruments_from_workbook(
            WORKBOOK, include_zero_disbursement=True
        )
        lc_nr = load_lc_nr_instruments_from_workbook(
            WORKBOOK, include_zero_disbursement=True
        )
        portfolio = PVPortfolio(instruments=tuple(instruments) + tuple(lc_nr))
        ext = ExternalDebtBook(
            portfolio=portfolio, inputs=load_external_debt_inputs(WORKBOOK)
        )
        _WORKBOOK_MACRO_BOOK = MacroDebtBook(
            inputs=load_macro_debt_inputs(WORKBOOK), external=ext
        )
    return _WORKBOOK_MACRO_BOOK


@pytest.mark.parametrize(
    ("method", "row", "years"),
    [
        ("total_external", 6, [2020, 2023, 2024, 2025]),
        ("mlt_external", 9, [2020, 2023, 2024, 2025]),
        ("short_term_external", 10, [2020, 2023, 2024, 2025]),
        ("revenues_incl_grants", 45, [2020, 2023, 2024]),
        ("gdp_usd", 56, [2020, 2023, 2024]),
        ("foreign_gdp_deflator", 58, [2020, 2023, 2024]),
        ("fx_eop", 59, [2020, 2023, 2024]),
        ("fx_pa", 60, [2020, 2023, 2024]),
        ("external_gfn", 74, [2024, 2025, 2026]),
        ("residual_financing_gap", 77, [2024, 2025, 2026]),
        ("total_public_debt", 80, [2024, 2025, 2026]),
        ("pv_external_lcu", 92, [2024, 2025, 2026]),
    ],
)
def test_macro_parity_vs_excel(method: str, row: int, years: list[int]) -> None:
    book = _workbook_macro_book()
    got = getattr(book, method)().reindex(years)
    expected = _macro_cached(row, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-8, abs=1e-6
        ), f"{method} year {year}"


def test_dom_loader_accepts_macro_book() -> None:
    macro = _workbook_macro_book()
    from_sheet = load_domestic_debt_inputs(WORKBOOK)
    from_book = load_domestic_debt_inputs(WORKBOOK, macro_book=macro)
    for year in (2020, 2023, 2024):
        assert from_book.revenues_incl_grants.loc[year] == pytest.approx(
            float(from_sheet.revenues_incl_grants.loc[year]), rel=1e-8, abs=1e-6
        )
        assert from_book.gdp_usd.loc[year] == pytest.approx(
            float(from_sheet.gdp_usd.loc[year]), rel=1e-8, abs=1e-6
        )
        assert from_book.domestic_debt_stock.loc[year] == pytest.approx(
            float(from_sheet.domestic_debt_stock.loc[year]), rel=1e-8, abs=1e-6
        )
