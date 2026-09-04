"""Public B-sheet debt-service and stock path helpers."""

from __future__ import annotations

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.macro_shocks import apply_real_gdp_shock
from lic_dsf.stress.market_access import (
    _market_add_int_interest_parts,
    _shock_window_years,
)
from lic_dsf.stress.public_gfn import (
    _align,
    _b1_primary_deficit_lcu,
    _b1_public_gdp_lcu,
    _fx_shock_projection_year,
)
from lic_dsf.stress.residual_pv import PublicResFinOverlay
from lic_dsf.stress.types import Input6StandardParams


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


__all__ = [
    "_b1_scenario_debt_service_lcu",
    "_b5_avg_fx_pa",
    "_b5_fx_face_uplift_factor",
    "_b5_ppg_amort_fx_factor",
    "_b5_ppg_interest_fx_factor",
    "_b5_public_debt_service_parts_lcu",
    "_b5_public_fx_eop_for_debt_service",
    "_combo_primary_deficit_lcu",
    "_combo_public_debt_service_parts_lcu",
    "_macro_debt_service_parts_lcu",
    "_macro_debt_service_total_lcu",
    "_public_domestic_st_lcu_path",
    "_public_existing_debt_service_lcu",
    "_public_existing_debt_service_parts_lcu",
    "_public_external_face_lcu_path",
    "_public_external_pv_lcu_path",
]
