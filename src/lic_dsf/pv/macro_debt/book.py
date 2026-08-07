"""Macro-Debt_Data book: Input 3 panel + Ext/Input 5 projection stitch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from lic_dsf.pv.macro_debt import derived as _derived
from lic_dsf.pv.macro_debt import stocks as _stocks

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.types import MacroDebtInputs


@dataclass(slots=True)
class MacroDebtBook:
    """Normalized macro + debt panel (Excel ``Macro-Debt_Data``).

    Pass-through series come from ``inputs`` (Input 3 / Input 5). Projection
    PPG external stocks and service stitch from ``external`` when provided.
    """

    inputs: MacroDebtInputs
    external: ExternalDebtBook | None = None

    # --- Pass-through -------------------------------------------------

    def gdp_usd(self) -> pd.Series:
        """Macro R56."""
        return self.inputs.gdp_usd.reindex(list(self.inputs.years)).astype(float)

    def gdp_constant(self) -> pd.Series:
        """Macro R57."""
        return self.inputs.gdp_constant.reindex(list(self.inputs.years)).astype(float)

    def fx_eop(self) -> pd.Series:
        """Macro R59."""
        return self.inputs.fx_eop.reindex(list(self.inputs.years)).astype(float)

    def fx_pa(self) -> pd.Series:
        """Macro R60."""
        return self.inputs.fx_pa.reindex(list(self.inputs.years)).astype(float)

    def revenues_incl_grants(self) -> pd.Series:
        """Macro R45."""
        return self.inputs.revenues_incl_grants.reindex(list(self.inputs.years)).astype(
            float
        )

    def grants(self) -> pd.Series:
        """Macro R46."""
        return self.inputs.grants.reindex(list(self.inputs.years)).astype(float)

    def current_account(self) -> pd.Series:
        """Macro R28."""
        return self.inputs.current_account.reindex(list(self.inputs.years)).astype(
            float
        )

    def exports(self) -> pd.Series:
        """Macro R29."""
        return self.inputs.exports.reindex(list(self.inputs.years)).astype(float)

    # --- Stocks / service stitch --------------------------------------

    def mlt_external(self) -> pd.Series:
        """Macro R9."""
        return _stocks.mlt_external(self.inputs, self.external)

    def short_term_external(self) -> pd.Series:
        """Macro R10."""
        return _stocks.short_term_external(self.inputs, self.external)

    def ppg_external(self) -> pd.Series:
        """Macro R8."""
        return _stocks.ppg_external(self.inputs, self.external)

    def domestic_debt(self) -> pd.Series:
        """Macro R14."""
        return _stocks.domestic_debt(self.inputs)

    def domestic_mlt(self) -> pd.Series:
        """Macro R15."""
        return _stocks.domestic_mlt(self.inputs)

    def domestic_st(self) -> pd.Series:
        """Macro R16."""
        return _stocks.domestic_st(self.inputs)

    def domestic_interest(self) -> pd.Series:
        """Macro R21."""
        return _stocks.domestic_interest(self.inputs)

    def domestic_amortization(self) -> pd.Series:
        """Macro R26."""
        return _stocks.domestic_amortization(self.inputs)

    def private_st_external(self) -> pd.Series:
        """Macro R13."""
        return _stocks.private_st_external(self.inputs)

    def private_interest(self) -> pd.Series:
        """Macro R20."""
        return _stocks.private_interest(self.inputs)

    def private_amortization(self) -> pd.Series:
        """Macro R25."""
        return _stocks.private_amortization(self.inputs)

    def external_interest(self) -> pd.Series:
        """Macro R18."""
        return _stocks.external_interest(self.inputs, self.external)

    def external_amortization(self) -> pd.Series:
        """Macro R23."""
        return _stocks.external_amortization(self.inputs, self.external)

    def ppg_interest(self) -> pd.Series:
        """Macro R19."""
        return _stocks.ppg_interest(self.inputs, self.external)

    def ppg_amortization(self) -> pd.Series:
        """Macro R24."""
        return _stocks.ppg_amortization(self.inputs, self.external)

    def pv_external_lcu(self) -> pd.Series:
        """Macro R92."""
        return _stocks.pv_external_lcu(self.inputs, self.external)

    def grant_element_percent(self) -> pd.Series:
        """Macro R90 (Ext R408 in projection)."""
        return _stocks.grant_element_percent(self.inputs, self.external)

    def gdp_lcu(self) -> pd.Series:
        """Nominal GDP in LCU (``gdp_usd × fx_pa``)."""
        return self.gdp_usd() * self.fx_pa()

    def revenues_excl_grants(self) -> pd.Series:
        """Macro R95: ``(revenues − grants) / FX(pa)``."""
        return (self.revenues_incl_grants() - self.grants()) / self.fx_pa().replace(
            0.0, pd.NA
        )

    def private_debt_service_to_exports(self) -> pd.Series:
        """Macro R71: private DS / exports × 100."""
        prior_st = pd.Series(self.private_st_external().shift(1), dtype=float).fillna(
            0.0
        )
        numer = self.private_amortization() + self.private_interest() + prior_st
        return (100.0 * numer / self.exports().replace(0.0, pd.NA)).astype(float)

    def interest_expenditure(self) -> pd.Series:
        """Macro R49."""
        return _derived.interest_expenditure(self.inputs, self.external)

    # --- Derived ------------------------------------------------------

    def primary_balance(self) -> pd.Series:
        """Macro R44."""
        return _derived.primary_balance(self.inputs)

    def external_gfn(self) -> pd.Series:
        """Macro R74."""
        return _derived.external_gfn(self.inputs, self.external)

    def residual_financing_gap(self) -> pd.Series:
        """Macro R77."""
        return _derived.residual_financing_gap(self.inputs, self.external)

    def total_public_debt(self) -> pd.Series:
        """Macro R80."""
        return _derived.total_public_debt(self.inputs, self.external)

    def public_external_debt_lcu(self) -> pd.Series:
        """Macro R81."""
        return _derived.public_external_debt_lcu(self.inputs, self.external)

    def public_domestic_debt(self) -> pd.Series:
        """Macro R82."""
        return _derived.public_domestic_debt(self.inputs)

    def public_gfn(self) -> pd.Series:
        """Macro R101."""
        return _derived.public_gfn(self.inputs, self.external)

    def real_gdp_growth(self) -> pd.Series:
        """Macro R107."""
        return _derived.real_gdp_growth(self.inputs)

    def depreciation_of_nc(self) -> pd.Series:
        """Macro R114."""
        return _derived.depreciation_of_nc(self.inputs)

    def summary(self) -> pd.DataFrame:
        """Headline Macro-Debt_Data panel rows."""
        return pd.DataFrame(
            {
                "PPG external debt": self.ppg_external(),
                "MLT external": self.mlt_external(),
                "Short-term external": self.short_term_external(),
                "Total public domestic debt": self.domestic_debt(),
                "Revenues incl. grants": self.revenues_incl_grants(),
                "Grants": self.grants(),
                "GDP USD": self.gdp_usd(),
                "FX eop": self.fx_eop(),
                "FX pa": self.fx_pa(),
                "External GFN": self.external_gfn(),
                "Residual financing gap": self.residual_financing_gap(),
                "Total public debt": self.total_public_debt(),
                "PV of PPG external (LCU)": self.pv_external_lcu(),
                "Public GFN": self.public_gfn(),
            }
        ).T

    def as_domestic_macro_fields(self) -> dict[str, pd.Series]:
        """Macro series consumed by ``DomesticDebtInputs``."""
        return {
            "revenues_incl_grants": self.revenues_incl_grants(),
            "grants": self.grants(),
            "domestic_debt_stock": self.domestic_debt(),
            "domestic_interest_due": self.domestic_interest(),
            "gdp_usd": self.gdp_usd(),
            "fx_pa": self.fx_pa(),
        }
