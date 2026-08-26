"""LIC-DSF-style present-value calculations for a single financing instrument.

Mirrors the standard ``PV_Base`` instrument template:

* ``internal()`` — unit loan of ``unit_base`` (default 100) as a DataFrame
  (debt stock, amortization, interest, PV, grant element, ``t-g`` / ``t-m``).
* ``external()`` — Output block scaled by disbursements as a DataFrame
  (new borrowing, cumulative, stock, PV, debt service, interest, amortization).

Year indexing matches LIC-DSF: column ``t`` uses age ``t - 1`` for the
grace/maturity amortization window on the unit loan.
"""

from __future__ import annotations

from lic_dsf.pv.domestic_debt import (
    DEFAULT_PEER_MEDIAN_DEBT_TO_GDP,
    DEFAULT_PEER_MEDIAN_DS_TO_REVENUES,
    DomesticDebtBook,
    DomesticDebtInputs,
)
from lic_dsf.pv.external_debt import (
    CREDITOR_GROUPS,
    ExternalDebtBook,
    ExternalDebtInputs,
    ResidualFinancingOverrides,
    ResidualFinancingParams,
    calculate_residual_defaults,
    creditor_group_for_name,
    grant_element_new_disbursements,
    grant_element_value,
    new_disbursements_net_of_ge,
    public_dsa_residual_params,
    resolve_residual_params,
)
from lic_dsf.pv.instrument import PresentValueInstrument
from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.pv.macro_debt import MacroDebtBook, MacroDebtInputs
from lic_dsf.pv.mathutil import excel_npv
from lic_dsf.pv.portfolio import PVPortfolio

__all__ = [
    "CREDITOR_GROUPS",
    "DEFAULT_PEER_MEDIAN_DEBT_TO_GDP",
    "DEFAULT_PEER_MEDIAN_DS_TO_REVENUES",
    "DomesticDebtBook",
    "DomesticDebtInputs",
    "ExternalDebtBook",
    "ExternalDebtInputs",
    "LocalCurrencyNonResidentInstrument",
    "MacroDebtBook",
    "MacroDebtInputs",
    "PVPortfolio",
    "PresentValueInstrument",
    "ResidualFinancingOverrides",
    "ResidualFinancingParams",
    "calculate_residual_defaults",
    "creditor_group_for_name",
    "excel_npv",
    "grant_element_new_disbursements",
    "grant_element_value",
    "new_disbursements_net_of_ge",
    "public_dsa_residual_params",
    "resolve_residual_params",
]
