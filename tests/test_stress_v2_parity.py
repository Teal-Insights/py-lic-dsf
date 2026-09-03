"""Phase 0+ stress-v2 parity harness: catalogs and layer coverage."""

from __future__ import annotations

import pytest

from tests.conftest import WORKBOOK_XLSX, stress_v2_enabled
from tests.parity import compare_probes, read_cached_output
from tests.parity.catalogs.bsheet_external import (
    EXTERNAL_METRIC_ROWS,
    EXTERNAL_RESIDUAL_ROW,
    EXTERNAL_SHEETS,
    bsheet_external_probes,
)
from tests.parity.catalogs.bsheet_public import (
    PUBLIC_METRIC_ROWS,
    PUBLIC_SHEETS,
    bsheet_public_probes,
)
from tests.parity.catalogs.resfin import (
    PV_STRESS_B1_ROWS,
    PV_STRESS_B3_ROWS,
    RESFIN_PUB_B1_ROWS,
    resfin_probes,
)
from tests.parity.stress_sut import build_v2_sut, probes_for_layer

WORKBOOK = WORKBOOK_XLSX


def test_stress_package_is_active_sut() -> None:
    assert stress_v2_enabled() is True


@pytest.mark.parametrize("scenario_id", tuple(EXTERNAL_SHEETS))
def test_bsheet_external_catalog_covers_priority_rows(scenario_id: str) -> None:
    probes = bsheet_external_probes(WORKBOOK, scenario_id)
    rows = {p.row for p in probes}
    expected = {row for row, _label, _phase in EXTERNAL_METRIC_ROWS}
    residual = EXTERNAL_RESIDUAL_ROW.get(scenario_id, 86)
    expected = (expected - {86}) | {residual}
    assert expected <= rows
    assert all(p.sheet == EXTERNAL_SHEETS[scenario_id] for p in probes)
    assert all(
        isinstance(p.sut_key, tuple) and p.sut_key[0] == scenario_id for p in probes
    )
    excel = read_cached_output(WORKBOOK, probes)
    numeric = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert len(numeric) > 0


@pytest.mark.parametrize("scenario_id", tuple(PUBLIC_SHEETS))
def test_bsheet_public_catalog_covers_priority_rows(scenario_id: str) -> None:
    probes = bsheet_public_probes(WORKBOOK, scenario_id)
    rows = {p.row for p in probes}
    expected = {row for row, _label, _phase in PUBLIC_METRIC_ROWS}
    assert expected <= rows
    assert 43 not in rows  # template R43 is interest, not PV/revenue
    assert all(p.sheet == PUBLIC_SHEETS[scenario_id] for p in probes)
    excel = read_cached_output(WORKBOOK, probes)
    numeric = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert len(numeric) > 0


def test_resfin_b1_catalog_covers_fill_and_pv_stress() -> None:
    probes = resfin_probes(WORKBOOK)
    pub_rows = {p.row for p in probes if p.sheet == "PV_ResFin_pub"}
    stress_rows = {p.row for p in probes if p.sheet == "PV Stress"}
    assert {row for row, _ in RESFIN_PUB_B1_ROWS} <= pub_rows
    assert {row for row, _ in PV_STRESS_B1_ROWS} <= stress_rows
    assert {row for row, _ in PV_STRESS_B3_ROWS} <= stress_rows
    excel = read_cached_output(WORKBOOK, probes)
    numeric = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert len(numeric) > 0


@pytest.mark.stress
@pytest.mark.parametrize(
    "layer",
    ("output31", "output32", "bsheet_ext", "bsheet_pub", "resfin"),
)
def test_v2_layer_no_missing_sut(layer: str) -> None:
    """Phase 8: every catalog probe has a v2 SUT value (numeric Excel drifts OK)."""
    probes = probes_for_layer(layer, WORKBOOK)  # type: ignore[arg-type]
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = build_v2_sut(layer, WORKBOOK)  # type: ignore[arg-type]
    report = compare_probes(excel, sut)
    missing = report[report["missing_sut"]]
    assert missing.empty, missing[["sut_key", "year"]].head(20).to_string()
