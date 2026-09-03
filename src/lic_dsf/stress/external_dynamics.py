"""External B-sheet debt dynamics (Phase 3): R12–R30 identity → R86 gap.

Formulas delegate to ``lic_dsf.stress.bound`` on first pass so Excel semantics
stay identical. ResFin PV interest feedback uses
:class:`~lic_dsf.stress.resfin.ResidualFinancingEngine` (Phase 4).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
import lic_dsf.stress.bound as _bound
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.resfin import EXTERNAL_INTEREST_TOL, ResidualFinancingEngine
from lic_dsf.stress.spec import ScenarioSpec, ShockKind


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


@dataclass(frozen=True, slots=True)
class ExternalGapResult:
    """Residual gross borrowing (Excel R86 / B5 R87) after optional ResFin loop."""

    gap: pd.Series
    resfin_interest: pd.Series
    iterations: int
    resfin_pv: pd.Series | None = None

    @property
    def residual_borrowing(self) -> pd.Series:
        """Alias for ``gap`` (Excel residual gross borrowing path)."""
        return self.gap


@dataclass(slots=True)
class ExternalDebtDynamics:
    """Excel external B-sheet debt identity under a shocked macro path."""

    path: ShockedMacroPath
    external: ExternalDebtBook
    ext_base: BaselineExternalBook
    residual: ResidualFinancingParams
    fx_depreciation_pct: float = 0.0
    fx_passthrough: float = 0.0
    inflation_elasticity: float = 0.0
    net_exports_elasticity: float = 0.0
    historical_averages: bool = False
    hist_ca_deficit_pct: float | None = None
    hist_fdi_pct: float | None = None
    ext_r86_zero: bool = False
    cl_external_ppg_share: float = 0.0
    additional_borrowing_interest: pd.Series | None = None
    post_shock_r18_unscaled: bool = False

    @classmethod
    def from_context(
        cls,
        ctx: StressContext,
        path: ShockedMacroPath,
        spec: ScenarioSpec,
        *,
        additional_borrowing_interest: pd.Series | None = None,
        residual: ResidualFinancingParams | None = None,
    ) -> ExternalDebtDynamics:
        """Build dynamics kwargs from ``ScenarioSpec`` + Input 6."""
        input6 = ctx.input6
        interactions = bool(input6.interactions_on)
        fx_pct = float(path.metadata.fx_depreciation_pct)
        hist_ca: float | None = None
        hist_fdi: float | None = None
        historical = spec.shock_kind is ShockKind.HISTORICAL
        if historical:
            hist_ca, hist_fdi = _bound.historical_identity_pins(path.baseline)
        return cls(
            path=path,
            external=ctx.external,
            ext_base=ctx.ext_base,
            residual=residual if residual is not None else ctx.residual,
            fx_depreciation_pct=fx_pct,
            fx_passthrough=float(input6.fx_passthrough) if interactions else 0.0,
            inflation_elasticity=(
                float(input6.inflation_elasticity) if interactions else 0.0
            ),
            net_exports_elasticity=(
                float(input6.net_exports_elasticity) if interactions else 0.0
            ),
            historical_averages=historical,
            hist_ca_deficit_pct=hist_ca,
            hist_fdi_pct=hist_fdi,
            ext_r86_zero=bool(spec.ext_r86_zero),
            cl_external_ppg_share=(
                _bound.CL_EXTERNAL_PPG_SHARE
                if (
                    spec.shock_kind is ShockKind.TAILORED_COMBINED_CL
                    and spec.output_binding.output_31_source != "public_external_methods"
                )
                else 0.0
            ),
            additional_borrowing_interest=additional_borrowing_interest,
            # C3 sheet copies baseline R18 % after the window; B3 scales USD.
            post_shock_r18_unscaled=spec.shock_kind is ShockKind.TAILORED_COMMODITY,
        )

    def _borrow_kwargs(self) -> dict[str, object]:
        return {
            "fx_depreciation_pct": self.fx_depreciation_pct,
            "fx_passthrough": self.fx_passthrough,
            "inflation_elasticity": self.inflation_elasticity,
            "net_exports_elasticity": self.net_exports_elasticity,
            "historical_averages": self.historical_averages,
            "hist_ca_deficit_pct": self.hist_ca_deficit_pct,
            "hist_fdi_pct": self.hist_fdi_pct,
            "additional_borrowing_interest": self.additional_borrowing_interest,
            "post_shock_r18_unscaled": self.post_shock_r18_unscaled,
        }

    def _resfin_engine(self) -> ResidualFinancingEngine:
        return ResidualFinancingEngine.for_external(
            self.residual,
            self.path.years,
            external=self.external,
        )

    def exports_to_gdp(self) -> pd.Series:
        """B-sheet exports/GDP (%) (R19)."""
        return _bound.bsheet_exports_to_gdp(
            self.path.baseline,
            self.path.shocked,
            fx_depreciation_pct=self.fx_depreciation_pct,
        )

    def compute_gap(
        self,
        *,
        resfin_interest: pd.Series | None = None,
    ) -> ExternalGapResult:
        """One-shot R86 residual gross borrowing (no ResFin interest iteration)."""
        years = self.path.years
        if self.ext_r86_zero:
            z = _zero(years)
            return ExternalGapResult(
                gap=z,
                resfin_interest=z.copy(),
                iterations=0,
                resfin_pv=z.copy(),
            )
        gap = _bound.external_residual_borrowing(
            self.path.baseline,
            self.path.shocked,
            resfin_interest=resfin_interest,
            **self._borrow_kwargs(),  # type: ignore[arg-type]
        )
        if self.cl_external_ppg_share > 0.0:
            gap = (gap + _bound.external_cl_gap_usd(
                self.path.baseline,
                self.path.shocked,
                share=self.cl_external_ppg_share,
            )).astype(float)
        interest = (
            _align(resfin_interest, years).fillna(0.0)
            if resfin_interest is not None
            else _zero(years)
        )
        return ExternalGapResult(
            gap=gap.astype(float),
            resfin_interest=interest,
            iterations=1,
            resfin_pv=None,
        )

    def compute_gap_converged(self, *, max_iter: int = 25) -> ExternalGapResult:
        """Iterate R86 with ResFin interest feedback (legacy ``_converged_external_gap``)."""
        years = self.path.years
        if self.ext_r86_zero:
            return self.compute_gap()

        engine = self._resfin_engine()
        resfin_interest = _zero(years)
        gap = _zero(years)
        resfin_pv = _zero(years)
        iterations = 0
        for i in range(max_iter):
            iterations = i + 1
            gap = _bound.external_residual_borrowing(
                self.path.baseline,
                self.path.shocked,
                resfin_interest=resfin_interest,
                **self._borrow_kwargs(),  # type: ignore[arg-type]
            )
            if self.cl_external_ppg_share > 0.0:
                gap = (gap + _bound.external_cl_gap_usd(
                    self.path.baseline,
                    self.path.shocked,
                    share=self.cl_external_ppg_share,
                )).astype(float)
            if float(gap.fillna(0.0).abs().sum()) == 0.0:
                resfin_pv = _zero(years)
                break
            overlay = engine.build_external_overlay(gap)
            new_interest = _align(overlay.interest, years).fillna(0.0)
            resfin_pv = _align(overlay.pv, years).fillna(0.0)
            if float((new_interest - resfin_interest).abs().max()) < EXTERNAL_INTEREST_TOL:
                break
            resfin_interest = new_interest
        return ExternalGapResult(
            gap=gap.astype(float),
            resfin_interest=resfin_interest.astype(float),
            iterations=iterations,
            resfin_pv=resfin_pv.astype(float),
        )


# Re-export helpers used by tests / later phases.
bsheet_exports_to_gdp = _bound.bsheet_exports_to_gdp
historical_identity_pins = _bound.historical_identity_pins
hybrid_external_debt_to_gdp = _bound.hybrid_external_debt_to_gdp

__all__ = [
    "ExternalDebtDynamics",
    "ExternalGapResult",
    "bsheet_exports_to_gdp",
    "historical_identity_pins",
    "hybrid_external_debt_to_gdp",
]
