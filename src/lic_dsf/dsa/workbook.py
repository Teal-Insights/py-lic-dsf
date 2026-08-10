"""Load Macro / Ext / baseline DSA books from a LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook
from lic_dsf.pv import (
    ExternalDebtBook,
    MacroDebtBook,
    PresentValueInstrument,
    PVPortfolio,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)


def load_core(
    path: str | Path,
    *,
    include_zero_disbursement: bool = True,
) -> tuple[MacroDebtBook, ExternalDebtBook, BaselineExternalBook, BaselinePublicBook]:
    """Load instruments, Ext/Macro inputs, and baseline DSA books from a workbook.

    Loads Input 4 / PV and Input 5 LC-NR instruments (including empty slots when
    `include_zero_disbursement` is true), Ext and Macro sheet inputs, then wires
    `ExternalDebtBook` -> `MacroDebtBook` -> baseline external / public books.

    Does not load CI Summary, Input 6, Input 7 ResFin, Dom debt, or realism
    inputs; call those loaders separately when needed.

    Args:
        path: Path to the LIC-DSF Excel workbook.
        include_zero_disbursement: Keep empty Input 4/5 slots so creditor
            grouping matches Excel row structure.

    Returns:
        `(macro, external, ext_base, pub_base)` wired from the same portfolio
        and Macro / Ext inputs.
    """
    instruments = load_instruments_from_workbook(
        path, include_zero_disbursement=include_zero_disbursement
    )
    lc_nr = load_lc_nr_instruments_from_workbook(
        path, include_zero_disbursement=include_zero_disbursement
    )
    # LC-NR instruments duck-type PresentValueInstrument.external() for portfolios.
    portfolio = PVPortfolio(
        instruments=cast(
            tuple[PresentValueInstrument, ...],
            tuple(instruments) + tuple(lc_nr),
        )
    )
    external = ExternalDebtBook(
        portfolio=portfolio,
        inputs=load_external_debt_inputs(path),
    )
    macro = MacroDebtBook(inputs=load_macro_debt_inputs(path), external=external)
    return (
        macro,
        external,
        BaselineExternalBook(macro=macro, external=external),
        BaselinePublicBook(macro=macro, external=external),
    )
