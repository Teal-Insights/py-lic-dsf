"""Ext_Debt_Data: existing debt + ExternalDebtBook headlines."""

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.existing_debt import (
    existing_mlt_nominal,
    existing_mlt_pv,
)
from lic_dsf.pv.external_debt.fxutil import lc_to_usd
from lic_dsf.pv.external_debt.residual import (
    ResidualFinancingOverrides,
    ResidualFinancingParams,
    calculate_residual_defaults,
    resolve_residual_params,
)
from lic_dsf.pv.external_debt.types import ExternalDebtInputs
from lic_dsf.pv.external_debt.workbook import load_external_debt_inputs

__all__ = [
    "ExternalDebtBook",
    "ExternalDebtInputs",
    "ResidualFinancingOverrides",
    "ResidualFinancingParams",
    "calculate_residual_defaults",
    "existing_mlt_nominal",
    "existing_mlt_pv",
    "lc_to_usd",
    "load_external_debt_inputs",
    "resolve_residual_params",
]
