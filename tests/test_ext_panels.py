"""Tests for Ext existing-service, evolution, and memorandum panels."""

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

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_book() -> ExternalDebtBook:
    years = (2023, 2024, 2025)
    service = pd.DataFrame(
        {
            2023: [10.0, 20.0],
            2024: [12.0, 18.0],
            2025: [8.0, 16.0],
        },
        index=["IMF", "Eurobond"],
    )
    zero = _zero(years)
    inputs = ExternalDebtInputs(
        years=years,
        existing_debt_service=service,
        existing_principal=pd.Series(
            {2023: 15.0, 2024: 20.0, 2025: 10.0}, dtype=float
        ),
        existing_discount_rates={"IMF": 0.05, "Eurobond": 0.05},
        arrears=pd.Series({2023: 0.0, 2024: 5.0, 2025: 0.0}, dtype=float),
        short_term_external=zero.copy(),
        sdr_pv=zero.copy(),
        sdr_interest=zero.copy(),
        macro_ppg_external=zero.copy(),
        macro_mlt_external=pd.Series(
            {2023: 1100.0, 2024: 1200.0, 2025: 1300.0}, dtype=float
        ),
        fx_eop=pd.Series({2023: 4.0, 2024: 5.0, 2025: 5.0}, dtype=float),
        fx_pa=pd.Series({2023: 4.0, 2024: 4.5, 2025: 5.0}, dtype=float),
        locally_issued_debt_stock=pd.Series(
            {2023: 100.0, 2024: 80.0, 2025: 60.0}, dtype=float
        ),
        locally_issued_principal=pd.Series(
            {2023: 5.0, 2024: 6.0, 2025: 7.0}, dtype=float
        ),
        locally_issued_interest=pd.Series(
            {2023: 2.0, 2024: 3.0, 2025: 4.0}, dtype=float
        ),
        locally_issued_st=zero.copy(),
        locally_issued_st_principal=zero.copy(),
        locally_issued_st_interest=zero.copy(),
        domestic_mlt_disbursements_usd=zero.copy(),
        domestic_st_disbursements_usd=zero.copy(),
        short_term_interest_rate=0.0,
        residual_interest_rates={},
        grant_element_weight_names=frozenset(),
    )
    instrument = PresentValueInstrument(
        name="IMF",
        grace=1,
        maturity=3,
        interest_rate=0.0,
        discount_rate=0.05,
        disbursements=[0.0, 100.0, 0.0],
        years=years,
    )
    return ExternalDebtBook(
        portfolio=PVPortfolio(instruments=(instrument,)),
        inputs=inputs,
    )


def test_existing_service_and_evolution_synthetic() -> None:
    book = _synthetic_book()
    service = book.existing_debt_service()
    assert service.loc["Total", 2024] == pytest.approx(30.0)
    assert "IMF" in service.index

    totals = book.existing_service_totals()
    assert totals.loc["Existing external debt service", 2024] == pytest.approx(30.0)
    assert totals.loc["    Existing principal", 2024] == pytest.approx(20.0)
    assert totals.loc["    Existing interest", 2024] == pytest.approx(10.0)
    assert totals.loc["Locally-issued debt service", 2024] == pytest.approx(9.0)
    assert totals.loc["Total existing + local service", 2024] == pytest.approx(39.0)

    evo = book.debt_evolution()
    existing = book.existing_mlt_nominal()
    local = book.inputs.locally_issued_debt_stock
    assert evo.loc["Existing MLT (incl. local adj.)", 2024] == pytest.approx(
        float(existing.loc[2024])
    )
    assert evo.loc["Locally-issued", 2024] == pytest.approx(float(local.loc[2024]))
    assert evo.loc["Existing external (excl. local)", 2024] == pytest.approx(
        float(existing.loc[2024] - local.loc[2024])
    )

    memo = book.memorandum()
    assert memo.loc["External debt outstanding", 2024] == pytest.approx(
        float(book.new_mlt_nominal().loc[2024])
        + 5.0
        + float(existing.loc[2024])
    )
    assert memo.loc["Exchange rate (eop)", 2024] == pytest.approx(5.0)
    assert memo.loc["Exchange rate (pa)", 2024] == pytest.approx(4.5)


@pytest.mark.skipif(not WORKBOOK.is_file(), reason="template workbook missing")
def test_workbook_parity_panels() -> None:
    instruments = load_instruments_from_workbook(
        WORKBOOK, include_zero_disbursement=True
    )
    lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
    book = ExternalDebtBook(
        portfolio=PVPortfolio(tuple(instruments) + tuple(lc_nr)),
        inputs=load_external_debt_inputs(WORKBOOK),
    )
    totals = book.existing_service_totals()
    evo = book.debt_evolution()
    memo = book.memorandum()

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ext = wb["Ext_Debt_Data"]
        col = 6  # 2024
        assert totals.loc["Existing external debt service", 2024] == pytest.approx(
            float(ext.cell(42, col).value), abs=1e-6
        )
        assert totals.loc["    Existing principal", 2024] == pytest.approx(
            float(ext.cell(43, col).value), abs=1e-6
        )
        assert totals.loc["Locally-issued debt service", 2024] == pytest.approx(
            float(ext.cell(55, col).value), abs=1e-6
        )
        assert totals.loc["    Locally-issued principal", 2024] == pytest.approx(
            float(ext.cell(56, col).value), abs=1e-6
        )
        assert evo.loc["Existing external (excl. local)", 2024] == pytest.approx(
            float(ext.cell(45, col).value), abs=1e-6
        )
        assert evo.loc["Locally-issued", 2024] == pytest.approx(
            float(ext.cell(58, col).value), abs=1e-6
        )
        assert evo.loc["Existing MLT (incl. local adj.)", 2024] == pytest.approx(
            float(ext.cell(67, col).value), abs=1e-6
        )
        assert memo.loc["External debt outstanding", 2024] == pytest.approx(
            float(ext.cell(398, col).value), abs=1e-6
        )
        assert memo.loc["Exchange rate (eop)", 2024] == pytest.approx(
            float(ext.cell(402, col).value), abs=1e-9
        )
        assert memo.loc["Exchange rate (pa)", 2024] == pytest.approx(
            float(ext.cell(403, col).value), abs=1e-9
        )
    finally:
        wb.close()
