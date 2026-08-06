"""LIC-DSF Present Value instrument library (PV_Base-style unit loan + output)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lic_dsf.pv import (
    PresentValueInstrument,
    PVPortfolio,
    load_instruments_from_workbook,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


# MULTI1 terms from PV_Base (workbook cached values).
MULTI1 = dict(
    name="MULTI1",
    grace=5,
    maturity=30,
    interest_rate=0.0075,
    discount_rate=0.05,
)


def _year_values(frame, row: str):
    return frame.loc[row].drop(labels=["Term"], errors="ignore")


def test_internal_returns_dataframe_matching_multi1() -> None:
    """Internal block is a unit loan of 100 (grant-element / PV schedule)."""
    pv = PresentValueInstrument(
        **MULTI1,
        disbursements=[0.0] * 15,
        horizon=15,
    )
    internal = pv.internal()

    assert list(internal.index)[0] == "MULTI1"
    assert "Term" in internal.columns
    amort = _year_values(internal, f"Discount {pv.name} / Amortization")
    stock = _year_values(internal, f"Interest {pv.name} / Debt stock")
    interest = _year_values(internal, "Interest")
    service = _year_values(internal, "Total debt service")
    unit_pv = _year_values(internal, "PV of debt")
    grant = _year_values(internal, "Grant element")

    assert amort.iloc[:7].tolist() == pytest.approx([0, 0, 0, 0, 0, 0, 4])
    assert stock.iloc[:7].tolist() == pytest.approx([100, 100, 100, 100, 100, 100, 96])
    assert interest.iloc[0] == pytest.approx(0.0)
    assert interest.iloc[1] == pytest.approx(0.75)
    assert service.iloc[1] == pytest.approx(0.75)
    assert service.iloc[6] == pytest.approx(4.75)
    assert unit_pv.iloc[0] == pytest.approx(52.54611281125682, rel=1e-9)
    assert grant.iloc[0] == pytest.approx(47.45388718874318, rel=1e-9)


def test_external_scales_unit_pv_by_disbursement() -> None:
    """Output PV scales unit PV/100 by new borrowing when interest < discount."""
    pv = PresentValueInstrument(
        name="demo",
        grace=5,
        maturity=30,
        interest_rate=0.0075,
        discount_rate=0.05,
        disbursements=[200.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        horizon=7,
    )
    external = pv.external()
    internal = pv.internal()
    unit_pv0 = float(_year_values(internal, "PV of debt").iloc[0])

    assert external.loc["New forex borrowing (gross, USD)"].iloc[0] == pytest.approx(
        200.0
    )
    assert external.loc["cumulative"].iloc[0] == pytest.approx(200.0)
    assert external.loc["cumulative"].iloc[2] == pytest.approx(200.0)
    assert external.loc[f"PV of debt   {pv.name}"].iloc[0] == pytest.approx(
        200.0 * unit_pv0 / 100.0
    )


def test_external_stock_and_service_track_disbursements() -> None:
    pv = PresentValueInstrument(
        name="short",
        grace=1,
        maturity=3,
        interest_rate=0.10,
        discount_rate=0.05,
        disbursements=[100.0, 0.0, 0.0, 0.0, 0.0],
    )
    external = pv.external()
    borrowing = external.loc["New forex borrowing (gross, USD)"]
    amort = external.loc["Amortization"]
    stock = external.loc["Stock of new forex debt (in USD)"]

    assert borrowing.iloc[0] == pytest.approx(100.0)
    assert amort.sum() == pytest.approx(100.0)
    assert stock.iloc[-1] == pytest.approx(0.0, abs=1e-9)
    assert all(float(x) >= -1e-9 for x in stock)


def test_rejects_invalid_terms() -> None:
    with pytest.raises(ValueError, match="maturity"):
        PresentValueInstrument(
            name="bad",
            grace=5,
            maturity=5,
            interest_rate=0.01,
            discount_rate=0.05,
            disbursements=[0.0],
        )


def test_interest_ge_discount_uses_stock_as_unit_pv() -> None:
    """When interest >= discount, unit PV row equals debt stock (LIC-DSF IF)."""
    pv = PresentValueInstrument(
        name="mkt",
        grace=1,
        maturity=5,
        interest_rate=0.08,
        discount_rate=0.05,
        disbursements=[50.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    )
    internal = pv.internal()
    unit_pv = _year_values(internal, "PV of debt")
    stock = _year_values(internal, f"Interest {pv.name} / Debt stock")
    grant = _year_values(internal, "Grant element")
    assert unit_pv.iloc[0] == pytest.approx(float(stock.iloc[0]))
    assert grant.iloc[0] == pytest.approx(0.0)


def test_load_instruments_from_workbook_loads_eurobond_terms() -> None:
    """Input 4 Eurobond terms + disbursements become a PresentValueInstrument."""
    instruments = load_instruments_from_workbook(WORKBOOK)
    by_name = {i.name: i for i in instruments}
    assert "Eurobond" in by_name
    eurobond = by_name["Eurobond"]
    assert eurobond.grace == 9
    assert eurobond.maturity == 12
    assert eurobond.interest_rate == pytest.approx(0.09)
    assert eurobond.discount_rate == pytest.approx(0.05)
    assert eurobond.years is not None
    assert eurobond.years[0] == 2024
    assert eurobond.disbursements[3] == pytest.approx(250.0)
    assert sum(eurobond.disbursements) == pytest.approx(6388.888888888889)


def test_load_instruments_skips_incomplete_terms() -> None:
    """PC2–PC5 have empty grace/maturity in this template and cannot be built."""
    instruments = load_instruments_from_workbook(
        WORKBOOK,
        include_zero_disbursement=True,
    )
    names = {i.name for i in instruments}
    assert "PC2" not in names
    assert "Export Credit Agencies" in names
    assert "MULTI1" in names


def test_load_instruments_include_zero_disbursement_filter() -> None:
    all_instruments = load_instruments_from_workbook(
        WORKBOOK,
        include_zero_disbursement=True,
    )
    nonzero = load_instruments_from_workbook(
        WORKBOOK,
        include_zero_disbursement=False,
    )
    assert len(all_instruments) > len(nonzero)
    assert all(sum(i.disbursements) != 0 for i in nonzero)
    assert any(sum(i.disbursements) == 0 for i in all_instruments)


def test_load_instruments_disambiguates_duplicate_fx_bond_names() -> None:
    instruments = load_instruments_from_workbook(
        WORKBOOK,
        include_zero_disbursement=True,
    )
    names = [i.name for i in instruments]
    fx = [n for n in names if n.startswith("Bonds (1 to 3 years)-FX")]
    assert len(fx) == 2
    assert len(set(fx)) == 2


def _two_instrument_portfolio() -> PVPortfolio:
    years = (2024, 2025, 2026, 2027)
    a = PresentValueInstrument(
        name="A",
        grace=1,
        maturity=3,
        interest_rate=0.10,
        discount_rate=0.05,
        disbursements=[100.0, 0.0, 0.0, 0.0],
        years=years,
    )
    b = PresentValueInstrument(
        name="B",
        grace=1,
        maturity=3,
        interest_rate=0.10,
        discount_rate=0.05,
        disbursements=[50.0, 0.0, 0.0, 0.0],
        years=years,
    )
    return PVPortfolio(instruments=(a, b))


def test_pv_portfolio_get_and_external() -> None:
    portfolio = _two_instrument_portfolio()
    assert portfolio.get("A").name == "A"
    assert portfolio.external("A").loc["Interest", 2025] == pytest.approx(10.0)
    with pytest.raises(KeyError, match="missing"):
        portfolio.get("missing")


def test_pv_portfolio_aggregate_external_sums_outputs() -> None:
    portfolio = _two_instrument_portfolio()
    totals = portfolio.aggregate_external()
    assert "PV of debt" in totals.index
    assert "PV of debt   A" not in totals.index
    assert totals.loc["Interest", 2025] == pytest.approx(15.0)
    assert totals.loc["New forex borrowing (gross, USD)", 2024] == pytest.approx(
        150.0
    )


def test_pv_portfolio_interest_and_new_debt_service() -> None:
    portfolio = _two_instrument_portfolio()
    interest = portfolio.interest()
    assert list(interest.index) == ["A", "B"]
    assert interest.loc["A", 2025] == pytest.approx(10.0)
    assert interest.loc["B", 2025] == pytest.approx(5.0)

    service = portfolio.new_debt_service()
    assert service.loc["Interest", 2025] == pytest.approx(15.0)
    assert service.loc["Amortization", 2025] == pytest.approx(
        float(portfolio.amortization().sum(axis=0).loc[2025])
    )
    assert service.loc["Total new debt service", 2025] == pytest.approx(
        float(service.loc["Interest", 2025] + service.loc["Amortization", 2025])
    )


def test_pv_portfolio_from_workbook_eurobond_interest() -> None:
    instruments = load_instruments_from_workbook(
        WORKBOOK,
        include_zero_disbursement=False,
    )
    portfolio = PVPortfolio(tuple(instruments))
    interest = portfolio.interest()
    assert "Eurobond" in interest.index
    assert float(interest.loc["Eurobond"].sum()) > 0.0
    totals = portfolio.aggregate_external()
    assert totals.loc["Interest"].sum() == pytest.approx(interest.sum().sum())
