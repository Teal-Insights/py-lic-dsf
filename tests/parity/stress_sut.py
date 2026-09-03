"""Legacy vs v2 SUT builders for stress-layer differential tests.

V2 builders return an empty mapping until Phases 1+ implement ``stress``.
Legacy builders wrap the current ``lic_dsf.stress`` runners.
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

SutKind = Literal["legacy", "v2"]
Layer = Literal["output31", "output32", "bsheet_ext", "bsheet_pub", "resfin"]

Sut = pd.DataFrame | Mapping[Hashable, object]


def build_v2_sut(layer: Layer, workbook: str | Path) -> dict[Hashable, object] | pd.DataFrame:
    """V2 SUT mapping across ResFin / external / public layers."""
    if layer == "resfin":
        return _v2_resfin(workbook)
    if layer == "bsheet_ext":
        return _v2_bsheet_ext(workbook)
    if layer == "bsheet_pub":
        return _v2_bsheet_pub(workbook)
    if layer == "output31":
        return _v2_output31(workbook)
    if layer == "output32":
        return _v2_output32(workbook)
    return {}


def _v2_resfin(workbook: str | Path) -> dict[Hashable, object]:
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


def _v2_bsheet_ext(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.stress import ScenarioRegistry, StressContext, StressSuite

    ctx = StressContext.from_workbook(workbook)
    results = StressSuite(context=ctx).run_external_standard()
    out: dict[Hashable, object] = {}
    for scenario_id in EXTERNAL_SHEETS:
        result = results.get(scenario_id)
        if result is None or result.external_ratios is None:
            continue
        ratios = result.external_ratios
        for row, attr, _phase in EXTERNAL_METRIC_ROWS:
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


def _v2_output31(workbook: str | Path) -> pd.DataFrame:
    from lic_dsf.stress.suite import build_output31_from_v2_suite

    return build_output31_from_v2_suite(workbook)


def _v2_output32(workbook: str | Path) -> pd.DataFrame:
    from lic_dsf.stress.suite import build_output32_from_v2_suite

    return build_output32_from_v2_suite(workbook)


def _v2_bsheet_pub(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.stress import PublicScenarioRunner, ScenarioRegistry, StressContext

    ctx = StressContext.from_workbook(workbook)
    runner = PublicScenarioRunner(context=ctx)
    out: dict[Hashable, object] = {}
    for scenario_id in PUBLIC_SHEETS:
        result = runner.run(ScenarioRegistry.get(scenario_id))
        assert result.public_ratios is not None
        ratios = result.public_ratios
        for row, attr, _phase in PUBLIC_METRIC_ROWS:
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


def _book_series(book: object, attr: str) -> pd.Series:
    if attr == "gdp_usd":
        return book.macro.gdp_usd()
    if attr == "real_gdp_growth":
        return book.macro.real_gdp_growth()
    if attr == "exports_to_gdp":
        return book.exports_to_gdp()
    if attr == "residual_gross_borrowing":
        return book.residual_borrowing
    if attr == "pv_ppg_to_gdp":
        return book.pv_ppg_external_to_gdp()
    if attr == "pv_ppg_to_exports":
        return book.pv_ppg_external_to_exports()
    if attr == "ppg_ds_to_exports":
        return book.ppg_debt_service_to_exports()
    if attr == "ppg_ds_to_revenue":
        return book.ppg_debt_service_to_revenue()
    if attr == "gdp_lcu":
        return book.gdp_lcu()
    if attr == "public_gfn":
        return book.public_gfn()
    if attr == "pv_public_to_gdp":
        return book.pv_public_debt_to_gdp()
    if attr == "pv_public_to_revenue":
        return book.pv_public_debt_to_revenue_grants()
    if attr == "ds_to_revenue":
        return book.debt_service_to_revenue_grants()
    raise KeyError(attr)


def _legacy_output31(workbook: str | Path) -> pd.DataFrame:
    from lic_dsf.load import (
        load_ci_summary,
        load_core,
        load_input1_market,
        load_input6_standard,
        load_input7_residual_params,
    )
    from lic_dsf.output import output_31_table
    from lic_dsf.stress import (
        run_a1_historical_external,
        run_standard_external_stress,
        run_standard_public_stress,
    )

    macro, external, ext_base, _pub = load_core(workbook)
    input6 = load_input6_standard(workbook)
    residual = load_input7_residual_params(workbook)
    market_access, _embi = load_input1_market(workbook)
    suite = run_standard_external_stress(macro, external, input6, residual)
    historical = run_a1_historical_external(macro, external, residual)
    public = run_standard_public_stress(
        macro, external, input6, residual, market_access=market_access
    )
    thresh = load_ci_summary(workbook).thresholds.as_dict()
    return output_31_table(
        ext_base,
        historical=historical,
        external_stress=suite,
        public_stress=public,
        thresholds=thresh,
    )


def _legacy_output32(workbook: str | Path) -> pd.DataFrame:
    from lic_dsf.load import (
        load_ci_summary,
        load_core,
        load_input1_market,
        load_input6_standard,
        load_input7_residual_params,
        load_tailored_params,
    )
    from lic_dsf.load.tailored import load_customized_public_spec
    from lic_dsf.output import output_32_table
    from lic_dsf.stress import run_standard_public_stress, run_tailored_public_stress

    macro, external, _ext, pub_base = load_core(workbook)
    input6 = load_input6_standard(workbook)
    residual = load_input7_residual_params(workbook)
    tailored_params = load_tailored_params(workbook)
    market_access, _embi = load_input1_market(workbook)
    public = run_standard_public_stress(
        macro, external, input6, residual, market_access=market_access
    )
    tailored = run_tailored_public_stress(
        macro,
        external,
        residual,
        tailored_params,
        input6,
        custom_spec=load_customized_public_spec(workbook),
    )
    thresh = load_ci_summary(workbook).thresholds.public_pv_debt_to_gdp
    return output_32_table(
        pub_base,
        public_stress=public,
        tailored=tailored,
        public_threshold=thresh,
    )


def _legacy_bsheet_ext(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.load import (
        load_core,
        load_input6_standard,
        load_input7_residual_params,
    )
    from lic_dsf.stress import run_standard_external_stress

    macro, external, _ext, _pub = load_core(workbook)
    input6 = load_input6_standard(workbook)
    residual = load_input7_residual_params(workbook)
    suite = run_standard_external_stress(macro, external, input6, residual)
    out: dict[Hashable, object] = {}
    for scenario_id in EXTERNAL_SHEETS:
        book = suite[scenario_id]
        for row, attr, _phase in EXTERNAL_METRIC_ROWS:
            series = _book_series(book, attr)
            if attr == "residual_gross_borrowing":
                row = EXTERNAL_RESIDUAL_ROW.get(scenario_id, row)
            out.update(_series_cells(scenario_id, series, (row,)))
    return out


def _legacy_bsheet_pub(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.load import (
        load_core,
        load_input6_standard,
        load_input7_residual_params,
    )
    from lic_dsf.stress import run_b1_gdp_public

    macro, external, _ext, _pub = load_core(workbook)
    input6 = load_input6_standard(workbook)
    residual = load_input7_residual_params(workbook)
    book = run_b1_gdp_public(macro, external, input6, residual)
    out: dict[Hashable, object] = {}
    for row, attr, _phase in PUBLIC_METRIC_ROWS:
        series = _book_series(book, attr)
        out.update(_series_cells("B1_GDP", series, (row,)))
    return out


def _legacy_resfin(workbook: str | Path) -> dict[Hashable, object]:
    from lic_dsf.load import (
        load_core,
        load_input6_standard,
        load_input7_residual_params,
    )
    from lic_dsf.stress import (
        public_residual_gap,
        run_b1_gdp_external,
        run_b1_gdp_public,
        run_b3_exports_external,
    )

    macro, external, _ext, _pub = load_core(workbook)
    input6 = load_input6_standard(workbook)
    residual = load_input7_residual_params(workbook)
    ext_book = run_b1_gdp_external(macro, external, input6, residual)
    pub_book = run_b1_gdp_public(macro, external, input6, residual)
    b3_book = run_b3_exports_external(macro, external, input6, residual)
    out: dict[Hashable, object] = {}
    pub_gap = public_residual_gap(
        pub_book.public_gfn(), macro.public_gfn(), pub_book.years
    )
    fill_map = {
        67: pub_gap,
        69: ext_book.residual_borrowing,
        72: pub_book.resfin.fill.external_mlt_usd,
        75: pub_book.resfin.ext.pv,
        77: pub_book.resfin.ext.interest,
        78: pub_book.resfin.ext.amortization,
        85: pub_book.resfin.fill.domestic_mlt_lcu,
        90: pub_book.resfin.dom_mlt.interest,
        91: pub_book.resfin.dom_mlt.amortization,
        98: pub_book.resfin.fill.domestic_st_lcu,
        99: pub_book.resfin.dom_st.interest,
    }
    for row, _label in RESFIN_PUB_B1_ROWS:
        series = fill_map.get(row)
        if series is None:
            continue
        out.update(_series_cells("B1_GDP", series, (row,)))
    pv_map = {
        29: ext_book.residual_borrowing,
        32: ext_book.resfin_pv,
        35: ext_book.resfin_interest,
        36: ext_book.resfin_amortization,
    }
    for row, _label in PV_STRESS_B1_ROWS:
        series = pv_map.get(row)
        if series is None:
            continue
        out.update(_series_cells("B1_GDP", series, (row,)))
    b3_map = {
        46: b3_book.residual_borrowing,
        49: b3_book.resfin_pv,
        52: b3_book.resfin_interest,
        53: b3_book.resfin_amortization,
    }
    for row, _label in PV_STRESS_B3_ROWS:
        out.update(_series_cells("B3_Exports", b3_map[row], (row,)))
    return out


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
        probes: list[Probe] = []
        for scenario_id in PUBLIC_SHEETS:
            probes.extend(bsheet_public_probes(workbook, scenario_id))
        return tuple(probes)
    if layer == "resfin":
        return resfin_probes(workbook)
    raise KeyError(layer)


def build_sut(layer: Layer, kind: SutKind, workbook: str | Path) -> Sut:
    """Build the SUT mapping or Output-shaped table for ``layer`` / ``kind``."""
    if kind == "v2":
        return build_v2_sut(layer, workbook)
    if layer == "output31":
        return _legacy_output31(workbook)
    if layer == "output32":
        return _legacy_output32(workbook)
    if layer == "bsheet_ext":
        return _legacy_bsheet_ext(workbook)
    if layer == "bsheet_pub":
        return _legacy_bsheet_pub(workbook)
    if layer == "resfin":
        return _legacy_resfin(workbook)
    raise KeyError(layer)
