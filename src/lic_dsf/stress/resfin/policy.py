"""Public residual-financing split policies (capped vs absolute)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.stress.residual_pv import ResidualFill, split_residual_financing
from lic_dsf.stress.spec import ResidualPolicyKind, ScenarioSpec


class ResidualPolicy(Protocol):
    """Split a public ΔGFN into ext MLT / dom MLT / ST disbursements."""

    def split(
        self,
        public_gap: pd.Series,
        external_gap: pd.Series,
        params: ResidualFinancingParams,
        fx: pd.Series,
        *,
        years: tuple[int, ...] | None = None,
    ) -> ResidualFill:
        """Return three-way residual fill for ``public_gap``."""


@dataclass(frozen=True, slots=True)
class CappedResidualPolicy:
    """B1 / B3–B6: modality 1 vs 2 capped by external residual vs public share."""

    def split(
        self,
        public_gap: pd.Series,
        external_gap: pd.Series,
        params: ResidualFinancingParams,
        fx: pd.Series,
        *,
        years: tuple[int, ...] | None = None,
    ) -> ResidualFill:
        return split_residual_financing(
            public_gap,
            external_gap,
            params,
            fx,
            modality="capped",
            years=years,
        )


@dataclass(frozen=True, slots=True)
class AbsoluteResidualPolicy:
    """B2 primary balance: full gap × J-column shares (no modality 1 cap)."""

    def split(
        self,
        public_gap: pd.Series,
        external_gap: pd.Series,
        params: ResidualFinancingParams,
        fx: pd.Series,
        *,
        years: tuple[int, ...] | None = None,
    ) -> ResidualFill:
        # Absolute branch ignores external_gap in the legacy split (shares only).
        return split_residual_financing(
            public_gap,
            external_gap,
            params,
            fx,
            modality="absolute",
            years=years,
        )


def policy_from_kind(kind: ResidualPolicyKind) -> ResidualPolicy:
    """Return the concrete policy for a registry marker."""
    if kind is ResidualPolicyKind.ABSOLUTE:
        return AbsoluteResidualPolicy()
    return CappedResidualPolicy()


def policy_from_spec(spec: ScenarioSpec) -> ResidualPolicy:
    """Return the split policy declared on ``spec``."""
    return policy_from_kind(spec.residual_policy)


__all__ = [
    "AbsoluteResidualPolicy",
    "CappedResidualPolicy",
    "ResidualPolicy",
    "policy_from_kind",
    "policy_from_spec",
]
