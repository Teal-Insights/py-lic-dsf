"""Prior-vintage loader from Excel ``Imported data``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook


@dataclass(frozen=True, slots=True)
class VintageSeries:
    """One imported vintage series keyed as ``country.series.vintage``.

    Attributes:
        key: Excel key (e.g. ``652.NGDPD.2019-03-07.A``).
        series_code: Short code (e.g. ``NGDPD``).
        vintage_year: Vintage year label (e.g. 2019).
        vintage_date: Issue date string when present.
        values: Year → value map.
    """

    key: str
    series_code: str
    vintage_year: int | str
    vintage_date: str | None
    values: pd.Series


@dataclass(frozen=True, slots=True)
class ImportedDataCatalog:
    """Catalog of imported DSA vintage series.

    Attributes:
        country: Country name.
        country_code: IFS country code.
        current_vintage_year: Current DSA vintage year.
        latest_vintage_id: Latest vintage id string.
        prior_5y_vintage_id: Vintage id from five years ago.
        series: Map of series key → `VintageSeries`.
    """

    country: str
    country_code: int
    current_vintage_year: int
    latest_vintage_id: str
    prior_5y_vintage_id: str
    series: dict[str, VintageSeries]

    def get(self, series_code: str, vintage_year: int | str) -> VintageSeries | None:
        """Look up a series by code and vintage year label."""
        for item in self.series.values():
            if item.series_code == series_code and item.vintage_year == vintage_year:
                return item
        return None

    def by_code(self, series_code: str) -> list[VintageSeries]:
        """Return all vintages for a series code."""
        return [s for s in self.series.values() if s.series_code == series_code]


def load_imported_data(path: str | Path) -> ImportedDataCatalog:
    """Load ``Imported data`` vintage series from a LIC-DSF workbook.

    Parses country metadata and rows whose column D looks like
    ``{code}.{SERIES}.{date}.A`` (or the shorter Realism-linked keys).

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        Catalog of vintage series.
    """
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
