"""Load CI Summary, Trigger flags, and Input 1 market-access cells."""

from __future__ import annotations

from pathlib import Path

from fastpyxl import load_workbook

from lic_dsf.rating.classification import (
    ApplicableThresholds,
    DebtCarryingCapacity,
    classify_ci,
)
from lic_dsf.rating.workbook import CiSummarySnapshot, TriggerFlags


def load_ci_summary(path: str | Path) -> CiSummarySnapshot:
    """Load CI score, DCC, and applicable thresholds from ``CI Summary``.

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        `CiSummarySnapshot` for the workbook's country.
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["CI Summary"]
        country = str(ws.cell(3, 3).value or "")
        country_code = int(ws.cell(4, 3).value)
        dcc_final = str(ws.cell(6, 3).value or ws.cell(9, 2).value)
        ci_score = float(ws.cell(25, 5).value)
        dcc_current = str(ws.cell(9, 3).value or "")
        dcc_previous = str(ws.cell(9, 4).value or "")
        dcc_two_previous = str(ws.cell(9, 5).value or "")

        # Prefer sheet DCC label; fall back to CI cut-offs.
        try:
            dcc = DebtCarryingCapacity(dcc_final)
        except ValueError:
            dcc = classify_ci(ci_score)

        # Applicable thresholds from the APPLICABLE block (cols H–I).
        pv_x = float(ws.cell(10, 9).value)
        pv_gdp = float(ws.cell(11, 9).value)
        ds_x = float(ws.cell(13, 9).value)
        ds_rev = float(ws.cell(14, 9).value)
        public_pv = float({"Weak": 35.0, "Medium": 55.0, "Strong": 70.0}[dcc.value])
        thresholds = ApplicableThresholds(
            dcc=dcc,
            pv_debt_to_exports=pv_x,
            pv_debt_to_gdp=pv_gdp,
            debt_service_to_exports=ds_x,
            debt_service_to_revenue=ds_rev,
            public_pv_debt_to_gdp=public_pv,
        )

        return CiSummarySnapshot(
            country=country,
            country_code=country_code,
            ci_score=ci_score,
            dcc=dcc,
            thresholds=thresholds,
            dcc_current=dcc_current,
            dcc_previous=dcc_previous,
            dcc_two_previous=dcc_two_previous,
        )
    finally:
        wb.close()


def load_trigger_flags(
    path: str | Path,
    country_code: int,
) -> TriggerFlags | None:
    """Look up Trigger-sheet market-LIC / disaster-style flags.

    The Trigger sheet stores PPP / market-access style flags per IFS code.
    Column ``incgr`` (E) is used as a market-access proxy (1/2); ``licdsf``
    (F) marks LIC-DSF coverage.

    Args:
        path: Workbook path.
        country_code: IFS country code.

    Returns:
        `TriggerFlags` or ``None`` if the country is absent.
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Trigger"]
        for r in range(5, (ws.max_row or 0) + 1):
            code = ws.cell(r, 1).value
            if code != country_code:
                continue
            isocode = str(ws.cell(r, 2).value or "")
            country = str(ws.cell(r, 3).value or "")
            incgr = ws.cell(r, 5).value
            # Market LIC proxy: incgr == 2 in template samples (Cabo Verde…).
            market = isinstance(incgr, (int, float)) and int(incgr) >= 2
            disaster = False  # full disaster DB not loaded here
            return TriggerFlags(
                country_code=int(code),
                isocode=isocode,
                country=country,
                market_lic=market,
                disaster_flag=disaster,
            )
        return None
    finally:
        wb.close()


def load_input1_market(path: str | Path) -> tuple[bool, float | None]:
    """Load Output 5-2 market-access and EMBI inputs from Input 1.

    Excel Output 5-2 is gated by Input 1 ``C27`` (Market access), not the
    Trigger-sheet ``incgr`` proxy. EMBI is ``C29`` when ``C28`` is Yes.

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        ``(market_access, embi_spread_bps)``. ``embi_spread`` is ``None``
        when the spread is marked unavailable.
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Input 1 - Basics"]
        access = str(ws.cell(27, 3).value or "").strip().lower() == "yes"
        embi_available = str(ws.cell(28, 3).value or "").strip().lower() == "yes"
        raw = ws.cell(29, 3).value
        embi: float | None = None
        if (
            embi_available
            and isinstance(raw, (int, float))
            and not isinstance(raw, bool)
        ):
            embi = float(raw)
        return access, embi
    finally:
        wb.close()
