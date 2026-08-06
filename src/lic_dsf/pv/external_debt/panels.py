"""Ext_Debt existing-service, evolution, and memorandum panels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook


def existing_debt_service(book: ExternalDebtBook) -> pd.DataFrame:
    """Per-creditor existing MLT debt service + Total (Ext R12–R40 / R42)."""
    years = list(book.inputs.years)
    service = book.inputs.existing_debt_service.reindex(columns=years).fillna(0.0)
    panel = service.copy()
    panel.loc["Total"] = panel.sum(axis=0)
    return panel


def existing_service_totals(book: ExternalDebtBook) -> pd.DataFrame:
    """Existing + locally-issued service headlines (Ext R42–R44, R55–R57, R61–R63)."""
    years = list(book.inputs.years)
    ext_service = (
        book.inputs.existing_debt_service.reindex(columns=years).fillna(0.0).sum(axis=0)
    )
    ext_principal = book.inputs.existing_principal.reindex(years).fillna(0.0)
    ext_interest = ext_service - ext_principal

    local_principal = book.inputs.locally_issued_principal.reindex(years).fillna(0.0)
    local_interest = book.inputs.locally_issued_interest.reindex(years).fillna(0.0)
    local_service = local_principal + local_interest

    return pd.DataFrame(
        {
            "Existing external debt service": ext_service,
            "    Existing principal": ext_principal,
            "    Existing interest": ext_interest,
            "Locally-issued debt service": local_service,
            "    Locally-issued principal": local_principal,
            "    Locally-issued interest": local_interest,
            "Total existing + local service": ext_service + local_service,
            "    Total principal": ext_principal + local_principal,
            "    Total interest": ext_interest + local_interest,
        }
    ).T


def debt_evolution(book: ExternalDebtBook) -> pd.DataFrame:
    """Nominal stock evolution panels (Ext R45 / R58 / R67).

    ``Existing external (excl. local)`` is ``existing_mlt_nominal - local stock``,
    matching Ext R45 on the template. ``Locally-issued`` is Input 5 stock (R58).
    ``Existing MLT (incl. local adj.)`` is Ext R67.
    """
    years = list(book.inputs.years)
    existing = book.existing_mlt_nominal().reindex(years).fillna(0.0)
    local = book.inputs.locally_issued_debt_stock.reindex(years).fillna(0.0)
    return pd.DataFrame(
        {
            "Existing external (excl. local)": existing - local,
            "Locally-issued": local,
            "Existing MLT (incl. local adj.)": existing,
        }
    ).T


def memorandum(book: ExternalDebtBook) -> pd.DataFrame:
    """Memorandum items (Ext R398 / R402 / R403).

    ``External debt outstanding`` = new MLT stock + arrears + existing MLT
    nominal (Ext R398). FX rates are Macro pass-throughs. Full residency
    ``FX-denominated debt outstanding`` (R399) is not reconstructed here.
    """
    years = list(book.inputs.years)
    outstanding = (
        book.new_mlt_nominal().reindex(years).fillna(0.0)
        + book.inputs.arrears.reindex(years).fillna(0.0)
        + book.existing_mlt_nominal().reindex(years).fillna(0.0)
    )
    return pd.DataFrame(
        {
            "External debt outstanding": outstanding,
            "Exchange rate (eop)": book.inputs.fx_eop.reindex(years).fillna(0.0),
            "Exchange rate (pa)": book.inputs.fx_pa.reindex(years).fillna(0.0),
        }
    ).T
