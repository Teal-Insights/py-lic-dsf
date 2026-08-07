"""Baseline - public sustainability ratios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.book import MacroDebtBook


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


@dataclass(slots=True)
class BaselinePublicBook:
    """Public DSA baseline ratios (Excel ``Baseline - public``).

    Consumes ``MacroDebtBook`` public debt / fiscal series. ``external`` is
    retained for API symmetry with ``BaselineExternalBook`` (Macro already
    stitches Ext into PV / service when constructed with an Ext book).
    """

    macro: MacroDebtBook
    external: ExternalDebtBook

    @property
    def years(self) -> tuple[int, ...]:
        """Projection / history years from Macro."""
        return self.macro.inputs.years

    def gdp_lcu(self) -> pd.Series:
        """Baseline R52: ``GDP_USD × FX(pa)``."""
        return self.macro.gdp_lcu()

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Baseline R12: ``100 × Macro R80 / GDP_LCU``."""
        return _pct(self.macro.total_public_debt(), self.gdp_lcu())

    def ppg_external_debt_to_gdp(self) -> pd.Series:
        """Baseline R20: ``100 × Macro R81 / GDP_LCU``."""
        return _pct(self.macro.public_external_debt_lcu(), self.gdp_lcu())

    def revenues_incl_grants_to_gdp(self) -> pd.Series:
        """Baseline R24: ``100 × revenues / GDP_LCU``."""
        return _pct(self.macro.revenues_incl_grants(), self.gdp_lcu())

    def primary_deficit_to_gdp(self) -> pd.Series:
        """Baseline R23: ``100 × (primary expenditure − revenues) / GDP_LCU``.

        Sign convention matches Excel Realism 4: (+) = deficit, (−) = surplus.
        """
        return _pct(
            -self.macro.primary_balance(),
            self.gdp_lcu(),
        )

    def grants_to_gdp(self) -> pd.Series:
        """Baseline R25: ``100 × grants / GDP_LCU``."""
        return _pct(self.macro.grants(), self.gdp_lcu())

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """Baseline R42: ``100 × (Macro R92 + R82) / GDP_LCU``, clamped at 0."""
        numer = self.macro.pv_external_lcu() + self.macro.public_domestic_debt()
        return _clamp_nonnegative(_pct(numer, self.gdp_lcu()))

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """Baseline R43: ``R42 / R24 × 100``."""
        return (
            self.pv_public_debt_to_gdp() / self.revenues_incl_grants_to_gdp() * 100.0
        ).astype(float)

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Baseline R45 Dom feeder.

        ``100 × (interest_exp + prior dom ST + (dom amort + PPG amort) × FX)
        / revenues``, clamped at 0.
        """
        prior_dom_st = pd.Series(self.macro.domestic_st().shift(1), dtype=float).fillna(
            0.0
        )
        numer = (
            self.macro.interest_expenditure()
            + prior_dom_st
            + (self.macro.domestic_amortization() + self.macro.ppg_amortization())
            * self.macro.fx_pa()
        )
        return _clamp_nonnegative(_pct(numer, self.macro.revenues_incl_grants()))

    def public_gfn_to_gdp(self) -> pd.Series:
        """Baseline R47: ``100 × Macro R101 / GDP_LCU``."""
        return _pct(self.macro.public_gfn(), self.gdp_lcu())

    def public_gfn(self) -> pd.Series:
        """Macro R101 level (Baseline R48 uses / FX)."""
        return self.macro.public_gfn()
