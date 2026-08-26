"""Load Input 6 tailored-test flags and A2 customized-scenario spec."""

from __future__ import annotations

from pathlib import Path

from fastpyxl import load_workbook

from lic_dsf.load._cells import _prefer_user, _tailored_applicability
from lic_dsf.scenario.customized import CustomizedScenarioSpec
from lic_dsf.stress.tailored import TailoredParams

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


def load_customized_public_spec(path: str | Path) -> CustomizedScenarioSpec | None:
    """Load A2 public spec when Customized Scenario - public C3 is Yes."""
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[_CUSTOMIZED_PUBLIC_SHEET]
        on = str(ws.cell(3, 3).value or "").strip().lower() == "yes"
        if not on:
            return None
        title = str(ws.cell(7, 2).value or "Custom").strip()
        return CustomizedScenarioSpec(name=title, short_name="A2")
    finally:
        wb.close()
