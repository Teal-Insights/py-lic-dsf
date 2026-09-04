"""Public GFN identity (B-sheet R88–R90 / PV_ResFin_pub R67)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.public import (
    _a1_primary_deficit_lcu,
    _a1_public_gdp_lcu,
    _b1_primary_deficit_lcu,
    _b1_public_gdp_lcu,
    _inflation_elasticity,
    _public_domestic_st_lcu_path,
    estimate_b1_public_gfn,
)
from lic_dsf.stress.residual_pv import PublicResFinOverlay, public_residual_gap
from lic_dsf.stress.types import Input6StandardParams


@dataclass(slots=True)
class PublicGFNIdentity:
    """Excel public GFN block under a shocked macro path.

    Owns GDP LCU compounding, primary deficit, GFN, and residual gap. Does not
    build ResFin instruments — callers feed overlays from
    :class:`~lic_dsf.stress.resfin.ResidualFinancingEngine`.
    """

    path: ShockedMacroPath
    inflation_elasticity: float = 0.0
    fx_passthrough: float = 0.0
    market_access: bool = False
    historical: bool = False
    external: ExternalDebtBook | None = None
    input6: Input6StandardParams | None = None
    external_dsa_borrowing_usd: pd.Series | None = None
    # Excel B2_PB_non_mkt_pub still includes domestic add.int (H80/H89) but
    # zeros the external add.int rate (B70:C70 = 0).
    include_external_add_int: bool = True
    _gdp_lcu_cache: pd.Series | None = None

    @classmethod
    def from_path(
        cls,
        path: ShockedMacroPath,
        *,
        input6: Input6StandardParams | None = None,
        inflation_elasticity: float | None = None,
        fx_passthrough: float | None = None,
        market_access: bool = False,
        gdp_lcu: pd.Series | None = None,
        historical: bool = False,
        external: ExternalDebtBook | None = None,
        external_dsa_borrowing_usd: pd.Series | None = None,
        include_external_add_int: bool = True,
    ) -> PublicGFNIdentity:
        """Build identity; resolve inflation elasticity from Input 6 when needed."""
        if inflation_elasticity is None:
            inflation_elasticity = (
                _inflation_elasticity(input6) if input6 is not None else 0.0
            )
        if fx_passthrough is None:
            fx_passthrough = (
                float(input6.fx_passthrough)
                if input6 is not None and input6.interactions_on
                else 0.0
            )
        return cls(
            path=path,
            inflation_elasticity=float(inflation_elasticity),
            fx_passthrough=float(fx_passthrough),
            market_access=bool(market_access),
            historical=bool(historical),
            external=external,
            input6=input6,
            external_dsa_borrowing_usd=external_dsa_borrowing_usd,
            include_external_add_int=bool(include_external_add_int),
            _gdp_lcu_cache=gdp_lcu,
        )


    @property
    def baseline(self) -> MacroDebtBook:
        """Baseline macro book."""
        return self.path.baseline

    @property
    def shocked(self) -> MacroDebtBook:
        """Shocked macro book."""
        return self.path.shocked

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon."""
        return self.path.years

    def gdp_lcu(self) -> pd.Series:
        """Public B-sheet R41 shocked GDP in LCU."""
        if self._gdp_lcu_cache is not None:
            return self._gdp_lcu_cache.astype(float)
        if self.historical:
            self._gdp_lcu_cache = _a1_public_gdp_lcu(self.baseline)
        elif self.path.metadata.lcu_deflator_growth is not None:
            # C3_commodity_prices_pub R41: shocked real × Excel R54 deflator.
            from lic_dsf.stress.public import _align, _growth_pct

            years = self.years
            first = self.path.first_projection_year
            shock_const = _align(self.shocked.gdp_constant(), years).replace(
                0.0, pd.NA
            )
            real_s = _growth_pct(shock_const)
            defl_s = _align(
                self.path.metadata.lcu_deflator_growth, years
            ).astype(float)
            out = _align(self.baseline.gdp_lcu(), years).copy()
            for year in years:
                if year <= first:
                    continue
                prior = year - 1
                if prior not in out.index:
                    continue
                rg = float(real_s.loc[year]) if pd.notna(real_s.loc[year]) else 0.0
                dg = float(defl_s.loc[year]) if pd.notna(defl_s.loc[year]) else 0.0
                out.loc[year] = (
                    float(out.loc[prior]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
                )
            self._gdp_lcu_cache = out.astype(float)
        else:
            self._gdp_lcu_cache = _b1_public_gdp_lcu(
                self.baseline,
                self.shocked,
                self.inflation_elasticity,
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=float(self.path.metadata.fx_depreciation_pct),
            )
        return self._gdp_lcu_cache

    def primary_deficit_lcu(self) -> pd.Series:
        """Public R88 primary deficit under stress (LCU)."""
        if self.historical:
            return _a1_primary_deficit_lcu(self.baseline, self.gdp_lcu())
        denom = self.path.metadata.primary_exp_gdp_denominator
        return _b1_primary_deficit_lcu(
            self.baseline,
            self.shocked,
            self.gdp_lcu(),
            primary_exp_gdp_denominator=denom,
            use_shocked_revenues=denom is not None,
        )

    def compute_gfn(
        self, resfin: PublicResFinOverlay | None = None
    ) -> pd.Series:
        """B-sheet R90 public GFN (LCU), optionally with ResFin service."""
        combo = bool(
            self.path.metadata.exports_shocked_in_levels
            and self.path.metadata.fx_depreciation_pct
        )
        prior_st = None
        if resfin is not None and self.fx_passthrough and self.path.metadata.fx_depreciation_pct:
            prior_st = _public_domestic_st_lcu_path(
                self.shocked,
                resfin,
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=float(self.path.metadata.fx_depreciation_pct),
                combo_primary=combo,
            )
        denom = self.path.metadata.primary_exp_gdp_denominator
        return estimate_b1_public_gfn(
            self.baseline,
            self.shocked,
            resfin,
            inflation_elasticity=self.inflation_elasticity,
            gdp_lcu=self.gdp_lcu(),
            market_access=self.market_access,
            include_external_add_int=self.include_external_add_int,
            historical=self.historical,
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=float(self.path.metadata.fx_depreciation_pct),
            combo_primary=combo,
            input6=self.input6,
            external=self.external,
            prior_st=prior_st,
            external_dsa_borrowing_usd=self.external_dsa_borrowing_usd,
            primary_exp_gdp_denominator=denom,
            use_shocked_revenues=denom is not None,
        )

    def compute_gap(
        self,
        baseline_gfn: pd.Series | None = None,
        stressed_gfn: pd.Series | None = None,
        *,
        resfin: PublicResFinOverlay | None = None,
    ) -> pd.Series:
        """Public residual gap R67: stressed GFN − baseline GFN (LCU).

        Zeroes years before the first projection year.
        """
        base = (
            baseline_gfn
            if baseline_gfn is not None
            else self.baseline.public_gfn()
        )
        stress = (
            stressed_gfn
            if stressed_gfn is not None
            else self.compute_gfn(resfin)
        )
        gap = public_residual_gap(stress, base, self.years)
        first = self.path.first_projection_year
        for year in self.years:
            if year < first:
                gap.loc[year] = 0.0
        return gap.astype(float)


__all__ = ["PublicGFNIdentity"]
