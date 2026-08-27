"""Public stress DSA with three-way residual financing (``PV_ResFin_pub``)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.residual_pv import (
    PublicResFinOverlay,
    build_public_resfin_overlay,
    gdp_deflator_growth,
    public_residual_gap,
    split_residual_financing,
)
from lic_dsf.stress.shocks import apply_real_gdp_shock
from lic_dsf.stress.types import Input6StandardParams


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def _inflation_elasticity(input6: Input6StandardParams) -> float:
    if not input6.interactions_on:
        return 0.0
    return float(input6.inflation_elasticity)


def _growth_pct(level: pd.Series) -> pd.Series:
    prior = pd.Series(level.shift(1), dtype=float)
    return (100.0 * (level / prior.replace(0.0, pd.NA) - 1.0)).astype(float)


def _b1_public_gdp_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    inflation_elasticity: float,
) -> pd.Series:
    """B1_GDP_pub R41: LCU GDP compounded with shocked real × LCU deflator.

    Differs from ``gdp_usd × FX(pa)``: Excel applies the inflation elasticity
    to the LCU deflator (Macro R109) and compounds in LCU, not USD.
    """
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    base_lcu = _align(baseline_macro.gdp_lcu(), years)
    base_const = _align(baseline_macro.gdp_constant(), years).replace(0.0, pd.NA)
    shock_const = _align(shocked_macro.gdp_constant(), years).replace(0.0, pd.NA)
    real_s = _growth_pct(shock_const)
    real_b = _growth_pct(base_const)
    defl_b = _growth_pct(base_lcu / base_const)
    defl_s = defl_b - (real_b - real_s) * inflation_elasticity
    out = base_lcu.copy()
    for year in years:
        if year <= first:
            continue
        prior = year - 1
        if prior not in out.index:
            continue
        rg = float(real_s.loc[year]) if pd.notna(real_s.loc[year]) else 0.0
        dg = float(defl_s.loc[year]) if pd.notna(defl_s.loc[year]) else 0.0
        out.loc[year] = float(out.loc[prior]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
    return out.astype(float)


def _b1_other_identified_flows_lcu(baseline_macro: MacroDebtBook) -> pd.Series:
    """B1 R89: other identified debt-creating flows at baseline LCU.

    Matches Baseline R33/100 × GDP_LCU: contingent + other flows −
    privatization − debt relief.
    """
    years = baseline_macro.inputs.years
    return (
        _align(baseline_macro.inputs.contingent_liabilities, years).fillna(0.0)
        + _align(baseline_macro.inputs.other_debt_creating_flows, years).fillna(0.0)
        - _align(baseline_macro.inputs.privatization, years).fillna(0.0)
        - _align(baseline_macro.inputs.debt_relief, years).fillna(0.0)
    )


def _b1_primary_deficit_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    shocked_gdp_lcu: pd.Series,
) -> pd.Series:
    """Public R88: primary deficit LCU under stress.

    Non-grant revenue scales with shocked GDP at the baseline share (B1).
    Primary expenditure comes from ``shocked_macro`` so B2's expenditure
    shock feeds GFN; B1 leaves expenditure at baseline LCU.
    """
    years = baseline_macro.inputs.years
    gdp_s = _align(shocked_gdp_lcu, years).replace(0.0, pd.NA)
    gdp_b = _align(baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
    prim_exp = _align(shocked_macro.inputs.primary_expenditure, years).fillna(0.0)
    grants = _align(baseline_macro.grants(), years).fillna(0.0)
    rev_excl = _align(baseline_macro.revenues_incl_grants(), years).fillna(0.0) - grants
    return (prim_exp - rev_excl * (gdp_s / gdp_b) - grants).astype(float)


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
) -> tuple[float, float]:
    """Return (external, domestic) add.int interest rates (decimals).

    Matches ``PV_ResFin-add.int.cost - mkt`` B37–B40: external is
    ``min(400 bps, 100 bps × PB-deviation)`` averaged over the shock window;
    domestic is ``25 bps × PB-deviation`` averaged the same way.
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


def _market_add_int_interest_lcu(
    resfin: PublicResFinOverlay,
    shocked_macro: MacroDebtBook,
    baseline_macro: MacroDebtBook | None = None,
) -> pd.Series:
    """Market-access add.int interest in LCU (ext × FX + domestic).

    Mirrors ``PV_ResFin-add.int.cost - mkt`` interest rows fed into B2 R85–R87.
    Disbursements are restricted to the PB shock window.
    """
    years = list(shocked_macro.inputs.years)
    first = shocked_macro.inputs.first_projection_year
    proj = [y for y in years if y >= first]
    shock_years = _shock_window_years(shocked_macro.inputs.years, first)
    fx = _align(shocked_macro.fx_pa(), shocked_macro.inputs.years).fillna(1.0)
    if baseline_macro is not None:
        ext_rate, dom_rate = _market_add_int_rates(baseline_macro, shocked_macro)
    else:
        ext_rate, dom_rate = 0.04, 0.0203

    ext_disb = [
        float(resfin.fill.external_mlt_usd.reindex([y]).fillna(0.0).loc[y])
        if y in shock_years
        else 0.0
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
    out = pd.Series(0.0, index=years, dtype=float)
    prior_ext = 0.0
    prior_dom_mlt = 0.0
    prior_dom_st = 0.0
    for i, year in enumerate(proj):
        out.loc[year] = (
            prior_ext * ext_rate * float(fx.loc[year])
            + prior_dom_mlt * dom_rate
            + prior_dom_st * dom_rate
        )
        prior_ext = ext_stock[i]
        prior_dom_mlt = dom_mlt_stock[i]
        prior_dom_st = dom_st_disb[i]
    return out.astype(float)


def estimate_b1_public_gfn(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay | None = None,
    *,
    inflation_elasticity: float = 0.0,
    gdp_lcu: pd.Series | None = None,
    market_access: bool = False,
) -> pd.Series:
    """B1_GDP_pub R90 public GFN (LCU).

    Identity: primary deficit + existing interest + existing amort + prior
    domestic ST + other identified flows. Debt service is not scaled with
    GDP. Residual-financing service and prior ResFin ST are added when
    ``resfin`` is provided (R84–R87 / prior R81). Market-access B2 also
    adds ``PV_ResFin-add.int.cost - mkt`` interest into the GFN identity.
    """
    years = shocked_macro.inputs.years
    shocked_gdp = (
        gdp_lcu
        if gdp_lcu is not None
        else _b1_public_gdp_lcu(baseline_macro, shocked_macro, inflation_elasticity)
    )
    fx = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    interest = _align(shocked_macro.interest_expenditure(), years).fillna(0.0)
    amort = (
        _align(shocked_macro.ppg_amortization(), years).fillna(0.0)
        + _align(shocked_macro.domestic_amortization(), years).fillna(0.0)
    ) * fx
    prior_st = _align(shocked_macro.domestic_st(), years).shift(1).fillna(0.0)
    gfn = (
        _b1_primary_deficit_lcu(baseline_macro, shocked_macro, shocked_gdp)
        + interest
        + amort
        + prior_st
        + _b1_other_identified_flows_lcu(baseline_macro)
    ).astype(float)

    if resfin is None:
        return gfn

    first = shocked_macro.inputs.first_projection_year
    extra = pd.Series(0.0, index=list(years), dtype=float)
    for year in years:
        if year < first:
            continue
        extra.loc[year] = (
            float(resfin.dom_mlt.interest.reindex([year]).fillna(0.0).loc[year])
            + float(resfin.dom_st.interest.reindex([year]).fillna(0.0).loc[year])
            + float(resfin.ext.interest.reindex([year]).fillna(0.0).loc[year])
            * float(fx.loc[year])
            + float(resfin.ext.amortization.reindex([year]).fillna(0.0).loc[year])
            * float(fx.loc[year])
            + float(resfin.dom_mlt.amortization.reindex([year]).fillna(0.0).loc[year])
        )
    prior_resfin_st = resfin.dom_st.stock.shift(1).fillna(0.0)
    for year in years:
        if year < first:
            continue
        extra.loc[year] = float(extra.loc[year]) + float(
            prior_resfin_st.reindex([year]).fillna(0.0).loc[year]
        )
    if market_access:
        extra = extra + _market_add_int_interest_lcu(
            resfin, shocked_macro, baseline_macro
        )
    return (gfn + extra).astype(float)


@dataclass(slots=True)
class StressPublicBook:
    """Public DSA ratios under stress with three-way ResFin overlays."""

    macro: MacroDebtBook
    external: ExternalDebtBook
    baseline_macro: MacroDebtBook
    resfin: PublicResFinOverlay
    scenario_id: str = "B1_GDP_pub"
    inflation_elasticity: float = 0.0
    market_access: bool = False
    # Excel B2_mkt uses PV_ResFin upper block (market gap) for external PV
    # but the lower block (non-mkt gap) for external DS (R145). When set,
    # debt-service ratios use this overlay's external service instead of
    # ``resfin.ext``.
    resfin_external_ds: PublicResFinOverlay | None = None

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked Macro book."""
        return self.macro.inputs.years

    def gdp_lcu(self) -> pd.Series:
        """B1 R41 shocked GDP in LCU (real × LCU deflator compounding)."""
        return _b1_public_gdp_lcu(
            self.baseline_macro, self.macro, self.inflation_elasticity
        )

    def _resfin_external_lcu(self) -> pd.Series:
        fx = self.macro.fx_pa()
        return _align(self.resfin.ext.pv, self.years).fillna(0.0) * _align(
            fx, self.years
        ).fillna(1.0)

    def _resfin_domestic_debt(self) -> pd.Series:
        return _align(self.resfin.dom_mlt.stock, self.years).fillna(0.0) + _align(
            self.resfin.dom_st.stock, self.years
        ).fillna(0.0)

    def _market_add_int_interest_usd(self) -> pd.Series:
        """``PV_ResFin-add.int.cost - mkt`` R34 additional external interest."""
        if not self.market_access:
            return pd.Series(0.0, index=list(self.years), dtype=float)
        stock = self._market_add_int_stock_usd()
        ext_rate, _dom = _market_add_int_rates(self.baseline_macro, self.macro)
        prior = stock.shift(1).fillna(0.0)
        return (prior * ext_rate).astype(float)

    def _market_add_int_stock_usd(self) -> pd.Series:
        """Add.int face stock: shock-window forex disb only, then amortize."""
        years = list(self.years)
        first = self.macro.inputs.first_projection_year
        proj = [y for y in years if y >= first]
        shock_years = _shock_window_years(self.years, first)
        disb = _align(self.resfin.fill.external_mlt_usd, self.years).fillna(0.0)
        new_borrowing = [
            float(disb.loc[y]) if y in shock_years else 0.0 for y in proj
        ]
        stock_proj = _amortizing_stock_from_disbursements(
            new_borrowing, grace=4, maturity=9
        )
        out = pd.Series(0.0, index=years, dtype=float)
        for year, value in zip(proj, stock_proj, strict=True):
            out.loc[year] = float(value)
        return out.astype(float)

    def _market_add_int_pv_usd(self) -> pd.Series:
        """``PV_ResFin-add.int.cost - mkt`` R32 PV of future add. interest.

        Excel's B2 market sheet adds this overlay from the second shock year
        onward (``G91``+), not in the first shock year (``F91``).
        """
        if not self.market_access:
            return pd.Series(0.0, index=list(self.years), dtype=float)
        interest = self._market_add_int_interest_usd()
        years = list(self.years)
        first = self.macro.inputs.first_projection_year
        proj = [y for y in years if y >= first]
        first_add_year = proj[2] if len(proj) >= 3 else (proj[-1] if proj else None)
        discount = 0.05
        ext_rate, _dom = _market_add_int_rates(self.baseline_macro, self.macro)
        out = pd.Series(0.0, index=years, dtype=float)
        for i, year in enumerate(years):
            if first_add_year is None or year < first_add_year:
                continue
            future = interest.iloc[i + 1 :].astype(float).tolist()
            if not future:
                continue
            if ext_rate > discount:
                out.loc[year] = float(sum(future))
            else:
                out.loc[year] = float(
                    sum(v / ((1.0 + discount) ** (k + 1)) for k, v in enumerate(future))
                )
        return out.astype(float)

    def _resfin_ext_stock_usd(self) -> pd.Series:
        """Face stock of public ResFin external MLT (USD)."""
        external = self.resfin.ext.instrument.external()
        key = "Stock of new forex debt (in USD)"
        years = list(self.years)
        if key not in external.index:
            return _align(self.resfin.ext.pv, self.years).fillna(0.0)
        values = {
            year: float(external.loc[key, year]) if year in external.columns else 0.0
            for year in years
        }
        return pd.Series(values, dtype=float)

    def _external_pv_usd(self) -> pd.Series:
        """Baseline Ext PPG PV + public ResFin PV (+ market add.int PV)."""
        return (
            _align(self.external.total_pv_of_debt(), self.years).fillna(0.0)
            + _align(self.resfin.ext.pv, self.years).fillna(0.0)
            + self._market_add_int_pv_usd()
        ).astype(float)

    def _external_ppg_debt_service_usd(self) -> pd.Series:
        """PPG external DS + ResFin service (+ market add.int interest).

        Market-access Excel wires DS to the non-mkt ResFin block (R145) plus
        add.int interest, while PV uses the market ResFin block (R111).
        """
        ds_resfin = self.resfin_external_ds or self.resfin
        return (
            _align(self.baseline_macro.ppg_interest(), self.years).fillna(0.0)
            + _align(self.baseline_macro.ppg_amortization(), self.years).fillna(0.0)
            + _align(ds_resfin.ext.interest, self.years).fillna(0.0)
            + _align(ds_resfin.ext.amortization, self.years).fillna(0.0)
            + self._market_add_int_interest_usd()
        ).astype(float)

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet external PV / GDP (R101)."""
        gdp_usd = self.gdp_lcu() / _align(self.macro.fx_pa(), self.years).replace(
            0.0, pd.NA
        )
        return _clamp_nonnegative(_pct(self._external_pv_usd(), gdp_usd))

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet external PV / exports (R102)."""
        return _clamp_nonnegative(
            _pct(self._external_pv_usd(), self.baseline_macro.exports())
        )

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet PPG DS / exports (R103)."""
        return _clamp_nonnegative(
            _pct(
                self._external_ppg_debt_service_usd(),
                self.baseline_macro.exports(),
            )
        )

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """Output 3-1 B2 path: public-sheet PPG DS / revenue excl. grants (R104)."""
        return _clamp_nonnegative(
            _pct(
                self._external_ppg_debt_service_usd(),
                self.baseline_macro.revenues_excl_grants(),
            )
        )

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Public debt / GDP including ResFin stocks."""
        numer = (
            self.macro.total_public_debt()
            + self._resfin_external_lcu()
            + self._resfin_domestic_debt()
        )
        return _pct(numer, self.gdp_lcu())

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """PV of public debt / GDP including ResFin PV."""
        numer = (
            self.macro.pv_external_lcu()
            + self.macro.public_domestic_debt()
            + self._resfin_external_lcu()
            + _align(self.resfin.dom_mlt.pv, self.years).fillna(0.0)
            + _align(self.resfin.dom_st.stock, self.years).fillna(0.0)
        )
        return _clamp_nonnegative(_pct(numer, self.gdp_lcu()))

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """PV of public debt / revenue+grants (Output 3-2 middle block).

        B1 holds fiscal ratios as percent of GDP, so the revenue/GDP
        denominator is the baseline path. Do not divide unshocked LCU
        revenue by shocked GDP.
        """
        base_rev_to_gdp = _pct(
            self.baseline_macro.revenues_incl_grants(),
            self.baseline_macro.gdp_lcu(),
        )
        return (
            self.pv_public_debt_to_gdp() / base_rev_to_gdp.replace(0.0, pd.NA) * 100.0
        ).astype(float)

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Debt service / revenue+grants including ResFin service."""
        fx = self.macro.fx_pa()
        prior_dom_st = pd.Series(self.macro.domestic_st().shift(1), dtype=float).fillna(
            0.0
        )
        prior_resfin_st = (
            _align(self.resfin.dom_st.stock, self.years).shift(1).fillna(0.0)
        )
        numer = (
            self.macro.interest_expenditure()
            + prior_dom_st
            + prior_resfin_st
            + (self.macro.domestic_amortization() + self.macro.ppg_amortization()) * fx
            + _align(self.resfin.dom_mlt.interest, self.years).fillna(0.0)
            + _align(self.resfin.dom_st.interest, self.years).fillna(0.0)
            + _align(self.resfin.dom_mlt.amortization, self.years).fillna(0.0)
            + _align(self.resfin.ext.interest, self.years).fillna(0.0) * fx
            + _align(self.resfin.ext.amortization, self.years).fillna(0.0) * fx
        )
        return _clamp_nonnegative(_pct(numer, self.macro.revenues_incl_grants()))

    def public_gfn(self) -> pd.Series:
        """B1 R90 public GFN (LCU)."""
        return estimate_b1_public_gfn(
            self.baseline_macro,
            self.macro,
            self.resfin,
            inflation_elasticity=self.inflation_elasticity,
            market_access=self.market_access,
        )

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP including ResFin service."""
        rev_to_gdp = _pct(
            self.baseline_macro.revenues_incl_grants(),
            self.baseline_macro.gdp_lcu(),
        )
        return (self.debt_service_to_revenue_grants() * rev_to_gdp / 100.0).astype(
            float
        )


def _run_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    shocked_macro: MacroDebtBook,
    scenario_id: str,
    *,
    inflation_elasticity: float = 0.0,
    iterations: int = 25,
    tol: float = 1e-6,
    public_gap: pd.Series | None = None,
    ext_r86: pd.Series | None = None,
    market_access: bool = False,
) -> StressPublicBook:
    """Shocked Macro + three-way public ResFin fixed point."""
    years = shocked_macro.inputs.years
    shocked_gdp_lcu = _b1_public_gdp_lcu(macro, shocked_macro, inflation_elasticity)
    r86 = (
        ext_r86.reindex(list(years)).fillna(0.0).astype(float)
        if ext_r86 is not None
        else pd.Series(0.0, index=list(years), dtype=float)
    )
    deflator = gdp_deflator_growth(macro.gdp_lcu(), macro.gdp_constant())
    fx = shocked_macro.fx_pa()
    baseline_gfn = macro.public_gfn()

    if public_gap is not None:
        gap = public_gap.reindex(list(years)).fillna(0.0).astype(float)
        fill = split_residual_financing(
            gap, r86, residual_params, fx, modality="capped", years=years
        )
        overlay = build_public_resfin_overlay(
            fill, residual_params, deflator=deflator, years=years
        )
        return StressPublicBook(
            macro=shocked_macro,
            external=external,
            baseline_macro=macro,
            resfin=overlay,
            scenario_id=scenario_id,
            inflation_elasticity=inflation_elasticity,
            market_access=market_access,
        )

    overlay: PublicResFinOverlay | None = None
    prev_gap: pd.Series | None = None
    for _ in range(max(iterations, 1)):
        stressed_gfn = estimate_b1_public_gfn(
            macro,
            shocked_macro,
            overlay,
            inflation_elasticity=inflation_elasticity,
            gdp_lcu=shocked_gdp_lcu,
            market_access=market_access,
        )
        gap = public_residual_gap(stressed_gfn, baseline_gfn, years)
        for year in years:
            if year < shocked_macro.inputs.first_projection_year:
                gap.loc[year] = 0.0
        fill = split_residual_financing(
            gap, r86, residual_params, fx, modality="capped", years=years
        )
        overlay = build_public_resfin_overlay(
            fill, residual_params, deflator=deflator, years=years
        )
        if prev_gap is not None and float((gap - prev_gap).abs().max()) < tol:
            break
        prev_gap = gap

    assert overlay is not None
    resfin_external_ds: PublicResFinOverlay | None = None
    if market_access:
        # Non-mkt GFN (no add.int) drives Excel's R145 DS block.
        overlay_ds: PublicResFinOverlay | None = None
        prev_gap_ds: pd.Series | None = None
        for _ in range(max(iterations, 1)):
            stressed_gfn_ds = estimate_b1_public_gfn(
                macro,
                shocked_macro,
                overlay_ds,
                inflation_elasticity=inflation_elasticity,
                gdp_lcu=shocked_gdp_lcu,
                market_access=False,
            )
            gap_ds = public_residual_gap(stressed_gfn_ds, baseline_gfn, years)
            for year in years:
                if year < shocked_macro.inputs.first_projection_year:
                    gap_ds.loc[year] = 0.0
            fill_ds = split_residual_financing(
                gap_ds, r86, residual_params, fx, modality="capped", years=years
            )
            overlay_ds = build_public_resfin_overlay(
                fill_ds, residual_params, deflator=deflator, years=years
            )
            if (
                prev_gap_ds is not None
                and float((gap_ds - prev_gap_ds).abs().max()) < tol
            ):
                break
            prev_gap_ds = gap_ds
        resfin_external_ds = overlay_ds

    return StressPublicBook(
        macro=shocked_macro,
        external=external,
        baseline_macro=macro,
        resfin=overlay,
        scenario_id=scenario_id,
        inflation_elasticity=inflation_elasticity,
        market_access=market_access,
        resfin_external_ds=resfin_external_ds,
    )


def run_b1_gdp_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    iterations: int = 25,
    tol: float = 1e-6,
    public_gap: pd.Series | None = None,
    ext_r86: pd.Series | None = None,
) -> StressPublicBook:
    """Run B1 real-GDP public stress with three-way residual financing.

    Args:
        macro: Baseline Macro book.
        external: Baseline Ext book.
        input6: Input 6 standard shock params.
        residual_params: Input 7 value-used params (public J shares + terms).
        iterations: Max fixed-point iterations for GFN ↔ ResFin feedback
            (stops early when ``max(|Δ gap|) < tol``).
        tol: Convergence tolerance on successive public residual gaps (LCU).
        public_gap: Optional precomputed public ΔGFN (LCU); skips GFN iteration.
        ext_r86: Optional external residual gap (USD); defaults to zeros (B1).

    Returns:
        ``StressPublicBook`` with ResFin fill and overlays.
    """
    shocked_inputs = apply_real_gdp_shock(macro.inputs, input6)
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B1_GDP_pub",
        inflation_elasticity=_inflation_elasticity(input6),
        iterations=iterations,
        tol=tol,
        public_gap=public_gap,
        ext_r86=ext_r86,
    )


def run_a1_historical_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public A1: key variables at 10-year historical averages."""
    from lic_dsf.stress.shocks import apply_historical_averages_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_historical_averages_shock(macro.inputs), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "A1_Historical_pub"
    )


def run_b2_pb_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> StressPublicBook:
    """Public B2 primary-balance stress.

    Output 3-1 wires B2 from the public B2 sheet's external-ratio block
    (``B2_PB_mkt_pub`` / ``B2_PB_non_mkt_pub``). Pass ``market_access=True``
    to include the market-access additional-interest PV overlay.
    """
    from lic_dsf.stress.shocks import apply_primary_balance_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_primary_balance_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B2_PrimaryBalance_pub",
        market_access=market_access,
    )


def run_b3_exports_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B3 exports stress."""
    from lic_dsf.stress.shocks import apply_exports_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_exports_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "B3_Exports_pub"
    )


def run_b4_other_flows_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B4 other-flows stress."""
    from lic_dsf.stress.shocks import apply_other_flows_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_other_flows_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked_macro, "B4_OtherFlows_pub"
    )


def run_b5_fx_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B5 FX-depreciation stress."""
    from lic_dsf.stress.shocks import apply_fx_depreciation_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_fx_depreciation_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B5_FX_pub",
        inflation_elasticity=_inflation_elasticity(input6),
    )


def run_b6_combo_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Public B6 combination stress."""
    from lic_dsf.stress.shocks import apply_combo_shock

    shocked_macro = MacroDebtBook(
        inputs=apply_combo_shock(macro.inputs, input6), external=external
    )
    return _run_public_stress(
        macro,
        external,
        residual_params,
        shocked_macro,
        "B6_Combo_pub",
        inflation_elasticity=_inflation_elasticity(input6),
    )


def run_standard_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> dict[str, StressPublicBook]:
    """Run public A1 / B1–B6 and return them by scenario id."""
    return {
        "A1_Historical": run_a1_historical_public(macro, external, residual_params),
        "B1_GDP": run_b1_gdp_public(macro, external, input6, residual_params),
        "B2_PrimaryBalance": run_b2_pb_public(
            macro, external, input6, residual_params, market_access=market_access
        ),
        "B3_Exports": run_b3_exports_public(macro, external, input6, residual_params),
        "B4_OtherFlows": run_b4_other_flows_public(
            macro, external, input6, residual_params
        ),
        "B5_FX": run_b5_fx_public(macro, external, input6, residual_params),
        "B6_Combo": run_b6_combo_public(macro, external, input6, residual_params),
    }
