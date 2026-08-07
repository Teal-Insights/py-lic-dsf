"""Dom_Debt_Data book: domestic debt indicators + Indicators panels."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.domestic_debt import indicators as _indicators
from lic_dsf.pv.domestic_debt import presentation as _presentation
from lic_dsf.pv.domestic_debt.types import DomesticDebtInputs


@dataclass(slots=True)
class DomesticDebtBook:
    """Domestic debt indicator book (Excel ``Dom_Debt_Data`` / Indicators).

    Computes Dom_Debt_Data derived ratios from Baseline/Macro series held on
    ``inputs``, and exposes Dom_Debt_Indicators chart windows plus Input 7
    borrowing assumptions.
    """

    inputs: DomesticDebtInputs

    def domestic_debt_to_gdp(self) -> pd.Series:
        """Domestic debt / GDP (Dom R10)."""
        return _indicators.domestic_debt_to_gdp(self.inputs)

    def domestic_ds_to_revenues(self) -> pd.Series:
        """Domestic debt service / revenues incl. grants (Dom R16)."""
        return _indicators.domestic_ds_to_revenues(self.inputs)

    def gdp_lcu(self) -> pd.Series:
        """Nominal GDP in LCU (Dom R33)."""
        return _indicators.gdp_lcu(self.inputs)

    def domestic_interest_lcu(self) -> pd.Series:
        """Domestic interest due in LCU (Dom R29)."""
        return _indicators.domestic_interest_lcu(self.inputs)

    def change_in_domestic_debt(self) -> pd.Series:
        """Change in domestic debt stock (Dom R28)."""
        return _indicators.change_in_domestic_debt(self.inputs)

    def net_issuance_to_gdp(self) -> pd.Series:
        """Net domestic debt issuance / GDP (Dom R25)."""
        return _indicators.net_issuance_to_gdp(self.inputs)

    def net_issuance_to_prior_dom_debt(self) -> pd.Series:
        """Net issuance / prior domestic debt-to-GDP (Dom R34)."""
        return _indicators.net_issuance_to_prior_dom_debt(self.inputs)

    def peer_median_debt_to_gdp(self) -> pd.Series:
        """LIC-DSF peer median debt/GDP band (Dom R14)."""
        return _indicators.peer_median_debt_to_gdp(self.inputs)

    def peer_median_ds_to_revenues(self) -> pd.Series:
        """LIC-DSF peer median DS/revenues band (Dom R22)."""
        return _indicators.peer_median_ds_to_revenues(self.inputs)

    def summary_averages(self, series: pd.Series) -> pd.Series:
        """Hist / near-term / outer / full-projection averages for ``series``."""
        return _indicators.summary_averages(
            series,
            first_projection_year=self.inputs.first_projection_year,
            years=self.inputs.years,
        )

    def summary(self) -> pd.DataFrame:
        """Headline Dom_Debt_Data indicator rows."""
        return pd.DataFrame(
            {
                "Domestic debt / GDP": self.domestic_debt_to_gdp(),
                "Peer median debt / GDP": self.peer_median_debt_to_gdp(),
                "Domestic debt service / Revenues incl. grants": (
                    self.domestic_ds_to_revenues()
                ),
                "Peer median DS / revenues": self.peer_median_ds_to_revenues(),
                "Net domestic debt issuance / GDP": self.net_issuance_to_gdp(),
                "Net issuance / prior domestic debt/GDP": (
                    self.net_issuance_to_prior_dom_debt()
                ),
                "Change in domestic debt": self.change_in_domestic_debt(),
                "GDP (LCU)": self.gdp_lcu(),
            }
        ).T

    def indicator_charts(self) -> pd.DataFrame:
        """Dom_Debt_Indicators chart series over the J:Y year window."""
        return _presentation.indicator_charts(
            domestic_debt_to_gdp=self.domestic_debt_to_gdp(),
            peer_median_debt_to_gdp=self.peer_median_debt_to_gdp(),
            domestic_ds_to_revenues=self.domestic_ds_to_revenues(),
            peer_median_ds_to_revenues=self.peer_median_ds_to_revenues(),
            net_issuance_to_gdp=self.net_issuance_to_gdp(),
            years=self.inputs.years,
            first_projection_year=self.inputs.first_projection_year,
        )

    def borrowing_assumptions(self) -> pd.DataFrame:
        """Input 7 domestic MLT/ST shares and terms (Indicators panel)."""
        return _presentation.borrowing_assumptions(self.inputs)
