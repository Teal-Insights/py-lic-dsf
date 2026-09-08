"""Tests for ``lic_dsf.realism`` (Realism 1–4 / Output 4 panels)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.dsa import BaselinePublicBook
from lic_dsf.load import (
    load_capital_assumptions,
    load_external_debt_inputs,
    load_imported_data,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_lic_program_distribution,
    load_macro_debt_inputs,
    load_multiplier_grid,
)
from lic_dsf.output import (
    fiscal_adjustment_panel,
    fiscal_multiplier_panel,
    forecast_error_panel,
    invest_growth_panel,
)
from lic_dsf.pv import ExternalDebtBook, MacroDebtBook, PVPortfolio
from lic_dsf.realism import (
    CapitalAssumptions,
    MultiplierAssumptions,
    cumulative_multiplier_impact,
    debt_creating_flow_panel,
    debt_stock_from_ratio,
    fiscal_adjustment_from_primary_balance,
    forecast_error,
    gdp_rebase_scale,
    other_identified_flows_to_gdp,
    place_in_lic_histogram,
    projected_three_year_adjustment,
    public_automatic_debt_dynamics,
    rebase_ratio_to_outturn_gdp,
    three_year_fiscal_adjustment,
    total_external_to_gdp,
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

    from lic_dsf.output import realism4_sheet_table
    from lic_dsf.realism.compare_realism4 import build_realism4_comparison
    from tests.parity.equality import ABS_TOL

    macro, external = _workbook_books()
    pub = BaselinePublicBook(macro=macro, external=external)
    pd_pct = pub.primary_deficit_to_gdp()

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        base = wb["Baseline - public"]
        year_cols = {
            int(base.cell(7, c).value): c
            for c in range(4, 40)
            if isinstance(base.cell(7, c).value, (int, float))
        }
        for year in range(2021, 2036):
            excel = float(base.cell(23, year_cols[year]).value)
            assert float(pd_pct.loc[year]) == pytest.approx(excel, abs=ABS_TOL)

        r4 = wb["Realism 4 - Fiscal adjustment"]
        r4_years = {
            int(r4.cell(8, c).value): c
            for c in range(6, 25)
            if isinstance(r4.cell(8, c).value, (int, float))
        }
        assert max(r4_years) == 2035
        adj = three_year_fiscal_adjustment(pd_pct)
        for year, col in r4_years.items():
            excel_adj = r4.cell(10, col).value
            if not isinstance(excel_adj, (int, float)):
                continue
            assert float(adj.loc[year]) == pytest.approx(float(excel_adj), abs=ABS_TOL)

        first_proj = macro.inputs.first_projection_year
        projected = projected_three_year_adjustment(pd_pct, first_proj)
        assert projected == pytest.approx(float(r4.cell(14, 4).value), abs=ABS_TOL)
        placement = place_in_lic_histogram(projected)
        assert placement.category == int(r4.cell(14, 6).value)
        assert placement.bin_edge == pytest.approx(float(r4.cell(14, 5).value), abs=ABS_TOL)
        assert placement.percent_of_sample == pytest.approx(
            float(r4.cell(14, 7).value), abs=ABS_TOL
        )
    finally:
        wb.close()

    panel = fiscal_adjustment_panel(pd_pct, first_proj)
    assert "percent_of_sample" in panel.columns
    assert panel.attrs["placement"].adjustment == pytest.approx(projected)

    frame = build_realism4_comparison(WORKBOOK)
    assert int(frame["missing_sut"].sum()) == 0
    assert bool(frame["passed"].all())
    table = realism4_sheet_table(WORKBOOK)
    assert 2035 in table.columns
    assert float(table.loc["3-yr Fiscal adjustment", 2035]) == pytest.approx(
        float(adj.loc[2035]), abs=ABS_TOL
    )


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


def test_constant_rebase_scale_uses_first_year() -> None:
    old = pd.Series({2020: 10.0, 2021: 12.0, 2022: 15.0, 2023: 18.0})
    new = pd.Series({2020: 20.0, 2021: 22.0, 2022: 24.0, 2023: 26.0})
    scale = gdp_rebase_scale(old, new, mode="constant")
    assert float(scale.loc[2020]) == pytest.approx(0.5)
    assert float(scale.loc[2023]) == pytest.approx(0.5)
    ratio = pd.Series({2020: 40.0, 2021: 50.0, 2022: 60.0, 2023: 70.0})
    rebased = rebase_ratio_to_outturn_gdp(old, new, ratio)
    assert float(rebased.loc[2021]) == pytest.approx(25.0)


def test_last_vintage_rebase_scale_varies_then_freezes() -> None:
    old = pd.Series({2020: 10.0, 2021: 12.0, 2022: 20.0, 2023: 30.0, 2024: 40.0})
    new = pd.Series({2020: 20.0, 2021: 15.0, 2022: 10.0, 2023: 10.0, 2024: 10.0})
    scale = gdp_rebase_scale(old, new, mode="last_vintage", first_projection_year=2024)
    assert float(scale.loc[2020]) == pytest.approx(0.5)
    assert float(scale.loc[2021]) == pytest.approx(0.8)
    assert float(scale.loc[2022]) == pytest.approx(2.0)
    assert float(scale.loc[2023]) == pytest.approx(2.0)
    assert float(scale.loc[2024]) == pytest.approx(2.0)
    ratio = pd.Series({2020: 10.0, 2021: 10.0, 2022: 10.0, 2023: 10.0, 2024: 10.0})
    rebased = rebase_ratio_to_outturn_gdp(
        old, new, ratio, mode="last_vintage", first_projection_year=2024
    )
    assert float(rebased.loc[2021]) == pytest.approx(8.0)
    assert float(rebased.loc[2024]) == pytest.approx(20.0)


def test_total_external_to_gdp_adds_private_usd_share() -> None:
    d_ppg = pd.Series({2024: 50.0})
    private = pd.Series({2024: 8.0})
    gdp_usd = pd.Series({2024: 200.0})
    d_gdp = total_external_to_gdp(d_ppg, private, gdp_usd)
    assert float(d_gdp.loc[2024]) == pytest.approx(54.0)


def test_leftover_residual_subtracts_automatic_dynamics() -> None:
    change = pd.Series({2020: 0.0, 2021: 10.0})
    primary = pd.Series({2020: 0.0, 2021: 3.0})
    other = pd.Series({2020: 0.0, 2021: 1.0})
    real_i = pd.Series({2020: 0.0, 2021: 2.0})
    real_g = pd.Series({2020: 0.0, 2021: -4.0})
    fx = pd.Series({2020: 0.0, 2021: 5.0})
    panel = debt_creating_flow_panel(
        change,
        primary,
        other,
        real_interest=real_i,
        real_gdp_growth=real_g,
        real_exchange_rate=fx,
    )
    # 10 - 3 - 1 - 2 - (-4) - 5 = 3
    assert float(panel.loc["Residual / GDP", 2021]) == pytest.approx(3.0)


def test_public_automatic_debt_dynamics_uses_baseline_identities() -> None:
    du = pd.Series({2020: 50.0, 2021: 55.0})
    d_fc = pd.Series({2020: 20.0, 2021: 22.0})
    g = pd.Series({2020: 3.0, 2021: 4.0})
    pi = pd.Series({2020: 8.0, 2021: 10.0})
    pi_us = pd.Series({2020: 1.0, 2021: 2.0})
    fx_eop = pd.Series({2020: 2.0, 2021: 2.2})
    i_ext = pd.Series({2020: 4.0, 2021: 5.0})
    i_dom = pd.Series({2020: 11.0, 2021: 12.0})
    panel = public_automatic_debt_dynamics(
        public_debt_to_gdp=du,
        fc_debt_to_gdp=d_fc,
        real_gdp_growth=g,
        gdp_deflator_growth=pi,
        us_deflator_growth=pi_us,
        fx_eop=fx_eop,
        interest_rate_external=i_ext,
        interest_rate_domestic=i_dom,
    )
    den = 1.04
    r_dom = (12.0 - 10.0) / 1.10
    r_ext = (5.0 - 2.0) / 1.02
    r_avg = 0.4 * r_ext + 0.6 * r_dom
    assert float(panel.loc["DUCIR_GDP", 2021]) == pytest.approx(
        r_avg / 100.0 * 50.0 / den
    )
    assert float(panel.loc["DUCGDPR_GDP", 2021]) == pytest.approx(-0.04 * 50.0 / den)
    real_dep = (100.0 + 10.0) * 1.02 / 1.10 - 100.0
    assert float(panel.loc["DUCER_GDP", 2021]) == pytest.approx(
        real_dep / 100.0 * 20.0 * (1.0 + r_ext / 100.0) / den
    )


def test_other_identified_flows_to_gdp_net_of_relief() -> None:
    gdp = pd.Series({2021: 200.0})
    of = other_identified_flows_to_gdp(
        contingent=pd.Series({2021: 10.0}),
        other=pd.Series({2021: 5.0}),
        privatization=pd.Series({2021: 4.0}),
        debt_relief=pd.Series({2021: 1.0}),
        gdp_lcu=gdp,
    )
    assert float(of.loc[2021]) == pytest.approx(5.0)


def test_debt_stock_from_ratio_uses_same_vintage_gdp() -> None:
    ratio = pd.Series({2029: 34.0})
    gdp = pd.Series({2029: 100.0})
    stock = debt_stock_from_ratio(ratio, gdp)
    assert float(stock.loc[2029]) == pytest.approx(34.0)


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
