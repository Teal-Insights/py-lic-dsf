"""Public GFN identity (B-sheet R88–R90 / PV_ResFin_pub R67)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.residual_pv import PublicResFinOverlay, public_residual_gap
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


def _extra_fx_depreciation_ppt(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
) -> pd.Series:
    """Shock-year extra eop FX depreciation vs baseline (percentage points)."""
    years = shocked_macro.inputs.years
    fx_b = _align(baseline_macro.fx_eop(), years)
    fx_s = _align(shocked_macro.fx_eop(), years)
    extra = 100.0 * (
        fx_s / fx_s.shift(1).replace(0.0, pd.NA)
        - fx_b / fx_b.shift(1).replace(0.0, pd.NA)
    )
    return extra.fillna(0.0).astype(float)


def _fx_shock_projection_year(
    years: tuple[int, ...], first_projection_year: int
) -> int | None:
    """Second projection year — Excel applies FX passthrough to LCU deflator."""
    proj = [y for y in years if y >= first_projection_year]
    return proj[1] if len(proj) >= 2 else None


def _shocked_real_and_lcu_deflator(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    inflation_elasticity: float,
    fx_passthrough: float = 0.0,
    fx_depreciation_pct: float = 0.0,
) -> tuple[pd.Series, pd.Series]:
    """Shocked real GDP growth and LCU deflator (%) for public B-sheets.

    LCU deflator is the baseline LCU deflator, minus the inflation-elasticity
    interaction on the real-growth gap. B5/B6 add ``passthrough × depreciation``
    in the **second projection year** only (Excel public R54), using the Input 6
    shock size — not the realized extra FX depreciation from compounded paths.
    """
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    base_lcu = _align(baseline_macro.gdp_lcu(), years)
    base_const = _align(baseline_macro.gdp_constant(), years).replace(0.0, pd.NA)
    shock_const = _align(shocked_macro.gdp_constant(), years).replace(0.0, pd.NA)
    real_s = _growth_pct(shock_const)
    real_b = _growth_pct(base_const)
    defl_b = _growth_pct(base_lcu / base_const)
    if fx_passthrough and fx_depreciation_pct:
        # B5/B6 public R54: baseline LCU deflator plus passthrough × shock size
        # in the FX year only; Excel does not apply the GDP ε deflator interaction
        # on these sheets (B6 combo has real_growth gaps but R54 still tracks defl_b).
        defl_s = defl_b.copy()
        shock_year = _fx_shock_projection_year(years, first)
        if shock_year is not None:
            defl_s.loc[shock_year] = float(defl_b.loc[shock_year]) + float(
                fx_passthrough
            ) * float(fx_depreciation_pct)
    else:
        defl_s = defl_b - (real_b - real_s) * inflation_elasticity
    return real_s.astype(float), defl_s.astype(float)


def _b1_public_gdp_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    inflation_elasticity: float,
    fx_passthrough: float = 0.0,
    fx_depreciation_pct: float = 0.0,
) -> pd.Series:
    """B1_GDP_pub R41: LCU GDP compounded with shocked real × LCU deflator.

    Differs from ``gdp_usd × FX(pa)``: Excel applies the inflation elasticity
    to the LCU deflator (Macro R109) and compounds in LCU, not USD. B5/B6 add
    FX passthrough into that LCU deflator in the depreciation year.
    """
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    real_s, defl_s = _shocked_real_and_lcu_deflator(
        baseline_macro,
        shocked_macro,
        inflation_elasticity,
        fx_passthrough=fx_passthrough,
        fx_depreciation_pct=fx_depreciation_pct,
    )
    out = _align(baseline_macro.gdp_lcu(), years).copy()
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


def _a1_public_gdp_lcu(baseline_macro: MacroDebtBook) -> pd.Series:
    """A1_Historical_pub R41: LCU GDP with hist-avg real × LCU deflator.

    Excel pins both rates to 10-year historical means from the second
    projection year (``R42`` / ``R54``), not the USD-deflator path used on
    the external A1 Macro shock.
    """
    from lic_dsf.stress.macro_shocks import _hist_mean_sd

    years = baseline_macro.inputs.years
    first = baseline_macro.inputs.first_projection_year
    proj = [y for y in years if y >= first]
    start = proj[1] if len(proj) >= 2 else (proj[0] if proj else first)
    real_g = _growth_pct(_align(baseline_macro.gdp_constant(), years))
    defl_g = _align(baseline_macro.lcu_deflator_growth(), years)
    hist_real, _ = _hist_mean_sd(real_g, years, first)
    hist_defl, _ = _hist_mean_sd(defl_g, years, first)
    out = _align(baseline_macro.gdp_lcu(), years).copy()
    for year in years:
        if year < start:
            continue
        prior = year - 1
        if prior not in out.index:
            continue
        out.loc[year] = (
            float(out.loc[prior])
            * (1.0 + float(hist_real) / 100.0)
            * (1.0 + float(hist_defl) / 100.0)
        )
    return out.astype(float)


def _public_real_and_lcu_deflator(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    inflation_elasticity: float,
    *,
    historical: bool,
    fx_passthrough: float = 0.0,
    fx_depreciation_pct: float = 0.0,
) -> tuple[pd.Series, pd.Series]:
    """Real GDP growth and LCU deflator (%) used on public B-sheets."""
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    if historical:
        from lic_dsf.stress.macro_shocks import _hist_mean_sd

        proj = [y for y in years if y >= first]
        start = proj[1] if len(proj) >= 2 else (proj[0] if proj else first)
        real_g = _growth_pct(_align(baseline_macro.gdp_constant(), years))
        defl_g = _align(baseline_macro.lcu_deflator_growth(), years)
        hist_real, _ = _hist_mean_sd(real_g, years, first)
        hist_defl, _ = _hist_mean_sd(defl_g, years, first)
        real_s = real_g.copy()
        defl_s = defl_g.copy()
        for year in years:
            if year >= start:
                real_s.loc[year] = float(hist_real)
                defl_s.loc[year] = float(hist_defl)
        return real_s.astype(float), defl_s.astype(float)

    return _shocked_real_and_lcu_deflator(
        baseline_macro,
        shocked_macro,
        inflation_elasticity,
        fx_passthrough=fx_passthrough,
        fx_depreciation_pct=fx_depreciation_pct,
    )


def _b1_other_identified_flows_lcu(macro: MacroDebtBook) -> pd.Series:
    """Public R89: other identified debt-creating flows (LCU).

    Matches Baseline R33/100 × GDP_LCU: contingent + other flows −
    privatization − debt relief. Callers pass the shocked Macro so C1 / any
    other-flow shock on those fields enters GFN and debt dynamics; B1–B5 keep
    baseline levels.
    """
    years = macro.inputs.years
    return (
        _align(macro.inputs.contingent_liabilities, years).fillna(0.0)
        + _align(macro.inputs.other_debt_creating_flows, years).fillna(0.0)
        - _align(macro.inputs.privatization, years).fillna(0.0)
        - _align(macro.inputs.debt_relief, years).fillna(0.0)
    )


def _b1_primary_deficit_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    shocked_gdp_lcu: pd.Series,
    *,
    primary_exp_gdp_denominator: pd.Series | None = None,
    use_shocked_revenues: bool = False,
) -> pd.Series:
    """Public R88: primary deficit LCU under stress.

    Non-grant revenue scales with shocked GDP at the baseline share (B1).
    Primary expenditure comes from ``shocked_macro`` so B2's expenditure
    shock feeds GFN; B1 leaves expenditure at baseline LCU.

    Excel ``C3_commodity_prices_pub`` R20/R88: expenditure % uses
    ``B1_GDP_pub`` R41 in the denominator (template quirk), and revenue
    includes the Input 6 L27 drop on the shocked path — pass
    ``primary_exp_gdp_denominator`` + ``use_shocked_revenues=True``.
    """
    years = baseline_macro.inputs.years
    gdp_s = _align(shocked_gdp_lcu, years).replace(0.0, pd.NA)
    prim_exp = _align(shocked_macro.inputs.primary_expenditure, years).fillna(0.0)
    if primary_exp_gdp_denominator is not None and use_shocked_revenues:
        denom = _align(primary_exp_gdp_denominator, years).replace(0.0, pd.NA)
        gdp_b = _align(baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
        grants = _align(baseline_macro.grants(), years).fillna(0.0)
        rev_excl_b = (
            _align(baseline_macro.revenues_incl_grants(), years).fillna(0.0) - grants
        )
        # Excel R18: baseline nongrant % + grants % − AA66 (revenue drop ppt),
        # applied to C3 R41 — not the USD-GDP hold used on the external path.
        shock_gdp = _align(shocked_macro.gdp_lcu(), years).replace(0.0, pd.NA)
        held_on_shock = rev_excl_b * (shock_gdp / gdp_b) + grants
        drop_on_shock = held_on_shock - _align(
            shocked_macro.revenues_incl_grants(), years
        ).fillna(0.0)
        drop_on_r41 = drop_on_shock / shock_gdp * gdp_s
        rev_on_r41 = rev_excl_b * (gdp_s / gdp_b) + grants - drop_on_r41
        return (prim_exp * gdp_s / denom - rev_on_r41).astype(float)
    gdp_b = _align(baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
    grants = _align(baseline_macro.grants(), years).fillna(0.0)
    rev_excl = _align(baseline_macro.revenues_incl_grants(), years).fillna(0.0) - grants
    return (prim_exp - rev_excl * (gdp_s / gdp_b) - grants).astype(float)


def _a1_primary_deficit_lcu(
    baseline_macro: MacroDebtBook,
    shocked_gdp_lcu: pd.Series,
) -> pd.Series:
    """A1 R88: primary deficit pinned to 10-year hist mean % of GDP from year 2.

    Excel ``R17`` = ``Baseline AL23`` from the second projection year, held
    flat thereafter; ``R88 = R17/100 × R41``.
    """
    from lic_dsf.dsa.baseline.public import BaselinePublicBook
    from lic_dsf.stress.macro_shocks import _hist_mean_sd

    years = baseline_macro.inputs.years
    first = baseline_macro.inputs.first_projection_year
    proj = [y for y in years if y >= first]
    start = proj[1] if len(proj) >= 2 else (proj[0] if proj else first)
    # External book unused by primary_deficit_to_gdp; pass a lightweight stub
    # via the baseline Macro's attached external when present.
    external = baseline_macro.external
    if external is None:
        raise ValueError("baseline MacroDebtBook.external is required for A1 PD pin")
    base_book = BaselinePublicBook(macro=baseline_macro, external=external)
    pd_gdp = base_book.primary_deficit_to_gdp()
    hist_pd, _ = _hist_mean_sd(pd_gdp, years, first)
    gdp = _align(shocked_gdp_lcu, years)
    out = pd.Series(0.0, index=list(years), dtype=float)
    for year in years:
        if year < first:
            out.loc[year] = float(pd_gdp.reindex([year]).fillna(0.0).loc[year]) / 100.0 * float(
                gdp.loc[year]
            )
        elif year < start:
            # First projection year keeps baseline PD/GDP × shocked R41.
            rate = float(pd_gdp.loc[year])
            out.loc[year] = rate / 100.0 * float(gdp.loc[year])
        else:
            out.loc[year] = float(hist_pd) / 100.0 * float(gdp.loc[year])
    return out.astype(float)


def estimate_b1_public_gfn(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay | None = None,
    *,
    inflation_elasticity: float = 0.0,
    gdp_lcu: pd.Series | None = None,
    market_access: bool = False,
    include_external_add_int: bool = True,
    historical: bool = False,
    fx_passthrough: float = 0.0,
    fx_depreciation_pct: float = 0.0,
    combo_primary: bool = False,
    prior_st: pd.Series | None = None,
    input6: Input6StandardParams | None = None,
    external: ExternalDebtBook | None = None,
    external_dsa_borrowing_usd: pd.Series | None = None,
    primary_exp_gdp_denominator: pd.Series | None = None,
    use_shocked_revenues: bool = False,
) -> pd.Series:
    """B1_GDP_pub R90 public GFN (LCU).

    Identity: primary deficit + existing interest + existing amort + prior
    domestic ST + other identified flows. Debt service is not scaled with
    GDP. Residual-financing service and prior ResFin ST are added when
    ``resfin`` is provided (R84–R87 / prior R81). Market-access B2 also
    adds ``PV_ResFin-add.int.cost - mkt`` interest into the GFN identity.
    """

    from lic_dsf.stress.market_access import _market_add_int_interest_lcu
    from lic_dsf.stress.ratios.public_paths import (
        _combo_primary_deficit_lcu,
        _public_existing_debt_service_lcu,
    )

    years = shocked_macro.inputs.years
    shocked_gdp = (
        gdp_lcu
        if gdp_lcu is not None
        else (
            _a1_public_gdp_lcu(baseline_macro)
            if historical
            else _b1_public_gdp_lcu(
                baseline_macro,
                shocked_macro,
                inflation_elasticity,
                fx_passthrough=fx_passthrough,
                fx_depreciation_pct=fx_depreciation_pct,
            )
        )
    )
    fx = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    interest, amort = _public_existing_debt_service_lcu(
        baseline_macro,
        shocked_macro,
        fx_passthrough=fx_passthrough,
        fx_depreciation_pct=fx_depreciation_pct,
        combo_primary=combo_primary,
        input6=input6,
        external=external,
        inflation_elasticity=inflation_elasticity,
        resfin=resfin,
        market_access=market_access,
        gdp_lcu=shocked_gdp,
        external_dsa_borrowing_usd=external_dsa_borrowing_usd,
    )
    custom_prior_st = prior_st is not None
    prior_st = (
        prior_st.shift(1).fillna(0.0)
        if custom_prior_st
        else _align(shocked_macro.domestic_st(), years).shift(1).fillna(0.0)
    )
    if historical:
        primary = _a1_primary_deficit_lcu(baseline_macro, shocked_gdp)
    elif combo_primary:
        assert input6 is not None and external is not None
        primary = _combo_primary_deficit_lcu(
            baseline_macro,
            shocked_gdp,
            input6,
            external,
            inflation_elasticity=inflation_elasticity,
        )
    else:
        primary = _b1_primary_deficit_lcu(
            baseline_macro,
            shocked_macro,
            shocked_gdp,
            primary_exp_gdp_denominator=primary_exp_gdp_denominator,
            use_shocked_revenues=use_shocked_revenues,
        )
    gfn = (
        primary
        + interest
        + amort
        + prior_st
        + _b1_other_identified_flows_lcu(shocked_macro)
    ).astype(float)

    if resfin is None:
        return gfn

    first = shocked_macro.inputs.first_projection_year
    extra = pd.Series(0.0, index=list(years), dtype=float)
    # Combo and B5 FX fold ResFin service into interest/amort parts; only the
    # prior ResFin ST stock still needs to be added (unless prior_st is custom).
    resfin_in_parts = combo_primary or bool(fx_passthrough and fx_depreciation_pct)
    if resfin_in_parts:
        if custom_prior_st:
            # Custom short-term series already includes ResFin; nothing extra.
            pass
        else:
            prior_resfin_st = resfin.dom_st.stock.shift(1).fillna(0.0)
            for year in years:
                if year < first:
                    continue
                extra.loc[year] = float(
                    prior_resfin_st.reindex([year]).fillna(0.0).loc[year]
                )
    else:
        for year in years:
            if year < first:
                continue
            dom_resfin_i = float(
                resfin.dom_mlt.interest.reindex([year]).fillna(0.0).loc[year]
            ) + float(resfin.dom_st.interest.reindex([year]).fillna(0.0).loc[year])
            ext_resfin_i = float(
                resfin.ext.interest.reindex([year]).fillna(0.0).loc[year]
            ) * float(fx.loc[year])
            extra.loc[year] = (
                dom_resfin_i
                + ext_resfin_i
                + float(resfin.ext.amortization.reindex([year]).fillna(0.0).loc[year])
                * float(fx.loc[year])
                + float(resfin.dom_mlt.amortization.reindex([year]).fillna(0.0).loc[year])
            )
        if not custom_prior_st:
            prior_resfin_st = resfin.dom_st.stock.shift(1).fillna(0.0)
            for year in years:
                if year < first:
                    continue
                extra.loc[year] = float(extra.loc[year]) + float(
                    prior_resfin_st.reindex([year]).fillna(0.0).loc[year]
                )
    if market_access and not combo_primary:
        extra = extra + _market_add_int_interest_lcu(
            resfin,
            shocked_macro,
            baseline_macro,
            include_external=include_external_add_int,
        )
    return (gfn + extra).astype(float)


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
            from lic_dsf.stress.ratios.public_paths import (
                _public_domestic_st_lcu_path,
            )

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


__all__ = [
    "PublicGFNIdentity",
    "_a1_primary_deficit_lcu",
    "_a1_public_gdp_lcu",
    "_align",
    "_b1_other_identified_flows_lcu",
    "_b1_primary_deficit_lcu",
    "_b1_public_gdp_lcu",
    "_clamp_nonnegative",
    "_extra_fx_depreciation_ppt",
    "_fx_shock_projection_year",
    "_growth_pct",
    "_inflation_elasticity",
    "_pct",
    "_public_real_and_lcu_deflator",
    "_shocked_real_and_lcu_deflator",
    "estimate_b1_public_gfn",
]
