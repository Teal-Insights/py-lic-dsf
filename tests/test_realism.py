"""Tests for ``lic_dsf.realism`` (Realism 1–4 / Output 4 panels)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.dsa import BaselinePublicBook
from lic_dsf.pv import (
    ExternalDebtBook,
    MacroDebtBook,
    PVPortfolio,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)
from lic_dsf.realism import (
    CapitalAssumptions,
    MultiplierAssumptions,
    cumulative_multiplier_impact,
    fiscal_adjustment_from_primary_balance,
    fiscal_adjustment_panel,
    fiscal_multiplier_panel,
    forecast_error,
    forecast_error_panel,
    invest_growth_panel,
    load_capital_assumptions,
    load_imported_data,
    load_lic_program_distribution,
    load_multiplier_grid,
    place_in_lic_histogram,
    projected_three_year_adjustment,
    three_year_fiscal_adjustment,
    underlying_growth,
    unit_impulse,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"

_CACHE: tuple[MacroDebtBook, ExternalDebtBook] | None = None


def _workbook_books() -> tuple[MacroDebtBook, ExternalDebtBook]:
    global _CACHE
    if _CACHE is None:
        instruments = load_instruments_from_workbook(
            WORKBOOK, include_zero_disbursement=True
        )
        lc_nr = load_lc_nr_instruments_from_workbook(
            WORKBOOK, include_zero_disbursement=True
        )
        portfolio = PVPortfolio(instruments=tuple(instruments) + tuple(lc_nr))
        external = ExternalDebtBook(
            portfolio=portfolio, inputs=load_external_debt_inputs(WORKBOOK)
        )
        macro = MacroDebtBook(
            inputs=load_macro_debt_inputs(WORKBOOK), external=external
        )
        _CACHE = (macro, external)
    return _CACHE


def test_three_year_adjustment_synthetic() -> None:
    pd_pct = pd.Series(
        {2021: 3.0, 2022: 2.0, 2023: 1.0, 2024: 0.0, 2025: -1.0, 2026: -2.0}
    )
    adj = three_year_fiscal_adjustment(pd_pct)
    assert adj.loc[2024] == pytest.approx(3.0)
    assert adj.loc[2026] == pytest.approx(3.0)


def test_place_in_histogram_matches_template_bin() -> None:
    placement = place_in_lic_histogram(4.640069788646649)
    assert placement.category == 20
    assert placement.bin_edge == pytest.approx(4.5)
    assert placement.percent_of_sample == pytest.approx(0.4405286343612335)


def test_primary_deficit_and_realism4_parity() -> None:
    from fastpyxl import load_workbook

    macro, external = _workbook_books()
    pub = BaselinePublicBook(macro=macro, external=external)
    pd_pct = pub.primary_deficit_to_gdp()

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        base = wb["Baseline - public"]
        year_cols = {
            int(base.cell(7, c).value): c
            for c in range(4, 30)
            if isinstance(base.cell(7, c).value, (int, float))
        }
        for year in (2021, 2022, 2023, 2024, 2025, 2026):
            excel = float(base.cell(23, year_cols[year]).value)
            assert float(pd_pct.loc[year]) == pytest.approx(excel, rel=1e-6)

        r4 = wb["Realism 4 - Fiscal adjustment"]
        r4_years = {
            int(r4.cell(8, c).value): c
            for c in range(6, 15)
            if isinstance(r4.cell(8, c).value, (int, float))
        }
        adj = three_year_fiscal_adjustment(pd_pct)
        for year, col in r4_years.items():
            excel_adj = r4.cell(10, col).value
            if not isinstance(excel_adj, (int, float)):
                continue
            assert float(adj.loc[year]) == pytest.approx(float(excel_adj), rel=1e-6)

        first_proj = macro.inputs.first_projection_year
        projected = projected_three_year_adjustment(pd_pct, first_proj)
        assert projected == pytest.approx(float(r4.cell(14, 4).value), rel=1e-6)
        placement = place_in_lic_histogram(projected)
        assert placement.category == int(r4.cell(14, 6).value)
        assert placement.percent_of_sample == pytest.approx(
            float(r4.cell(14, 7).value), rel=1e-6
        )
    finally:
        wb.close()

    panel = fiscal_adjustment_panel(pd_pct, first_proj)
    assert "percent_of_sample" in panel.columns
    assert panel.attrs["placement"].adjustment == pytest.approx(projected)


def test_fiscal_multiplier_parity() -> None:
    from fastpyxl import load_workbook

    macro, _ = _workbook_books()
    pb_level = macro.primary_balance()
    gdp = macro.gdp_lcu()
    pb_pct = 100.0 * pb_level / gdp.replace(0.0, pd.NA)
    growth = macro.real_gdp_growth()
    first_proj = macro.inputs.first_projection_year

    adj = fiscal_adjustment_from_primary_balance(pb_pct)
    assumptions = MultiplierAssumptions(m=0.2, persistence=0.6)
    impact = cumulative_multiplier_impact(adj, assumptions, first_proj)
    under = underlying_growth(growth, impact, first_proj)

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        ws = wb["Realism 2 - Fiscal multiplier"]
        # R51 = 2024 impact col D (m=0.2)
        assert float(impact.loc[2024]) == pytest.approx(
            float(ws.cell(51, 4).value), rel=1e-5
        )
        assert float(impact.loc[2025]) == pytest.approx(
            float(ws.cell(52, 4).value), rel=1e-5
        )
        assert float(under.loc[2024]) == pytest.approx(
            float(ws.cell(51, 12).value), rel=1e-5
        )
        unit = unit_impulse(assumptions, range(3))
        assert unit.loc[0] == pytest.approx(-0.2)
        assert unit.loc[1] == pytest.approx(-0.12)
    finally:
        wb.close()

    panel = fiscal_multiplier_panel(pb_pct, growth, first_proj)
    assert ("impact", 0.2) in panel.columns


def test_invest_growth_panel_smoke() -> None:
    assumptions = load_capital_assumptions(WORKBOOK)
    assert assumptions.depreciation == pytest.approx(0.05)
    assert assumptions.beta == pytest.approx(0.15)
    ig = pd.Series({2023: 4.0, 2024: 3.0, 2025: 2.5})
    g = pd.Series({2023: 3.0, 2024: 5.0, 2025: 4.0})
    panel = invest_growth_panel(
        ig, g, CapitalAssumptions(depreciation=0.05, efficiency=1.0, beta=0.15)
    )
    assert "Contribution of government capital" in panel.index


def test_imported_and_forecast_error_smoke() -> None:
    catalog = load_imported_data(WORKBOOK)
    assert catalog.country_code == 652
    assert catalog.current_vintage_year == 2024
    # At least some vintage keys should load when year headers are present.
    dist = load_lic_program_distribution(WORKBOOK)
    assert len(dist.frequencies) == 28
    grid = load_multiplier_grid(WORKBOOK)
    assert len(grid) == 5
    assert grid[0].m == pytest.approx(0.2)

    current = pd.Series({2019: 40.0, 2020: 45.0, 2021: 50.0})
    prior = pd.Series({2019: 42.0, 2020: 48.0, 2021: 55.0})
    err = forecast_error(prior, current)
    assert err.loc[2020] == pytest.approx(3.0)
    panel = forecast_error_panel(current, prior)
    assert "Forecast error (prior − current)" in panel.index
