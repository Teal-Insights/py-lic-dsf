"""Tests for Ext_Debt_Data existing-debt inputs and ExternalDebtBook."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.pv import (
    ExternalDebtBook,
    ExternalDebtInputs,
    PresentValueInstrument,
    PVPortfolio,
    excel_npv,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)
from lic_dsf.pv.external_debt.existing_debt import existing_mlt_pv
from lic_dsf.pv.external_debt.fxutil import lc_to_usd

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_inputs() -> ExternalDebtInputs:
    years = (2023, 2024, 2025, 2026)
    service = pd.DataFrame(
        {
            2023: [10.0, 20.0],
            2024: [10.0, 20.0],
            2025: [10.0, 20.0],
            2026: [10.0, 20.0],
        },
        index=["IMF", "Eurobond"],
    )
    principal = pd.Series({2023: 15.0, 2024: 15.0, 2025: 15.0, 2026: 15.0}, dtype=float)
    zero = _zero(years)
    local_stock = pd.Series(
        {2023: 100.0, 2024: 80.0, 2025: 60.0, 2026: 40.0}, dtype=float
    )
    local_principal = pd.Series(
        {2023: 5.0, 2024: 5.0, 2025: 5.0, 2026: 5.0}, dtype=float
    )
    local_interest = pd.Series(
        {2023: 2.0, 2024: 2.0, 2025: 2.0, 2026: 2.0}, dtype=float
    )
    return ExternalDebtInputs(
        years=years,
        existing_debt_service=service,
        existing_principal=principal,
        existing_discount_rates={"IMF": 0.05, "Eurobond": 0.05},
        arrears=zero.copy(),
        short_term_external=pd.Series(
            {2023: 50.0, 2024: 40.0, 2025: 0.0, 2026: 0.0}, dtype=float
        ),
        sdr_pv=zero.copy(),
        sdr_interest=zero.copy(),
        macro_ppg_external=pd.Series(
            {2023: 1100.0, 2024: 1200.0, 2025: 1300.0, 2026: 1400.0}, dtype=float
        ),
        macro_mlt_external=pd.Series(
            {2023: 1050.0, 2024: 1160.0, 2025: 1300.0, 2026: 1400.0}, dtype=float
        ),
        fx_eop=pd.Series({2023: 4.0, 2024: 5.0, 2025: 5.0, 2026: 5.0}, dtype=float),
        fx_pa=pd.Series({2023: 4.0, 2024: 5.0, 2025: 5.0, 2026: 5.0}, dtype=float),
        locally_issued_debt_stock=local_stock,
        locally_issued_principal=local_principal,
        locally_issued_interest=local_interest,
        locally_issued_st=zero.copy(),
        locally_issued_st_principal=zero.copy(),
        locally_issued_st_interest=zero.copy(),
        domestic_mlt_disbursements_usd=zero.copy(),
        domestic_st_disbursements_usd=zero.copy(),
        short_term_interest_rate=0.10,
        residual_interest_rates={},
        grant_element_weight_names=frozenset(),
    )


def _tiny_portfolio() -> PVPortfolio:
    years = (2024, 2025, 2026)
    instrument = PresentValueInstrument(
        name="NewLoan",
        grace=1,
        maturity=3,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[100.0, 0.0, 0.0],
        years=years,
    )
    return PVPortfolio(instruments=(instrument,))


def test_lc_to_usd_divides_by_fx() -> None:
    lc = pd.Series({2024: 100.0, 2025: 50.0})
    fx = pd.Series({2024: 4.0, 2025: 0.0})
    usd = lc_to_usd(lc, fx)
    assert usd.loc[2024] == pytest.approx(25.0)
    assert usd.loc[2025] == pytest.approx(0.0)


def test_existing_mlt_pv_matches_excel_npv_definition() -> None:
    inputs = _synthetic_inputs()
    panel = existing_mlt_pv(inputs)
    assert list(panel.index) == ["IMF", "Eurobond", "Locally-issued", "Total"]
    expected_imf = excel_npv(0.05, [10.0, 10.0])
    assert panel.loc["IMF", 2024] == pytest.approx(expected_imf)
    assert panel.loc["Total", 2024] == pytest.approx(
        panel.loc["IMF", 2024]
        + panel.loc["Eurobond", 2024]
        + panel.loc["Locally-issued", 2024]
    )


def test_external_debt_book_total_pv_and_ppg_check() -> None:
    inputs = _synthetic_inputs()
    book = ExternalDebtBook(portfolio=_tiny_portfolio(), inputs=inputs)

    existing = book.existing_mlt_pv().loc["Total"]
    new_pv = book.new_mlt_pv()
    total = book.total_pv_of_debt()

    assert total.loc[2024] == pytest.approx(
        float(existing.loc[2024])
        + float(inputs.arrears.loc[2024])
        + float(new_pv.loc[2024])
        + float(book.total_st_external().loc[2024])
        + float(inputs.sdr_pv.loc[2024])
    )

    stock = book.existing_mlt_nominal()
    assert stock.loc[2023] == pytest.approx(1050.0)
    # 1050 - 15 principal - (100-80) local valuation
    assert stock.loc[2024] == pytest.approx(1050.0 - 15.0 - 20.0)

    check = book.nominal_ppg_check()
    assert check.loc[2024] == pytest.approx(
        float(inputs.macro_ppg_external.loc[2024])
        - float(book.new_mlt_nominal().loc[2024])
        - float(stock.loc[2024])
        - float(inputs.short_term_external.loc[2024])
        - float(inputs.arrears.loc[2024])
    )


def test_external_debt_book_includes_local_in_public_ds() -> None:
    book = ExternalDebtBook(portfolio=_tiny_portfolio(), inputs=_synthetic_inputs())
    ds = book.total_public_debt_service()
    # 2024: existing prin 15 + local 5 + new amort + prior ST 50
    assert ds.loc["    of which: principal", 2024] == pytest.approx(
        15.0 + 5.0 + float(book.new_debt_service().loc["Amortization", 2024]) + 50.0
    )
    assert ds.loc["    of which: interest", 2024] == pytest.approx(
        (30.0 - 15.0)  # existing service − principal
        + 2.0  # local interest
        + float(book.new_debt_service().loc["Interest", 2024])
        + 50.0 * 0.10  # prior ST × rate
    )


def test_external_debt_book_summary_rows() -> None:
    book = ExternalDebtBook(portfolio=_tiny_portfolio(), inputs=_synthetic_inputs())
    summary = book.summary()
    for label in (
        "PV of existing MLT debt",
        "PV of existing arrears",
        "PV of new MLT debt",
        "Total ST external debt",
        "    of which: locally-issued ST",
        "PV of net use of SDRs",
        "Total PV of debt",
        "Nominal value of new MLT",
        "Nominal PPG debt check",
        "Total public debt service",
        "    of which: principal",
        "    of which: interest",
        "Locally-issued MLT stock",
        "Locally-issued principal",
        "Locally-issued interest",
    ):
        assert label in summary.index


def test_load_external_debt_inputs_from_workbook() -> None:
    inputs = load_external_debt_inputs(WORKBOOK)
    assert 2024 in inputs.years
    assert "IMF" in inputs.existing_debt_service.index
    assert "Eurobond" in inputs.existing_debt_service.index
    assert inputs.existing_discount_rates["IMF"] == pytest.approx(0.05)
    assert float(inputs.existing_debt_service.loc["IMF"].sum()) > 0.0
    assert float(inputs.existing_principal.sum()) > 0.0
    assert float(inputs.short_term_external.loc[2023]) == pytest.approx(150.0)
    assert float(inputs.macro_mlt_external.loc[2023]) > 0.0
    assert float(inputs.locally_issued_debt_stock.loc[2024]) > 0.0
    assert float(inputs.locally_issued_principal.loc[2024]) > 0.0
    assert float(inputs.fx_pa.loc[2024]) > 0.0
    assert inputs.short_term_interest_rate == pytest.approx(0.10)


def _ext_values(row: int, years: tuple[int, ...]) -> dict[int, float | None]:
    from fastpyxl import load_workbook

    workbook = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        worksheet = workbook["Ext_Debt_Data"]
        year_to_col: dict[int, int] = {}
        for col in range(5, 70):
            year = worksheet.cell(9, col).value
            if isinstance(year, (int, float)) and int(year) in years:
                year_to_col[int(year)] = col
        out: dict[int, float | None] = {}
        for year in years:
            col = year_to_col.get(year)
            if col is None:
                out[year] = None
                continue
            raw = worksheet.cell(row, col).value
            out[year] = None if raw is None else float(raw)
    finally:
        workbook.close()
    return out


def test_workbook_parity_existing_and_headlines() -> None:
    inputs = load_external_debt_inputs(WORKBOOK)
    pv_base = load_instruments_from_workbook(WORKBOOK)
    lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
    portfolio = PVPortfolio(tuple(pv_base) + tuple(lc_nr))
    book = ExternalDebtBook(portfolio=portfolio, inputs=inputs)

    years = (2024, 2025, 2026)
    existing_total = book.existing_mlt_pv().loc["Total"]
    sheet_existing = _ext_values(242, years)
    sheet_new_pv = _ext_values(279, years)
    sheet_total_pv = _ext_values(391, years)
    sheet_ppg = _ext_values(393, years)

    for year in years:
        assert sheet_existing[year] is not None
        assert existing_total.loc[year] == pytest.approx(
            sheet_existing[year], rel=1e-9, abs=1e-6
        )
        assert book.new_mlt_pv().loc[year] == pytest.approx(
            sheet_new_pv[year], rel=1e-9, abs=1e-4
        )
        assert book.total_pv_of_debt().loc[year] == pytest.approx(
            sheet_total_pv[year], rel=1e-9, abs=1e-4
        )
        assert book.nominal_ppg_check().loc[year] == pytest.approx(
            sheet_ppg[year], rel=1e-9, abs=1e-4
        )


def test_workbook_parity_local_debt_and_public_ds() -> None:
    inputs = load_external_debt_inputs(WORKBOOK)
    pv_base = load_instruments_from_workbook(WORKBOOK)
    lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
    book = ExternalDebtBook(
        portfolio=PVPortfolio(tuple(pv_base) + tuple(lc_nr)),
        inputs=inputs,
    )
    years = (2024, 2025, 2026)
    sheet_stock = _ext_values(58, years)
    sheet_prin = _ext_values(56, years)
    sheet_st = _ext_values(386, years)
    sheet_ds = _ext_values(394, years)
    sheet_ds_prin = _ext_values(395, years)
    sheet_ds_int = _ext_values(396, years)
    ds = book.total_public_debt_service()

    for year in years:
        assert inputs.locally_issued_debt_stock.loc[year] == pytest.approx(
            sheet_stock[year], rel=1e-9, abs=1e-6
        )
        assert inputs.locally_issued_principal.loc[year] == pytest.approx(
            sheet_prin[year], rel=1e-9, abs=1e-6
        )
        assert book.total_st_external().loc[year] == pytest.approx(
            sheet_st[year], rel=1e-9, abs=1e-6
        )
        assert ds.loc["Total public debt service", year] == pytest.approx(
            sheet_ds[year], rel=1e-9, abs=1e-4
        )
        assert ds.loc["    of which: principal", year] == pytest.approx(
            sheet_ds_prin[year], rel=1e-9, abs=1e-4
        )
        assert ds.loc["    of which: interest", year] == pytest.approx(
            sheet_ds_int[year], rel=1e-9, abs=1e-4
        )
