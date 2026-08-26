"""Output 1-1 / 1-2 panels and Excel-geometry tables."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook

OUTPUT11_SHEET = "Output 1-1 - External DSA"
OUTPUT12_SHEET = "Output 1-2 - Public DSA"

_Getter = Callable[[BaselineExternalBook], pd.Series]
_PubGetter = Callable[[BaselinePublicBook], pd.Series]


def external_dsa_panel(book: BaselineExternalBook) -> pd.DataFrame:
    """Output 1-1 sustainability rows over the Macro year horizon."""
    return pd.DataFrame(
        {
            "PV of PPG external debt / GDP": book.pv_ppg_external_to_gdp(),
            "PV of PPG external debt / exports": book.pv_ppg_external_to_exports(),
            "PV of PPG external debt / revenue": book.pv_ppg_external_to_revenue(),
            "PPG debt service / exports": book.ppg_debt_service_to_exports(),
            "PPG debt service / revenue": book.ppg_debt_service_to_revenue(),
            "External GFN (USD)": book.external_gfn_usd(),
        }
    ).T


def public_dsa_panel(book: BaselinePublicBook) -> pd.DataFrame:
    """Output 1-2 sustainability / Dom feeder rows over the Macro year horizon."""
    return pd.DataFrame(
        {
            "Public sector debt / GDP": book.public_sector_debt_to_gdp(),
            "PPG external debt / GDP": book.ppg_external_debt_to_gdp(),
            "PV of public debt / GDP": book.pv_public_debt_to_gdp(),
            "PV of public debt / revenue+grants": (
                book.pv_public_debt_to_revenue_grants()
            ),
            "Debt service / revenue+grants": book.debt_service_to_revenue_grants(),
            "Public GFN / GDP": book.public_gfn_to_gdp(),
        }
    ).T


def _table(
    years: tuple[int, ...],
    rows: dict[int, pd.Series],
) -> pd.DataFrame:
    data = {row: series.reindex(list(years)).astype(float) for row, series in rows.items()}
    table = pd.DataFrame(data).T
    table.index.name = "excel_row"
    return table


def output_11_table(book: BaselineExternalBook) -> pd.DataFrame:
    """Output 1-1 shaped table keyed by Excel row number.

    Columns are Macro years. Thin ``external_dsa_panel`` remains the
    headline six-row view with economist labels.

    Projection years mirror Output's layout quirk: R21 is interest + real-GDP
    only (price/FX is omitted and shown as blank on R25). History keeps the
    full Baseline identity. R12 / R26 follow from that R21 definition.

    Args:
        book: Baseline external DSA book.

    Returns:
        DataFrame indexed by Output 1-1 row numbers.
    """
    endog = book.endogenous_debt_dynamics()
    first = book.macro.inputs.first_projection_year
    years = list(book.years)
    price_fx = endog["price_fx"].reindex(years).astype(float)
    interest = endog["interest"].reindex(years).astype(float)
    real_gdp = endog["real_gdp"].reindex(years).astype(float)
    full_endog = endog["endogenous"].reindex(years).astype(float)
    is_proj = pd.Series([y >= first for y in years], index=years)
    # Output R21: full endogenous in history; interest+growth only in projection.
    r21 = full_endog.where(~is_proj, interest + real_gdp)
    # Output R25: blank (NaN) from first projection year onward.
    r25 = price_fx.where(~is_proj, pd.NA).astype(float)
    identified = (
        book.non_interest_cad_to_gdp().reindex(years)
        + book.net_fdi_to_gdp().reindex(years)
        + r21
    ).astype(float)
    # With projection R21 excluding price/FX, change − identified already matches
    # Output R26 (= Baseline residual + price/FX). History uses full R21 so this
    # is the true residual.
    residual = (
        book.change_in_external_debt().reindex(years) - identified
    ).astype(float)

    rows: dict[int, pd.Series] = {
        8: book.external_debt_to_gdp(),
        9: book.ppg_external_to_gdp_nominal(),
        11: book.change_in_external_debt(),
        12: identified,
        13: book.non_interest_cad_to_gdp(),
        14: book.goods_services_deficit_to_gdp(),
        15: book.exports_to_gdp(),
        16: book.imports_to_gdp(),
        17: book.net_transfers_to_gdp(),
        18: book.official_transfers_to_gdp(),
        19: book.other_current_account_to_gdp(),
        20: book.net_fdi_to_gdp(),
        21: r21,
        22: book.endogenous_denominator(),
        23: interest,
        24: real_gdp,
        25: r25,
        26: residual,
        27: book.exceptional_financing_to_gdp(),
        30: book.pv_ppg_external_to_gdp(),
        31: book.pv_ppg_external_to_exports(),
        32: book.pv_ppg_external_to_revenue(),
        33: book.ppg_debt_service_to_exports(),
        34: book.ppg_debt_service_to_revenue(),
        35: book.external_gfn_usd(),
        38: book.macro.real_gdp_growth(),
        39: book.macro.usd_deflator_growth(),
        40: book.effective_interest_rate_external(),
        41: book.export_growth(),
        42: book.import_growth(),
        43: book.macro.grant_element_percent(),
        44: book.revenues_to_gdp(),
        45: book.aid_flows_usd(),
        46: book.grants_usd(),
        47: book.macro.concessional_loans(),
        48: book.grant_equivalent_to_gdp(),
        49: book.grant_equivalent_to_external_financing(),
        50: book.macro.gdp_usd(),
        51: book.nominal_dollar_gdp_growth(),
        54: book.pv_total_external_to_gdp(),
        55: book.pv_total_external_to_exports(),
        56: book.total_external_debt_service_to_exports(),
        57: book.pv_ppg_usd(),
        58: book.pv_change_over_prior_gdp(),
        59: book.stabilizing_non_interest_cad(),
    }
    return _table(book.years, rows)


def output_12_table(book: BaselinePublicBook) -> pd.DataFrame:
    """Output 1-2 shaped table keyed by Excel row number.

    Args:
        book: Baseline public DSA book.

    Returns:
        DataFrame indexed by Output 1-2 row numbers.
    """
    auto = book.automatic_debt_dynamics()
    rows: dict[int, pd.Series] = {
        8: book.public_sector_debt_to_gdp(),
        9: book.ppg_external_debt_to_gdp(),
        11: book.change_in_public_debt(),
        12: book.identified_debt_creating_flows(),
        13: book.primary_deficit_to_gdp(),
        14: book.revenues_incl_grants_to_gdp(),
        15: book.grants_to_gdp(),
        16: book.primary_expenditure_to_gdp(),
        17: auto.loc["DUCIR_GDP"] + auto.loc["DUCGDPR_GDP"] + auto.loc["DUCER_GDP"],
        18: auto.loc["DUCIR_GDP"] + auto.loc["DUCGDPR_GDP"],
        19: auto.loc["DUCIR_GDP"],
        20: auto.loc["DUCGDPR_GDP"],
        21: auto.loc["DUCER_GDP"],
        22: 1.0 + book.macro.real_gdp_growth() / 100.0,
        23: book.other_identified_flows_to_gdp(),
        24: book.privatization_to_gdp(),
        25: book.contingent_liabilities_to_gdp(),
        26: book.debt_relief_to_gdp(),
        27: book.other_debt_creating_to_gdp(),
        28: book.residual_public_flows(),
        31: book.pv_public_debt_to_gdp(),
        32: book.pv_public_debt_to_revenue_grants(),
        33: book.pv_public_debt_to_revenue(),
        35: book.debt_service_to_revenue_grants(),
        36: book.debt_service_to_revenue(),
        37: book.public_gfn_to_gdp(),
        38: book.public_gfn_usd(),
        41: book.gdp_lcu(),
        42: book.macro.real_gdp_growth(),
        43: book.average_nominal_interest_public(),
        44: book.macro.interest_rate_external(),
        45: book.macro.interest_rate_domestic(),
        46: book.real_interest_public(),
        47: book.real_interest_domestic(),
        48: book.real_interest_external(),
        49: book.macro.fx_pa(),
        50: book.macro.depreciation_of_nc(),
        51: book.fx_dollar_per_lc(),
        52: book.nominal_appreciation(),
        53: book.real_exchange_rate_depreciation(),
        54: book.macro.lcu_deflator_growth(),
        55: book.macro.usd_deflator_growth(),
        56: book.real_primary_spending_growth(),
        57: book.stabilizing_primary_deficit(),
        58: book.pv_contingent_liabilities_to_gdp(),
    }
    return _table(book.years, rows)


OUTPUT11_NUMERIC_ROWS: tuple[int, ...] = (
    8,
    9,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    23,
    24,
    25,
    26,
    27,
    30,
    31,
    32,
    33,
    34,
    35,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    54,
    55,
    56,
    57,
    58,
    59,
)
OUTPUT12_NUMERIC_ROWS: tuple[int, ...] = (
    8,
    9,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    23,
    24,
    25,
    26,
    27,
    28,
    31,
    32,
    35,
    37,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    58,
)
