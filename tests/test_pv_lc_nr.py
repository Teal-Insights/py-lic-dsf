"""Tests for local-currency non-resident (PV_LC_NR) instruments."""

from __future__ import annotations

from pathlib import Path

import pytest

from lic_dsf.load import load_lc_nr_instruments_from_workbook
from lic_dsf.pv import LocalCurrencyNonResidentInstrument

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def test_lc_nr_flat_fx_single_vintage_amortizes_after_grace() -> None:
    """One LC disbursement; flat FX; grace=1, maturity=2 → amort in year index 2."""
    instrument = LocalCurrencyNonResidentInstrument(
        name="demo",
        grace=1,
        maturity=2,
        discount_rate=0.05,
        interest_rates=[0.10, 0.10, 0.10],
        disbursements_lc=[100.0, 0.0, 0.0],
        fx_pa=[5.0, 5.0, 5.0],
        fx_eop=[5.0, 5.0, 5.0],
        years=(2024, 2025, 2026),
    )
    external = instrument.external()
    assert external.loc["Stock of new forex debt (in USD)", 2024] == pytest.approx(20.0)
    assert external.loc["Interest", 2024] == pytest.approx(0.0)
    assert external.loc["Interest", 2025] == pytest.approx(100.0 * 0.10 / 5.0)
    assert external.loc["Amortization", 2025] == pytest.approx(0.0)
    assert external.loc["Amortization", 2026] == pytest.approx(100.0 / 5.0)
    assert external.loc["Stock of new forex debt (in USD)", 2026] == pytest.approx(
        0.0, abs=1e-9
    )


def test_lc_nr_fx_pa_and_eop_differ() -> None:
    instrument = LocalCurrencyNonResidentInstrument(
        name="fx",
        grace=1,
        maturity=2,
        discount_rate=0.05,
        interest_rates=[0.10, 0.10, 0.10],
        disbursements_lc=[100.0, 0.0, 0.0],
        fx_pa=[4.0, 5.0, 5.0],
        fx_eop=[5.0, 5.0, 5.0],
        years=(2024, 2025, 2026),
    )
    external = instrument.external()
    # Stock uses eop; interest uses pa on prior LC stock.
    assert external.loc["Stock of new forex debt (in USD)", 2024] == pytest.approx(
        100.0 / 5.0
    )
    assert external.loc["Interest", 2025] == pytest.approx(100.0 * 0.10 / 5.0)


def test_lc_nr_multi_vintage_sums_cohorts() -> None:
    instrument = LocalCurrencyNonResidentInstrument(
        name="multi",
        grace=1,
        maturity=2,
        discount_rate=0.05,
        interest_rates=[0.10, 0.10, 0.10, 0.10],
        disbursements_lc=[100.0, 50.0, 0.0, 0.0],
        fx_pa=[5.0, 5.0, 5.0, 5.0],
        fx_eop=[5.0, 5.0, 5.0, 5.0],
        years=(2024, 2025, 2026, 2027),
    )
    external = instrument.external()
    # Year-0 stock = only first vintage.
    assert external.loc["Stock of new forex debt (in USD)", 2024] == pytest.approx(20.0)
    # Year-1 stock = first vintage still outstanding + second vintage.
    assert external.loc["Stock of new forex debt (in USD)", 2025] == pytest.approx(
        20.0 + 10.0
    )


def test_lc_nr_rejects_invalid_terms() -> None:
    with pytest.raises(ValueError, match="maturity"):
        LocalCurrencyNonResidentInstrument(
            name="bad",
            grace=2,
            maturity=2,
            discount_rate=0.05,
            interest_rates=[0.1],
            disbursements_lc=[1.0],
            fx_pa=[1.0],
            fx_eop=[1.0],
        )


def _read_pv_lc_nr_panel(
    sheet_name: str,
) -> tuple[
    str,
    int,
    int,
    float,
    list[int],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
]:
    from fastpyxl import load_workbook

    workbook = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        worksheet = workbook[sheet_name]
        years: list[int] = []
        fx_pa: list[float] = []
        fx_eop: list[float] = []
        disbursements: list[float] = []
        rates: list[float] = []
        stock: list[float] = []
        pv: list[float] = []
        interest: list[float] = []
        amort: list[float] = []
        col = 4
        while worksheet.cell(3, col).value is not None and col < 60:
            fx_pa_raw = worksheet.cell(4, col).value
            fx_eop_raw = worksheet.cell(5, col).value
            if fx_pa_raw in (None, 0) or fx_eop_raw in (None, 0):
                break
            years.append(int(worksheet.cell(3, col).value))
            fx_pa.append(float(fx_pa_raw))
            fx_eop.append(float(fx_eop_raw))
            disbursements.append(float(worksheet.cell(6, col).value or 0))
            rates.append(float(worksheet.cell(7, col).value or 0))
            stock.append(float(worksheet.cell(14, col).value or 0))
            pv.append(float(worksheet.cell(15, col).value or 0))
            interest.append(float(worksheet.cell(17, col).value or 0))
            amort.append(float(worksheet.cell(18, col).value or 0))
            col += 1
        name = str(worksheet.cell(3, 1).value)
        grace = int(worksheet.cell(16, 2).value)
        maturity = int(worksheet.cell(17, 2).value)
        discount = float(worksheet.cell(19, 2).value)
    finally:
        workbook.close()
    return (
        name,
        grace,
        maturity,
        discount,
        years,
        rates,
        disbursements,
        fx_pa,
        fx_eop,
        stock,
        pv,
        interest,
        amort,
    )


@pytest.mark.parametrize(
    ("sheet_name", "expected_grace", "expected_maturity"),
    [
        ("PV_LC_NR1", 1, 2),
        ("PV_LC_NR2", 3, 5),
        ("PV_LC_NR3", 6, 7),
    ],
)
def test_lc_nr_parity_with_workbook_summary(
    sheet_name: str, expected_grace: int, expected_maturity: int
) -> None:
    (
        name,
        grace,
        maturity,
        discount,
        years,
        rates,
        disbursements,
        fx_pa,
        fx_eop,
        sheet_stock,
        sheet_pv,
        sheet_interest,
        sheet_amort,
    ) = _read_pv_lc_nr_panel(sheet_name)
    assert grace == expected_grace
    assert maturity == expected_maturity
    instrument = LocalCurrencyNonResidentInstrument(
        name=name,
        grace=grace,
        maturity=maturity,
        discount_rate=discount,
        interest_rates=rates,
        disbursements_lc=disbursements,
        fx_pa=fx_pa,
        fx_eop=fx_eop,
        years=years,
    )
    external = instrument.external()
    for i, year in enumerate(years):
        assert external.loc["Stock of new forex debt (in USD)", year] == pytest.approx(
            sheet_stock[i], rel=1e-9, abs=1e-7
        )
        assert external.loc["PV of debt", year] == pytest.approx(
            sheet_pv[i], rel=1e-9, abs=1e-7
        )
        assert external.loc["Interest", year] == pytest.approx(
            sheet_interest[i], rel=1e-9, abs=1e-7
        )
        assert external.loc["Amortization", year] == pytest.approx(
            sheet_amort[i], rel=1e-9, abs=1e-7
        )


def test_load_lc_nr_instruments_from_workbook() -> None:
    instruments = load_lc_nr_instruments_from_workbook(WORKBOOK)
    assert len(instruments) == 3
    by_name = {i.name: i for i in instruments}
    assert "Bonds (1 to 3 years)-LC" in by_name
    assert "Bonds (4 to 7 years)-LC" in by_name
    assert "Bonds (beyond 7 years)-LC" in by_name
    short = by_name["Bonds (1 to 3 years)-LC"]
    assert short.grace == 1
    assert short.maturity == 2
    assert short.years is not None and short.years[0] == 2024
    # Loader inputs follow Input 5 / Macro through 2044; instrument extends
    # runoff years so outer Macro PV still matches Ext / PV_LC_NR.
    external = short.external()
    assert float(
        external.loc["Stock of new forex debt (in USD)", 2024]
    ) == pytest.approx(323.9889846960328, rel=1e-9)
    assert float(external.loc["Interest", 2025]) == pytest.approx(
        46.58143394668185, rel=1e-9
    )


def test_lc_nr_runoff_keeps_pv_when_stock_outstanding() -> None:
    """Last Macro year must still see future TDS after disbursements end."""
    instrument = LocalCurrencyNonResidentInstrument(
        name="long",
        grace=6,
        maturity=7,
        discount_rate=0.05,
        interest_rates=[0.10] * 5,
        disbursements_lc=[100.0, 0.0, 0.0, 0.0, 0.0],
        fx_pa=[5.0] * 5,
        fx_eop=[5.0] * 5,
        years=(2024, 2025, 2026, 2027, 2028),
    )
    external = instrument.external()
    assert 2028 in external.columns
    assert 2028 + 7 in external.columns  # maturity runoff past input years
    stock_2028 = float(external.loc["Stock of new forex debt (in USD)", 2028])
    pv_2028 = float(external.loc["PV of debt", 2028])
    assert stock_2028 > 0.0
    assert pv_2028 == pytest.approx(stock_2028, rel=1e-9, abs=1e-9)


def test_loaded_lc_nr_pv_matches_ext_through_macro_end() -> None:
    """Input-5/Macro-truncated load must still match Ext LC PV at outer Macro years."""
    from fastpyxl import load_workbook

    from lic_dsf.load import load_external_debt_inputs, load_instruments_from_workbook
    from lic_dsf.pv import ExternalDebtBook, PVPortfolio

    workbook = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ws = workbook["Ext_Debt_Data"]
        year_to_col = {
            int(ws.cell(1, col).value): col
            for col in range(1, 80)
            if isinstance(ws.cell(1, col).value, (int, float))
            and 1990 <= float(ws.cell(1, col).value) <= 2100
        }
        excel_lc = {
            year: float(ws.cell(314, year_to_col[year]).value)
            for year in (2037, 2038, 2044)
        }
        excel_new = {
            year: float(ws.cell(279, year_to_col[year]).value)
            for year in (2037, 2038, 2044)
        }
    finally:
        workbook.close()

    instruments = load_instruments_from_workbook(
        WORKBOOK, include_zero_disbursement=True
    )
    lc_nr = load_lc_nr_instruments_from_workbook(
        WORKBOOK, include_zero_disbursement=True
    )
    book = ExternalDebtBook(
        portfolio=PVPortfolio(instruments=tuple(instruments) + tuple(lc_nr)),
        inputs=load_external_debt_inputs(WORKBOOK),
    )
    pv = book.portfolio.pv()
    lc_names = [
        "Bonds (1 to 3 years)-LC",
        "Bonds (4 to 7 years)-LC",
        "Bonds (beyond 7 years)-LC",
    ]
    for year in (2037, 2038, 2044):
        py_lc = float(pv.loc[lc_names, year].sum())
        assert py_lc == pytest.approx(excel_lc[year], rel=1e-9, abs=1e-4)
        assert float(book.new_mlt_pv().loc[year]) == pytest.approx(
            excel_new[year], rel=1e-9, abs=1e-4
        )
