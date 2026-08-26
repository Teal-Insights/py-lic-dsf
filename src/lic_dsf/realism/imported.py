"""Prior-vintage catalog types from Excel ``Imported data``."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


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
