"""Market-access and combo additional-interest overlays."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.creditor_groups import creditor_group_for_name
from lic_dsf.pv.instrument import PresentValueInstrument
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.public_gfn import _align
from lic_dsf.stress.residual_pv import PublicResFinOverlay

if TYPE_CHECKING:
    from lic_dsf.stress.context import StressContext
    from lic_dsf.stress.ratios.public import StressPublicRatios
    from lic_dsf.stress.tailored_params import TailoredParams


def _shock_window_years(
    years: tuple[int, ...], first_projection_year: int
) -> set[int]:
    """Second and third projection years (Input 6 bound-test window)."""
    proj = [y for y in years if y >= first_projection_year]
    return set(proj[1:3]) if len(proj) >= 3 else set()


def _amortizing_stock_from_disbursements(
    disbursements: list[float],
    *,
    grace: int,
    maturity: int,
) -> list[float]:
    """Excel CHOOSE-style cumulative amortization stock path."""
    grace = max(int(grace), 0)
    maturity = max(int(maturity), grace + 1)
    span = float(maturity - grace)
    cumulative: list[float] = []
    running = 0.0
    for amount in disbursements:
        running += amount
        cumulative.append(running)

    def _cum_at(offset: int) -> float:
        if offset <= 0:
            return 0.0
        idx = offset - 1
        if idx >= len(cumulative):
            return 0.0
        return cumulative[idx]

    stock: list[float] = []
    for t, amount in enumerate(disbursements):
        tg = max(t - grace, 0)
        tm = max(t - maturity, 0)
        amort = (_cum_at(tg) - _cum_at(tm)) / span if span else 0.0
        if t == 0:
            stock.append(max(amount - amort, 0.0))
        else:
            stock.append(max(stock[t - 1] + amount - amort, 0.0))
    return stock


def _market_add_int_rates(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    *,
    stressed_primary_deficit_pct: pd.Series | None = None,
) -> tuple[float, float]:
    """Return (external, domestic) add.int interest rates (decimals).

    Matches ``PV_ResFin-add.int.cost - mkt`` B37–B40: external is
    ``min(400 bps, 100 bps × PB-deviation)`` averaged over the shock window;
    domestic is ``25 bps × PB-deviation`` averaged the same way.

    PB deviation is ``stressed_primary_deficit% − baseline_primary_deficit%``
    (Excel B6 block: ``B6!R17 − Baseline!R23``). When
    ``stressed_primary_deficit_pct`` is omitted, the shocked macro's primary
    balance is converted to a deficit %.
    """
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    shock_years = sorted(_shock_window_years(years, first))
    if not shock_years:
        return 0.04, 0.0
    gdp = _align(baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
    base_pb = (
        100.0
        * (
            _align(baseline_macro.inputs.revenues_incl_grants, years)
            - _align(baseline_macro.inputs.primary_expenditure, years)
        )
        / gdp
    )
    if stressed_primary_deficit_pct is not None:
        # Excel Baseline R23 is primary deficit % (= −balance). Deviation:
        # stressed_deficit − baseline_deficit = R17 − R23.
        base_deficit = (-base_pb).astype(float)
        stress_def = _align(stressed_primary_deficit_pct, years).astype(float)
        deviations = [
            float(stress_def.loc[y]) - float(base_deficit.loc[y])
            if pd.notna(stress_def.loc[y]) and pd.notna(base_deficit.loc[y])
            else 0.0
            for y in shock_years
        ]
    else:
        shock_pb = (
            100.0
            * (
                _align(shocked_macro.inputs.revenues_incl_grants, years)
                - _align(shocked_macro.inputs.primary_expenditure, years)
            )
            / gdp
        )
        # Excel R17 is primary deficit % (= −balance). Deviation in deficit ppt:
        deviations = [
            float((-shock_pb.loc[y]) - (-base_pb.loc[y]))
            if pd.notna(shock_pb.loc[y]) and pd.notna(base_pb.loc[y])
            else 0.0
            for y in shock_years
        ]
    ext_rates = [min(0.04, d) for d in deviations]
    dom_rates = [25.0 / 10000.0 * d for d in deviations]
    return (
        float(sum(ext_rates) / len(ext_rates)),
        float(sum(dom_rates) / len(dom_rates)),
    )


def _market_add_int_interest_parts(
    resfin: PublicResFinOverlay,
    shocked_macro: MacroDebtBook,
    baseline_macro: MacroDebtBook | None = None,
    *,
    stressed_primary_deficit_pct: pd.Series | None = None,
    external_dsa_borrowing_usd: pd.Series | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Market-access add.int interest split (ext USD, dom MLT LCU, dom ST LCU).

    Mirrors ``PV_ResFin-add.int.cost - mkt`` rows 100 / 113 / 122 fed into
    B6 ``R87`` / ``R86``.

    B6 external add.int (row 95/100) disburses from external DSA R86
    (``PV_ResFin_pub`` row 210), not the public three-way external fill.
    Domestic legs still use the public ResFin fill.
    """
    years = list(shocked_macro.inputs.years)
    first = shocked_macro.inputs.first_projection_year
    proj = [y for y in years if y >= first]
    shock_years = _shock_window_years(shocked_macro.inputs.years, first)
    if baseline_macro is not None:
        ext_rate, dom_rate = _market_add_int_rates(
            baseline_macro,
            shocked_macro,
            stressed_primary_deficit_pct=stressed_primary_deficit_pct,
        )
    else:
        ext_rate, dom_rate = 0.04, 0.0203

    if external_dsa_borrowing_usd is not None:
        ext_src = _align(external_dsa_borrowing_usd, tuple(years)).fillna(0.0)
    else:
        ext_src = resfin.fill.external_mlt_usd
    ext_disb = [
        float(ext_src.reindex([y]).fillna(0.0).loc[y]) if y in shock_years else 0.0
        for y in proj
    ]
    dom_mlt_disb = [
        float(resfin.fill.domestic_mlt_lcu.reindex([y]).fillna(0.0).loc[y])
        if y in shock_years
        else 0.0
        for y in proj
    ]
    dom_st_disb = [
        float(resfin.fill.domestic_st_lcu.reindex([y]).fillna(0.0).loc[y])
        if y in shock_years
        else 0.0
        for y in proj
    ]
    ext_stock = _amortizing_stock_from_disbursements(ext_disb, grace=4, maturity=9)
    dom_mlt_stock = _amortizing_stock_from_disbursements(
        dom_mlt_disb, grace=2, maturity=3
    )
    ext_usd = pd.Series(0.0, index=years, dtype=float)
    dom_mlt = pd.Series(0.0, index=years, dtype=float)
    dom_st = pd.Series(0.0, index=years, dtype=float)
    prior_ext = 0.0
    prior_dom_mlt = 0.0
    prior_dom_st = 0.0
    for i, year in enumerate(proj):
        ext_usd.loc[year] = prior_ext * ext_rate
        dom_mlt.loc[year] = prior_dom_mlt * dom_rate
        dom_st.loc[year] = prior_dom_st * dom_rate
        prior_ext = ext_stock[i]
        prior_dom_mlt = dom_mlt_stock[i]
        prior_dom_st = dom_st_disb[i]
    return ext_usd.astype(float), dom_mlt.astype(float), dom_st.astype(float)


def _market_add_int_interest_lcu(
    resfin: PublicResFinOverlay,
    shocked_macro: MacroDebtBook,
    baseline_macro: MacroDebtBook | None = None,
    *,
    include_external: bool = True,
) -> pd.Series:
    """Market-access add.int interest in LCU (ext × FX + domestic).

    Mirrors ``PV_ResFin-add.int.cost - mkt`` interest rows fed into B2 R85–R87.
    Disbursements are restricted to the PB shock window. Excel's non-mkt GFN
    keeps domestic add.int and zeros the external rate.
    """
    years = shocked_macro.inputs.years
    fx = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    ext_usd, dom_mlt, dom_st = _market_add_int_interest_parts(
        resfin, shocked_macro, baseline_macro
    )
    if not include_external:
        ext_usd = ext_usd * 0.0
    return (ext_usd * fx + dom_mlt + dom_st).astype(float)


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


__all__ = [
    "ComboMarketCost",
    "MarketAccessAddon",
    "MarketFinancingCost",
    "_amortizing_stock_from_disbursements",
    "_market_add_int_interest_lcu",
    "_market_add_int_interest_parts",
    "_market_add_int_rates",
    "_shock_window_years",
]
