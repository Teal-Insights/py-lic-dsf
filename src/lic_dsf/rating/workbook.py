"""Load CI Summary / Classification / Trigger lookups from the workbook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastpyxl import load_workbook

from lic_dsf.rating.classification import (
    ApplicableThresholds,
    DebtCarryingCapacity,
    classify_ci,
)


@dataclass(frozen=True, slots=True)
class CiSummarySnapshot:
    """CI Summary snapshot for the template country."""

    country: str
    country_code: int
    ci_score: float
    dcc: DebtCarryingCapacity
    thresholds: ApplicableThresholds
    dcc_current: str
    dcc_previous: str
    dcc_two_previous: str


@dataclass(frozen=True, slots=True)
class TriggerFlags:
    """Sparse Trigger-sheet flags used by rating modules."""

    country_code: int
    isocode: str
    country: str
    market_lic: bool
    disaster_flag: bool


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
