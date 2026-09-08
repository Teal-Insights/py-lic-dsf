"""Tailored scenarios (C1 / C3 / C4): Output 3-1 and 3-2 Excel parity."""

from __future__ import annotations

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
