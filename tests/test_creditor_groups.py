"""Tests for Ext creditor-group new-debt panels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastpyxl import load_workbook

from lic_dsf.pv import (
    ExternalDebtBook,
    ExternalDebtInputs,
    PresentValueInstrument,
    PVPortfolio,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)
from lic_dsf.pv.external_debt.creditor_groups import (
    CREDITOR_GROUPS,
    creditor_group_for_name,
    group_instrument_panel,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_book() -> ExternalDebtBook:
    years = (2024, 2025)
    multi = PresentValueInstrument(
        name="IMF",
        grace=1,
        maturity=3,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[100.0, 0.0],
        years=years,
    )
    commercial = PresentValueInstrument(
        name="Eurobond",
        grace=1,
        maturity=3,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[50.0, 25.0],
        years=years,
    )
    zero = _zero(years)
    inputs = ExternalDebtInputs(
        years=years,
        existing_debt_service=pd.DataFrame({y: [0.0] for y in years}, index=["IMF"]),
        existing_principal=zero.copy(),
        existing_discount_rates={"IMF": 0.05},
        arrears=zero.copy(),
        short_term_external=zero.copy(),
        sdr_pv=zero.copy(),
        sdr_interest=zero.copy(),
        macro_ppg_external=zero.copy(),
        macro_mlt_external=zero.copy(),
        fx_eop=pd.Series({y: 1.0 for y in years}, dtype=float),
        fx_pa=pd.Series({y: 1.0 for y in years}, dtype=float),
        locally_issued_debt_stock=zero.copy(),
        locally_issued_principal=zero.copy(),
        locally_issued_interest=zero.copy(),
        locally_issued_st=zero.copy(),
        locally_issued_st_principal=zero.copy(),
        locally_issued_st_interest=zero.copy(),
        domestic_mlt_disbursements_usd=zero.copy(),
        domestic_st_disbursements_usd=zero.copy(),
        short_term_interest_rate=0.0,
        residual_interest_rates={},
        grant_element_weight_names=frozenset(),
    )
    return ExternalDebtBook(
        portfolio=PVPortfolio(instruments=(multi, commercial)),
        inputs=inputs,
    )


def test_creditor_group_for_known_names() -> None:
    assert creditor_group_for_name("IMF") == "Multilaterals"
    assert creditor_group_for_name("Eurobond") == "Commercial"
    assert creditor_group_for_name("Bonds (1 to 3 years)-LC") == "Locally issued (NR)"
    assert (
        creditor_group_for_name("Bonds (1 to 3 years)-FX (residents)")
        == "FX local (residents)"
    )


def test_group_instrument_panel_sums_and_total() -> None:
    panel = pd.DataFrame(
        {
            2024: [10.0, 5.0, 3.0],
            2025: [0.0, 2.0, 1.0],
        },
        index=["IMF", "Eurobond", "Bonds (1 to 3 years)-LC"],
    )
    grouped = group_instrument_panel(panel)
    assert list(grouped.index) == list(CREDITOR_GROUPS) + ["Total"]
    assert grouped.loc["Multilaterals", 2024] == pytest.approx(10.0)
    assert grouped.loc["Commercial", 2024] == pytest.approx(5.0)
    assert grouped.loc["Locally issued (NR)", 2024] == pytest.approx(3.0)
    assert grouped.loc["Total", 2024] == pytest.approx(18.0)
    assert grouped.loc["Total", 2025] == pytest.approx(3.0)


def test_book_disbursements_by_creditor_synthetic() -> None:
    book = _synthetic_book()
    disb = book.new_disbursements_by_creditor()
    assert disb.loc["Multilaterals", 2024] == pytest.approx(100.0)
    assert disb.loc["Commercial", 2024] == pytest.approx(50.0)
    assert disb.loc["Commercial", 2025] == pytest.approx(25.0)
    assert disb.loc["Total", 2024] == pytest.approx(150.0)
    assert disb.loc["Other multilaterals", 2024] == pytest.approx(0.0)


@pytest.mark.skipif(not WORKBOOK.is_file(), reason="template workbook missing")
def test_workbook_parity_creditor_group_totals() -> None:
    instruments = load_instruments_from_workbook(
        WORKBOOK, include_zero_disbursement=True
    )
    lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
    book = ExternalDebtBook(
        portfolio=PVPortfolio(tuple(instruments) + tuple(lc_nr)),
        inputs=load_external_debt_inputs(WORKBOOK),
    )

    interest = book.new_interest_by_creditor()
    amort = book.new_amortization_by_creditor()
    pv = book.new_pv_by_creditor()
    stock = book.new_stock_by_creditor()
    disb = book.new_disbursements_by_creditor()

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ext = wb["Ext_Debt_Data"]
        # 2024 = column F
        col = 6
        # Grand totals
        assert interest.loc["Total", 2024] == pytest.approx(
            float(ext.cell(142, col).value), abs=1e-6
        )
        assert amort.loc["Total", 2024] == pytest.approx(
            float(ext.cell(192, col).value), abs=1e-6
        )
        assert pv.loc["Total", 2024] == pytest.approx(
            float(ext.cell(279, col).value), abs=1e-6
        )
        assert stock.loc["Total", 2024] == pytest.approx(
            float(ext.cell(329, col).value), abs=1e-6
        )
        assert disb.loc["Total", 2024] == pytest.approx(
            float(ext.cell(122, col).value), abs=1e-6
        )
        # Group subtotals (interest + disbursements)
        assert interest.loc["Multilaterals", 2024] == pytest.approx(
            float(ext.cell(143, col).value), abs=1e-6
        )
        assert interest.loc["Other multilaterals", 2024] == pytest.approx(
            float(ext.cell(154, col).value), abs=1e-6
        )
        assert interest.loc["Official bilaterals", 2024] == pytest.approx(
            float(ext.cell(158, col).value), abs=1e-6
        )
        assert interest.loc["Commercial", 2024] == pytest.approx(
            float(ext.cell(171, col).value), abs=1e-6
        )
        assert interest.loc["Locally issued (NR)", 2024] == pytest.approx(
            float(ext.cell(177, col).value), abs=1e-6
        )
        assert interest.loc["FX local (residents)", 2024] == pytest.approx(
            float(ext.cell(187, col).value), abs=1e-6
        )
        assert disb.loc["Multilaterals", 2024] == pytest.approx(
            float(ext.cell(71, col).value), abs=1e-6
        )
        assert disb.loc["Commercial", 2024] == pytest.approx(
            float(ext.cell(99, col).value), abs=1e-6
        )
        assert disb.loc["Locally issued (NR)", 2024] == pytest.approx(
            float(ext.cell(105, col).value), abs=1e-6
        )
    finally:
        wb.close()
