"""Creditor-group taxonomy for Ext_Debt new-debt panels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.portfolio import PVPortfolio

# Ext top-level new-debt groups (disb R71/82/86/99/105/115; interest R143…).
CREDITOR_GROUPS: tuple[str, ...] = (
    "Multilaterals",
    "Other multilaterals",
    "Official bilaterals",
    "Commercial",
    "Locally issued (NR)",
    "FX local (residents)",
)

# Input 4 row → Ext group (same bands as PV_Base loader).
INPUT4_ROW_TO_GROUP: dict[int, str] = {
    10: "Multilaterals",
    11: "Multilaterals",
    12: "Multilaterals",
    13: "Multilaterals",
    14: "Multilaterals",
    15: "Multilaterals",
    16: "Multilaterals",
    17: "Multilaterals",
    18: "Multilaterals",
    19: "Multilaterals",
    21: "Other multilaterals",
    22: "Other multilaterals",
    23: "Other multilaterals",
    26: "Official bilaterals",
    27: "Official bilaterals",
    28: "Official bilaterals",
    29: "Official bilaterals",
    30: "Official bilaterals",
    32: "Official bilaterals",
    33: "Official bilaterals",
    34: "Official bilaterals",
    35: "Official bilaterals",
    36: "Official bilaterals",
    38: "Commercial",
    39: "Commercial",
    40: "Commercial",
    41: "Commercial",
    42: "Commercial",
    54: "Locally issued (NR)",
    55: "Locally issued (NR)",
    56: "Locally issued (NR)",
    59: "FX local (residents)",
    60: "FX local (residents)",
    61: "FX local (residents)",
}

# Exact names produced by the Input 4 / LC-NR loaders for this template family.
_NAME_TO_GROUP: dict[str, str] = {
    "IMF": "Multilaterals",
    "IDA - regular": "Multilaterals",
    "IDA - 50Y loans": "Multilaterals",
    "IDA - SML": "Multilaterals",
    "IDA NEW 40-year credits": "Multilaterals",
    "IDA NEW Regular": "Multilaterals",
    "IDA NEW Blend (also enter) -->": "Multilaterals",
    "IDA NEW 60-year credits": "Multilaterals",
    "MULTI1": "Multilaterals",
    "MULTI2": "Multilaterals",
    "OTH_MULTI1": "Other multilaterals",
    "OTH_MULTI2": "Other multilaterals",
    "OTH_MULTI3": "Other multilaterals",
    "Export Credit Agencies": "Official bilaterals",
    "PC2": "Official bilaterals",
    "PC3": "Official bilaterals",
    "PC4": "Official bilaterals",
    "PC5": "Official bilaterals",
    "Export Import Bank of NPC": "Official bilaterals",
    "NPC2": "Official bilaterals",
    "NPC3": "Official bilaterals",
    "NPC4": "Official bilaterals",
    "NPC5": "Official bilaterals",
    "Eurobond": "Commercial",
    "Commecial Bank": "Commercial",
    "COM3": "Commercial",
    "COM4": "Commercial",
    "COM5": "Commercial",
    "Bonds (1 to 3 years)-FX (non-residents)": "Locally issued (NR)",
    "Bonds (4 to 7 years)-FX (non-residents)": "Locally issued (NR)",
    "Bonds (beyond 7 years)-FX (non-residents)": "Locally issued (NR)",
    "Bonds (1 to 3 years)-LC": "Locally issued (NR)",
    "Bonds (4 to 7 years)-LC": "Locally issued (NR)",
    "Bonds (beyond 7 years)-LC": "Locally issued (NR)",
    "Bonds (1 to 3 years)-FX (residents)": "FX local (residents)",
    "Bonds (4 to 7 years)-FX (residents)": "FX local (residents)",
    "Bonds (beyond 7 years)-FX (residents)": "FX local (residents)",
}


def creditor_group_for_name(name: str) -> str:
    """Return Ext creditor group for an instrument name.

    Uses the template name table, then suffix heuristics for FX holder
    disambiguation / LC-NR tenors.
    """
    if name in _NAME_TO_GROUP:
        return _NAME_TO_GROUP[name]
    if name.endswith("(residents)"):
        return "FX local (residents)"
    if name.endswith("(non-residents)"):
        return "Locally issued (NR)"
    if name.endswith("-LC"):
        return "Locally issued (NR)"
    raise KeyError(f"no creditor group for instrument {name!r}")


def group_instrument_panel(
    panel: pd.DataFrame,
    *,
    groups: tuple[str, ...] = CREDITOR_GROUPS,
) -> pd.DataFrame:
    """Sum a per-instrument metric panel into Ext creditor groups + Total.

    Args:
        panel: Rows = instrument names, columns = years.
        groups: Group row order (default Ext top-level order).

    Returns:
        DataFrame with one row per group (zeros if empty) plus ``Total``.
    """
    if panel.empty:
        empty = pd.DataFrame(0.0, index=list(groups) + ["Total"], columns=[])
        return empty

    labeled = panel.copy()
    labeled.index = [creditor_group_for_name(str(name)) for name in labeled.index]
    grouped = labeled.groupby(level=0, sort=False).sum()
    ordered = grouped.reindex(list(groups), fill_value=0.0)
    ordered.loc["Total"] = ordered.sum(axis=0)
    return ordered


def _metric_by_creditor(book: ExternalDebtBook, panel: pd.DataFrame) -> pd.DataFrame:
    years = list(book.inputs.years)
    grouped = group_instrument_panel(panel)
    return grouped.reindex(columns=years).fillna(0.0)


def _new_borrowing_panel(portfolio: PVPortfolio) -> pd.DataFrame:
    rows: dict[str, pd.Series] = {}
    for instrument in portfolio.instruments:
        rows[instrument.name] = instrument.external().loc[
            "New forex borrowing (gross, USD)"
        ]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).T


def new_disbursements_by_creditor(book: ExternalDebtBook) -> pd.DataFrame:
    """New forex borrowing by Ext creditor group (Ext R71–R122 shape)."""
    return _metric_by_creditor(book, _new_borrowing_panel(book.portfolio))


def new_interest_by_creditor(book: ExternalDebtBook) -> pd.DataFrame:
    """New MLT interest by Ext creditor group (Ext R142–R187 shape)."""
    return _metric_by_creditor(book, book.portfolio.interest())


def new_amortization_by_creditor(book: ExternalDebtBook) -> pd.DataFrame:
    """New MLT amortization by Ext creditor group (Ext R192–R237 shape)."""
    return _metric_by_creditor(book, book.portfolio.amortization())


def new_pv_by_creditor(book: ExternalDebtBook) -> pd.DataFrame:
    """New MLT PV by Ext creditor group (Ext R279–R324 shape)."""
    return _metric_by_creditor(book, book.portfolio.pv())


def new_stock_by_creditor(book: ExternalDebtBook) -> pd.DataFrame:
    """New MLT stock by Ext creditor group (Ext R329–R374 shape)."""
    return _metric_by_creditor(book, book.portfolio.stock())
