"""Public stress ratio projections (Output 3-2 + Output 3-1 B2)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.public import StressPublicBook
from lic_dsf.stress.public_gfn import PublicGFNIdentity
from lic_dsf.stress.residual_pv import PublicResFinOverlay


@dataclass(slots=True)
class StressPublicRatios:
    """Public DSA ratios under stress (no shock / gap iteration logic).

    Public methods feed Output 3-2. External-facing methods feed Output 3-1 B2
    (Chart Data wires B2 from the public B2 sheet, not an external B2 book).
    """

    path: ShockedMacroPath
    external: ExternalDebtBook
    resfin: PublicResFinOverlay
    inflation_elasticity: float = 0.0
    fx_passthrough: float = 0.0
    market_access: bool = False
    resfin_external_ds: PublicResFinOverlay | None = None
    gfn: PublicGFNIdentity | None = None
    scenario_id: str = "B1_GDP_pub"

    @classmethod
    def from_path(
        cls,
        path: ShockedMacroPath,
        external: ExternalDebtBook,
        resfin: PublicResFinOverlay,
        *,
        inflation_elasticity: float = 0.0,
        fx_passthrough: float = 0.0,
        market_access: bool = False,
        resfin_external_ds: PublicResFinOverlay | None = None,
        gfn: PublicGFNIdentity | None = None,
        scenario_id: str = "B1_GDP_pub",
    ) -> StressPublicRatios:
        """Build ratios from a shocked path and public ResFin overlay."""
        return cls(
            path=path,
            external=external,
            resfin=resfin,
            inflation_elasticity=float(inflation_elasticity),
            fx_passthrough=float(fx_passthrough),
            market_access=bool(market_access),
            resfin_external_ds=resfin_external_ds,
            gfn=gfn,
            scenario_id=scenario_id,
        )

    def _book(self) -> StressPublicBook:
        gdp_override = self.gfn.gdp_lcu() if self.gfn is not None else None
        combo = False
        if self.gfn is not None:
            combo = bool(
                self.path.metadata.exports_shocked_in_levels
                and self.path.metadata.fx_depreciation_pct
            )
        return StressPublicBook(
            macro=self.path.shocked,
            external=self.external,
            baseline_macro=self.path.baseline,
            resfin=self.resfin,
            scenario_id=self.scenario_id,
            inflation_elasticity=self.inflation_elasticity,
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=float(self.path.metadata.fx_depreciation_pct),
            combo_primary=combo,
            input6=self.gfn.input6 if self.gfn is not None else None,
            market_access=self.market_access,
            resfin_external_ds=self.resfin_external_ds,
            gdp_lcu_override=gdp_override,
            external_dsa_borrowing_usd=(
                self.gfn.external_dsa_borrowing_usd if self.gfn is not None else None
            ),
            primary_exp_gdp_denominator=self.path.metadata.primary_exp_gdp_denominator,
            lcu_deflator_growth=self.path.metadata.lcu_deflator_growth,
        )

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon."""
        return self.path.years

    def gdp_lcu(self) -> pd.Series:
        """B1 R41 shocked GDP in LCU."""
        if self.gfn is not None:
            return self.gfn.gdp_lcu()
        return self._book().gdp_lcu()

    def public_gfn(self) -> pd.Series:
        """B1 R90 public GFN (LCU)."""
        if self.gfn is not None:
            return self.gfn.compute_gfn(self.resfin)
        return self._book().public_gfn()

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Public debt / GDP including ResFin stocks."""
        return self._book().public_sector_debt_to_gdp()

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """PV of public debt / GDP (Output 3-2 / B-sheet R13)."""
        return self._book().pv_public_debt_to_gdp()

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """PV of public debt / revenue+grants (B-sheet R95)."""
        return self._book().pv_public_debt_to_revenue_grants()

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Debt service / revenue+grants (B-sheet R93)."""
        return self._book().debt_service_to_revenue_grants()

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP including ResFin service."""
        return self._book().debt_service_to_gdp()

    # --- Output 3-1 B2 (public-sheet external-ratio block) ---

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """Output 3-1 B2: public-sheet external PV / GDP."""
        return self._book().pv_ppg_external_to_gdp()

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """Output 3-1 B2: public-sheet external PV / exports."""
        return self._book().pv_ppg_external_to_exports()

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """Output 3-1 B2: public-sheet PPG DS / exports."""
        return self._book().ppg_debt_service_to_exports()

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """Output 3-1 B2: public-sheet PPG DS / revenue excl. grants."""
        return self._book().ppg_debt_service_to_revenue()


__all__ = ["StressPublicRatios"]
