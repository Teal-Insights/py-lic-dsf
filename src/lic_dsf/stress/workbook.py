"""Load Input 6 standard stress parameters from the LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.stress.types import Input6StandardParams, ThresholdRule

if TYPE_CHECKING:
    from lic_dsf.stress.scenario import CachedStressExternalBook

_SHEET = "Input 6(optional)-Standard Test"


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _prefer_user(default: Any, user: Any) -> float:
    """Return user column when numeric, else default."""
    user_n = _as_float(user)
    if user_n is not None:
        return user_n
    default_n = _as_float(default)
    if default_n is None:
        raise ValueError(f"expected numeric Input 6 cell, got {default!r}/{user!r}")
    return default_n


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


_ADD_COST_SHEET = "PV_Base-add.cost.mkt"


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


_TAILORED_SHEET = "Input 6 - Tailored Tests"
_CUSTOMIZED_EXTERNAL_SHEET = "Customized Scenario-External"

_RATIO_METHODS = (
    "pv_ppg_external_to_gdp",
    "pv_ppg_external_to_exports",
    "ppg_debt_service_to_exports",
    "ppg_debt_service_to_revenue",
)

_CACHED_SHEETS: dict[str, tuple[str, tuple[int, int, int, int], str]] = {
    "A2_Custom": (
        _CUSTOMIZED_EXTERNAL_SHEET,
        (82, 83, 86, 87),
        "A2_Custom",
    ),
    "C1_CombinedCL": (
        "C1_Combined CL",
        (101, 102, 103, 104),
        "C1_CombinedCL",
    ),
    "C3_Commodity": (
        "C3_Commodity prices_ext",
        (35, 36, 39, 40),
        "C3_Commodity",
    ),
    "C4_Market": (
        "C4_Market_financing",
        (82, 83, 96, 99),
        "C4_Market",
    ),
}


def _year_columns(ws: Any, *, scan_rows: range = range(6, 10)) -> dict[int, int]:
    """Map projection year → column on a B-sheet-style stress tab."""
    for row in scan_rows:
        cols: dict[int, int] = {}
        for col in range(3, 45):
            value = ws.cell(row, col).value
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                year = int(value)
                if 1900 < year < 2200:
                    cols[year] = col
        if cols:
            return cols
    return {}


def _read_ratio_series(
    ws: Any,
    row: int,
    year_cols: dict[int, int],
) -> pd.Series:
    return pd.Series(
        {
            year: float(ws.cell(row, col).value)
            for year, col in year_cols.items()
            if isinstance(ws.cell(row, col).value, (int, float))
            and not isinstance(ws.cell(row, col).value, bool)
        },
        dtype=float,
    )


def _tailored_applicability(ws: Any) -> dict[str, bool]:
    """Read tailored-test On/Off flags from Input 6 - Tailored Tests."""
    flags: dict[str, bool] = {}
    for row, key in ((9, "C2_NaturalDisaster"), (10, "C3_Commodity"), (11, "C4_Market")):
        raw = ws.cell(row, 3).value
        flags[key] = str(raw or "").strip().lower() == "yes"
    return flags


def load_cached_external_stress(
    path: str | Path,
) -> dict[str, CachedStressExternalBook]:
    """Load A2 / tailored C* external ratios from Excel stress sheets.

    Full Python runners for these scenarios are not implemented yet; this loader
    reads the materialized B-sheet ratios so Output 3-1 tables can include A2
    and C1/C3/C4 (and skips C2/C3/C4 when Input 6 marks them inapplicable).

    Args:
        path: Path to a LIC-DSF workbook.

    Returns:
        Scenario id → cached ratio book.
    """
    from lic_dsf.stress.scenario import CachedStressExternalBook

    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        tailored_flags = _tailored_applicability(workbook[_TAILORED_SHEET])
        customized_on = (
            str(workbook[_CUSTOMIZED_EXTERNAL_SHEET].cell(3, 4).value or "")
            .strip()
            .lower()
            == "yes"
        )
        books: dict[str, CachedStressExternalBook] = {}
        for key, (sheet_name, rows, scenario_id) in _CACHED_SHEETS.items():
            if key == "A2_Custom" and not customized_on:
                continue
            if key == "C3_Commodity" and not tailored_flags["C3_Commodity"]:
                continue
            if key == "C4_Market" and not tailored_flags["C4_Market"]:
                continue
            if sheet_name not in workbook.sheetnames:
                continue
            ws = workbook[sheet_name]
            year_cols = _year_columns(ws)
            if not year_cols:
                continue
            series = {
                method: _read_ratio_series(ws, row, year_cols)
                for method, row in zip(_RATIO_METHODS, rows, strict=True)
            }
            books[key] = CachedStressExternalBook(
                scenario_id=scenario_id,  # type: ignore[arg-type]
                _pv_ppg_external_to_gdp=series["pv_ppg_external_to_gdp"],
                _pv_ppg_external_to_exports=series["pv_ppg_external_to_exports"],
                _ppg_debt_service_to_exports=series["ppg_debt_service_to_exports"],
                _ppg_debt_service_to_revenue=series["ppg_debt_service_to_revenue"],
            )
        return books
    finally:
        workbook.close()
