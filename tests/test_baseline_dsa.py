"""Tests for Baseline DSA sustainability ratios (``lic_dsf.dsa``)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.dsa import (
    BaselineExternalBook,
    BaselinePublicBook,
    external_dsa_panel,
    load_core,
    public_dsa_panel,
)
from lic_dsf.pv import (
    ExternalDebtBook,
    ExternalDebtInputs,
    MacroDebtBook,
    MacroDebtInputs,
    PresentValueInstrument,
    PVPortfolio,
    load_domestic_debt_inputs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

_CACHE: tuple[MacroDebtBook, ExternalDebtBook] | None = None


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_macro_ext() -> tuple[MacroDebtBook, ExternalDebtBook]:
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
    external = ExternalDebtBook(
        portfolio=PVPortfolio(instruments=(instrument,)), inputs=ext_inputs
    )
    macro_inputs = MacroDebtInputs(
        years=years,
        first_projection_year=2024,
        gdp_usd=pd.Series({2023: 1000.0, 2024: 1100.0, 2025: 1200.0}),
        gdp_constant=pd.Series({2023: 900.0, 2024: 950.0, 2025: 1000.0}),
        fx_eop=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5}),
        fx_pa=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5}),
        current_account=z.copy(),
        exports=pd.Series({2023: 400.0, 2024: 440.0, 2025: 480.0}),
        imports=z.copy(),
        current_transfers_net=z.copy(),
        current_transfers_official=z.copy(),
        fdi=z.copy(),
        exceptional_financing=z.copy(),
        reserves_flow=z.copy(),
        revenues_incl_grants=pd.Series({2023: 200.0, 2024: 220.0, 2025: 240.0}),
        grants=pd.Series({2023: 20.0, 2024: 22.0, 2025: 24.0}),
        privatization=z.copy(),
        primary_expenditure=pd.Series({2023: 150.0, 2024: 160.0, 2025: 170.0}),
        public_assets=z.copy(),
        contingent_liabilities=z.copy(),
        other_debt_creating_flows=z.copy(),
        debt_relief=z.copy(),
        mlt_external=pd.Series({2023: 500.0, 2024: 0.0, 2025: 0.0}),
        short_term_external=pd.Series({2023: 50.0, 2024: 0.0, 2025: 0.0}),
        private_mlt_external=z.copy(),
        private_st_external=pd.Series({2023: 10.0, 2024: 10.0, 2025: 10.0}),
        domestic_mlt=pd.Series({2023: 200.0, 2024: 0.0, 2025: 0.0}),
        domestic_st=pd.Series({2023: 20.0, 2024: 0.0, 2025: 0.0}),
        ppg_interest=pd.Series({2023: 10.0, 2024: 0.0, 2025: 0.0}),
        private_interest=z.copy(),
        domestic_interest=pd.Series({2023: 5.0, 2024: 0.0, 2025: 0.0}),
        ppg_amortization=pd.Series({2023: 15.0, 2024: 0.0, 2025: 0.0}),
        private_amortization=z.copy(),
        domestic_amortization=pd.Series({2023: 4.0, 2024: 0.0, 2025: 0.0}),
        concessional_loans=z.copy(),
        domestic_mlt_input5=pd.Series({2023: 0.0, 2024: 210.0, 2025: 220.0}),
        domestic_st_input5=pd.Series({2023: 0.0, 2024: 22.0, 2025: 24.0}),
        domestic_interest_lcu_input5=pd.Series({2023: 0.0, 2024: 12.5, 2025: 12.5}),
        domestic_principal_lcu_input5=pd.Series({2023: 0.0, 2024: 30.0, 2025: 32.0}),
        public_gfn_input5=pd.Series({2023: 0.0, 2024: 80.0, 2025: 85.0}),
    )
    macro = MacroDebtBook(inputs=macro_inputs, external=external)
    return macro, external


def _workbook_books() -> tuple[MacroDebtBook, ExternalDebtBook]:
    global _CACHE
    if _CACHE is None:
        macro, external, _, _ = load_core(WORKBOOK)
        _CACHE = (macro, external)
    return _CACHE


def test_load_core_wires_ext_macro_and_baseline_books() -> None:
    macro, external, ext_base, pub_base = load_core(WORKBOOK)
    assert macro.external is external
    assert ext_base.macro is macro
    assert ext_base.external is external
    assert pub_base.macro is macro
    assert pub_base.external is external
    assert 2024 in ext_base.years
    assert float(ext_base.pv_ppg_external_to_gdp().loc[2024]) > 0.0
    assert float(pub_base.pv_public_debt_to_gdp().loc[2024]) > 0.0


def test_synthetic_pv_to_gdp_and_public_debt_to_gdp() -> None:
    macro, external = _synthetic_macro_ext()
    ext_base = BaselineExternalBook(macro=macro, external=external)
    pub_base = BaselinePublicBook(macro=macro, external=external)

    pv = float(external.total_pv_of_debt().loc[2024])
    gdp = 1100.0
    assert ext_base.pv_ppg_external_to_gdp().loc[2024] == pytest.approx(
        100.0 * pv / gdp
    )
    assert pub_base.public_sector_debt_to_gdp().loc[2024] == pytest.approx(
        100.0 * float(macro.total_public_debt().loc[2024]) / (1100.0 * 2.5)
    )


def test_panels_have_expected_rows() -> None:
    macro, external = _synthetic_macro_ext()
    ext_panel = external_dsa_panel(BaselineExternalBook(macro=macro, external=external))
    pub_panel = public_dsa_panel(BaselinePublicBook(macro=macro, external=external))
    assert "PV of PPG external debt / GDP" in ext_panel.index
    assert "PPG debt service / revenue" in ext_panel.index
    assert "Public sector debt / GDP" in pub_panel.index
    assert "Debt service / revenue+grants" in pub_panel.index


def test_workbook_smoke() -> None:
    macro, external = _workbook_books()
    ext_base = BaselineExternalBook(macro=macro, external=external)
    pub_base = BaselinePublicBook(macro=macro, external=external)
    assert ext_base.years[0] <= 2013
    assert 2024 in ext_base.years
    assert float(ext_base.pv_ppg_external_to_gdp().loc[2024]) > 0.0
    assert float(pub_base.public_sector_debt_to_gdp().loc[2024]) > 0.0


def _baseline_cached(
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


@pytest.mark.parametrize(
    ("method", "row"),
    [
        ("pv_ppg_external_to_gdp", 35),
        ("pv_ppg_external_to_exports", 36),
        ("pv_ppg_external_to_revenue", 37),
        ("ppg_debt_service_to_exports", 39),
        ("ppg_debt_service_to_revenue", 40),
    ],
)
def test_external_baseline_parity(method: str, row: int) -> None:
    years = [2019, 2020, 2023, 2024, 2025]
    macro, external = _workbook_books()
    book = BaselineExternalBook(macro=macro, external=external)
    got = getattr(book, method)().reindex(years)
    expected = _baseline_cached("Baseline - external", 8, 3, row, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-7, abs=1e-5
        ), f"{method} {year}"


@pytest.mark.parametrize(
    ("method", "row"),
    [
        ("public_sector_debt_to_gdp", 12),
        ("ppg_external_debt_to_gdp", 20),
        ("pv_public_debt_to_gdp", 42),
        ("pv_public_debt_to_revenue_grants", 43),
        ("debt_service_to_revenue_grants", 45),
    ],
)
def test_public_baseline_parity(method: str, row: int) -> None:
    years = [2019, 2020, 2023, 2024, 2025]
    macro, external = _workbook_books()
    book = BaselinePublicBook(macro=macro, external=external)
    got = getattr(book, method)().reindex(years)
    expected = _baseline_cached("Baseline - public", 7, 4, row, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-7, abs=1e-5
        ), f"{method} {year}"


def test_dom_loader_accepts_baseline_books() -> None:
    macro, external = _workbook_books()
    pub = BaselinePublicBook(macro=macro, external=external)
    ext = BaselineExternalBook(macro=macro, external=external)
    from_sheet = load_domestic_debt_inputs(WORKBOOK)
    from_books = load_domestic_debt_inputs(
        WORKBOOK,
        macro_book=macro,
        baseline_public=pub,
        baseline_external=ext,
    )
    for year in (2019, 2023, 2024):
        assert from_books.public_sector_debt_pct_gdp.loc[year] == pytest.approx(
            float(from_sheet.public_sector_debt_pct_gdp.loc[year]),
            rel=1e-7,
            abs=1e-5,
        )
        assert from_books.ppg_external_debt_pct_gdp.loc[year] == pytest.approx(
            float(from_sheet.ppg_external_debt_pct_gdp.loc[year]),
            rel=1e-7,
            abs=1e-5,
        )
        assert from_books.public_ds_to_revenue_grants.loc[year] == pytest.approx(
            float(from_sheet.public_ds_to_revenue_grants.loc[year]),
            rel=1e-7,
            abs=1e-5,
        )
        assert from_books.ppg_ds_to_revenue.loc[year] == pytest.approx(
            float(from_sheet.ppg_ds_to_revenue.loc[year]),
            rel=1e-7,
            abs=1e-5,
        )
