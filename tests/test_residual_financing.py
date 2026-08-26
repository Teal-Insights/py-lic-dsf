"""Tests for Input 7-style residual financing defaults and overrides."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastpyxl import load_workbook

from lic_dsf.load import (
    load_external_debt_inputs,
    load_input7_residual_params,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)
from lic_dsf.pv import (
    ExternalDebtBook,
    ExternalDebtInputs,
    PresentValueInstrument,
    PVPortfolio,
    ResidualFinancingOverrides,
    ResidualFinancingParams,
    calculate_residual_defaults,
    resolve_residual_params,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _synthetic_book() -> ExternalDebtBook:
    """Known disbursements + terms → exact residual shares/terms."""
    years = (2023, 2024, 2025, 2026)
    instrument = PresentValueInstrument(
        name="LoanA",
        grace=2,
        maturity=6,
        interest_rate=0.10,
        discount_rate=0.05,
        disbursements=[0.0, 100.0, 50.0, 0.0],
        years=years,
    )
    portfolio = PVPortfolio(instruments=(instrument,))
    zero = _zero(years)
    inputs = ExternalDebtInputs(
        years=years,
        existing_debt_service=pd.DataFrame({y: [0.0] for y in years}, index=["IMF"]),
        existing_principal=zero.copy(),
        existing_discount_rates={"IMF": 0.05},
        arrears=zero.copy(),
        short_term_external=pd.Series(
            {2023: 0.0, 2024: 10.0, 2025: 0.0, 2026: 0.0}, dtype=float
        ),
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
        domestic_mlt_disbursements_usd=pd.Series(
            {2023: 0.0, 2024: 40.0, 2025: 30.0, 2026: 20.0}, dtype=float
        ),
        domestic_st_disbursements_usd=pd.Series(
            {2023: 0.0, 2024: 50.0, 2025: 20.0, 2026: 10.0}, dtype=float
        ),
        short_term_interest_rate=0.0,
        residual_interest_rates={},
        grant_element_weight_names=frozenset(),
    )
    return ExternalDebtBook(portfolio=portfolio, inputs=inputs)


def test_calculate_residual_defaults_synthetic_shares_and_terms() -> None:
    book = _synthetic_book()
    # Skip 2023 (current); average first 2 projection years 2024–2025.
    params = calculate_residual_defaults(book, average_years=2)

    # 2024: ext=100, st=10, dom_mlt=40, dom_st=50 → total=200
    # shares: 0.5, 0.2, 0.25
    # 2025: ext=50, st=0, dom_mlt=30, dom_st=20 → total=100
    # shares: 0.5, 0.3, 0.2
    assert params.external_mlt_share == pytest.approx(0.5)
    assert params.domestic_mlt_share == pytest.approx(0.25)
    assert params.domestic_st_share == pytest.approx(0.225)
    # Interest always 10% → 10.0 percent; grace 2; maturity 6
    assert params.avg_interest_rate == pytest.approx(10.0)
    assert params.avg_grace == pytest.approx(2.0)
    assert params.avg_maturity == pytest.approx(6.0)
    assert params.avg_grace_rounded == 2
    assert params.avg_maturity_rounded == 6


def test_resolve_residual_params_override_interest_only() -> None:
    defaults = ResidualFinancingParams(
        external_mlt_share=0.4,
        domestic_mlt_share=0.3,
        domestic_st_share=0.3,
        avg_interest_rate=8.0,
        avg_grace=4.0,
        avg_maturity=9.0,
        avg_grace_rounded=4,
        avg_maturity_rounded=9,
    )
    resolved = resolve_residual_params(
        defaults,
        ResidualFinancingOverrides(avg_interest_rate=5.0),
    )
    assert resolved.avg_interest_rate == pytest.approx(5.0)
    assert resolved.external_mlt_share == pytest.approx(0.4)
    assert resolved.domestic_mlt_share == pytest.approx(0.3)
    assert resolved.domestic_st_share == pytest.approx(0.3)


def test_resolve_residual_params_partial_share_renormalizes_st() -> None:
    defaults = ResidualFinancingParams(
        external_mlt_share=0.4,
        domestic_mlt_share=0.3,
        domestic_st_share=0.25,
        avg_interest_rate=8.0,
        avg_grace=4.0,
        avg_maturity=9.0,
        avg_grace_rounded=4,
        avg_maturity_rounded=9,
    )
    resolved = resolve_residual_params(
        defaults,
        ResidualFinancingOverrides(
            external_mlt_share=0.5,
            domestic_mlt_share=0.2,
        ),
    )
    assert resolved.external_mlt_share == pytest.approx(0.5)
    assert resolved.domestic_mlt_share == pytest.approx(0.2)
    assert resolved.domestic_st_share == pytest.approx(0.3)


def test_book_residual_params_delegates() -> None:
    book = _synthetic_book()
    defaults = book.residual_defaults(average_years=2)
    resolved = book.residual_params(
        ResidualFinancingOverrides(avg_grace=3.0),
        average_years=2,
    )
    assert resolved.avg_grace == pytest.approx(3.0)
    assert resolved.avg_grace_rounded == 3
    assert resolved.external_mlt_share == pytest.approx(defaults.external_mlt_share)


@pytest.mark.skipif(not WORKBOOK.is_file(), reason="template workbook missing")
def test_workbook_parity_residual_defaults_vs_ext_c_cells() -> None:
    instruments = load_instruments_from_workbook(
        WORKBOOK, include_zero_disbursement=True
    )
    lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
    portfolio = PVPortfolio(tuple(instruments) + tuple(lc_nr))
    inputs = load_external_debt_inputs(WORKBOOK)
    book = ExternalDebtBook(portfolio=portfolio, inputs=inputs)

    params = calculate_residual_defaults(book, average_years=11)

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ext = wb["Ext_Debt_Data"]
        assert params.external_mlt_share == pytest.approx(
            float(ext.cell(126, 3).value), abs=1e-9
        )
        assert params.domestic_mlt_share == pytest.approx(
            float(ext.cell(127, 3).value), abs=1e-9
        )
        assert params.domestic_st_share == pytest.approx(
            float(ext.cell(128, 3).value), abs=1e-9
        )
        assert params.avg_interest_rate == pytest.approx(
            float(ext.cell(131, 3).value), abs=1e-9
        )
        assert params.avg_grace_rounded == int(ext.cell(132, 3).value)
        assert params.avg_maturity_rounded == int(ext.cell(133, 3).value)
    finally:
        wb.close()


@pytest.mark.skipif(not WORKBOOK.is_file(), reason="template workbook missing")
def test_load_input7_residual_params_workbook() -> None:
    params = load_input7_residual_params(WORKBOOK)
    assert params.external_mlt_share == pytest.approx(0.4343925896763784)
    assert params.domestic_mlt_share == pytest.approx(0.2275655436226405)
    assert params.domestic_st_share == pytest.approx(0.33804186670098113, rel=1e-6)
    assert params.avg_interest_rate == pytest.approx(7.982399291786421)
    assert params.discount_rate == pytest.approx(0.05)
    assert params.avg_maturity_rounded == 9
    assert params.avg_grace_rounded == 4
    assert params.domestic_mlt_real_rate == pytest.approx(0.029220917972601)
    assert params.domestic_mlt_maturity == 3
    assert params.domestic_mlt_grace == 2
    assert params.domestic_st_real_rate == pytest.approx(0.03472169156537851)


def test_resolve_overrides_domestic_fields() -> None:
    defaults = ResidualFinancingParams(
        external_mlt_share=0.4,
        domestic_mlt_share=0.3,
        domestic_st_share=0.3,
        avg_interest_rate=8.0,
        avg_grace=4.0,
        avg_maturity=9.0,
        avg_grace_rounded=4,
        avg_maturity_rounded=9,
        domestic_mlt_real_rate=0.02,
        domestic_st_real_rate=0.03,
        discount_rate=0.05,
    )
    resolved = resolve_residual_params(
        defaults,
        ResidualFinancingOverrides(
            domestic_mlt_real_rate=0.05,
            discount_rate=0.04,
        ),
    )
    assert resolved.domestic_mlt_real_rate == pytest.approx(0.05)
    assert resolved.discount_rate == pytest.approx(0.04)
    assert resolved.domestic_st_real_rate == pytest.approx(0.03)
