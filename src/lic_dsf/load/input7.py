"""Load Input 7 residual-financing terms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastpyxl import load_workbook

from lic_dsf.load._cells import _as_float
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams

_INPUT7 = "Input 7 - Residual Financing"


def _require_float(value: Any, cell: str) -> float:
    number = _as_float(value)
    if number is None:
        raise ValueError(f"Input 7 {cell} must be numeric, got {value!r}")
    return number


def load_input7_residual_params(path: str | Path) -> ResidualFinancingParams:
    """Load Input 7 **value-used** residual financing terms.

    Reads public shares ``J9–J11``, external terms ``E14–E17`` (interest stored
    as decimal → converted to percent), and domestic public terms ``J19–J23``.

    Args:
        path: Path to a LIC-DSF workbook.

    Returns:
        Params ready for public / external stress residual fills.
    """
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        if _INPUT7 not in workbook.sheetnames:
            raise ValueError(f"workbook missing sheet {_INPUT7!r}")
        ws = workbook[_INPUT7]

        # Public shares (J = col 10). Fall back to Ext decade defaults in H if
        # J is blank.
        ext_share = _require_float(ws.cell(9, 10).value or ws.cell(9, 8).value, "J9")
        dom_mlt_share = _require_float(
            ws.cell(10, 10).value or ws.cell(10, 8).value, "J10"
        )
        dom_st_share = _require_float(
            ws.cell(11, 10).value or ws.cell(11, 8).value, "J11"
        )

        # External terms: E14 decimal → percent; E15 discount; E16/E17 ints.
        interest_decimal = _require_float(ws.cell(14, 5).value, "E14")
        discount = _require_float(ws.cell(15, 5).value, "E15")
        maturity = int(_require_float(ws.cell(16, 5).value, "E16"))
        grace = int(_require_float(ws.cell(17, 5).value, "E17"))

        dom_mlt_rate = _require_float(ws.cell(19, 10).value, "J19")
        dom_mlt_mat = int(_require_float(ws.cell(20, 10).value, "J20"))
        dom_mlt_grace = int(_require_float(ws.cell(21, 10).value, "J21"))
        dom_st_rate = _require_float(ws.cell(23, 10).value, "J23")

        return ResidualFinancingParams(
            external_mlt_share=ext_share,
            domestic_mlt_share=dom_mlt_share,
            domestic_st_share=dom_st_share,
            avg_interest_rate=interest_decimal * 100.0,
            avg_grace=float(grace),
            avg_maturity=float(maturity),
            avg_grace_rounded=grace,
            avg_maturity_rounded=maturity,
            domestic_mlt_real_rate=dom_mlt_rate,
            domestic_mlt_maturity=dom_mlt_mat,
            domestic_mlt_grace=dom_mlt_grace,
            domestic_st_real_rate=dom_st_rate,
            discount_rate=discount,
        )
    finally:
        workbook.close()
