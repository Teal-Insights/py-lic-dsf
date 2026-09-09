"""Typed inputs for Ext_Debt_Data existing-debt and headline mixes."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class ExternalDebtInputs:
    """Workbook-facing series Ext_Debt needs beyond new-loan portfolios.

    Field names use **existing** (already-contracted) debt; Excel labels this
    block "old MLT". Locally-issued series are Input 5 flows converted to USD.

    ``residual_interest_rates`` maps instrument name → Input 4 interest
    (decimal) for Ext residual SUMPRODUCT bands (LC-NR rows 49–51), where Ext
    weights those rates rather than the year-varying Input 5 coupon path.

    ``grant_element_weight_names`` lists instruments Ext includes in the R408
    GE numerator. Empty means weight every portfolio instrument's unit-loan GE
    (synthetic books). The workbook loader matches Ext's Input 4 row bands
    (notably excluding IDA NEW rows 14–17).

    ``concessionality_threshold`` is Input 1 ``C15`` (default 0.35): Ext R417
    includes new MLT disbursements for GE-weighted instruments with unit GE%
    at or above this cutoff.
    """

    years: tuple[int, ...]
    existing_debt_service: pd.DataFrame
    existing_principal: pd.Series
    existing_discount_rates: dict[str, float]
    arrears: pd.Series
    short_term_external: pd.Series
    sdr_pv: pd.Series
    sdr_interest: pd.Series
    macro_ppg_external: pd.Series
    macro_mlt_external: pd.Series
    fx_eop: pd.Series
    fx_pa: pd.Series
    locally_issued_debt_stock: pd.Series
    locally_issued_principal: pd.Series
    locally_issued_interest: pd.Series
    locally_issued_st: pd.Series
    locally_issued_st_principal: pd.Series
    locally_issued_st_interest: pd.Series
    domestic_mlt_disbursements_usd: pd.Series
    domestic_st_disbursements_usd: pd.Series
    short_term_interest_rate: float
    residual_interest_rates: dict[str, float]
    grant_element_weight_names: frozenset[str]
    fx_denominated_outstanding: pd.Series = dataclasses.field(
        default_factory=lambda: pd.Series(dtype=float)
    )
    concessionality_threshold: float = 0.35
