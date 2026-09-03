"""Probe catalog for residual-financing sheets.

``PV_ResFin_pub`` B1 fill: year row 2, first column 4.
``PV Stress`` B1 external MLT overlay: year row 3, first column 4.
``PV_ResFin-add.int.cost - mkt`` B2 assumptions: year row 34, first column 2
(Phase 7; layout is not a standard B-sheet).
"""

from __future__ import annotations

from pathlib import Path

from tests.parity.catalogs.layout import probes_for_metric_rows
from tests.parity.probes import Probe

PV_RESFIN_PUB_SHEET = "PV_ResFin_pub"
PV_STRESS_SHEET = "PV Stress"
ADD_INT_SHEET = "PV_ResFin-add.int.cost - mkt"

# B1 block on PV_ResFin_pub (starts at "Bounds Test 1" row 65).
RESFIN_PUB_B1_ROWS: tuple[tuple[int, str], ...] = (
    (67, "new_borrowing_lcu"),
    (69, "external_dsa_borrowing_usd"),
    (72, "new_forex_borrowing_usd"),
    (75, "pv_new_forex_usd"),
    (77, "forex_interest"),
    (78, "forex_amortization"),
    (85, "dom_mlt_borrowing"),
    (90, "dom_mlt_interest"),
    (91, "dom_mlt_amortization"),
    (98, "dom_st_borrowing"),
    (99, "dom_st_interest"),
)

# B6 combo block on PV_ResFin_pub (B1 block + 141 rows).
_RESFIN_PUB_B6_ROW_OFFSET = 141
RESFIN_PUB_B6_ROWS: tuple[tuple[int, str], ...] = tuple(
    (row + _RESFIN_PUB_B6_ROW_OFFSET, label) for row, label in RESFIN_PUB_B1_ROWS
)

# B1 block on PV Stress (starts at row 27).
PV_STRESS_B1_ROWS: tuple[tuple[int, str], ...] = (
    (29, "new_forex_borrowing_usd"),
    (32, "pv_new_forex_usd"),
    (35, "interest"),
    (36, "amortization"),
)

# B3 block on PV Stress (starts at row 44).
PV_STRESS_B3_ROWS: tuple[tuple[int, str], ...] = (
    (46, "new_forex_borrowing_usd"),
    (49, "pv_new_forex_usd"),
    (52, "interest"),
    (53, "amortization"),
)

# Phase 7 stub: B2 market-access assumption years in cols B–C.
ADD_INT_B2_ROWS: tuple[tuple[int, str], ...] = (
    (35, "pb_deviation_ppt"),
    (39, "additional_domestic_interest_rate"),
)


def resfin_pub_b1_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """B1 three-way fill on ``PV_ResFin_pub``."""
    return probes_for_metric_rows(
        path=workbook,
        sheet=PV_RESFIN_PUB_SHEET,
        year_row=2,
        first_col=4,
        scenario_id="B1_GDP",
        rows=RESFIN_PUB_B1_ROWS,
    )


def resfin_pub_b6_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """B6 combo three-way fill on ``PV_ResFin_pub``."""
    return probes_for_metric_rows(
        path=workbook,
        sheet=PV_RESFIN_PUB_SHEET,
        year_row=2,
        first_col=4,
        scenario_id="B6_Combo",
        rows=RESFIN_PUB_B6_ROWS,
    )


def pv_stress_b1_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """B1 external MLT PV / interest / amort on ``PV Stress``."""
    return probes_for_metric_rows(
        path=workbook,
        sheet=PV_STRESS_SHEET,
        year_row=3,
        first_col=4,
        scenario_id="B1_GDP",
        rows=PV_STRESS_B1_ROWS,
    )


def pv_stress_b3_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """B3 external MLT PV / interest / amort on ``PV Stress``."""
    return probes_for_metric_rows(
        path=workbook,
        sheet=PV_STRESS_SHEET,
        year_row=3,
        first_col=4,
        scenario_id="B3_Exports",
        rows=PV_STRESS_B3_ROWS,
    )


def add_int_b2_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """B2 market add.int assumption rows (Phase 7)."""
    return probes_for_metric_rows(
        path=workbook,
        sheet=ADD_INT_SHEET,
        year_row=34,
        first_col=2,
        scenario_id="B2_PrimaryBalance",
        rows=ADD_INT_B2_ROWS,
    )


def resfin_probes(workbook: str | Path) -> tuple[Probe, ...]:
    """All ResFin probes (B1 fill + PV Stress B1/B3 + add.int stub)."""
    return (
        *resfin_pub_b1_probes(workbook),
        *pv_stress_b1_probes(workbook),
        *pv_stress_b3_probes(workbook),
        *add_int_b2_probes(workbook),
    )
