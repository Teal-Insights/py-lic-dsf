"""Baseline - external sustainability ratios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.book import MacroDebtBook


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


@dataclass(slots=True)
class BaselineExternalBook:
    """External DSA baseline ratios (Excel ``Baseline - external``).

    Consumes ``MacroDebtBook`` denominators and ``ExternalDebtBook`` PPG PV /
    service. Year horizon follows Macro.
    """

    macro: MacroDebtBook
    external: ExternalDebtBook

    @property
    def years(self) -> tuple[int, ...]:
        """Projection / history years from Macro."""
        return self.macro.inputs.years

    def pv_ppg_usd(self) -> pd.Series:
        """PPG external PV in USD (Ext R391 / Baseline R50)."""
        return _align(self.external.total_pv_of_debt(), self.years)

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """Baseline R35: ``100 × PV / GDP``, clamped at 0."""
        return _clamp_nonnegative(_pct(self.pv_ppg_usd(), self.macro.gdp_usd()))

    def exports_to_gdp(self) -> pd.Series:
        """Baseline R19: exports / GDP × 100."""
        return _pct(self.macro.exports(), self.macro.gdp_usd())

    def revenues_to_gdp(self) -> pd.Series:
        """Baseline R60: Macro R98 = revenues excl. grants / GDP × 100."""
        return _pct(self.macro.revenues_excl_grants(), self.macro.gdp_usd())

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """Baseline R36: ``R35 / R19 × 100`` (= ``100 × PV / exports``)."""
        return (self.pv_ppg_external_to_gdp() / self.exports_to_gdp() * 100.0).astype(
            float
        )

    def pv_ppg_external_to_revenue(self) -> pd.Series:
        """Baseline R37: ``R35 / R60 × 100``."""
        return (self.pv_ppg_external_to_gdp() / self.revenues_to_gdp() * 100.0).astype(
            float
        )

    def total_external_debt_service_to_exports(self) -> pd.Series:
        """Baseline R38: ``100 × (prior priv ST + ext interest + ext amort) / exports``."""
        prior_priv_st = pd.Series(
            self.macro.private_st_external().shift(1), dtype=float
        ).fillna(0.0)
        numer = (
            prior_priv_st
            + self.macro.external_interest()
            + self.macro.external_amortization()
        )
        return _pct(numer, self.macro.exports())

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """Baseline R39: ``max(0, R38 − private DS/exports)``."""
        return _clamp_nonnegative(
            self.total_external_debt_service_to_exports()
            - self.macro.private_debt_service_to_exports()
        )

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """Baseline R40: ``max(0, R39 × exports / revenues_excl_grants)``."""
        # R39 is already a percent; Excel does (R39 * exports) / R95
        # = PPG_DS/exports*100 * exports / rev = 100 * PPG_DS / rev.
        raw = (
            self.ppg_debt_service_to_exports()
            * self.macro.exports()
            / self.macro.revenues_excl_grants().replace(0.0, pd.NA)
        )
        return _clamp_nonnegative(
            raw.replace([float("inf"), float("-inf")], pd.NA).astype(float)
        )

    def external_gfn_usd(self) -> pd.Series:
        """Baseline R41: Macro R74."""
        return self.macro.external_gfn()
