"""Structural tests for the stress context and scenario registry."""

from __future__ import annotations

from typing import get_args

import pytest

from lic_dsf.stress import (
    OutputBinding,
    ResidualPolicyKind,
    ScenarioRegistry,
    ScenarioSpec,
    ShockKind,
    StressContext,
    StressScenarioRunner,
)
from lic_dsf.stress.types import StressScenarioId
from tests.conftest import WORKBOOK_XLSX

WORKBOOK = WORKBOOK_XLSX


def test_stress_context_from_workbook() -> None:
    ctx = StressContext.from_workbook(WORKBOOK)
    assert ctx.macro is not None
    assert ctx.external is not None
    assert ctx.ext_base is not None
    assert ctx.pub_base is not None
    assert ctx.input6 is not None
    assert ctx.residual is not None
    assert ctx.tailored is not None
    assert isinstance(ctx.market_access, bool)
    assert ctx.macro.inputs.years == ctx.ext_base.years


def test_registry_covers_every_stress_scenario_id() -> None:
    known = set(ScenarioRegistry.all_specs())
    expected = set(get_args(StressScenarioId))
    assert known == expected


def test_standard_registry_ids() -> None:
    assert set(ScenarioRegistry.STANDARD) == {
        "A1_Historical",
        "B1_GDP",
        "B2_PrimaryBalance",
        "B3_Exports",
        "B4_OtherFlows",
        "B5_FX",
        "B6_Combo",
    }


def test_b1_ext_r86_zero() -> None:
    spec = ScenarioRegistry.get("B1_GDP")
    assert spec.ext_r86_zero is True
    assert spec.residual_policy is ResidualPolicyKind.CAPPED
    assert spec.shock_kind is ShockKind.GDP
    assert spec.output_binding.output_31_source == "external"


def test_b2_absolute_policy_and_output_binding() -> None:
    spec = ScenarioRegistry.get("B2_PrimaryBalance")
    assert spec.residual_policy is ResidualPolicyKind.ABSOLUTE
    assert spec.couple_ext_r86 is True
    assert spec.market_access is None  # from Input 1
    assert spec.output_binding == OutputBinding(
        output_31_source="public_external_methods",
        output_32_source="public",
    )
    ctx = StressContext.from_workbook(WORKBOOK)
    assert ScenarioRegistry.resolve_market_access(
        spec, context_market_access=ctx.market_access
    ) is ctx.market_access


def test_b5_b6_fx_revalue_off_matches_excel_cache() -> None:
    """Cached B5/B6 sheets do not include LC-NR reval in R35."""
    assert ScenarioRegistry.get("B5_FX").fx_revalue_portfolio is False
    assert ScenarioRegistry.get("B6_Combo").fx_revalue_portfolio is False
    assert ScenarioRegistry.get("B3_Exports").fx_revalue_portfolio is False
    assert ScenarioRegistry.get("C4_Market").fx_revalue_portfolio is False
    assert ScenarioRegistry.get("C4_Market").ext_r86_zero is True


def test_tailored_scenarios_are_registered() -> None:
    for sid in (
        "A2_Custom",
        "C1_CombinedCL",
        "C2_NaturalDisaster",
        "C3_Commodity",
        "C4_Market",
    ):
        spec = ScenarioRegistry.get(sid)
        assert spec.id == sid
        assert spec.shock_kind.value.startswith("tailored") or sid == "A2_Custom"


def test_unknown_id_raises_key_error() -> None:
    with pytest.raises(KeyError, match="unknown"):
        ScenarioRegistry.get("NotAScenario")  # type: ignore[arg-type]


def test_runner_returns_shocked_macro_path() -> None:
    ctx = StressContext.from_workbook(WORKBOOK)
    runner = StressScenarioRunner(context=ctx)
    result = runner.run(ScenarioRegistry.get("B1_GDP"))
    from lic_dsf.stress.path import ShockedMacroPath
    from lic_dsf.stress.runner import ScenarioRunResult

    assert isinstance(result, ScenarioRunResult)
    assert isinstance(result.path, ShockedMacroPath)
    assert result.external_gap is not None
    assert result.resfin is not None
    assert result.external_ratios is not None
    assert result.scenario_id == "B1_GDP"
    assert (
        result.path.metadata.shock_window_years[0]
        >= ctx.macro.inputs.first_projection_year
    )

def test_runner_accepts_tailored() -> None:
    ctx = StressContext.from_workbook(WORKBOOK)
    runner = StressScenarioRunner(context=ctx)
    result = runner.run(ScenarioRegistry.get("C1_CombinedCL"))
    assert result.external_ratios is not None
    assert result.scenario_id == "C1_CombinedCL"


def test_scenario_spec_is_frozen() -> None:
    spec = ScenarioRegistry.get("B1_GDP")
    assert isinstance(spec, ScenarioSpec)
    with pytest.raises(AttributeError):
        spec.ext_r86_zero = False  # type: ignore[misc]
