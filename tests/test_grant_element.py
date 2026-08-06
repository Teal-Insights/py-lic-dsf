"""Tests for Ext R407–R409 grant element of new disbursements."""

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
    grant_element_new_disbursements,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_book() -> ExternalDebtBook:
    years = (2023, 2024, 2025)
    soft = PresentValueInstrument(
        name="Soft",
        grace=5,
        maturity=10,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[0.0, 100.0, 0.0],
        years=years,
    )
    hard = PresentValueInstrument(
        name="Hard",
        grace=1,
        maturity=3,
        interest_rate=0.10,
        discount_rate=0.05,
        disbursements=[0.0, 100.0, 0.0],
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
        portfolio=PVPortfolio(instruments=(soft, hard)),
        inputs=inputs,
    )


def test_grant_element_weighted_average_of_internal_ge() -> None:
    book = _synthetic_book()
    soft, hard = book.portfolio.instruments
    ge_soft = float(soft.internal().loc["Grant element"].iloc[1])
    ge_hard = float(hard.internal().loc["Grant element"].iloc[1])
    # Equal 100+100 disbursements in 2024 → simple average of the two GEs.
    expected = (ge_soft + ge_hard) / 2.0

    series = grant_element_new_disbursements(book)
    assert series.loc[2024] == pytest.approx(expected)
    assert series.loc[2023] == pytest.approx(0.0)
    assert series.loc[2025] == pytest.approx(0.0)

    # R407 / R409 identities
    den = 200.0
    assert book.grant_element_percent().loc[2024] == pytest.approx(expected)
    assert book.new_disbursements_net_of_ge().loc[2024] == pytest.approx(
        den * (1.0 - expected / 100.0)
    )
    assert book.grant_element_value().loc[2024] == pytest.approx(
        expected * den / 100.0
    )


@pytest.mark.skipif(not WORKBOOK.is_file(), reason="template workbook missing")
def test_workbook_parity_grant_element_vs_ext_f408() -> None:
    instruments = load_instruments_from_workbook(
        WORKBOOK, include_zero_disbursement=True
    )
    lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
    book = ExternalDebtBook(
        portfolio=PVPortfolio(tuple(instruments) + tuple(lc_nr)),
        inputs=load_external_debt_inputs(WORKBOOK),
    )
    ge = grant_element_new_disbursements(book)

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ext = wb["Ext_Debt_Data"]
        years = [y for y in book.inputs.years if y >= 2024][:5]
        for i, year in enumerate(years):
            excel = ext.cell(408, 6 + i).value
            if excel is None or excel == "":
                assert ge.loc[year] == pytest.approx(0.0)
            else:
                assert ge.loc[year] == pytest.approx(float(excel), abs=1e-6)
            r122 = float(ext.cell(122, 6 + i).value or 0.0)
            r407 = ext.cell(407, 6 + i).value
            r409 = ext.cell(409, 6 + i).value
            if r122 and r407 is not None:
                assert book.new_disbursements_net_of_ge().loc[year] == pytest.approx(
                    float(r407), abs=1e-4
                )
            if r122 and r409 is not None:
                assert book.grant_element_value().loc[year] == pytest.approx(
                    float(r409), abs=1e-4
                )
    finally:
        wb.close()
