"""Probe catalog for public B-sheets (``B*_pub``).

Year headers: row 7, first data column 3 (matches
``test_residual_financing_applied._sheet_row``).

Row 43 on this template is *average nominal interest on public debt*, not
PV/revenue. PV public / revenue+grants is row 95. See
``docs/plans/stress-v2/KNOWN_GAPS.md``.
"""

from __future__ import annotations

from pathlib import Path

from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.probes import Probe

PUBLIC_METRIC_ROWS: tuple[tuple[int, str, str], ...] = (
    (41, "gdp_lcu", "Phase 2"),
    (42, "real_gdp_growth", "Phase 2"),
    (90, "public_gfn", "Phase 6"),
    (13, "pv_public_to_gdp", "Phase 6"),
    (95, "pv_public_to_revenue", "Phase 6"),
    (93, "ds_to_revenue", "Phase 6"),
)

PUBLIC_SHEETS: dict[str, str] = {
    "B1_GDP": "B1_GDP_pub",
    "B2_PrimaryBalance": "B2_PB_mkt_pub",
    "B3_Exports": "B3_Exports_pub",
    "B4_OtherFlows": "B4_other flows_pub",
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
    rows = tuple((row, label) for row, label, _phase in PUBLIC_METRIC_ROWS)
    return probes_for_metric_rows(
        path=workbook,
        sheet=sheet,
        year_row=YEAR_ROW,
        first_col=FIRST_COL,
        scenario_id=scenario_id,
        rows=rows,
    )
