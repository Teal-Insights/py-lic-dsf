"""Typed inputs for Dom_Debt_Data indicator calculations."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Template Dom_Debt_Data D14 / D22 peer benchmarks.
DEFAULT_PEER_MEDIAN_DEBT_TO_GDP = 17.1
DEFAULT_PEER_MEDIAN_DS_TO_REVENUES = 21.7


@dataclass(slots=True)
class DomesticDebtInputs:
    """Series Dom_Debt_Data needs from Baseline / Macro / Input 7.

    Baseline fields are DSA **ratios** (percent of GDP or of revenues), matching
    the VLOOKUP keys on Dom_Debt_Data. Macro stocks and flows are levels;
    ``domestic_interest_due`` is the Macro row before FX conversion (Dom R29
    multiplies by ``fx_pa``).

    ``residual_domestic_*_share`` are Ext C127/C128 (Input 7 ``H10``/``H11``)
    shares of total residual financing; Indicators renormalizes them to
    domestic-only MLT/ST shares.
    """

    years: tuple[int, ...]
    first_projection_year: int
    public_sector_debt_pct_gdp: pd.Series
    ppg_external_debt_pct_gdp: pd.Series
    public_ds_to_revenue_grants: pd.Series
    ppg_ds_to_revenue: pd.Series
    revenues_incl_grants: pd.Series
    grants: pd.Series
    domestic_debt_stock: pd.Series
    domestic_interest_due: pd.Series
    gdp_usd: pd.Series
    fx_pa: pd.Series
    fx_denominated_domestic_stock: pd.Series
    fx_denominated_domestic_interest: pd.Series
    peer_median_debt_to_gdp: float = DEFAULT_PEER_MEDIAN_DEBT_TO_GDP
    peer_median_ds_to_revenues: float = DEFAULT_PEER_MEDIAN_DS_TO_REVENUES
    residual_domestic_mlt_share: float = 0.0
    residual_domestic_st_share: float = 0.0
    domestic_mlt_avg_interest: float = 0.0
    domestic_mlt_avg_maturity: float = 0.0
    domestic_mlt_avg_grace: float = 0.0
    domestic_st_avg_interest: float = 0.0
