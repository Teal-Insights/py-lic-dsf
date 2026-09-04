"""Market-access and combo additional-interest overlays."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.creditor_groups import creditor_group_for_name
from lic_dsf.pv.instrument import PresentValueInstrument
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.public import (
    _amortizing_stock_from_disbursements,
    _market_add_int_interest_lcu,
    _market_add_int_rates,
    _shock_window_years,
)
from lic_dsf.stress.ratios.public import StressPublicRatios
from lic_dsf.stress.residual_pv import PublicResFinOverlay
from lic_dsf.stress.tailored_params import TailoredParams


@dataclass(frozen=True, slots=True)
class MarketAccessAddon:
    """B2 market-access add.int from ``PV_ResFin-add.int.cost - mkt``."""

    path: ShockedMacroPath
    resfin: PublicResFinOverlay
    enabled: bool = True

    @classmethod
    def from_path(
        cls,
        path: ShockedMacroPath,
        resfin: PublicResFinOverlay,
        *,
        enabled: bool,
    ) -> MarketAccessAddon:
        """Build an addon gated on Input 1 / scenario market access."""
        return cls(path=path, resfin=resfin, enabled=bool(enabled))

    def rates(self) -> tuple[float, float]:
        """Return (external, domestic) add.int rates (decimals)."""
        if not self.enabled:
            return 0.0, 0.0
        return _market_add_int_rates(self.path.baseline, self.path.shocked)

    def additional_interest_lcu(self) -> pd.Series:
        """Market-access add.int interest in LCU (ext × FX + domestic)."""
        years = self.path.years
        if not self.enabled:
            return pd.Series(0.0, index=list(years), dtype=float)
        return _market_add_int_interest_lcu(
            self.resfin, self.path.shocked, self.path.baseline
        )

    def adjust_public_ratios(self, ratios: StressPublicRatios) -> StressPublicRatios:
        """Attach market-access flag / dual-block overlays onto public ratios.

        Ratio numerators already read ``market_access`` and
        ``resfin_external_ds`` from :class:`StressPublicRatios`; this helper
        ensures the flag matches the addon gate.
        """
        if ratios.market_access == self.enabled:
            return ratios
        return replace(
            ratios,  # type: ignore[type-var]
            market_access=self.enabled,
        )


@dataclass(frozen=True, slots=True)
class MarketFinancingCost:
    """C4 market-financing add.int: fixed bps on commercial borrowing (Input 6)."""

    bps: float
    years: int = 3

    def compute(
        self,
        baseline: MacroDebtBook,
        shocked: MacroDebtBook,
        external: ExternalDebtBook,
        *,
        tailored: TailoredParams | None = None,
    ) -> pd.Series:
        """Additional nominal interest on shock-window commercial disbursements."""
        from lic_dsf.stress.market_terms import shortened_terms_for_instrument

        del baseline  # API compat with ComboMarketCost
        years = shocked.inputs.years
        year_list = list(years)
        first = shocked.inputs.first_projection_year
        proj = [y for y in year_list if y >= first]
        if len(proj) < 2 or self.bps <= 0.0 or self.years <= 0:
            return pd.Series(0.0, index=year_list, dtype=float)
        shock_years = set(proj[1 : 1 + int(self.years)])
        rate = float(self.bps) / 10_000.0
        interest = pd.Series(0.0, index=year_list, dtype=float)
        for inst in external.portfolio.instruments:
            if not isinstance(inst, PresentValueInstrument):
                continue
            if creditor_group_for_name(str(inst.name)) != "Commercial":
                continue
            disb_series = pd.Series(
                list(inst.disbursements),
                index=list(inst.years)[: len(inst.disbursements)],
                dtype=float,
            )
            disb = [
                float(disb_series.reindex([y]).fillna(0.0).loc[y])
                if y in shock_years
                else 0.0
                for y in proj
            ]
            if not any(abs(v) > 0.0 for v in disb):
                continue
            grace = int(inst.grace)
            maturity = int(inst.maturity)
            if tailored is not None:
                terms = shortened_terms_for_instrument(inst, tailored)
                grace = terms.grace_rounded
                maturity = terms.maturity_rounded
            stock = _amortizing_stock_from_disbursements(
                disb, grace=grace, maturity=maturity
            )
            prior = 0.0
            for i, year in enumerate(proj):
                interest.loc[year] = float(interest.loc[year]) + prior * rate
                prior = float(stock[i])
        return interest.astype(float)

    def compute_from_context(
        self,
        ctx: StressContext,
        path: ShockedMacroPath,
        *,
        external: ExternalDebtBook | None = None,
    ) -> pd.Series:
        """Build C4 add.int using tailored Input 6 market cost (400 bps, 3 years)."""
        tailored = ctx.tailored
        if tailored is None or tailored.market_cost_bps <= 0.0:
            return pd.Series(0.0, index=list(path.years), dtype=float)
        return MarketFinancingCost(bps=float(tailored.market_cost_bps)).compute(
            path.baseline,
            path.shocked,
            external if external is not None else ctx.external,
            tailored=tailored,
        )


@dataclass(frozen=True, slots=True)
class ComboMarketCost:
    """B6 combo additional external interest (``PV_Base-add.cost.mkt`` R13).

    Only shock-window commercial new borrowing is re-priced at the average
    PB-driven cost uplift (capped at 400 bps). Interest is prior commercial
    stock × uplift rate.
    """

    bps_per_ppt: float = 100.0
    cap_bps: float = 400.0

    def uplift_rate(
        self,
        baseline: MacroDebtBook,
        shocked: MacroDebtBook,
    ) -> float:
        """Average external cost increase as a decimal interest rate."""
        # Reuse market-access rate math (min(400 bps, 100×PB deviation)).
        ext_rate, _dom = _market_add_int_rates(baseline, shocked)
        # _market_add_int_rates already encodes 100 bps/ppt and 400 bps cap.
        return float(ext_rate)

    def compute(
        self,
        baseline: MacroDebtBook,
        shocked: MacroDebtBook,
        external: ExternalDebtBook,
        *,
        shock_years: set[int] | None = None,
    ) -> pd.Series:
        """Additional nominal interest on commercial external debt (USD)."""
        years = shocked.inputs.years
        year_list = list(years)
        first = shocked.inputs.first_projection_year
        if shock_years is None:
            shock_years = _shock_window_years(years, first)
        rate = self.uplift_rate(baseline, shocked)
        if rate <= 0.0 or not shock_years:
            return pd.Series(0.0, index=year_list, dtype=float)

        proj = [y for y in year_list if y >= first]
        interest = pd.Series(0.0, index=year_list, dtype=float)
        for inst in external.portfolio.instruments:
            if not isinstance(inst, PresentValueInstrument):
                continue
            if creditor_group_for_name(str(inst.name)) != "Commercial":
                continue
            disb_series = pd.Series(
                list(inst.disbursements),
                index=list(inst.years)[: len(inst.disbursements)],
                dtype=float,
            )
            disb = [
                float(disb_series.reindex([y]).fillna(0.0).loc[y])
                if y in shock_years
                else 0.0
                for y in proj
            ]
            if not any(abs(v) > 0.0 for v in disb):
                continue
            stock = _amortizing_stock_from_disbursements(
                disb, grace=int(inst.grace), maturity=int(inst.maturity)
            )
            prior = 0.0
            for i, year in enumerate(proj):
                interest.loc[year] = float(interest.loc[year]) + prior * rate
                prior = float(stock[i])
        return interest.astype(float)

    def compute_from_context(
        self,
        ctx: StressContext,
        path: ShockedMacroPath,
        *,
        external: ExternalDebtBook | None = None,
    ) -> pd.Series:
        """Convenience wrapper using a shocked path and optional FX-adjusted Ext."""
        start, end = path.metadata.shock_window_years
        return self.compute(
            path.baseline,
            path.shocked,
            external if external is not None else ctx.external,
            shock_years=set(range(int(start), int(end) + 1)),
        )


__all__ = ["ComboMarketCost", "MarketAccessAddon", "MarketFinancingCost"]
