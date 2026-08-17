"""Load Probability approach regressors from a LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.pv.macro_debt.workbook import load_macro_debt_inputs
from lic_dsf.scenario.probability import DistressCovariates

_IMPORTED = "Imported data"
_HIST_YEARS = 5
_PROJ_YEARS = 11


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def _average(series: pd.Series, years: list[int]) -> float:
    values = [
        float(series.loc[year])
        for year in years
        if year in series.index and pd.notna(series.loc[year])
    ]
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _load_cpia(path: str | Path, years: list[int]) -> pd.Series:
    """CPIA from Imported data (Probability approach ``C109:R109``).

    Excel ``IFERROR(INDEX(...), previous year)``: forward-fill gaps.
    """
    wb = load_workbook(path, data_only=True, read_only=False)
    try:
        ws = wb[_IMPORTED]
        header_row = None
        data_row = None
        year_cols: dict[int, int] = {}
        in_probability_block = False
        for row in range(1, min((ws.max_row or 1) + 1, 200)):
            label = str(ws.cell(row, 2).value or "").strip()
            if "probability approach" in label.lower():
                in_probability_block = True
                continue
            if not in_probability_block or label.upper() != "CPIA":
                continue
            years_found: dict[int, int] = {}
            for col in range(1, (ws.max_column or 1) + 1):
                year = _as_int(ws.cell(row - 1, col).value) if row > 1 else None
                if year is not None:
                    years_found[year] = col
            if len(years_found) < 4:
                continue
            data_row = row
            header_row = row - 1
            year_cols = years_found
            break
        if data_row is None or header_row is None:
            return pd.Series(dtype=float)
        values: dict[int, float] = {}
        last: float | None = None
        for year in years:
            col = year_cols.get(year)
            raw = _as_float(ws.cell(data_row, col).value) if col is not None else None
            if raw is None:
                raw = last
            if raw is not None:
                values[year] = raw
                last = raw
        return pd.Series(values, dtype=float)
    finally:
        wb.close()


def probability_window_years(first_projection_year: int) -> list[int]:
    """Excel ``C76:R76``: five history years plus eleven projection years."""
    start = first_projection_year - _HIST_YEARS
    return list(range(start, first_projection_year + _PROJ_YEARS))


def load_distress_covariates(path: str | Path) -> DistressCovariates:
    """Load Excel ``H77:H81`` period averages from Input 3 / Macro / CPIA.

    Args:
        path: LIC-DSF workbook path.

    Returns:
        Scalar covariates for the Probability approach ``NORMDIST``.
    """
    path = Path(path)
    inputs = load_macro_debt_inputs(path)
    macro = MacroDebtBook(inputs=inputs)
    years = probability_window_years(int(inputs.first_projection_year))
    gdp = inputs.gdp_usd.reindex(years).astype(float)
    imports = inputs.imports.reindex(years).astype(float)
    remittances = (
        inputs.workers_remittances.reindex(years).astype(float)
        if inputs.workers_remittances is not None
        else pd.Series(0.0, index=years, dtype=float)
    )
    reserves = (
        inputs.reserves_stock.reindex(years).astype(float)
        if inputs.reserves_stock is not None
        else pd.Series(0.0, index=years, dtype=float)
    )
    world = (
        inputs.world_real_growth.reindex(years).astype(float)
        if inputs.world_real_growth is not None
        else pd.Series(dtype=float)
    )
    world = world.replace(0.0, pd.NA)
    reserves_imports = 100.0 * reserves / imports.replace(0.0, pd.NA)
    remittances_gdp = 100.0 * remittances / gdp.replace(0.0, pd.NA)
    cpia = _load_cpia(path, years)
    growth = macro.real_gdp_growth().reindex(years).astype(float)
    return DistressCovariates(
        cpia=_average(cpia, years),
        real_gdp_growth=_average(growth, years),
        reserves_imports=_average(reserves_imports, years),
        remittances_gdp=_average(remittances_gdp, years),
        world_growth=_average(world, years),
    )
