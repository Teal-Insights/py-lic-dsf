"""Compatibility shim — import from ``lic_dsf.resfin`` (plus stress-only helpers)."""

from __future__ import annotations

from lic_dsf.resfin import (
    AbsoluteResidualPolicy,
    CappedResidualPolicy,
    ResidualPolicy,
    ResidualPolicyKind,
    policy_from_kind,
)
from lic_dsf.stress.spec import ScenarioSpec


def policy_from_spec(spec: ScenarioSpec) -> ResidualPolicy:
    """Return the split policy declared on ``spec``."""
    return policy_from_kind(spec.residual_policy)


__all__ = [
    "AbsoluteResidualPolicy",
    "CappedResidualPolicy",
    "ResidualPolicy",
    "ResidualPolicyKind",
    "policy_from_kind",
    "policy_from_spec",
]
