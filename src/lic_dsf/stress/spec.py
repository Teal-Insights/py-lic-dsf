"""Declarative scenario recipes and registry for stress.

``ResidualPolicyKind`` selects :class:`~lic_dsf.stress.resfin.CappedResidualPolicy`
or :class:`~lic_dsf.stress.resfin.AbsoluteResidualPolicy`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Literal, get_args

from lic_dsf.stress.types import StressScenarioId

Output31Source = Literal["external", "public_external_methods"]
Output32Source = Literal["public"]


class ShockKind(str, Enum):
    """Which macro / tailored shock adapter a scenario uses."""

    HISTORICAL = "historical"
    GDP = "gdp"
    PRIMARY_BALANCE = "primary_balance"
    EXPORTS = "exports"
    OTHER_FLOWS = "other_flows"
    FX = "fx"
    COMBO = "combo"
    TAILORED_CUSTOM = "tailored_custom"
    TAILORED_COMBINED_CL = "tailored_combined_cl"
    TAILORED_NATURAL_DISASTER = "tailored_natural_disaster"
    TAILORED_COMMODITY = "tailored_commodity"
    TAILORED_MARKET = "tailored_market"


class ResidualPolicyKind(str, Enum):
    """ResFin split policy marker for :func:`lic_dsf.stress.resfin.policy_from_kind`."""

    CAPPED = "capped"
    ABSOLUTE = "absolute"


@dataclass(frozen=True, slots=True)
class OutputBinding:
    """Which ratio book feeds Output 3-1 / 3-2 rows for this scenario.

    Excel Chart Data wires Output 3-1 B2 to public-book external-ratio methods
    (``B2_PB_*_pub``), not an external B2 sheet.
    """

    output_31_source: Output31Source
    output_32_source: Output32Source = "public"


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """Single source of truth for Excel B-sheet scenario semantics."""

    id: StressScenarioId
    shock_kind: ShockKind
    residual_policy: ResidualPolicyKind
    # None means resolve from ``StressContext.market_access`` (Input 1).
    market_access: bool | None
    couple_ext_r86: bool
    fx_revalue_portfolio: bool
    ext_r86_zero: bool
    output_binding: OutputBinding


def _standard(
    scenario_id: StressScenarioId,
    shock_kind: ShockKind,
    *,
    residual_policy: ResidualPolicyKind = ResidualPolicyKind.CAPPED,
    market_access: bool | None = False,
    couple_ext_r86: bool = False,
    fx_revalue_portfolio: bool = False,
    ext_r86_zero: bool = False,
    output_31_source: Output31Source = "external",
) -> ScenarioSpec:
    return ScenarioSpec(
        id=scenario_id,
        shock_kind=shock_kind,
        residual_policy=residual_policy,
        market_access=market_access,
        couple_ext_r86=couple_ext_r86,
        fx_revalue_portfolio=fx_revalue_portfolio,
        ext_r86_zero=ext_r86_zero,
        output_binding=OutputBinding(output_31_source=output_31_source),
    )


def _tailored(
    scenario_id: StressScenarioId,
    shock_kind: ShockKind,
    *,
    fx_revalue_portfolio: bool = False,
    couple_ext_r86: bool = False,
    ext_r86_zero: bool = False,
    output_31_source: Output31Source = "external",
    residual_policy: ResidualPolicyKind = ResidualPolicyKind.CAPPED,
) -> ScenarioSpec:
    """Tailored A2/C* recipe."""
    return ScenarioSpec(
        id=scenario_id,
        shock_kind=shock_kind,
        residual_policy=residual_policy,
        market_access=False,
        couple_ext_r86=couple_ext_r86,
        fx_revalue_portfolio=fx_revalue_portfolio,
        ext_r86_zero=ext_r86_zero,
        output_binding=OutputBinding(output_31_source=output_31_source),
    )


class ScenarioRegistry:
    """Lookup table for standard and tailored scenario recipes."""

    STANDARD: ClassVar[dict[StressScenarioId, ScenarioSpec]] = {
        "A1_Historical": _standard(
            "A1_Historical",
            ShockKind.HISTORICAL,
            couple_ext_r86=True,
        ),
        "B1_GDP": _standard(
            "B1_GDP",
            ShockKind.GDP,
            ext_r86_zero=True,
        ),
        "B2_PrimaryBalance": _standard(
            "B2_PrimaryBalance",
            ShockKind.PRIMARY_BALANCE,
            residual_policy=ResidualPolicyKind.ABSOLUTE,
            market_access=None,  # from Input 1
            couple_ext_r86=True,
            output_31_source="public_external_methods",
        ),
        "B3_Exports": _standard("B3_Exports", ShockKind.EXPORTS),
        "B4_OtherFlows": _standard("B4_OtherFlows", ShockKind.OTHER_FLOWS),
        "B5_FX": _standard(
            "B5_FX",
            ShockKind.FX,
            # Cached B5 sheet does not revalue LC-NR into R35; adjuster remains
            # available for optional use after workbook recalc.
            fx_revalue_portfolio=False,
        ),
        "B6_Combo": _standard(
            "B6_Combo",
            ShockKind.COMBO,
            fx_revalue_portfolio=False,
            market_access=None,
        ),
    }

    TAILORED: ClassVar[dict[StressScenarioId, ScenarioSpec]] = {
        "A2_Custom": _tailored("A2_Custom", ShockKind.TAILORED_CUSTOM),
        "C1_CombinedCL": _tailored(
            "C1_CombinedCL",
            ShockKind.TAILORED_COMBINED_CL,
            # Excel C1 Output 3-1 / public sheet uses public three-way ResFin
            # (ongoing ext MLT), not a one-shot external CL gap alone.
            couple_ext_r86=True,
            output_31_source="public_external_methods",
        ),
        "C2_NaturalDisaster": _tailored(
            "C2_NaturalDisaster", ShockKind.TAILORED_NATURAL_DISASTER
        ),
        "C3_Commodity": _tailored(
            "C3_Commodity", ShockKind.TAILORED_COMMODITY
        ),
        "C4_Market": _tailored(
            "C4_Market",
            ShockKind.TAILORED_MARKET,
            fx_revalue_portfolio=False,
            # Excel C4_Market_financing does not refill an FX-driven R86 gap;
            # PV/DS adjustments are commercial Δ + shortened-term ResFin only.
            ext_r86_zero=True,
        ),
    }

    @classmethod
    def all_specs(cls) -> dict[StressScenarioId, ScenarioSpec]:
        """Return standard + tailored specs."""
        return {**cls.STANDARD, **cls.TAILORED}

    @classmethod
    def get(cls, scenario_id: StressScenarioId | str) -> ScenarioSpec:
        """Return the recipe for ``scenario_id``.

        Raises:
            KeyError: Unknown id.
        """
        sid = scenario_id  # type: ignore[assignment]
        specs = cls.all_specs()
        if sid not in specs:
            raise KeyError(f"unknown stress scenario id: {scenario_id!r}")
        return specs[sid]

    @classmethod
    def resolve_market_access(cls, spec: ScenarioSpec, *, context_market_access: bool) -> bool:
        """Resolve Input 1 inheritance for B2-style specs."""
        if spec.market_access is None:
            return bool(context_market_access)
        return bool(spec.market_access)


def assert_registry_covers_all_ids() -> None:
    """Raise if any ``StressScenarioId`` lacks a registry entry."""
    known = set(ScenarioRegistry.all_specs())
    expected = set(get_args(StressScenarioId))
    missing = expected - known
    extra = known - expected
    if missing or extra:
        raise AssertionError(f"registry mismatch: missing={missing!r} extra={extra!r}")
