"""Unified residual-financing PV engine.

External DSA mode: 100% ext MLT fill from R86 gap.
Public DSA mode: three-way split via :class:`ResidualPolicy` + GFN fixed point.

Tolerances (documented):
- Public GFN gap loop: ``tol=1e-6`` LCU
- External ResFin interest loop: ``1e-9`` USD (in ``ExternalDebtDynamics``)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.public import _inflation_elasticity
from lic_dsf.stress.residual_pv import (
    PublicResFinOverlay,
    ResidualFill,
    ResFinOverlay,
    build_public_resfin_overlay,
    external_dsa_residual_params,
    gdp_deflator_growth,
    public_dsa_residual_params,
    resfin_instrument,
    resfin_overlay_series,
)
from lic_dsf.stress.types import Input6StandardParams
from lic_dsf.stress.resfin.policy import ResidualPolicy, policy_from_kind
from lic_dsf.stress.spec import ResidualPolicyKind

ResFinMode = Literal["external_dsa", "public_dsa"]

PUBLIC_GAP_TOL = 1e-6
EXTERNAL_INTEREST_TOL = 1e-9


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).fillna(0.0).astype(float)


def _discount_rate(external: ExternalDebtBook | None, params: ResidualFinancingParams) -> float:
    if params.discount_rate:
        return float(params.discount_rate)
    if external is not None:
        for instrument in external.portfolio.instruments:
            rate = getattr(instrument, "discount_rate", None)
            if rate is not None:
                return float(rate)
    return 0.05


@dataclass(frozen=True, slots=True)
class ResidualFinancingResult:
    """Overlays produced by :class:`ResidualFinancingEngine`."""

    external: ResFinOverlay | None
    public: PublicResFinOverlay | None
    fill: ResidualFill | None
    converged: bool
    iterations: int
    public_gap: pd.Series | None = None


@dataclass(slots=True)
class ResidualFinancingEngine:
    """Build external / public ResFin overlays and run public GFN fixed-point."""

    params: ResidualFinancingParams
    years: tuple[int, ...]
    mode: ResFinMode = "external_dsa"
    discount_rate: float | None = None
    policy: ResidualPolicy | None = None
    external: ExternalDebtBook | None = None

    @classmethod
    def for_external(
        cls,
        params: ResidualFinancingParams,
        years: tuple[int, ...],
        *,
        external: ExternalDebtBook | None = None,
        discount_rate: float | None = None,
    ) -> ResidualFinancingEngine:
        """Engine configured for external DSA (100% ext MLT)."""
        return cls(
            params=external_dsa_residual_params(params),
            years=years,
            mode="external_dsa",
            discount_rate=discount_rate,
            external=external,
        )

    @classmethod
    def for_public(
        cls,
        params: ResidualFinancingParams,
        years: tuple[int, ...],
        *,
        policy: ResidualPolicy | ResidualPolicyKind = ResidualPolicyKind.CAPPED,
        external: ExternalDebtBook | None = None,
        discount_rate: float | None = None,
    ) -> ResidualFinancingEngine:
        """Engine configured for public DSA J-column shares."""
        if isinstance(policy, ResidualPolicyKind):
            policy = policy_from_kind(policy)
        return cls(
            params=public_dsa_residual_params(params),
            years=years,
            mode="public_dsa",
            discount_rate=discount_rate,
            policy=policy,
            external=external,
        )

    def _rate(self) -> float:
        if self.discount_rate is not None:
            return float(self.discount_rate)
        return _discount_rate(self.external, self.params)

    def build_external_overlay(self, gap_usd: pd.Series) -> ResFinOverlay:
        """PV / interest / amort overlay for an external residual gap (USD)."""
        years = self.years
        gap = _align(gap_usd, years)
        if float(gap.abs().sum()) == 0.0:
            zero = pd.Series(0.0, index=list(years), dtype=float)
            instrument = resfin_instrument(
                gap,
                self.params if self.mode == "external_dsa" else external_dsa_residual_params(self.params),
                discount_rate=self._rate(),
                years=years,
                apply_share=True,
            )
            return ResFinOverlay(
                pv=zero,
                interest=zero.copy(),
                amortization=zero.copy(),
                debt_service=zero.copy(),
                instrument=instrument,
            )
        params = (
            self.params
            if self.mode == "external_dsa"
            else external_dsa_residual_params(self.params)
        )
        instrument = resfin_instrument(
            gap,
            params,
            discount_rate=self._rate(),
            years=years,
            apply_share=True,
        )
        return resfin_overlay_series(instrument, years)

    def build_public_overlay(
        self,
        fill: ResidualFill,
        *,
        deflator: pd.Series,
    ) -> PublicResFinOverlay:
        """Three-way public overlay from an already-split fill."""
        return build_public_resfin_overlay(
            fill,
            self.params,
            deflator=deflator,
            years=self.years,
        )

    def split_public(
        self,
        public_gap: pd.Series,
        external_gap: pd.Series,
        fx: pd.Series,
    ) -> ResidualFill:
        """Apply the engine's split policy to public / external gaps."""
        policy = self.policy or policy_from_kind(ResidualPolicyKind.CAPPED)
        return policy.split(
            public_gap,
            external_gap,
            self.params,
            fx,
            years=self.years,
        )

    def solve_public_with_gfn_feedback(
        self,
        baseline_macro: MacroDebtBook,
        shocked_macro: MacroDebtBook,
        *,
        external_gap: pd.Series | None = None,
        input6: Input6StandardParams | None = None,
        public_gap: pd.Series | None = None,
        inflation_elasticity: float | None = None,
        market_access: bool = False,
        include_external_add_int: bool = True,
        iterations: int = 25,
        tol: float = PUBLIC_GAP_TOL,
        gfn: object | None = None,
    ) -> ResidualFinancingResult:
        """Fixed-point: GFN → public gap → split → overlays → GFN service.

        Prefers :class:`~lic_dsf.stress.public_gfn.PublicGFNIdentity` when
        provided; otherwise builds one from the macro books.
        """
        from lic_dsf.stress.path import (
            ShockedMacroPath,
            ShockMetadata,
            projection_shock_window,
        )
        from lic_dsf.stress.public_gfn import PublicGFNIdentity

        years = self.years
        if inflation_elasticity is None:
            inflation_elasticity = (
                _inflation_elasticity(input6) if input6 is not None else 0.0
            )
        identity: PublicGFNIdentity
        if isinstance(gfn, PublicGFNIdentity):
            identity = gfn
        else:
            try:
                window = projection_shock_window(
                    years, shocked_macro.inputs.first_projection_year
                )
            except ValueError:
                first = shocked_macro.inputs.first_projection_year
                window = (first, first)
            path = ShockedMacroPath(
                baseline=baseline_macro,
                shocked=shocked_macro,
                metadata=ShockMetadata(
                    shock_window_years=window,
                    fx_depreciation_pct=0.0,
                    threshold_rule="baseline_projection",
                    interactions_on=False,
                ),
            )
            identity = PublicGFNIdentity.from_path(
                path,
                inflation_elasticity=float(inflation_elasticity),
                market_access=market_access,
            )

        r86 = (
            _align(external_gap, years)
            if external_gap is not None
            else pd.Series(0.0, index=list(years), dtype=float)
        )
        deflator = gdp_deflator_growth(
            baseline_macro.gdp_lcu(), baseline_macro.gdp_constant()
        )
        # Excel PV_ResFin_pub R27 is baseline period-average FX, not shocked FX.
        fx = baseline_macro.fx_pa()
        baseline_gfn = baseline_macro.public_gfn()

        if public_gap is not None:
            gap = _align(public_gap, years)
            fill = self.split_public(gap, r86, fx)
            overlay = self.build_public_overlay(fill, deflator=deflator)
            return ResidualFinancingResult(
                external=None,
                public=overlay,
                fill=fill,
                converged=True,
                iterations=0,
                public_gap=gap,
            )

        overlay: PublicResFinOverlay | None = None
        prev_gap: pd.Series | None = None
        gap = pd.Series(0.0, index=list(years), dtype=float)
        n_iter = 0
        for i in range(max(iterations, 1)):
            n_iter = i + 1
            # Keep market_access / add.int legs on the identity for this solve.
            identity.market_access = bool(market_access)
            identity.include_external_add_int = bool(include_external_add_int)
            stressed_gfn = identity.compute_gfn(overlay)
            gap = identity.compute_gap(baseline_gfn, stressed_gfn)
            fill = self.split_public(gap, r86, fx)
            overlay = self.build_public_overlay(fill, deflator=deflator)
            if prev_gap is not None and float((gap - prev_gap).abs().max()) < tol:
                return ResidualFinancingResult(
                    external=None,
                    public=overlay,
                    fill=fill,
                    converged=True,
                    iterations=n_iter,
                    public_gap=gap.astype(float),
                )
            prev_gap = gap

        assert overlay is not None
        return ResidualFinancingResult(
            external=None,
            public=overlay,
            fill=overlay.fill,
            converged=False,
            iterations=n_iter,
            public_gap=gap.astype(float),
        )
