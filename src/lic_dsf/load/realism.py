"""Load realism assumptions from the LIC-DSF workbook template."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.realism.fiscal_adjustment import DEFAULT_LIC_PROGRAM_DISTRIBUTION
from lic_dsf.realism.types import (
    CapitalAssumptions,
    LicProgramDistribution,
    MultiplierAssumptions,
)


def load_multiplier_grid(
    path: str | Path,
) -> list[MultiplierAssumptions]:
    """Load Realism 2 multiplier grid (``m`` columns with shared ``p``).

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        List of `MultiplierAssumptions` for each ``m`` column.
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Realism 2 - Fiscal multiplier"]
        out: list[MultiplierAssumptions] = []
        for c in range(4, 9):
            m = ws.cell(15, c).value
            p = ws.cell(16, c).value
            if isinstance(m, (int, float)) and isinstance(p, (int, float)):
                out.append(MultiplierAssumptions(m=float(m), persistence=float(p)))
        return out
    finally:
        wb.close()


def load_capital_assumptions(path: str | Path) -> CapitalAssumptions:
    """Load Realism 3 FAD capital stock assumptions.

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        `CapitalAssumptions` (initial ``G/Y`` left at default; pass via
        fixture when a vintage capital stock is available).
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Realism 3 - Invest-Growth"]
        d = float(ws.cell(10, 3).value)
        phi = float(ws.cell(11, 3).value)
        beta = float(ws.cell(14, 3).value)
        initial_gy_raw = ws.cell(70, 3).value
        initial_gy = float(initial_gy_raw) if initial_gy_raw is not None else 0.5
        return CapitalAssumptions(
            depreciation=d,
            efficiency=phi,
            beta=beta,
            initial_capital_to_gdp=initial_gy,
        )
    finally:
        wb.close()


def load_lic_program_distribution(
    path: str | Path | None = None,
) -> LicProgramDistribution:
    """Load the LIC program histogram (embedded default; path optional).

    The histogram is fixed in the template; when ``path`` is given the
    frequencies are re-read for parity checks.

    Args:
        path: Optional workbook path. When ``None``, returns the embedded
            default distribution.

    Returns:
        `LicProgramDistribution`.
    """
    if path is None:
        return DEFAULT_LIC_PROGRAM_DISTRIBUTION

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Realism 4 - Fiscal adjustment"]
        bins: list[float | str] = []
        freqs: list[float] = []
        pcts: list[float] = []
        cum: list[float] = []
        # R23–R50 categories (skip R22 sentinel -99 / freq 0).
        for r in range(23, 51):
            b = ws.cell(r, 1).value
            f = ws.cell(r, 2).value
            p = ws.cell(r, 4).value
            c = ws.cell(r, 5).value
            if f is None:
                continue
            if b is None and r == 23:
                bins.append(-4.5)  # open left display edge
            elif isinstance(b, str):
                bins.append(b)
            elif isinstance(b, (int, float)):
                bins.append(float(b))
            else:
                continue
            freqs.append(float(f))
            pcts.append(float(p) if isinstance(p, (int, float)) else 0.0)
            cum.append(float(c) if isinstance(c, (int, float)) else 0.0)
        return LicProgramDistribution(
            bins=tuple(bins),
            frequencies=tuple(freqs),
            percent_of_sample=tuple(pcts),
            cumulative_percent=tuple(cum),
        )
    finally:
        wb.close()


def load_imported_data(path: str | Path) -> ImportedDataCatalog:
    """Load ``Imported data`` vintage series from a LIC-DSF workbook.

    Parses country metadata and rows whose column D looks like
    ``{code}.{SERIES}.{date}.A`` (or the shorter Realism-linked keys).

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        Catalog of vintage series.
    """
    from lic_dsf.realism.imported import ImportedDataCatalog, VintageSeries

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Imported data"]
        country = str(ws.cell(2, 4).value or "")
        country_code = int(ws.cell(3, 4).value)
        current_vintage_year = int(ws.cell(5, 4).value)
        latest_vintage_id = str(ws.cell(6, 3).value or "")
        prior_5y_vintage_id = str(ws.cell(7, 3).value or "")

        # Year header row (template: row 10, years from col J / 10 onward).
        year_cols: dict[int, int] = {}
        for r in range(1, min(ws.max_row or 50, 40)):
            cols: dict[int, int] = {}
            for c in range(8, min((ws.max_column or 48) + 1, 50)):
                v = ws.cell(r, c).value
                if isinstance(v, (int, float)) and 1990 <= int(v) <= 2100:
                    cols[int(v)] = c
            if len(cols) >= 4:
                year_cols = cols
                break
        if not year_cols:
            year_cols = {2017 + i: 10 + i for i in range(15)}

        series: dict[str, VintageSeries] = {}
        for r in range(1, (ws.max_row or 0) + 1):
            key = ws.cell(r, 4).value
            code = ws.cell(r, 3).value
            vint = ws.cell(r, 2).value
            if not isinstance(key, str) or "." not in key:
                continue
            if not isinstance(code, str):
                continue
            values: dict[int, float] = {}
            for year, col in year_cols.items():
                cell = ws.cell(r, col).value
                if isinstance(cell, (int, float)):
                    values[year] = float(cell)
            if not values:
                continue
            vintage_date = None
            parts = key.split(".")
            if len(parts) >= 3:
                vintage_date = parts[2]
            series[key] = VintageSeries(
                key=key,
                series_code=code,
                vintage_year=vint if vint is not None else parts[0],
                vintage_date=vintage_date,
                values=pd.Series(values, dtype=float),
            )

        return ImportedDataCatalog(
            country=country,
            country_code=country_code,
            current_vintage_year=current_vintage_year,
            latest_vintage_id=latest_vintage_id,
            prior_5y_vintage_id=prior_5y_vintage_id,
            series=series,
        )
    finally:
        wb.close()
