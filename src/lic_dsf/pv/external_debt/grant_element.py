"""Grant element of new external MLT disbursements (Ext R407–R409)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook


def _unit_grant_element_percent(instrument: Any) -> float:
    """Scalar GE% Ext reads from Input 4 column I / PV_Base unit loan.

    For ``PresentValueInstrument`` this is the first projection-year cell of
    ``internal()``'s Grant element row (matches Input 4 ``I`` on the template).
    LC-NR lines use ``0`` in Input 4.
    """
    if isinstance(instrument, LocalCurrencyNonResidentInstrument):
        return 0.0
    internal = instrument.internal()
    if "Grant element" not in internal.index:
        return 0.0
    ge_row = internal.loc["Grant element"]
    # Column 0 is the Term scalar (usually NA); first year is column 1.
    if len(ge_row) < 2:
        return 0.0
    value = ge_row.iloc[1]
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def grant_element_new_disbursements(book: ExternalDebtBook) -> pd.Series:
    """Disbursement-weighted average grant element % (Ext R408).

    Weights each instrument's unit-loan GE% by that year's
    ``New forex borrowing (gross, USD)``, matching Ext's
    ``Σ(Input4!I × Ext disb) / R122``.
    """
    years = list(book.inputs.years)
    out = pd.Series(0.0, index=years, dtype=float)
    # Ext R408 omits some Input 4 lines from the GE numerator (e.g. IDA NEW)
    # while still counting their disbursements in R122. Empty set = weight all.
    included = book.inputs.grant_element_weight_names
    for year in years:
        num = 0.0
        den = 0.0
        for instrument in book.portfolio.instruments:
            disb = float(
                instrument.external()
                .loc["New forex borrowing (gross, USD)"]
                .reindex([year])
                .fillna(0.0)
                .loc[year]
            )
            if disb == 0.0:
                continue
            if included and instrument.name not in included:
                ge = 0.0
            else:
                ge = _unit_grant_element_percent(instrument)
            num += ge * disb
            den += disb
        out.loc[year] = (num / den) if den else 0.0
    return out


def new_disbursements_net_of_ge(book: ExternalDebtBook) -> pd.Series:
    """New external MLT disbursements net of grant element (Ext R407)."""
    disb = book.portfolio.aggregate_external().loc["New forex borrowing (gross, USD)"]
    ge = grant_element_new_disbursements(book)
    years = list(book.inputs.years)
    disb = disb.reindex(years).fillna(0.0)
    ge = ge.reindex(years).fillna(0.0)
    return disb * (1.0 - ge / 100.0)


def grant_element_value(book: ExternalDebtBook) -> pd.Series:
    """Grant-element dollar amount of new disbursements (Ext R409)."""
    disb = book.portfolio.aggregate_external().loc["New forex borrowing (gross, USD)"]
    ge = grant_element_new_disbursements(book)
    years = list(book.inputs.years)
    disb = disb.reindex(years).fillna(0.0)
    ge = ge.reindex(years).fillna(0.0)
    return ge * disb / 100.0
