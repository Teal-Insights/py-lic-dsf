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

    Reads public shares ``J9–J11``, external interest / discount / maturity /
    grace from ``D*``/``C*``/``E*`` (prefers overlaid D/C over stale E cache;
    interest decimal → percent), and domestic public terms ``J19–J23``.

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
        # J is blank. Excel ``I11 = 1 − I9 − I10``; surgical overlays that only
        # rewrite J9 leave a stale J11 cache, so always residualize ST.
        ext_share = _require_float(ws.cell(9, 10).value or ws.cell(9, 8).value, "J9")
        dom_mlt_share = _require_float(
            ws.cell(10, 10).value or ws.cell(10, 8).value, "J10"
        )
        dom_st_share = max(0.0, 1.0 - ext_share - dom_mlt_share)

        # External interest: Excel E14 = IF(ISNUMBER(D14), D14, C14). Prefer
        # D14/C14 so surgical overlays are not masked by a stale E14 cache
        # under data_only=True; fall back to E14 for unmodified workbooks.
        interest_decimal = _require_float(
            ws.cell(14, 4).value or ws.cell(14, 3).value or ws.cell(14, 5).value,
            "D14",
        )
        # Same IF(ISNUMBER(D),D,C) pattern for discount / maturity / grace.
        discount = _require_float(
            ws.cell(15, 4).value or ws.cell(15, 3).value or ws.cell(15, 5).value,
            "D15",
        )
        maturity = int(
            _require_float(
                ws.cell(16, 4).value or ws.cell(16, 3).value or ws.cell(16, 5).value,
                "D16",
            )
        )
        grace = int(
            _require_float(
                ws.cell(17, 4).value or ws.cell(17, 3).value or ws.cell(17, 5).value,
                "D17",
            )
        )

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
