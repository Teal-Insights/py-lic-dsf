"""Load Input 6 tailored-test flags and A2 customized-scenario spec."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.load._cells import _prefer_user, _tailored_applicability
from lic_dsf.scenario.customized import CustomizedScenarioSpec
from lic_dsf.stress.tailored_params import TailoredParams

_TAILORED_SHEET = "Input 6 - Tailored Tests"
_CUSTOMIZED_EXTERNAL_SHEET = "Customized Scenario-External"
_CUSTOMIZED_PUBLIC_SHEET = "Customized Scenario - public"


def _safe_prefer(default: object, user: object, fallback: float = 0.0) -> float:
    try:
        return _prefer_user(default, user)
    except ValueError:
        return fallback


def load_tailored_params(path: str | Path) -> TailoredParams:
    """Load tailored-test flags and sizes from Input 6 - Tailored Tests."""
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = workbook[_TAILORED_SHEET]
        flags = _tailored_applicability(ws)
        avg_shock = _safe_prefer(ws.cell(46, 7).value, ws.cell(46, 8).value)
        adj_share = _safe_prefer(ws.cell(30, 7).value, ws.cell(30, 8).value)
        # Excel C1 AA60: Input 2 F25 total (F21:F24 components), not a flat 10%.
        cl_pct = 10.0
        if "Input 2 - Debt Coverage" in workbook.sheetnames:
            i2 = workbook["Input 2 - Debt Coverage"]
            total = i2.cell(25, 6).value
            if total is None:
                parts = [i2.cell(r, 6).value for r in range(21, 25)]
                if any(p is not None for p in parts):
                    total = sum(float(p or 0.0) for p in parts)
            if total is not None:
                cl_pct = float(total)
        return TailoredParams(
            natural_disaster=flags["C2_NaturalDisaster"],
            commodity=flags["C3_Commodity"],
            market=flags["C4_Market"],
            disaster_shock_pct_gdp=_safe_prefer(
                ws.cell(21, 7).value, ws.cell(21, 8).value
            ),
            commodity_close_years=_safe_prefer(
                ws.cell(26, 7).value, ws.cell(26, 8).value
            ),
            commodity_adj_share=adj_share,
            commodity_avg_price_shock=avg_shock,
            market_cost_bps=_safe_prefer(ws.cell(52, 7).value, ws.cell(52, 8).value),
            market_fx_depreciation_pct=_safe_prefer(
                ws.cell(58, 7).value, ws.cell(58, 8).value
            ),
            market_maturity_cap=_safe_prefer(ws.cell(54, 7).value, ws.cell(54, 8).value),
            market_maturity_factor=_safe_prefer(
                ws.cell(55, 7).value, ws.cell(55, 8).value
            ),
            market_grace_factor=_safe_prefer(ws.cell(56, 7).value, ws.cell(56, 8).value),
            commodity_gdp_shock_ppt=_safe_prefer(
                ws.cell(26, 11).value, ws.cell(26, 12).value
            ),
            commodity_revenue_drop_ppt=_safe_prefer(
                ws.cell(27, 11).value, ws.cell(27, 12).value
            ),
            cl_shock_pct_gdp=cl_pct,
        )
    finally:
        workbook.close()


def load_customized_spec(path: str | Path) -> CustomizedScenarioSpec | None:
    """Load A2 spec when Customized Scenario-External D3 is Yes; else None."""
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[_CUSTOMIZED_EXTERNAL_SHEET]
        on = str(ws.cell(3, 4).value or "").strip().lower() == "yes"
        if not on:
            return None
        title = str(ws.cell(2, 4).value or "Custom").strip()
        return CustomizedScenarioSpec(name=title, short_name="A2")
    finally:
        wb.close()


def _custom_delta_series(ws, delta_row: int, years: list[int], first_col: int = 5):
    """Read a Customized Scenario delta row (ppt of GDP) keyed by year."""
    values = [
        float(ws.cell(delta_row, first_col + i).value or 0.0)
        for i in range(len(years))
    ]
    series = pd.Series(values, index=years, dtype=float)
    if float(series.abs().sum()) == 0.0:
        return None
    return series


def load_customized_public_spec(path: str | Path) -> CustomizedScenarioSpec | None:
    """Load A2 public spec when Customized Scenario - public C3 is Yes."""
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[_CUSTOMIZED_PUBLIC_SHEET]
        on = str(ws.cell(3, 3).value or "").strip().lower() == "yes"
        if not on:
            return None
        title = str(ws.cell(7, 2).value or "Custom").strip()
        years: list[int] = []
        col = 5
        while True:
            raw = ws.cell(7, col).value
            if raw is None:
                break
            years.append(int(raw))
            col += 1
        short = str(ws.cell(54, 2).value or "A2").strip()
        if short in {"[Short Name]", ""}:
            short = "A2"
        return CustomizedScenarioSpec(
            name=title,
            short_name=short,
            revenue_delta_pct_gdp=_custom_delta_series(ws, 11, years),
            primary_expenditure_delta_pct_gdp=_custom_delta_series(ws, 13, years),
            real_growth_delta=_custom_delta_series(ws, 20, years),
            export_delta_pct_gdp=_custom_delta_series(ws, 28, years),
        )
    finally:
        wb.close()
