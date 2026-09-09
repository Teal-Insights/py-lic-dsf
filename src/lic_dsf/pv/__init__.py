"""LIC-DSF-style present-value calculations for a single financing instrument.

Mirrors the standard ``PV_Base`` instrument template:

* ``internal()`` — unit loan of ``unit_base`` (default 100) as a DataFrame
  (debt stock, amortization, interest, PV, grant element, ``t-g`` / ``t-m``).
* ``external()`` — Output block scaled by disbursements as a DataFrame
  (new borrowing, cumulative, stock, PV, debt service, interest, amortization).

Year indexing matches LIC-DSF: column ``t`` uses age ``t - 1`` for the
grace/maturity amortization window on the unit loan.

Ext / Dom / Macro books live in ``lic_dsf.books``. Residual financing lives in
``lic_dsf.resfin``.
"""

from __future__ import annotations

from lic_dsf.pv.instrument import PresentValueInstrument
from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.pv.mathutil import excel_npv
from lic_dsf.pv.portfolio import PVPortfolio

__all__ = [
    "LocalCurrencyNonResidentInstrument",
    "PVPortfolio",
    "PresentValueInstrument",
    "excel_npv",
]
