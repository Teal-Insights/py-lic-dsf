"""Load Input 6 standard stress parameters and B6 add-cost interest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.load._cells import _prefer_user
from lic_dsf.stress.types import Input6StandardParams, ThresholdRule

_SHEET = "Input 6(optional)-Standard Test"
_ADD_COST_SHEET = "PV_Base-add.cost.mkt"


def _parse_threshold(value: Any) -> ThresholdRule:
    text = str(value or "").strip().lower()
    if "historical" in text and "baseline" not in text:
        return "historical_average"
    if "baseline" in text and "whichever" not in text and "lower" not in text:
        return "baseline_projection"
    return "whichever_lower"


def load_input6_standard(path: str | Path) -> Input6StandardParams:
    """Load standard stress-test sizes from ``Input 6(optional)-Standard Test``.

    Args:
        path: Path to a LIC-DSF workbook (``.xlsx`` / ``.xlsm``).

    Returns:
        Resolved shock sizes, threshold rule, and interaction elasticities.
    """
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        if _SHEET not in workbook.sheetnames:
            raise ValueError(f"workbook missing sheet {_SHEET!r}")
        ws = workbook[_SHEET]

        interactions_raw = ws.cell(8, 3).value
        interactions_on = str(interactions_raw or "").strip().lower() == "on"

        # New setting uses column D for the B1 threshold label (D18); else C18.
        setting = str(ws.cell(4, 3).value or "").strip().lower()
        threshold_cell = (
            ws.cell(18, 4).value if setting == "new" else ws.cell(18, 3).value
        )
        if threshold_cell is None:
            threshold_cell = ws.cell(18, 3).value
        threshold_rule = _parse_threshold(threshold_cell)

        return Input6StandardParams(
            threshold_rule=threshold_rule,
            interactions_on=interactions_on,
            gdp_shock_sd=_prefer_user(ws.cell(17, 3).value, ws.cell(17, 4).value),
            inflation_elasticity=_prefer_user(
                ws.cell(17, 7).value, ws.cell(17, 8).value
            ),
            primary_balance_shock_sd=_prefer_user(
                ws.cell(21, 3).value, ws.cell(21, 4).value
            ),
            domestic_borrowing_cost_bps=_prefer_user(
                ws.cell(21, 7).value, ws.cell(21, 8).value
            ),
            exports_shock_sd=_prefer_user(ws.cell(25, 3).value, ws.cell(25, 4).value),
            exports_gdp_elasticity=_prefer_user(
                ws.cell(25, 7).value, ws.cell(25, 8).value
            ),
            transfers_shock_sd=_prefer_user(ws.cell(29, 3).value, ws.cell(29, 4).value),
            fdi_shock_sd=_prefer_user(ws.cell(32, 3).value, ws.cell(32, 4).value),
            fx_depreciation_pct=_prefer_user(
                ws.cell(38, 3).value, ws.cell(38, 4).value
            ),
            fx_passthrough=_prefer_user(ws.cell(36, 7).value, ws.cell(36, 8).value),
            net_exports_elasticity=_prefer_user(
                ws.cell(37, 7).value, ws.cell(37, 8).value
            ),
            combo_gdp_shock_sd=_prefer_user(ws.cell(41, 3).value, ws.cell(41, 4).value),
            combo_exports_shock_sd=_prefer_user(
                ws.cell(44, 3).value, ws.cell(44, 4).value
            ),
            combo_primary_balance_shock_sd=_prefer_user(
                ws.cell(47, 3).value, ws.cell(47, 4).value
            ),
            combo_transfers_shock_sd=_prefer_user(
                ws.cell(50, 3).value, ws.cell(50, 4).value
            ),
            combo_fdi_shock_sd=_prefer_user(ws.cell(53, 3).value, ws.cell(53, 4).value),
            combo_fx_depreciation_pct=_prefer_user(
                ws.cell(58, 3).value, ws.cell(58, 4).value
            ),
        )
    finally:
        workbook.close()


def load_combo_additional_borrowing_interest(
    path: str | Path,
    years: tuple[int, ...],
) -> pd.Series:
    """Load B6 combo R112 additional external interest (``PV_Base-add.cost.mkt`` R13)."""
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        if _ADD_COST_SHEET not in workbook.sheetnames:
            return pd.Series(0.0, index=list(years), dtype=float)
        ws = workbook[_ADD_COST_SHEET]
        out: dict[int, float] = {}
        for col in range(5, 40):
            year = ws.cell(2, col).value
            if year is None:
                continue
            try:
                y = int(year)
            except (TypeError, ValueError):
                continue
            val = ws.cell(13, col).value
            out[y] = float(val) if val is not None else 0.0
        return pd.Series(out, dtype=float).reindex(list(years)).fillna(0.0).astype(float)
    finally:
        workbook.close()
