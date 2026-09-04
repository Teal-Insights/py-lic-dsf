"""Probe catalog for public B-sheets (``B*_pub``).

Year headers: row 7, first data column 3 (matches
``test_residual_financing_applied._sheet_row``).

Row 43 on this template is *average nominal interest on public debt*, not
PV/revenue. PV public / revenue+grants is row 95.
"""

from __future__ import annotations

from pathlib import Path

from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.probes import Probe

PUBLIC_METRIC_ROWS: tuple[tuple[int, str], ...] = (
    (41, "gdp_lcu"),
    (42, "real_gdp_growth"),
    (90, "public_gfn"),
    (13, "pv_public_to_gdp"),
    (95, "pv_public_to_revenue"),
    (93, "ds_to_revenue"),
)

# B3/B4 have no ``*_pub`` sheet: Output 3-2 for those ids is baseline public
# plus the external ResFin overlay (``Baseline - public`` R91/R92).
PUBLIC_SHEETS: dict[str, str] = {
    "B1_GDP": "B1_GDP_pub",
    "B2_PrimaryBalance": "B2_PB_mkt_pub",
    "B5_FX": "B5_depreciation_pub",
    "B6_Combo": "B6_combo_mkt_pub",
    "C1_CombinedCL": "C1_Combined CL",
    "C3_Commodity": "C3_commodity_prices_pub",
}

YEAR_ROW = 7
FIRST_COL = 3


def bsheet_public_probes(
    workbook: str | Path,
    scenario_id: str,
) -> tuple[Probe, ...]:
    """Probes for one public B-sheet scenario."""
    sheet = PUBLIC_SHEETS.get(scenario_id)
    if sheet is None:
        raise KeyError(
            f"no public B-sheet catalog for {scenario_id!r}; "
            f"known: {sorted(PUBLIC_SHEETS)}"
        )
    return probes_for_metric_rows(
        path=workbook,
        sheet=sheet,
        year_row=YEAR_ROW,
        first_col=FIRST_COL,
        scenario_id=scenario_id,
        rows=PUBLIC_METRIC_ROWS,
    )
