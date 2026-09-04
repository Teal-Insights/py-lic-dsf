"""Probe catalog for external B-sheets (``B*_ext``).

Year headers: row 8, first data column 3 (matches ``test_stress_dsa._sheet_cached``).
``sut_key`` is ``(scenario_id, sheet_row, year)``.
"""

from __future__ import annotations

from pathlib import Path

from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.probes import Probe

# Confirmed against the bundled template B1_GDP_ext labels (col B).
# B5 residual gross borrowing is on row 87 (row 86 is "Increase"); other
# standard external sheets use row 86.
EXTERNAL_METRIC_ROWS: tuple[tuple[int, str], ...] = (
    (46, "gdp_usd"),
    (50, "real_gdp_growth"),
    (19, "exports_to_gdp"),
    (86, "residual_gross_borrowing"),
    (35, "pv_ppg_to_gdp"),
    (36, "pv_ppg_to_exports"),
    (39, "ppg_ds_to_exports"),
    (40, "ppg_ds_to_revenue"),
)

# Scenario-specific residual row overrides (sheet layout differs).
EXTERNAL_RESIDUAL_ROW: dict[str, int] = {
    "B5_FX": 87,
}

EXTERNAL_SHEETS: dict[str, str] = {
    "A1_Historical": "A1_historical_ext",
    "B1_GDP": "B1_GDP_ext",
    "B3_Exports": "B3_Exports_ext",
    "B4_OtherFlows": "B4_other flows_ext",
    "B5_FX": "B5_depreciation_ext",
    "B6_Combo": "B6_Combo_mkt_ext",
    "C3_Commodity": "C3_Commodity prices_ext",
}

YEAR_ROW = 8
FIRST_COL = 3


def bsheet_external_probes(
    workbook: str | Path,
    scenario_id: str,
) -> tuple[Probe, ...]:
    """Probes for one external B-sheet scenario (B1 / B3 / B5 minimum)."""
    sheet = EXTERNAL_SHEETS.get(scenario_id)
    if sheet is None:
        raise KeyError(
            f"no external B-sheet catalog for {scenario_id!r}; "
            f"known: {sorted(EXTERNAL_SHEETS)}"
        )
    residual_row = EXTERNAL_RESIDUAL_ROW.get(scenario_id, 86)
    rows: list[tuple[int, str]] = []
    for row, label in EXTERNAL_METRIC_ROWS:
        if row == 86:
            rows.append((residual_row, label))
        else:
            rows.append((row, label))
    return probes_for_metric_rows(
        path=workbook,
        sheet=sheet,
        year_row=YEAR_ROW,
        first_col=FIRST_COL,
        scenario_id=scenario_id,
        rows=tuple(rows),
    )
