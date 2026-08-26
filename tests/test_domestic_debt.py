"""Tests for Dom_Debt_Data indicators and Dom_Debt_Indicators panels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.load import load_domestic_debt_inputs
from lic_dsf.pv import DomesticDebtBook, DomesticDebtInputs

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

PEER_MEDIAN_DEBT_GDP = 17.1
PEER_MEDIAN_DS_REV = 21.7


def _synthetic_inputs() -> DomesticDebtInputs:
    years = (2020, 2021, 2022, 2023)
    return DomesticDebtInputs(
        years=years,
        first_projection_year=2022,
        public_sector_debt_pct_gdp=pd.Series(
            {2020: 50.0, 2021: 55.0, 2022: 60.0, 2023: 58.0}, dtype=float
        ),
        ppg_external_debt_pct_gdp=pd.Series(
            {2020: 30.0, 2021: 32.0, 2022: 35.0, 2023: 40.0}, dtype=float
        ),
        public_ds_to_revenue_grants=pd.Series(
            {2020: 40.0, 2021: 42.0, 2022: 45.0, 2023: 50.0}, dtype=float
        ),
        ppg_ds_to_revenue=pd.Series(
            {2020: 10.0, 2021: 12.0, 2022: 15.0, 2023: 20.0}, dtype=float
        ),
        revenues_incl_grants=pd.Series(
            {2020: 100.0, 2021: 110.0, 2022: 120.0, 2023: 130.0}, dtype=float
        ),
        grants=pd.Series({2020: 10.0, 2021: 10.0, 2022: 20.0, 2023: 30.0}, dtype=float),
        domestic_debt_stock=pd.Series(
            {2020: 200.0, 2021: 250.0, 2022: 300.0, 2023: 280.0}, dtype=float
        ),
        domestic_interest_due=pd.Series(
            {2020: 5.0, 2021: 6.0, 2022: 7.0, 2023: 8.0}, dtype=float
        ),
        gdp_usd=pd.Series(
            {2020: 1000.0, 2021: 1100.0, 2022: 1200.0, 2023: 1300.0}, dtype=float
        ),
        fx_pa=pd.Series({2020: 2.0, 2021: 2.0, 2022: 2.5, 2023: 2.5}, dtype=float),
        fx_denominated_domestic_stock=pd.Series(0.0, index=list(years), dtype=float),
        fx_denominated_domestic_interest=pd.Series(0.0, index=list(years), dtype=float),
        peer_median_debt_to_gdp=PEER_MEDIAN_DEBT_GDP,
        peer_median_ds_to_revenues=PEER_MEDIAN_DS_REV,
        residual_domestic_mlt_share=0.2,
        residual_domestic_st_share=0.3,
        domestic_mlt_avg_interest=0.03,
        domestic_mlt_avg_maturity=5.0,
        domestic_mlt_avg_grace=2.0,
        domestic_st_avg_interest=0.04,
    )


def test_domestic_debt_to_gdp_clamps_negative() -> None:
    book = DomesticDebtBook(inputs=_synthetic_inputs())
    series = book.domestic_debt_to_gdp()
    assert series.loc[2020] == pytest.approx(20.0)
    assert series.loc[2021] == pytest.approx(23.0)
    assert series.loc[2023] == pytest.approx(18.0)


def test_domestic_ds_to_revenues_matches_excel_identity() -> None:
    book = DomesticDebtBook(inputs=_synthetic_inputs())
    series = book.domestic_ds_to_revenues()
    # 2020: 40 - 10 * (100-10)/100 = 40 - 9 = 31
    assert series.loc[2020] == pytest.approx(31.0)
    # 2022: 45 - 15 * (120-20)/120 = 45 - 12.5 = 32.5
    assert series.loc[2022] == pytest.approx(32.5)


def test_gdp_lcu_and_net_issuance() -> None:
    book = DomesticDebtBook(inputs=_synthetic_inputs())
    gdp_lcu = book.gdp_lcu()
    assert gdp_lcu.loc[2020] == pytest.approx(2000.0)
    assert gdp_lcu.loc[2022] == pytest.approx(3000.0)

    change = book.change_in_domestic_debt()
    assert pd.isna(change.loc[2020])
    assert change.loc[2021] == pytest.approx(50.0)
    assert change.loc[2023] == pytest.approx(-20.0)

    interest_lcu = book.domestic_interest_lcu()
    assert interest_lcu.loc[2021] == pytest.approx(12.0)  # 6 * 2

    net = book.net_issuance_to_gdp()
    assert pd.isna(net.loc[2020])
    # 2021: 100 * (50 - 12 - 0) / 2200 = 100 * 38 / 2200
    assert net.loc[2021] == pytest.approx(100.0 * 38.0 / 2200.0)

    prior = book.net_issuance_to_prior_dom_debt()
    assert pd.isna(prior.loc[2020])
    # 100 * net[2021] / debt_gdp[2020] = 100 * (100*38/2200) / 20
    assert prior.loc[2021] == pytest.approx(100.0 * (100.0 * 38.0 / 2200.0) / 20.0)


def test_peer_medians_are_constant_bands() -> None:
    book = DomesticDebtBook(inputs=_synthetic_inputs())
    debt = book.peer_median_debt_to_gdp()
    ds = book.peer_median_ds_to_revenues()
    assert list(debt.values) == [PEER_MEDIAN_DEBT_GDP] * 4
    assert list(ds.values) == [PEER_MEDIAN_DS_REV] * 4


def test_summary_contains_headline_rows() -> None:
    book = DomesticDebtBook(inputs=_synthetic_inputs())
    summary = book.summary()
    assert "Domestic debt / GDP" in summary.index
    assert "Domestic debt service / Revenues incl. grants" in summary.index
    assert "Net domestic debt issuance / GDP" in summary.index


def test_chart_window_and_borrowing_assumptions() -> None:
    book = DomesticDebtBook(inputs=_synthetic_inputs())
    charts = book.indicator_charts()
    # first_proj=2022 → window 2017..2032, clipped to available years 2020..2023
    assert list(charts.columns) == [2020, 2021, 2022, 2023]
    assert "Domestic debt / GDP" in charts.index
    assert "Peer median debt / GDP" in charts.index
    assert "Domestic DS / revenues" in charts.index
    assert "Net domestic debt issuance / GDP" in charts.index

    borrowing = book.borrowing_assumptions()
    assert borrowing.loc["Medium and long-term", "share"] == pytest.approx(0.4)
    assert borrowing.loc["Short-term", "share"] == pytest.approx(0.6)
    assert borrowing.loc["Medium and long-term", "avg_interest"] == pytest.approx(0.03)
    assert borrowing.loc["Short-term", "avg_interest"] == pytest.approx(0.04)


def test_load_domestic_debt_inputs_smoke() -> None:
    inputs = load_domestic_debt_inputs(WORKBOOK)
    assert inputs.first_projection_year == 2024
    assert 2013 in inputs.years
    assert 2024 in inputs.years
    assert inputs.peer_median_debt_to_gdp == pytest.approx(PEER_MEDIAN_DEBT_GDP)
    assert inputs.peer_median_ds_to_revenues == pytest.approx(PEER_MEDIAN_DS_REV)


def _dom_cached(row: int, years: list[int]) -> pd.Series:
    from fastpyxl import load_workbook

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ws = wb["Dom_Debt_Data"]
        year_cols: dict[int, int] = {}
        col = 4
        while True:
            value = ws.cell(7, col).value
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
            pytest.skip(f"Dom_Debt_Data R{row} missing cached values for {missing}")
        return pd.Series(out, dtype=float)
    finally:
        wb.close()


@pytest.mark.parametrize(
    ("method", "row"),
    [
        ("domestic_debt_to_gdp", 10),
        ("domestic_ds_to_revenues", 16),
        ("change_in_domestic_debt", 28),
        ("gdp_lcu", 33),
        ("net_issuance_to_gdp", 25),
        ("net_issuance_to_prior_dom_debt", 34),
    ],
)
def test_dom_debt_data_parity_vs_excel(method: str, row: int) -> None:
    years = [2019, 2020, 2023, 2024, 2025]
    inputs = load_domestic_debt_inputs(WORKBOOK)
    book = DomesticDebtBook(inputs=inputs)
    got = getattr(book, method)().reindex(years)
    expected = _dom_cached(row, years)
    for year in expected.index:
        assert got.loc[year] == pytest.approx(
            float(expected.loc[year]), rel=1e-9, abs=1e-7
        ), f"{method} year {year}"


def test_peer_median_parity_vs_excel() -> None:
    inputs = load_domestic_debt_inputs(WORKBOOK)
    book = DomesticDebtBook(inputs=inputs)
    years = [2019, 2024, 2030]
    for year in years:
        assert book.peer_median_debt_to_gdp().loc[year] == pytest.approx(17.1)
        assert book.peer_median_ds_to_revenues().loc[year] == pytest.approx(21.7)


def test_borrowing_assumptions_parity_vs_input7() -> None:
    from fastpyxl import load_workbook

    inputs = load_domestic_debt_inputs(WORKBOOK)
    book = DomesticDebtBook(inputs=inputs)
    borrowing = book.borrowing_assumptions()

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        i7 = wb["Input 7 - Residual Financing"]
        h10 = float(i7.cell(10, 8).value)
        h11 = float(i7.cell(11, 8).value)
        h19 = float(i7.cell(19, 8).value)
        h20 = float(i7.cell(20, 8).value)
        h21 = float(i7.cell(21, 8).value)
        h23 = float(i7.cell(23, 8).value)
    finally:
        wb.close()

    total = h10 + h11
    assert borrowing.loc["Medium and long-term", "share"] == pytest.approx(h10 / total)
    assert borrowing.loc["Short-term", "share"] == pytest.approx(h11 / total)
    assert borrowing.loc["Medium and long-term", "avg_interest"] == pytest.approx(h19)
    assert borrowing.loc["Medium and long-term", "avg_maturity"] == pytest.approx(h20)
    assert borrowing.loc["Medium and long-term", "avg_grace"] == pytest.approx(h21)
    assert borrowing.loc["Short-term", "avg_interest"] == pytest.approx(h23)
