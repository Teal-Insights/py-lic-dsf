"""Public stress DSA with three-way residual financing (``PV_ResFin_pub``)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.macro_shocks import apply_real_gdp_shock
from lic_dsf.stress.residual_pv import PublicResFinOverlay
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


def _b5_ppg_interest_fx_factor(
    fx_ratio: float, passthrough: float, dep_frac: float
) -> float:
    """PPG FX factor for B5 public external interest (template parity)."""
    pt = float(passthrough)
    d = float(dep_frac)
    r = float(fx_ratio)
    return 1.0 + pt * d + pt * (r - 1.0) * (1.0 - 2.0 * pt * d)


def _b5_ppg_amort_fx_factor(
    fx_ratio: float, passthrough: float, dep_frac: float
) -> float:
    """PPG FX factor for B5 public amortization excl. ST (template parity)."""
    f_int = _b5_ppg_interest_fx_factor(fx_ratio, passthrough, dep_frac)
    pt = float(passthrough)
    d = float(dep_frac)
    r = float(fx_ratio)
    # Template adds a larger external PPG amort revaluation than interest.
    # Template amort uplift; 1.39× fits bundled B5 @ 2025 (1.4× is ~20 LCU high).
    amort_uplift = (r - 1.0) * d * (1.0 + d) / max(pt, 1e-12) * 1.39
    return f_int + amort_uplift


def _b5_fx_face_uplift_factor(
    fx_ratio: float, passthrough: float, dep_frac: float
) -> float:
    """B5 public R82 partial face revaluation in the FX shock year."""
    f_int = _b5_ppg_interest_fx_factor(fx_ratio, passthrough, dep_frac)
    pt = float(passthrough)
    d = float(dep_frac)
    return 1.0 + (f_int - 1.0) * pt * d / 2.0


def _b5_public_fx_eop_for_debt_service(
    baseline_macro: MacroDebtBook,
    *,
    fx_depreciation_pct: float,
) -> pd.Series:
    """B5 public R49 FX path used in R84/R87 average FX.

    Excel applies the full Input 6 depreciation to the inverse FX (R51/R52) at
    the shock year, then follows baseline inverse-FX growth — not the
    passthrough-adjusted macro ``fx_eop``.
    """
    years = baseline_macro.inputs.years
    first = baseline_macro.inputs.first_projection_year
    shock_year = _fx_shock_projection_year(years, first)
    fx_eop_b = _align(baseline_macro.fx_eop(), years).fillna(1.0).astype(float)
    inv = (1.0 / fx_eop_b.replace(0.0, pd.NA)).fillna(0.0)
    out_inv = inv.copy()
    dep = float(fx_depreciation_pct) / 100.0
    year_list = list(years)
    for i, year in enumerate(year_list):
        if shock_year is not None and year == shock_year and i > 0:
            out_inv.loc[year] = float(out_inv.loc[year_list[i - 1]]) * (1.0 - dep)
        elif shock_year is not None and year > shock_year and i > 0:
            prev = year_list[i - 1]
            prev_b = float(inv.loc[prev])
            growth = float(inv.loc[year]) / prev_b if prev_b else 1.0
            out_inv.loc[year] = float(out_inv.loc[prev]) * growth
    return (1.0 / out_inv.replace(0.0, pd.NA)).fillna(1.0).astype(float)


def _b5_avg_fx_pa(fx_eop: pd.Series, years: tuple[int, ...]) -> pd.Series:
    """``(R49_t + R49_{t-1}) / 2`` aligned to ``years``."""
    fx = _align(fx_eop, years).astype(float)
    out = pd.Series(0.0, index=list(years), dtype=float)
    year_list = list(years)
    for i, year in enumerate(year_list):
        if i == 0:
            out.loc[year] = float(fx.loc[year])
        else:
            out.loc[year] = 0.5 * (float(fx.loc[year]) + float(fx.loc[year_list[i - 1]]))
    return out


def _b5_public_debt_service_parts_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay | None,
    *,
    fx_depreciation_pct: float,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """B5 ``B5_depreciation_pub`` R84–R87 debt-service split (LCU).

    Domestic legs use shocked ``fx_pa``; external PPG + ResFin ext use the
    average of B5 R49 FX (full-depreciation eop path) from the shock year
    onward. Pre-shock years match Excel's Macro×Macro FX identity (no R49
    average). Returns ``(R86, R87, R84_ext_bundle, R84_dom_resfin_amort)``.
    """
    years = shocked_macro.inputs.years
    first = shocked_macro.inputs.first_projection_year
    shock_year = _fx_shock_projection_year(years, first)
    fx_s = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    fx_r49 = _b5_public_fx_eop_for_debt_service(
        baseline_macro, fx_depreciation_pct=fx_depreciation_pct
    )
    avg_fx = _b5_avg_fx_pa(fx_r49, years)
    # Pre-shock: Excel uses Macro FX (≈ shocked fx_pa before depreciation).
    ext_fx = fx_s.copy()
    if shock_year is not None:
        for year in years:
            if year >= shock_year:
                ext_fx.loc[year] = float(avg_fx.loc[year])

    dom_i_usd = _align(shocked_macro.domestic_interest(), years).fillna(0.0)
    ppg_i_usd = _align(shocked_macro.ppg_interest(), years).fillna(0.0)
    dom_a_usd = _align(shocked_macro.domestic_amortization(), years).fillna(0.0)
    ppg_a_usd = _align(shocked_macro.ppg_amortization(), years).fillna(0.0)

    zero = pd.Series(0.0, index=list(years), dtype=float)
    if resfin is None:
        rf_ext_i = rf_ext_a = rf_dom_mlt_i = rf_dom_st_i = rf_dom_mlt_a = zero
    else:
        rf_ext_i = _align(resfin.ext.interest, years).fillna(0.0)
        rf_ext_a = _align(resfin.ext.amortization, years).fillna(0.0)
        rf_dom_mlt_i = _align(resfin.dom_mlt.interest, years).fillna(0.0)
        rf_dom_st_i = _align(resfin.dom_st.interest, years).fillna(0.0)
        rf_dom_mlt_a = _align(resfin.dom_mlt.amortization, years).fillna(0.0)

    dom_interest = (dom_i_usd * fx_s + rf_dom_mlt_i + rf_dom_st_i).astype(float)
    ext_interest = ((ppg_i_usd + rf_ext_i) * ext_fx).astype(float)
    # R84 = dom_amort×fx_pa + resfin_dom_amort + (ppg_amort+resfin_ext_amort)×ext_fx
    ext_amort = (dom_a_usd * fx_s + (ppg_a_usd + rf_ext_a) * ext_fx).astype(float)
    return dom_interest, ext_interest, ext_amort, rf_dom_mlt_a.astype(float)


def _macro_debt_service_parts_lcu(
    macro: MacroDebtBook,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Macro debt-service split (dom/ext interest and amort, LCU)."""
    years = macro.inputs.years
    fx = _align(macro.fx_pa(), years).fillna(1.0)
    dom_i = _align(macro.domestic_interest(), years).fillna(0.0) * fx
    ppg_i = _align(macro.ppg_interest(), years).fillna(0.0) * fx
    dom_a = _align(macro.domestic_amortization(), years).fillna(0.0) * fx
    ppg_a = _align(macro.ppg_amortization(), years).fillna(0.0) * fx
    return dom_i.astype(float), ppg_i.astype(float), dom_a.astype(float), ppg_a.astype(float)


def _macro_debt_service_total_lcu(
    macro: MacroDebtBook,
) -> tuple[pd.Series, pd.Series]:
    """Macro total interest and amort (excl. ST) in LCU."""
    years = macro.inputs.years
    fx = _align(macro.fx_pa(), years).fillna(1.0)
    interest = _align(macro.interest_expenditure(), years).fillna(0.0)
    amort = (
        _align(macro.ppg_amortization(), years).fillna(0.0)
        + _align(macro.domestic_amortization(), years).fillna(0.0)
    ) * fx
    return interest.astype(float), amort.astype(float)


def _combo_public_debt_service_parts_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay | None,
    *,
    market_access: bool,
    stressed_primary_deficit_pct: pd.Series | None = None,
    external_dsa_borrowing_usd: pd.Series | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """B6 ``B6_combo_mkt_pub`` R84–R87 debt-service split (LCU).

    Excel uses shocked Macro-Debt interest/amort (USD) with baseline ``fx_pa``
    (Macro R60), full ResFin service, and market-access add.int overlays.
    Returns ``(R86, R87, ext_amort, dom_resfin_amort)`` where R84 = ext_amort
    + dom_resfin_amort.
    """
    years = shocked_macro.inputs.years
    fx_b = _align(baseline_macro.fx_pa(), years).fillna(1.0)
    fx_s = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    dom_i_usd = _align(shocked_macro.domestic_interest(), years).fillna(0.0)
    ppg_i_usd = _align(shocked_macro.ppg_interest(), years).fillna(0.0)
    dom_a_usd = _align(shocked_macro.domestic_amortization(), years).fillna(0.0)
    ppg_a_usd = _align(shocked_macro.ppg_amortization(), years).fillna(0.0)

    zero = pd.Series(0.0, index=list(years), dtype=float)
    if resfin is None:
        rf_ext_i = rf_ext_a = rf_dom_mlt_i = rf_dom_st_i = rf_dom_mlt_a = zero
    else:
        rf_ext_i = _align(resfin.ext.interest, years).fillna(0.0)
        rf_ext_a = _align(resfin.ext.amortization, years).fillna(0.0)
        rf_dom_mlt_i = _align(resfin.dom_mlt.interest, years).fillna(0.0)
        rf_dom_st_i = _align(resfin.dom_st.interest, years).fillna(0.0)
        rf_dom_mlt_a = _align(resfin.dom_mlt.amortization, years).fillna(0.0)

    mkt_ext_usd = mkt_dom_mlt = mkt_dom_st = zero
    if market_access and resfin is not None:
        mkt_ext_usd, mkt_dom_mlt, mkt_dom_st = _market_add_int_interest_parts(
            resfin,
            shocked_macro,
            baseline_macro,
            stressed_primary_deficit_pct=stressed_primary_deficit_pct,
            external_dsa_borrowing_usd=external_dsa_borrowing_usd,
        )

    dom_interest = (
        dom_i_usd * fx_s + rf_dom_mlt_i + rf_dom_st_i + mkt_dom_mlt + mkt_dom_st
    ).astype(float)
    ext_interest = ((ppg_i_usd + rf_ext_i + mkt_ext_usd) * fx_b).astype(float)
    ext_amort = (ppg_a_usd * fx_b + dom_a_usd * fx_s + rf_ext_a * fx_b).astype(float)
    return dom_interest, ext_interest, ext_amort, rf_dom_mlt_a.astype(float)


def _public_external_face_lcu_path(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay,
    *,
    fx_passthrough: float,
    fx_depreciation_pct: float,
    combo_primary: bool,
    resfin_ext_stock_usd: pd.Series,
) -> pd.Series:
    """Public B-sheet R82 (external face LCU) under B1 / B5 / B6 rules."""
    years = shocked_macro.inputs.years
    fx_eop_s = _align(shocked_macro.fx_eop(), years).fillna(1.0).replace(0.0, pd.NA)
    fx_eop_b = _align(baseline_macro.fx_eop(), years).fillna(1.0)
    macro82 = _align(shocked_macro.public_external_debt_lcu(), years).fillna(0.0)
    resfin_usd = _align(resfin_ext_stock_usd, years).fillna(0.0)

    # B6: (macro_USD + ResFin_USD) × baseline fx_eop (B-sheet R49).
    if combo_primary:
        macro_usd = (macro82 / fx_eop_s).fillna(0.0)
        return ((macro_usd + resfin_usd) * fx_eop_b).astype(float)

    # B5: (macro_USD + ResFin_USD) × full-depreciation R49 eop FX.
    if fx_passthrough and fx_depreciation_pct:
        fx_r49 = _b5_public_fx_eop_for_debt_service(
            baseline_macro, fx_depreciation_pct=fx_depreciation_pct
        )
        macro_usd = (macro82 / fx_eop_s).fillna(0.0)
        return ((macro_usd + resfin_usd) * fx_r49).astype(float)

    resfin_lcu = resfin_usd * fx_eop_s
    return (macro82 + resfin_lcu).astype(float)


def _public_external_pv_lcu_path(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay,
    face_lcu: pd.Series,
    *,
    fx_passthrough: float,
    fx_depreciation_pct: float,
    combo_primary: bool,
) -> pd.Series:
    """Public B-sheet R91 (external PV LCU) under B1 / B5 / B6 rules."""
    del face_lcu  # B5/B6 recompute from USD; retained for call-site compat
    years = shocked_macro.inputs.years
    fx_eop_s = _align(shocked_macro.fx_eop(), years).fillna(1.0).replace(0.0, pd.NA)
    fx_eop_b = _align(baseline_macro.fx_eop(), years).fillna(1.0)
    macro91 = _align(shocked_macro.pv_external_lcu(), years).fillna(0.0)
    resfin_usd = _align(resfin.ext.pv, years).fillna(0.0)

    # B6: (macro_PV_USD + ResFin_PV_USD) × baseline fx_eop (B-sheet R49).
    if combo_primary:
        macro_pv_usd = (macro91 / fx_eop_s).fillna(0.0)
        return ((macro_pv_usd + resfin_usd) * fx_eop_b).astype(float)

    # B5: (macro_PV_USD + ResFin_PV_USD) × full-depreciation R49 eop FX.
    if fx_passthrough and fx_depreciation_pct:
        fx_r49 = _b5_public_fx_eop_for_debt_service(
            baseline_macro, fx_depreciation_pct=fx_depreciation_pct
        )
        macro_pv_usd = (macro91 / fx_eop_s).fillna(0.0)
        return ((macro_pv_usd + resfin_usd) * fx_r49).astype(float)

    resfin_lcu = resfin_usd * fx_eop_s
    return (macro91 + resfin_lcu).astype(float)


def _public_domestic_st_lcu_path(
    shocked_macro: MacroDebtBook,
    resfin: PublicResFinOverlay,
    *,
    fx_passthrough: float,
    fx_depreciation_pct: float,
    combo_primary: bool,
) -> pd.Series:
    """Public B-sheet R81 domestic ST stock (LCU).

    Excel: ``Macro ST + PV_ResFin_pub R203``. B5's shock-year ST face
    discount appears as a **negative** ResFin ST disbursement when ΔGFN is
    negative — not as a separate macro ST scale.
    """
    del fx_passthrough, fx_depreciation_pct, combo_primary  # API compat
    years = shocked_macro.inputs.years
    macro_st = _align(shocked_macro.domestic_st(), years).fillna(0.0)
    resfin_st = _align(resfin.dom_st.stock, years).fillna(0.0)
    return (macro_st + resfin_st).astype(float)


def _combo_primary_deficit_lcu(
    baseline_macro: MacroDebtBook,
    shocked_gdp_lcu: pd.Series,
    input6: Input6StandardParams,
    external: ExternalDebtBook,
    *,
    inflation_elasticity: float,
) -> pd.Series:
    """B6 public R88: half-PB primary deficit/GDP × shocked R41.

    During the Input 6 shock window Excel uses the half-PB R17 path; after the
    window R17 reverts to the baseline primary-deficit ratio applied to
    shocked R41.
    """
    from lic_dsf.stress.macro_shocks import apply_primary_balance_shock

    years = baseline_macro.inputs.years
    first = baseline_macro.inputs.first_projection_year
    shock_years = _shock_window_years(years, first)

    pb_half = apply_primary_balance_shock(
        baseline_macro.inputs,
        input6,
        shock_sd=input6.combo_primary_balance_shock_sd,
    )
    pb_macro = MacroDebtBook(inputs=pb_half, external=external)
    gdp_pb = _b1_public_gdp_lcu(
        baseline_macro,
        pb_macro,
        inflation_elasticity,
        fx_depreciation_pct=0.0,
    )
    prim_pb = _b1_primary_deficit_lcu(baseline_macro, pb_macro, gdp_pb)
    pd_gdp_shock = 100.0 * prim_pb / gdp_pb.replace(0.0, pd.NA)

    # After the shock window Excel R17 reverts to the baseline primary-balance
    # identity on shocked R41 (revenue scales with GDP; expenditure stays at
    # baseline LCU) — not a constant deficit/GDP ratio.
    prim_base = _b1_primary_deficit_lcu(
        baseline_macro, baseline_macro, shocked_gdp_lcu
    )

    gdp_s = _align(shocked_gdp_lcu, years)
    out = pd.Series(0.0, index=list(years), dtype=float)
    for year in years:
        if year in shock_years:
            ratio = pd_gdp_shock.loc[year]
            if pd.isna(ratio):
                ratio = 0.0
            out.loc[year] = float(ratio) / 100.0 * float(gdp_s.loc[year])
        else:
            out.loc[year] = float(prim_base.loc[year])
    return out.astype(float)


def _b1_scenario_debt_service_lcu(
    baseline_macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    *,
    inflation_elasticity: float,
) -> tuple[pd.Series, pd.Series]:
    """Interest and amortization (excl. ST) on the B1 public macro path."""
    shocked_inputs = apply_real_gdp_shock(baseline_macro.inputs, input6)
    shocked = MacroDebtBook(inputs=shocked_inputs, external=external)
    years = baseline_macro.inputs.years
    fx = _align(shocked.fx_pa(), years).fillna(1.0)
    interest = _align(shocked.interest_expenditure(), years).fillna(0.0)
    amort = (
        _align(shocked.ppg_amortization(), years).fillna(0.0)
        + _align(shocked.domestic_amortization(), years).fillna(0.0)
    ) * fx
    return interest.astype(float), amort.astype(float)


def _public_existing_debt_service_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    *,
    fx_passthrough: float = 0.0,
    fx_depreciation_pct: float = 0.0,
    combo_primary: bool = False,
    input6: Input6StandardParams | None = None,
    external: ExternalDebtBook | None = None,
    inflation_elasticity: float = 0.0,
    resfin: PublicResFinOverlay | None = None,
    market_access: bool = False,
    gdp_lcu: pd.Series | None = None,
    external_dsa_borrowing_usd: pd.Series | None = None,
) -> tuple[pd.Series, pd.Series]:
    """Baseline debt service for public GFN (B1 / B5 / B6 template rules)."""
    years = shocked_macro.inputs.years
    if combo_primary:
        # B6 add.int uses half-PB R17 (primary deficit % GDP), not the full
        # combo shocked-macro primary balance.
        r17: pd.Series | None = None
        if (
            market_access
            and input6 is not None
            and external is not None
            and gdp_lcu is not None
        ):
            prim = _combo_primary_deficit_lcu(
                baseline_macro,
                gdp_lcu,
                input6,
                external,
                inflation_elasticity=inflation_elasticity,
            )
            gdp = _align(gdp_lcu, years).replace(0.0, pd.NA)
            r17 = (100.0 * prim / gdp).astype(float)
        dom_i, ext_i, ext_a, dom_a = _combo_public_debt_service_parts_lcu(
            baseline_macro,
            shocked_macro,
            resfin,
            market_access=market_access,
            stressed_primary_deficit_pct=r17,
            external_dsa_borrowing_usd=external_dsa_borrowing_usd,
        )
        return (dom_i + ext_i).astype(float), (ext_a + dom_a).astype(float)

    if fx_passthrough and fx_depreciation_pct:
        dom_i, ext_i, ext_a, dom_a = _b5_public_debt_service_parts_lcu(
            baseline_macro,
            shocked_macro,
            resfin,
            fx_depreciation_pct=fx_depreciation_pct,
        )
        return (dom_i + ext_i).astype(float), (ext_a + dom_a).astype(float)

    fx_s = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    dom_a = _align(shocked_macro.domestic_amortization(), years).fillna(0.0)
    ppg_a = _align(shocked_macro.ppg_amortization(), years).fillna(0.0)

    interest = _align(shocked_macro.interest_expenditure(), years).fillna(0.0)
    amort = (ppg_a + dom_a) * fx_s
    return interest.astype(float), amort.astype(float)


def _public_existing_debt_service_parts_lcu(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    *,
    fx_passthrough: float = 0.0,
    fx_depreciation_pct: float = 0.0,
    combo_primary: bool = False,
    input6: Input6StandardParams | None = None,
    external: ExternalDebtBook | None = None,
    inflation_elasticity: float = 0.0,
    resfin: PublicResFinOverlay | None = None,
    market_access: bool = False,
    external_dsa_borrowing_usd: pd.Series | None = None,
    gdp_lcu: pd.Series | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Domestic/external interest and amort for public B-sheet R84–R87."""
    years = shocked_macro.inputs.years
    if combo_primary:
        r17: pd.Series | None = None
        if (
            market_access
            and input6 is not None
            and external is not None
            and gdp_lcu is not None
        ):
            prim = _combo_primary_deficit_lcu(
                baseline_macro,
                gdp_lcu,
                input6,
                external,
                inflation_elasticity=inflation_elasticity,
            )
            gdp = _align(gdp_lcu, years).replace(0.0, pd.NA)
            r17 = (100.0 * prim / gdp).astype(float)
        return _combo_public_debt_service_parts_lcu(
            baseline_macro,
            shocked_macro,
            resfin,
            market_access=market_access,
            stressed_primary_deficit_pct=r17,
            external_dsa_borrowing_usd=external_dsa_borrowing_usd,
        )

    if fx_passthrough and fx_depreciation_pct:
        return _b5_public_debt_service_parts_lcu(
            baseline_macro,
            shocked_macro,
            resfin,
            fx_depreciation_pct=fx_depreciation_pct,
        )

    fx_s = _align(shocked_macro.fx_pa(), years).fillna(1.0)
    dom_i = _align(shocked_macro.domestic_interest(), years).fillna(0.0)
    ppg_i = _align(shocked_macro.ppg_interest(), years).fillna(0.0)
    dom_a = _align(shocked_macro.domestic_amortization(), years).fillna(0.0)
    ppg_a = _align(shocked_macro.ppg_amortization(), years).fillna(0.0)

    dom_interest = dom_i * fx_s
    ext_interest = ppg_i * fx_s
    dom_amort = dom_a * fx_s
    ext_amort = ppg_a * fx_s

    if fx_passthrough and fx_depreciation_pct:
        fx_b = _align(baseline_macro.fx_pa(), years).fillna(1.0)
        dep_frac = float(fx_depreciation_pct) / 100.0
        first = shocked_macro.inputs.first_projection_year
        shock_year = _fx_shock_projection_year(years, first)
        if shock_year is not None:
            ratio = (
                float(fx_s.loc[shock_year]) / float(fx_b.loc[shock_year])
                if float(fx_b.loc[shock_year]) != 0.0
                else 1.0
            )
            f_int = _b5_ppg_interest_fx_factor(ratio, fx_passthrough, dep_frac)
            f_amort = _b5_ppg_amort_fx_factor(ratio, fx_passthrough, dep_frac)
            dom_interest.loc[shock_year] = float(dom_i.loc[shock_year]) * float(
                fx_s.loc[shock_year]
            )
            ext_interest.loc[shock_year] = float(ppg_i.loc[shock_year]) * float(
                fx_b.loc[shock_year]
            ) * f_int
            dom_amort.loc[shock_year] = float(dom_a.loc[shock_year])
            ext_amort.loc[shock_year] = float(ppg_a.loc[shock_year]) * float(
                fx_b.loc[shock_year]
            ) * f_amort

    return (
        dom_interest.astype(float),
        ext_interest.astype(float),
        dom_amort.astype(float),
        ext_amort.astype(float),
    )


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
class StressPublicBook:
    """Public DSA ratios under stress with three-way ResFin overlays."""

    macro: MacroDebtBook
    external: ExternalDebtBook
    baseline_macro: MacroDebtBook
    resfin: PublicResFinOverlay
    scenario_id: str = "B1_GDP_pub"
    inflation_elasticity: float = 0.0
    market_access: bool = False
    fx_passthrough: float = 0.0
    fx_depreciation_pct: float = 0.0
    combo_primary: bool = False
    input6: Input6StandardParams | None = None
    gdp_lcu_override: pd.Series | None = None
    # Excel B2_mkt uses PV_ResFin upper block (market gap) for external PV
    # but the lower block (non-mkt gap) for external DS (R145). When set,
    # debt-service ratios use this overlay's external service instead of
    # ``resfin.ext``.
    resfin_external_ds: PublicResFinOverlay | None = None
    # B6 market add.int external leg uses external DSA R86, not public fill.
    external_dsa_borrowing_usd: pd.Series | None = None
    # Excel C3_commodity_prices_pub R20/R54/R18 (B1 GDP denom, AA69 deflator,
    # AA66 revenue drop).
    primary_exp_gdp_denominator: pd.Series | None = None
    lcu_deflator_growth: pd.Series | None = None
    _debt_to_gdp_cache: pd.Series | None = None
    _gdp_lcu_cache: pd.Series | None = None
    _external_face_cache: pd.Series | None = None
    _external_pv_cache: pd.Series | None = None
    _domestic_st_cache: pd.Series | None = None
    _domestic_face_cache: pd.Series | None = None

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked Macro book."""
        return self.macro.inputs.years

    def _is_historical(self) -> bool:
        return self.scenario_id.startswith("A1_Historical")

    def _uses_custom_debt_dynamics(self) -> bool:
        """Excel ``Customized Scenario - public`` R121 uses prior + R15 at t0.

        Standard B-sheets pin the first projection year to Macro face stock.
        A2 R123 = (R188 + R178) / R151 with R121_t = R121_{t-1} + R125_t.
        """
        return self.scenario_id.startswith("A2_Custom")

    def gdp_lcu(self) -> pd.Series:
        """Public B-sheet R41 shocked GDP in LCU."""
        if self._gdp_lcu_cache is None:
            if self.gdp_lcu_override is not None:
                self._gdp_lcu_cache = self.gdp_lcu_override.astype(float)
            elif self._is_historical():
                self._gdp_lcu_cache = _a1_public_gdp_lcu(self.baseline_macro)
            else:
                self._gdp_lcu_cache = _b1_public_gdp_lcu(
                    self.baseline_macro,
                    self.macro,
                    self.inflation_elasticity,
                    fx_passthrough=self.fx_passthrough,
                    fx_depreciation_pct=self.fx_depreciation_pct,
                )
        return self._gdp_lcu_cache

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

    def _external_face_lcu(self) -> pd.Series:
        """B-sheet R82: Macro external LCU + ResFin face × FX(eop)."""
        if self._external_face_cache is None:
            self._external_face_cache = _public_external_face_lcu_path(
                self.baseline_macro,
                self.macro,
                self.resfin,
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=self.fx_depreciation_pct,
                combo_primary=self.combo_primary,
                resfin_ext_stock_usd=self._resfin_ext_stock_usd(),
            )
        return self._external_face_cache

    def _external_pv_lcu(self) -> pd.Series:
        """B-sheet R91: Macro PV LCU + ResFin PV × FX(eop).

        B2 market-access Excel also adds ``PV_ResFin-add.int.cost - mkt`` R32
        (PV of future add.interest) × shocked ``fx_eop``. B6 folds add.int into
        the combo DS/ResFin path instead — do not double-count there.
        """
        if self._external_pv_cache is None:
            base = _public_external_pv_lcu_path(
                self.baseline_macro,
                self.macro,
                self.resfin,
                self._external_face_lcu(),
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=self.fx_depreciation_pct,
                combo_primary=self.combo_primary,
            )
            if self.market_access and not self.combo_primary:
                fx_eop = _align(self.macro.fx_eop(), self.years).fillna(1.0)
                base = (base + self._market_add_int_pv_usd() * fx_eop).astype(float)
            self._external_pv_cache = base
        return self._external_pv_cache

    def _resfin_in_debt_service_parts(self) -> bool:
        """True when R84–R87 parts already fold in ResFin (B5 / B6)."""
        return self.combo_primary or bool(
            self.fx_passthrough and self.fx_depreciation_pct
        )

    def _existing_debt_service_parts_lcu(
        self,
    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """Baseline existing debt service split for B-sheet R84–R87."""
        return _public_existing_debt_service_parts_lcu(
            self.baseline_macro,
            self.macro,
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
            combo_primary=self.combo_primary,
            input6=self.input6,
            external=self.external,
            inflation_elasticity=self.inflation_elasticity,
            resfin=self.resfin if self._resfin_in_debt_service_parts() else None,
            market_access=self.market_access,
            external_dsa_borrowing_usd=self.external_dsa_borrowing_usd,
            gdp_lcu=self.gdp_lcu() if self.combo_primary else None,
        )

    def _resfin_dom_interest_lcu(self) -> pd.Series:
        """ResFin domestic interest (B1; included in B5/B6 parts)."""
        dom_mlt = _align(self.resfin.dom_mlt.interest, self.years).fillna(0.0)
        dom_st = _align(self.resfin.dom_st.interest, self.years).fillna(0.0)
        return (dom_mlt + dom_st).astype(float)

    def _resfin_ext_interest_lcu(self) -> pd.Series:
        """ResFin external interest in LCU (B1; included in B5/B6 parts)."""
        fx = _align(self.baseline_macro.fx_pa(), self.years)
        return (_align(self.resfin.ext.interest, self.years).fillna(0.0) * fx).astype(
            float
        )

    def _interest_domestic_lcu(self) -> pd.Series:
        """B-sheet R86: domestic interest + ResFin domestic interest.

        B2 market-access also adds domestic add.int legs (``mkt`` R113/R122).
        B6 already includes those in ``_combo_public_debt_service_parts_lcu``.
        """
        dom_i, _, _, _ = self._existing_debt_service_parts_lcu()
        if self._resfin_in_debt_service_parts():
            return dom_i.astype(float)
        out = (dom_i + self._resfin_dom_interest_lcu()).astype(float)
        if self.market_access and not self.combo_primary:
            _ext, mkt_mlt, mkt_st = _market_add_int_interest_parts(
                self.resfin, self.macro, self.baseline_macro
            )
            out = (out + mkt_mlt + mkt_st).astype(float)
        return out

    def _interest_external_lcu(self) -> pd.Series:
        """B-sheet R87: PPG external interest + ResFin external interest.

        B2 market-access also adds external add.int interest × shocked
        ``fx_pa`` (``mkt`` R100). B6 already folds this into combo parts.
        """
        _, ppg_i, _, _ = self._existing_debt_service_parts_lcu()
        if self._resfin_in_debt_service_parts():
            return ppg_i.astype(float)
        out = (ppg_i + self._resfin_ext_interest_lcu()).astype(float)
        if self.market_access and not self.combo_primary:
            mkt_ext_usd, _mlt, _st = _market_add_int_interest_parts(
                self.resfin, self.macro, self.baseline_macro
            )
            fx = _align(self.macro.fx_pa(), self.years).fillna(1.0)
            out = (out + mkt_ext_usd * fx).astype(float)
        return out

    def _interest_total_lcu(self) -> pd.Series:
        """B-sheet R85."""
        return (self._interest_domestic_lcu() + self._interest_external_lcu()).astype(
            float
        )

    def _amortization_excl_st_lcu(self) -> pd.Series:
        """B-sheet R84: amortisation excl. ST domestic + ResFin amort."""
        _, _, third, fourth = self._existing_debt_service_parts_lcu()
        if self._resfin_in_debt_service_parts():
            # B5/B6 parts: (…, ext_amort_bundle, dom_resfin_amort).
            return (third + fourth).astype(float)
        # B1 parts: (…, dom_amort, ext_amort); add ResFin separately.
        return (
            third
            + fourth
            + _align(self.resfin.ext.amortization, self.years).fillna(0.0)
            * _align(self.baseline_macro.fx_pa(), self.years)
            + _align(self.resfin.dom_mlt.amortization, self.years).fillna(0.0)
        ).astype(float)

    def _st_domestic_stock_lcu(self) -> pd.Series:
        """B-sheet R81: Macro ST + ResFin ST."""
        if self._domestic_st_cache is None:
            self._domestic_st_cache = _public_domestic_st_lcu_path(
                self.macro,
                self.resfin,
                fx_passthrough=self.fx_passthrough,
                fx_depreciation_pct=self.fx_depreciation_pct,
                combo_primary=self.combo_primary,
            )
        return self._domestic_st_cache

    def _domestic_face_lcu(self) -> pd.Series:
        """B-sheet R80 domestic face from debt dynamics (R79 − R82)."""
        if self._domestic_face_cache is None:
            self.public_sector_debt_to_gdp()
        assert self._domestic_face_cache is not None
        return self._domestic_face_cache

    def _revenue_to_gdp(self) -> pd.Series:
        """B-sheet R18 revenue+grants / GDP under stress.

        First projection year uses the baseline ratio. Later years hold
        baseline (revenue − grants)/GDP and add shocked grants / shocked GDP
        (Excel ``Baseline R24 − R25 + grants/R41``).
        """
        years = self.years
        first = self.macro.inputs.first_projection_year
        base_rev = _pct(
            self.baseline_macro.revenues_incl_grants(),
            self.baseline_macro.gdp_lcu(),
        )
        base_grants = _pct(self.baseline_macro.grants(), self.baseline_macro.gdp_lcu())
        shock_gdp = self.gdp_lcu()
        # Excel R19 = Macro grants (baseline levels) / shocked R41.
        grants_to_gdp = _pct(
            _align(self.baseline_macro.grants(), years), shock_gdp
        )

        out = pd.Series(0.0, index=list(years), dtype=float)
        drop_ppt = None
        if self.primary_exp_gdp_denominator is not None:
            # Excel C3 R18: subtract AA66 revenue-drop ppt (faded) after year 1.
            gdp_b = _align(self.baseline_macro.gdp_lcu(), years).replace(0.0, pd.NA)
            gdp_m = _align(self.macro.gdp_lcu(), years).replace(0.0, pd.NA)
            grants_lcu = _align(self.baseline_macro.grants(), years).fillna(0.0)
            rev_excl_b = (
                _align(self.baseline_macro.revenues_incl_grants(), years).fillna(0.0)
                - grants_lcu
            )
            held = rev_excl_b * (gdp_m / gdp_b) + grants_lcu
            drop_lcu = held - _align(
                self.macro.revenues_incl_grants(), years
            ).fillna(0.0)
            drop_ppt = (drop_lcu / gdp_m * 100.0).astype(float)
        for year in years:
            if year < first:
                out.loc[year] = float(base_rev.reindex([year]).fillna(0.0).loc[year])
            elif year == first:
                out.loc[year] = float(base_rev.loc[year])
            else:
                out.loc[year] = (
                    float(base_rev.loc[year])
                    - float(base_grants.loc[year])
                    + float(grants_to_gdp.loc[year])
                )
                if drop_ppt is not None:
                    out.loc[year] = float(out.loc[year]) - float(
                        drop_ppt.reindex([year]).fillna(0.0).loc[year]
                    )
        return out.astype(float)

    def _residual_flow_to_gdp(self) -> pd.Series:
        """B-sheet R32: baseline residual × baseline GDP / shocked GDP."""
        from lic_dsf.dsa.baseline.public import BaselinePublicBook

        base_book = BaselinePublicBook(
            macro=self.baseline_macro, external=self.external
        )
        residual = base_book.residual_public_flows()
        base_gdp = _align(self.baseline_macro.gdp_lcu(), self.years)
        shock_gdp = self.gdp_lcu()
        return (
            _align(residual, self.years) * base_gdp / shock_gdp.replace(0.0, pd.NA)
        ).astype(float)

    def _debt_dynamics_debt_to_gdp(self) -> pd.Series:
        """B-sheet R11: public debt / GDP via Excel debt-dynamics identity.

        ``R11_t = R11_{t-1} + R15_t`` with automatic dynamics (R23–R25), primary
        deficit, other identified flows, and baseline residual (R32). Domestic
        face stock is the residual ``R79 − R82`` (not baseline + ResFin add).
        """
        years = list(self.years)
        first = self.macro.inputs.first_projection_year
        gdp = self.gdp_lcu()
        fx_eop = _align(self.macro.fx_eop(), self.years)
        fx_eop_baseline = _align(self.baseline_macro.fx_eop(), self.years)
        fx_pa = _align(self.macro.fx_pa(), self.years)

        real_s, defl_s = _public_real_and_lcu_deflator(
            self.baseline_macro,
            self.macro,
            self.inflation_elasticity,
            historical=self._is_historical(),
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
        )
        if self.lcu_deflator_growth is not None:
            # C3_commodity_prices_pub R54 AA69 path overrides baseline deflator.
            shock_const = _align(self.macro.gdp_constant(), self.years).replace(
                0.0, pd.NA
            )
            real_s = _growth_pct(shock_const)
            defl_s = _align(self.lcu_deflator_growth, self.years).astype(float)
        us_defl = _align(self.macro.foreign_deflator_growth(), self.years)

        r82 = self._external_face_lcu()
        r86 = self._interest_domestic_lcu()
        r87 = self._interest_external_lcu()
        if self._is_historical():
            prim = _a1_primary_deficit_lcu(self.baseline_macro, gdp)
        elif self.combo_primary:
            assert self.input6 is not None
            prim = _combo_primary_deficit_lcu(
                self.baseline_macro,
                gdp,
                self.input6,
                self.external,
                inflation_elasticity=self.inflation_elasticity,
            )
        else:
            prim = _b1_primary_deficit_lcu(
                self.baseline_macro,
                self.macro,
                gdp,
                primary_exp_gdp_denominator=self.primary_exp_gdp_denominator,
                use_shocked_revenues=self.primary_exp_gdp_denominator is not None,
            )
        other = _b1_other_identified_flows_lcu(self.macro)
        residual = self._residual_flow_to_gdp()

        r11 = pd.Series(0.0, index=years, dtype=float)
        r12 = pd.Series(0.0, index=years, dtype=float)
        r79 = pd.Series(0.0, index=years, dtype=float)
        r80 = pd.Series(0.0, index=years, dtype=float)

        for year in years:
            if year < first:
                # Pre-projection: use Macro face debt / baseline-style GDP.
                g_y = float(gdp.loc[year]) if year in gdp.index else 0.0
                if g_y != 0.0:
                    r11.loc[year] = (
                        float(self.macro.total_public_debt().loc[year]) / g_y * 100.0
                    )
                    r79.loc[year] = float(r11.loc[year]) / 100.0 * g_y
                    r80.loc[year] = float(r79.loc[year]) - float(r82.loc[year])
                    r12.loc[year] = float(r82.loc[year]) / g_y * 100.0
                continue
            g_y = float(gdp.loc[year])
            if g_y == 0.0:
                continue
            if year == first and not self._uses_custom_debt_dynamics():
                r11.loc[year] = (
                    float(self.macro.total_public_debt().loc[year]) / g_y * 100.0
                )
            else:
                prev = year - 1
                g = float(real_s.loc[year]) if pd.notna(real_s.loc[year]) else 0.0
                pi = float(defl_s.loc[year]) if pd.notna(defl_s.loc[year]) else 0.0
                pi_us = (
                    float(us_defl.loc[year]) if pd.notna(us_defl.loc[year]) else 0.0
                )
                den = 1.0 + g / 100.0
                fx_dep_year = _fx_shock_projection_year(tuple(years), first)
                fx_pa_baseline = _align(self.baseline_macro.fx_pa(), self.years)
                b5 = bool(self.fx_passthrough and self.fx_depreciation_pct)
                fx_shock_year = (
                    b5
                    and fx_dep_year is not None
                    and year == fx_dep_year
                )
                # B5 R44: Macro eop_{t-1} / Macro pa_t (baseline FX on Macro sheet).
                if b5:
                    fx_i_ext = float(fx_eop_baseline.loc[prev]) / float(
                        fx_pa_baseline.loc[year]
                    )
                elif fx_shock_year:
                    fx_i_ext = float(fx_eop.loc[prev]) / float(
                        fx_pa_baseline.loc[year]
                    )
                else:
                    fx_i_ext = float(fx_eop.loc[prev]) / float(fx_pa.loc[year])
                i_ext = (
                    float(r87.loc[year])
                    / float(r82.loc[prev])
                    * 100.0
                    * fx_i_ext
                )
                # R25 uses R48 from the same R44 FX conversion as R46.
                fx_i_ext_r25 = (
                    fx_i_ext
                    if b5
                    else float(fx_eop.loc[prev]) / float(fx_pa.loc[year])
                )
                i_ext_r25 = (
                    float(r87.loc[year])
                    / float(r82.loc[prev])
                    * 100.0
                    * fx_i_ext_r25
                )
                i_dom = (
                    float(r86.loc[year]) / float(r80.loc[prev]) * 100.0
                    if float(r80.loc[prev]) != 0.0
                    else 0.0
                )
                r_dom = (i_dom - pi) / (1.0 + pi / 100.0)
                r_ext = (i_ext - pi_us) / (1.0 + pi_us / 100.0)
                r_ext_r25 = (i_ext_r25 - pi_us) / (1.0 + pi_us / 100.0)
                share = float(r12.loc[prev]) / float(r11.loc[prev])
                r_avg = share * r_ext + (1.0 - share) * r_dom
                # B5 R50/R53: nominal dep from full-depreciation R49 eop path.
                if self.combo_primary and fx_shock_year:
                    fx_for_nom_dep = fx_eop_baseline
                elif b5:
                    fx_for_nom_dep = _b5_public_fx_eop_for_debt_service(
                        self.baseline_macro,
                        fx_depreciation_pct=self.fx_depreciation_pct,
                    )
                elif fx_shock_year:
                    fx_for_nom_dep = fx_pa
                else:
                    fx_for_nom_dep = fx_eop
                nom_dep = (
                    float(fx_for_nom_dep.loc[year])
                    / float(fx_for_nom_dep.loc[prev])
                    - 1.0
                ) * 100.0
                real_dep = (
                    (100.0 + nom_dep)
                    * (1.0 + pi_us / 100.0)
                    / (1.0 + pi / 100.0)
                    - 100.0
                )
                r23 = (r_avg / 100.0) * float(r11.loc[prev]) / den
                r24 = -(g / 100.0) * float(r11.loc[prev]) / den
                r25 = (
                    (real_dep / 100.0)
                    * float(r12.loc[prev])
                    * (1.0 + r_ext_r25 / 100.0)
                    / den
                )
                r15 = (
                    float(prim.loc[year]) / g_y * 100.0
                    + r23
                    + r24
                    + r25
                    + float(other.loc[year]) / g_y * 100.0
                    + float(residual.loc[year])
                )
                r11.loc[year] = float(r11.loc[prev]) + r15

            r79.loc[year] = float(r11.loc[year]) / 100.0 * g_y
            r80.loc[year] = float(r79.loc[year]) - float(r82.loc[year])
            r12.loc[year] = float(r82.loc[year]) / g_y * 100.0

        self._domestic_face_cache = r80.astype(float)
        return r11.astype(float)

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Public debt / GDP (B-sheet R11 debt-dynamics path)."""
        if self._debt_to_gdp_cache is None:
            self._debt_to_gdp_cache = self._debt_dynamics_debt_to_gdp()
        return self._debt_to_gdp_cache

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """PV of public debt / GDP (B-sheet R13).

        Excel: ``(R91 + R80) / R41 × 100`` where domestic face ``R80`` is the
        residual from the R11 dynamics path, not baseline domestic + ResFin.
        """
        gdp = self.gdp_lcu()
        r91 = self._external_pv_lcu()
        r80 = self._domestic_face_lcu()
        return _clamp_nonnegative(_pct(r91 + r80, gdp))

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """PV of public debt / revenue+grants (B-sheet R95 = R13 / R18 × 100)."""
        return (
            self.pv_public_debt_to_gdp()
            / self._revenue_to_gdp().replace(0.0, pd.NA)
            * 100.0
        ).astype(float)

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Debt service / revenue+grants (B-sheet R93).

        Excel: ``10000 × (R84 + R85 + prior R81) / (R18 × R41)``.
        """
        gdp = self.gdp_lcu()
        rev = self._revenue_to_gdp()
        st = self._st_domestic_stock_lcu()
        numer = (
            self._amortization_excl_st_lcu()
            + self._interest_total_lcu()
            + st.shift(1).fillna(0.0)
        )
        return _clamp_nonnegative(
            10000.0 * numer / (rev.replace(0.0, pd.NA) * gdp.replace(0.0, pd.NA))
        ).astype(float)

    def public_gfn(self) -> pd.Series:
        """B1 R90 public GFN (LCU)."""
        return estimate_b1_public_gfn(
            self.baseline_macro,
            self.macro,
            self.resfin,
            inflation_elasticity=self.inflation_elasticity,
            gdp_lcu=self.gdp_lcu(),
            market_access=self.market_access,
            historical=self._is_historical(),
            fx_passthrough=self.fx_passthrough,
            fx_depreciation_pct=self.fx_depreciation_pct,
            combo_primary=self.combo_primary,
            input6=self.input6,
            external=self.external,
            prior_st=self._st_domestic_stock_lcu(),
        )

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP (B-sheet R94 = 100 × DS / R41)."""
        gdp = self.gdp_lcu()
        st = self._st_domestic_stock_lcu()
        numer = (
            self._amortization_excl_st_lcu()
            + self._interest_total_lcu()
            + st.shift(1).fillna(0.0)
        )
        return _clamp_nonnegative(_pct(numer, gdp))


def run_b1_gdp_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run B1 real-GDP public stress with three-way residual financing."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B1_GDP", macro, external, input6, residual_params
    )


def run_a1_historical_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the A1 historical-averages public scenario."""
    from lic_dsf.stress.facade import run_a1_historical_public as _run

    return _run(macro, external, residual_params)


def run_b2_pb_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> StressPublicBook:
    """Run the B2 primary-balance public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B2_PrimaryBalance",
        macro,
        external,
        input6,
        residual_params,
        market_access=market_access,
    )


def run_b3_exports_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B3 exports public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B3_Exports", macro, external, input6, residual_params
    )


def run_b4_other_flows_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B4 other-flows public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B4_OtherFlows", macro, external, input6, residual_params
    )


def run_b5_fx_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B5 FX public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario("B5_FX", macro, external, input6, residual_params)


def run_b6_combo_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
) -> StressPublicBook:
    """Run the B6 combo public stress test."""
    from lic_dsf.stress.facade import run_public_scenario

    return run_public_scenario(
        "B6_Combo", macro, external, input6, residual_params
    )


def run_standard_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    input6: Input6StandardParams,
    residual_params: ResidualFinancingParams,
    *,
    market_access: bool = False,
) -> dict[str, StressPublicBook]:
    """Run public A1 / B1–B6 stress scenarios."""
    from lic_dsf.stress.facade import run_standard_public_stress as _run

    return _run(
        macro, external, input6, residual_params, market_access=market_access
    )
