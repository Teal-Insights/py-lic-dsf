"""Existing (Excel: old) MLT debt service → PV and nominal stock."""

from __future__ import annotations

import pandas as pd

from lic_dsf.pv.external_debt.types import ExternalDebtInputs
from lic_dsf.pv.mathutil import excel_npv


def existing_mlt_pv(inputs: ExternalDebtInputs) -> pd.DataFrame:
    """Per-creditor PV of remaining existing MLT service (Ext R242 / R245…).

    For calendar year ``t``, Excel discounts service from ``t+1`` onward with
    ``NPV(discount_i, service_i[t+1:])`` — matching ``excel_npv``.
    """
    service = inputs.existing_debt_service
    years = list(inputs.years)
    rows: dict[str, dict[int, float]] = {}
    for name in service.index:
        rate = float(inputs.existing_discount_rates[name])
        path = [float(service.loc[name, year]) for year in years]
        by_year: dict[int, float] = {}
        for i, year in enumerate(years):
            future = path[i + 1 :]
            by_year[year] = excel_npv(rate, future) if future else 0.0
        rows[str(name)] = by_year
    panel = pd.DataFrame(rows).T
    # Ext R274: GE assumed zero for existing locally-issued debt → PV = stock.
    local = inputs.locally_issued_debt_stock.reindex(years).fillna(0.0)
    panel.loc["Locally-issued"] = local
    panel.loc["Total"] = panel.sum(axis=0)
    return panel


def existing_mlt_nominal(inputs: ExternalDebtInputs) -> pd.Series:
    """Nominal existing MLT stock excluding arrears (Ext R67 evolution).

    Seeds from Macro-Debt MLT external minus arrears, then rolls with
    principal amortization and locally-issued stock valuation changes
    (Ext: ``prev - principal - (local_prev - local_curr)``).
    """
    years = list(inputs.years)
    if not years:
        return pd.Series(dtype=float)

    arrears = inputs.arrears.reindex(years).fillna(0.0)
    principal = inputs.existing_principal.reindex(years).fillna(0.0)
    local = inputs.locally_issued_debt_stock.reindex(years).fillna(0.0)
    macro_mlt = inputs.macro_mlt_external.reindex(years).fillna(0.0)

    stock = {}
    stock[years[0]] = float(macro_mlt.loc[years[0]] - arrears.loc[years[0]])
    for i in range(1, len(years)):
        year = years[i]
        prev = years[i - 1]
        stock[year] = (
            stock[prev]
            - float(principal.loc[year])
            - (float(local.loc[prev]) - float(local.loc[year]))
        )
    return pd.Series(stock, dtype=float)
