"""Tailored scenarios (C1 / C3 / C4): Output 3-1 and 3-2 Excel parity."""

from __future__ import annotations

from dataclasses import replace

import pytest

from lic_dsf.stress import (
    ExternalScenarioRunner,
    PublicScenarioRunner,
    ScenarioRegistry,
    StressContext,
)
from lic_dsf.stress.output_map import (
    build_output31_external_table,
    build_output32_table,
)
from lic_dsf.stress.shocks.tailored import applicable_tailored_ids
from lic_dsf.stress.shocks.tailored_params import apply_natural_disaster_shock
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes

WORKBOOK = WORKBOOK_XLSX

_TAILORED = (
    ("C1_CombinedCL", "C1. Combined contingent liabilities"),
    ("C3_Commodity", "C3. Commodity price"),
    ("C4_Market", "C4. Market Financing"),
)
# Output 3-2 for C4 is the external ResFin overlay on baseline public; C1/C3
# own a public path.
_OUTPUT32_EXTERNAL = frozenset({"C4_Market"})


@pytest.fixture(scope="module")
def output31_tailored(stress_context: StressContext):
    runner = ExternalScenarioRunner(context=stress_context)
    results = {
        sid: runner.run(ScenarioRegistry.get(sid))  # type: ignore[arg-type]
        for sid, _ in _TAILORED
    }
    # C1 is coupled: prefer its public ratios on Output 3-1 (as the suite does).
    public = {}
    c1 = results.get("C1_CombinedCL")
    if c1 is not None and c1.public_ratios is not None:
        public["C1_CombinedCL"] = results.pop("C1_CombinedCL")
    return build_output31_external_table(
        stress_context.ext_base, results, public_results=public
    )


def _probes(catalog, label: str):
    probes = tuple(
        p
        for p in catalog(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    return probes, excel


def test_c1_cl_shock_pct_from_input2(stress_context: StressContext) -> None:
    """C1 uses Input 2 Debt Coverage F25 total (Excel AA60), not a flat 10%."""
    assert stress_context.tailored is not None
    assert float(stress_context.tailored.cl_shock_pct_gdp) == pytest.approx(
        9.375480101740473, abs=1e-9
    )


def test_c2_not_applicable_when_disaster_flag_off(
    stress_context: StressContext,
) -> None:
    """Template Input 6 C9=No → C2 is n.a. and excluded from tailored ids."""
    assert stress_context.tailored is not None
    assert stress_context.tailored.natural_disaster is False
    assert "C2_NaturalDisaster" not in applicable_tailored_ids(stress_context.tailored)


def test_c2_disaster_moves_output31_vs_baseline(
    stress_context: StressContext,
) -> None:
    """With disaster on, year-2 Output 3-1 C2 PV/GDP differs from baseline.

    Excel C2 feeds other-debt flows into public ResFin (plus associated GDP /
    exports ppt shocks). Zero sizes leave the macro path unchanged.
    """
    assert stress_context.tailored is not None
    years = list(stress_context.macro.inputs.years)
    first = stress_context.macro.inputs.first_projection_year
    shock_y = [y for y in years if y >= first][1]
    base_other = float(
        stress_context.macro.inputs.other_debt_creating_flows.reindex(years)
        .fillna(0.0)
        .loc[shock_y]
    )

    unchanged = apply_natural_disaster_shock(
        stress_context.macro.inputs,
        replace(
            stress_context.tailored,
            disaster_shock_pct_gdp=0.0,
            disaster_gdp_shock_ppt=0.0,
            disaster_exports_shock_ppt=0.0,
        ),
    )
    assert float(
        unchanged.other_debt_creating_flows.reindex(years).fillna(0.0).loc[shock_y]
    ) == pytest.approx(base_other)
    assert float(unchanged.gdp_usd.loc[shock_y]) == pytest.approx(
        float(stress_context.macro.inputs.gdp_usd.loc[shock_y])
    )

    on_params = replace(stress_context.tailored, natural_disaster=True)
    shocked = apply_natural_disaster_shock(stress_context.macro.inputs, on_params)
    assert float(shocked.other_debt_creating_flows.loc[shock_y]) > base_other
    assert float(shocked.gdp_usd.loc[shock_y]) < float(
        stress_context.macro.inputs.gdp_usd.loc[shock_y]
    )
    assert float(shocked.exports.loc[shock_y]) < float(
        stress_context.macro.inputs.exports.loc[shock_y]
    )

    ctx_on = replace(stress_context, tailored=on_params)
    result = ExternalScenarioRunner(context=ctx_on).run(
        ScenarioRegistry.get("C2_NaturalDisaster")
    )
    assert result.public_ratios is not None
    c2 = result.public_ratios.pv_ppg_external_to_gdp()
    base = stress_context.ext_base.pv_ppg_external_to_gdp()
    assert float(c2.loc[shock_y]) != pytest.approx(float(base.loc[shock_y]), abs=1e-6)
    assert float(c2.loc[shock_y]) > float(base.loc[shock_y])


@pytest.mark.parametrize(("scenario_id", "label"), _TAILORED)
def test_tailored_output31_matches_excel(
    scenario_id: str, label: str, output31_tailored
) -> None:
    probes, excel = _probes(output_31_probes, label)
    assert_all_passed(compare_probes(excel, output31_tailored, probes=probes))


@pytest.mark.parametrize(("scenario_id", "label"), _TAILORED)
def test_tailored_output32_matches_excel(
    scenario_id: str, label: str, stress_context: StressContext
) -> None:
    runner_cls = (
        ExternalScenarioRunner
        if scenario_id in _OUTPUT32_EXTERNAL
        else PublicScenarioRunner
    )
    result = runner_cls(context=stress_context).run(
        ScenarioRegistry.get(scenario_id)  # type: ignore[arg-type]
    )
    sut = build_output32_table(stress_context.pub_base, {scenario_id: result})
    probes, excel = _probes(output_32_probes, label)
    assert_all_passed(compare_probes(excel, sut, probes=probes))
