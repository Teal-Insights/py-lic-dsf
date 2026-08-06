"""Portfolio of ``PresentValueInstrument`` rows → new-debt aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv import PresentValueInstrument

_CANONICAL_EXTERNAL_ROWS: tuple[str, ...] = (
    "New forex borrowing (gross, USD)",
    "cumulative",
    "Stock of new forex debt (in USD)",
    "PV of debt",
    "Total debt service (in USD)",
    "Interest",
    "Amortization",
)


def _normalize_external(frame: pd.DataFrame) -> pd.DataFrame:
    """Map instrument-specific PV row labels to a canonical ``PV of debt`` row."""
    rename = {
        label: "PV of debt"
        for label in frame.index
        if isinstance(label, str) and label.startswith("PV of debt")
    }
    normalized = frame.rename(index=rename)
    missing = [row for row in _CANONICAL_EXTERNAL_ROWS if row not in normalized.index]
    if missing:
        raise KeyError(f"external() frame missing rows: {missing}")
    return normalized.loc[list(_CANONICAL_EXTERNAL_ROWS)]


@dataclass(slots=True)
class PVPortfolio:
    """Owns ``PresentValueInstrument`` instances and their Output projections.

    Stores instruments, caches each ``external()`` panel, and exposes portfolio
    operations (sums and per-instrument metric panels). Creditor grouping is
    out of scope here.
    """

    instruments: tuple[PresentValueInstrument, ...]
    _external_cache: dict[str, pd.DataFrame] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        # Accept any sequence at call sites (e.g. list from the workbook loader).
        object.__setattr__(self, "instruments", tuple(self.instruments))
        names = [instrument.name for instrument in self.instruments]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate instrument names in portfolio: {names}")

    def get(self, name: str) -> PresentValueInstrument:
        for instrument in self.instruments:
            if instrument.name == name:
                return instrument
        raise KeyError(name)

    def external(self, name: str) -> pd.DataFrame:
        """Return one instrument Output panel (cached)."""
        cached = self._external_cache.get(name)
        if cached is not None:
            return cached
        frame = self.get(name).external()
        self._external_cache[name] = frame
        return frame

    def _normalized_externals(self) -> list[pd.DataFrame]:
        return [_normalize_external(self.external(i.name)) for i in self.instruments]

    def aggregate_external(self) -> pd.DataFrame:
        """Sum Output rows across all instruments (canonical row labels)."""
        if not self.instruments:
            return pd.DataFrame(index=list(_CANONICAL_EXTERNAL_ROWS))
        frames = self._normalized_externals()
        total = frames[0].copy()
        for frame in frames[1:]:
            total = total.add(frame, fill_value=0.0)
        return total

    def _metric_panel(self, canonical_row: str) -> pd.DataFrame:
        rows: dict[str, pd.Series] = {}
        for instrument in self.instruments:
            frame = _normalize_external(self.external(instrument.name))
            rows[instrument.name] = frame.loc[canonical_row]
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).T

    def interest(self) -> pd.DataFrame:
        """Per-instrument Interest series."""
        return self._metric_panel("Interest")

    def amortization(self) -> pd.DataFrame:
        """Per-instrument Amortization series."""
        return self._metric_panel("Amortization")

    def pv(self) -> pd.DataFrame:
        """Per-instrument PV of debt series."""
        return self._metric_panel("PV of debt")

    def stock(self) -> pd.DataFrame:
        """Per-instrument nominal stock series."""
        return self._metric_panel("Stock of new forex debt (in USD)")

    def new_debt_service(self) -> pd.DataFrame:
        """Interest + Amortization portfolio totals and their sum."""
        interest_total = self.interest().sum(axis=0)
        amort_total = self.amortization().sum(axis=0)
        return pd.DataFrame(
            [
                interest_total,
                amort_total,
                interest_total + amort_total,
            ],
            index=["Interest", "Amortization", "Total new debt service"],
        )
