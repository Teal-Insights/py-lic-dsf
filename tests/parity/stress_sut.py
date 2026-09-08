"""SUT builders for stress-layer differential tests.

Each layer maps a probe catalog onto values produced by ``lic_dsf.stress``:
``(scenario_id, sheet_row, year)`` cells for B-sheet / ResFin layers, and an
Output 3-x shaped table for the Output layers.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from pathlib import Path
from typing import Literal

import pandas as pd

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
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes
from tests.parity.catalogs.resfin import (
    PV_STRESS_B1_ROWS,
    PV_STRESS_B3_ROWS,
    RESFIN_PUB_B1_ROWS,
    resfin_probes,
)
from tests.parity.probes import Probe

Layer = Literal["output31", "output32", "bsheet_ext", "bsheet_pub", "resfin"]

Sut = pd.DataFrame | Mapping[Hashable, object]


def build_sut(layer: Layer, workbook: str | Path) -> Sut:
    """Build the SUT mapping or Output-shaped table for ``layer``."""
    if layer == "resfin":
        return _resfin(workbook)
    if layer == "bsheet_ext":
        return _bsheet_ext(workbook)
    if layer == "bsheet_pub":
        return _bsheet_pub(workbook)
    if layer == "output31":
        from lic_dsf.stress.suite import build_output31_from_suite

        return build_output31_from_suite(workbook)
    if layer == "output32":
        from lic_dsf.stress.suite import build_output32_from_suite

        return build_output32_from_suite(workbook)
    raise KeyError(layer)


def probes_for_layer(layer: Layer, workbook: str | Path) -> tuple[Probe, ...]:
    """Return the probe catalog for ``layer``."""
    if layer == "output31":
        return output_31_probes(workbook)
    if layer == "output32":
        return output_32_probes(workbook)
    if layer == "bsheet_ext":
        probes: list[Probe] = []
        for scenario_id in EXTERNAL_SHEETS:
            probes.extend(bsheet_external_probes(workbook, scenario_id))
        return tuple(probes)
    if layer == "bsheet_pub":
        probes = []
        for scenario_id in PUBLIC_SHEETS:
            probes.extend(bsheet_public_probes(workbook, scenario_id))
        return tuple(probes)
    if layer == "resfin":
        return resfin_probes(workbook)
    raise KeyError(layer)


def _resfin(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.stress import ScenarioRegistry, StressContext, StressScenarioRunner

    ctx = StressContext.from_workbook(workbook)
    runner = StressScenarioRunner(context=ctx)
    out: dict[Hashable, object] = {}

    b1 = runner.run(ScenarioRegistry.get("B1_GDP"))
    assert b1.resfin.public is not None
    pub = b1.resfin.public
    fill_map = {
        67: b1.resfin.public_gap,
        69: b1.external_gap.gap,
        72: pub.fill.external_mlt_usd,
        75: pub.ext.pv,
        77: pub.ext.interest,
        78: pub.ext.amortization,
        85: pub.fill.domestic_mlt_lcu,
        90: pub.dom_mlt.interest,
        91: pub.dom_mlt.amortization,
        98: pub.fill.domestic_st_lcu,
        99: pub.dom_st.interest,
    }
    for row, _label in RESFIN_PUB_B1_ROWS:
        series = fill_map.get(row)
        if series is None:
            continue
        out.update(_series_cells("B1_GDP", series, (row,)))
    assert b1.resfin.external is not None
    b1_ext = b1.resfin.external
    pv_b1 = {
        29: b1.external_gap.gap,
        32: b1_ext.pv,
        35: b1_ext.interest,
        36: b1_ext.amortization,
    }
    for row, _label in PV_STRESS_B1_ROWS:
        out.update(_series_cells("B1_GDP", pv_b1[row], (row,)))

    b3 = runner.run(ScenarioRegistry.get("B3_Exports"))
    assert b3.resfin.external is not None
    b3_ext = b3.resfin.external
    pv_b3 = {
        46: b3.external_gap.gap,
        49: b3_ext.pv,
        52: b3_ext.interest,
        53: b3_ext.amortization,
    }
    for row, _label in PV_STRESS_B3_ROWS:
        out.update(_series_cells("B3_Exports", pv_b3[row], (row,)))
    return out


def _bsheet_ext(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.stress import ExternalScenarioRunner, ScenarioRegistry, StressContext

    ctx = StressContext.from_workbook(workbook)
    runner = ExternalScenarioRunner(context=ctx)
    out: dict[Hashable, object] = {}
    for scenario_id in EXTERNAL_SHEETS:
        result = runner.run(ScenarioRegistry.get(scenario_id))
        assert result.external_ratios is not None
        ratios = result.external_ratios
        for row, attr in EXTERNAL_METRIC_ROWS:
            if attr == "gdp_usd":
                series = result.path.shocked.gdp_usd()
            elif attr == "real_gdp_growth":
                series = result.path.shocked.real_gdp_growth()
            elif attr == "exports_to_gdp":
                series = ratios.exports_to_gdp()
            elif attr == "residual_gross_borrowing":
                series = result.external_gap.gap
                row = EXTERNAL_RESIDUAL_ROW.get(scenario_id, row)
            elif attr == "pv_ppg_to_gdp":
                series = ratios.pv_ppg_external_to_gdp()
            elif attr == "pv_ppg_to_exports":
                series = ratios.pv_ppg_external_to_exports()
            elif attr == "ppg_ds_to_exports":
                series = ratios.ppg_debt_service_to_exports()
            elif attr == "ppg_ds_to_revenue":
                series = ratios.ppg_debt_service_to_revenue()
            else:
                continue
            out.update(_series_cells(scenario_id, series, (row,)))
    return out


def _bsheet_pub(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.stress import PublicScenarioRunner, ScenarioRegistry, StressContext

    ctx = StressContext.from_workbook(workbook)
    runner = PublicScenarioRunner(context=ctx)
    out: dict[Hashable, object] = {}
    for scenario_id in PUBLIC_SHEETS:
        result = runner.run(ScenarioRegistry.get(scenario_id))
        assert result.public_ratios is not None
        ratios = result.public_ratios
        for row, attr in PUBLIC_METRIC_ROWS:
            if attr == "gdp_lcu":
                series = ratios.gdp_lcu()
            elif attr == "real_gdp_growth":
                series = result.path.shocked.real_gdp_growth()
            elif attr == "public_gfn":
                series = ratios.public_gfn()
            elif attr == "pv_public_to_gdp":
                series = ratios.pv_public_debt_to_gdp()
            elif attr == "pv_public_to_revenue":
                series = ratios.pv_public_debt_to_revenue_grants()
            elif attr == "ds_to_revenue":
                series = ratios.debt_service_to_revenue_grants()
            else:
                continue
            out.update(_series_cells(scenario_id, series, (row,)))
    return out


def _series_cells(
    scenario_id: str,
    series: pd.Series,
    rows: tuple[int, ...],
) -> dict[tuple[str, int, int], object]:
    out: dict[tuple[str, int, int], object] = {}
    for row in rows:
        for year, value in series.items():
            out[(scenario_id, row, int(year))] = value
    return out
