"""Typed inputs for Macro-Debt_Data pass-through and hist seeds."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class MacroDebtInputs:
    """Input 3 / Input 5 series Macro-Debt_Data normalizes.

    Hist debt stocks and service are Input 3 combinations matching Macro's
    pre-projection formulas. Projection domestic / public-GFN series come from
    Input 5 (Macro switches to those rows at ``first_projection_year``).

    Ext-stitched projection stocks (MLT, ST, PPG interest/amort, PV) are not
    stored here — ``MacroDebtBook`` reads them from ``ExternalDebtBook``.
    """

    years: tuple[int, ...]
    first_projection_year: int

    # Real economy / FX (Macro R56–R60)
    gdp_usd: pd.Series
    gdp_constant: pd.Series
    fx_eop: pd.Series
    fx_pa: pd.Series

    # External flows (Macro R28–R36)
    current_account: pd.Series
    exports: pd.Series
    imports: pd.Series
    current_transfers_net: pd.Series
    current_transfers_official: pd.Series
    fdi: pd.Series
    exceptional_financing: pd.Series
    reserves_flow: pd.Series

    # Fiscal (Macro R45–R53)
    revenues_incl_grants: pd.Series
    grants: pd.Series
    privatization: pd.Series
    primary_expenditure: pd.Series
    public_assets: pd.Series
    contingent_liabilities: pd.Series
    other_debt_creating_flows: pd.Series
    debt_relief: pd.Series

    # Input 3 hist debt (full horizon; used for year < first_projection_year)
    mlt_external: pd.Series
    short_term_external: pd.Series
    private_mlt_external: pd.Series
    private_st_external: pd.Series
    domestic_mlt: pd.Series
    domestic_st: pd.Series
    ppg_interest: pd.Series
    private_interest: pd.Series
    domestic_interest: pd.Series
    ppg_amortization: pd.Series
    private_amortization: pd.Series
    domestic_amortization: pd.Series
    concessional_loans: pd.Series

    # Input 5 projection overlays (Macro R15/R16/R21/R26/R101)
    domestic_mlt_input5: pd.Series
    domestic_st_input5: pd.Series
    domestic_interest_lcu_input5: pd.Series
    domestic_principal_lcu_input5: pd.Series
    public_gfn_input5: pd.Series
    # Macro R58 (Input 3 row 18); optional so synthetic fixtures stay compact.
    foreign_gdp_deflator: pd.Series | None = None
    # Macro R83 hist seed (Input 3 row 214, USD); × FX(eop) for LCU.
    fc_public_debt_usd: pd.Series | None = None
    # Probability approach (Input 3 rows 45 / 183 / 184).
    workers_remittances: pd.Series | None = None
    world_real_growth: pd.Series | None = None
    reserves_stock: pd.Series | None = None
    lc_external_usd: pd.Series | None = None
