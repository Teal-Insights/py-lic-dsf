"""B-sheet external debt-dynamics identity (residual gross borrowing)."""

from __future__ import annotations

import pandas as pd

from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.pv.macro_debt import stocks as _stocks
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.macro_shocks import depreciation_of_nc_pct, real_depreciation_pct


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _growth_pct(level: pd.Series) -> pd.Series:
    return (100.0 * (level / level.shift(1) - 1.0)).astype(float)


def _r26(real_g: float, deflator_g: float) -> float:
    return (
        1.0 + real_g / 100.0 + deflator_g / 100.0 + real_g / 100.0 * deflator_g / 100.0
    )


def _pct_of_gdp(level: pd.Series, gdp: pd.Series) -> pd.Series:
    return (100.0 * level / gdp.replace(0.0, pd.NA)).astype(float)


def _exports_shocked(exp_usd_b: float, exp_usd_s: float) -> bool:
    return abs(exp_usd_s - exp_usd_b) > 1e-9 * max(abs(exp_usd_b), 1.0)


def _bsheet_r19_pct(
    *,
    year: int,
    exp_b: float,
    exp_s: float,
    exp_usd_b: float,
    exp_usd_s: float,
    gdp_b: float,
    gdp_s: float,
    shock_window: tuple[int, ...],
    nx_year: int | None,
    fx_depreciation_pct: float,
) -> float:
    """B-sheet exports/GDP (R19): shocked ``E105/E46`` or baseline ``O19×O48/E46``."""
    if gdp_s == 0.0:
        return 0.0
    if nx_year is not None and year == nx_year and fx_depreciation_pct:
        return exp_b * gdp_b / gdp_s
    if year in shock_window:
        if _exports_shocked(exp_usd_b, exp_usd_s):
            return exp_s
        return exp_b * gdp_b / gdp_s
    return exp_s


def _bsheet_r18_shock_window(
    *,
    year: int,
    imp_b: float,
    exp_b: float,
    exp_s: float,
    exp_usd_b: float,
    exp_usd_s: float,
    gdp_b: float,
    gdp_s: float,
) -> float:
    """B-sheet R18 = R20 − R19 in the shock window (non-NX years)."""
    if gdp_s == 0.0:
        return 0.0
    r20 = imp_b * gdp_b / gdp_s
    if _exports_shocked(exp_usd_b, exp_usd_s):
        r19 = exp_s
    else:
        r19 = exp_b * gdp_b / gdp_s
    return r20 - r19


def bsheet_exports_to_gdp(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    *,
    fx_depreciation_pct: float = 0.0,
) -> pd.Series:
    """Exports/GDP (%) on the external B-sheet (R19), year-by-year."""
    years = baseline_macro.inputs.years
    year_list = list(years)
    first = baseline_macro.inputs.first_projection_year
    gdp_b = _align(baseline_macro.gdp_usd(), years)
    gdp_s = _align(shocked_macro.gdp_usd(), years)
    exp_s = _pct_of_gdp(_align(shocked_macro.exports(), years), gdp_s)
    exp_b = _pct_of_gdp(_align(baseline_macro.exports(), years), gdp_b)
    exp_usd_b = _align(baseline_macro.exports(), years)
    exp_usd_s = _align(shocked_macro.exports(), years)
    proj = [y for y in year_list if y >= first]
    shock_window = tuple(proj[1:3])
    nx_year = proj[2] if len(proj) >= 3 else None

    out = pd.Series(0.0, index=year_list, dtype=float)
    for year in year_list:
        if year < first:
            out.loc[year] = float(exp_b.loc[year]) if pd.notna(exp_b.loc[year]) else 0.0
            continue
        out.loc[year] = _bsheet_r19_pct(
            year=year,
            exp_b=float(exp_b.loc[year]),
            exp_s=float(exp_s.loc[year]),
            exp_usd_b=float(exp_usd_b.loc[year]),
            exp_usd_s=float(exp_usd_s.loc[year]),
            gdp_b=float(gdp_b.loc[year]),
            gdp_s=float(gdp_s.loc[year]),
            shock_window=shock_window,
            nx_year=nx_year,
            fx_depreciation_pct=fx_depreciation_pct,
        )
    return out.astype(float)


def hybrid_external_debt_to_gdp(macro: MacroDebtBook) -> pd.Series:
    """Baseline R12: PPG in LCU/GDP LCU plus private USD/GDP USD.

    Excel uses ``100 × Macro R81 / (GDP_USD × FX_pa)`` for PPG (eop LCU over
    period-average GDP LCU) plus private external / GDP.
    """
    return _stocks.hybrid_external_debt_to_gdp(macro.inputs, macro.external)


def _endogenous(
    *,
    prev_r12: float,
    prev_nom: float,
    real_g: float,
    deflator_g: float,
    dep: float,
    interest_usd: float,
    lc_share: float,
) -> float:
    """B-sheet R25 = R27 + R28 + R29."""
    den = _r26(real_g, deflator_g)
    rate_pct = (interest_usd / prev_nom * 100.0) if prev_nom else 0.0
    r27 = (rate_pct / 100.0) * prev_r12 / den
    r28 = -(real_g / 100.0) * prev_r12 / den
    r29 = (
        -(deflator_g / 100.0 * (1.0 + real_g / 100.0)) * prev_r12 / den
        + lc_share * (-dep / 100.0) * (1.0 + rate_pct / 100.0) * prev_r12 / den
    )
    return r27 + r28 + r29


def _lc_share_of_total(macro: MacroDebtBook) -> pd.Series:
    """Baseline R43: Macro R85 / 100.

    LC-denominated external (locally-issued + LC-NR) over total external USD
    (Macro R6), not the hybrid R12 stock which scales PPG by FX(eop)/FX(pa).
    History uses Input 3 row 208; projection uses Ext locally-issued + LC-NR.
    """
    years = macro.inputs.years
    total = _align(_stocks.total_external(macro.inputs, macro.external), years)
    total = total.replace(0.0, pd.NA)
    hist_usd = macro.inputs.lc_external_usd
    if hist_usd is None:
        hist = pd.Series(0.0, index=list(years), dtype=float)
    else:
        hist = (_align(hist_usd, years) / total).astype(float)

    local = pd.Series(0.0, index=list(years), dtype=float)
    if macro.external is not None:
        local = _align(macro.external.inputs.locally_issued_debt_stock, years).fillna(
            0.0
        )
        for inst in macro.external.portfolio.instruments:
            if not isinstance(inst, LocalCurrencyNonResidentInstrument):
                continue
            stock = inst.external().loc["Stock of new forex debt (in USD)"]
            for year in years:
                if year in stock.index:
                    local.loc[year] = float(local.loc[year]) + float(stock.loc[year])
    proj = (local / total).astype(float)
    return _stocks.hist_proj(
        hist, proj, years, macro.inputs.first_projection_year
    ).fillna(0.0)


def historical_identity_pins(macro: MacroDebtBook) -> tuple[float, float]:
    """10-year historical means of Baseline R17 (CA deficit) and R24 (FDI).

    Excel A1 ``E17 = −N70`` and ``E24 = −N75``: pin these % of GDP from the
    second projection year onward.
    """
    years = macro.inputs.years
    first = macro.inputs.first_projection_year
    gdp = _align(macro.gdp_usd(), years)
    r17 = -_pct_of_gdp(
        _align(macro.inputs.current_account, years)
        + _align(macro.external_interest(), years),
        gdp,
    )
    r24 = -_pct_of_gdp(_align(macro.inputs.fdi, years), gdp)
    hist_years = [y for y in years if y < first][-10:]
    ca_vals = [float(r17.loc[y]) for y in hist_years if pd.notna(r17.loc[y])]
    fdi_vals = [float(r24.loc[y]) for y in hist_years if pd.notna(r24.loc[y])]
    ca_pin = float(sum(ca_vals) / len(ca_vals)) if ca_vals else 0.0
    fdi_pin = float(sum(fdi_vals) / len(fdi_vals)) if fdi_vals else 0.0
    return ca_pin, fdi_pin


def external_residual_borrowing(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    *,
    fx_depreciation_pct: float = 0.0,
    fx_passthrough: float = 0.0,
    inflation_elasticity: float = 0.0,
    residual_interest_rate: float = 0.0,
    resfin_interest: pd.Series | None = None,
    net_exports_elasticity: float = 0.0,
    historical_averages: bool = False,
    hist_ca_deficit_pct: float | None = None,
    hist_fdi_pct: float | None = None,
    additional_borrowing_interest: pd.Series | None = None,
    post_shock_r18_unscaled: bool = False,
) -> pd.Series:
    """USD residual PPG MLT fill (Excel B-sheet residual gross borrowing).

    Evolves the external debt/GDP identity (B-sheet R12–R30) under the shocked
    Macro path, then residual = Δ stressed hybrid stock − Δ baseline stock.

    After the two-year shock window, the trade-balance term (R18) returns to
    the baseline goods-deficit path. Standard B3 sheets use
    ``baseline R18 × baseline GDP / shocked GDP`` (constant baseline USD
    deficit). C3 commodity (``post_shock_r18_unscaled=True``) copies baseline
    R18 as a % of shocked GDP — Excel ``C3_Commodity prices_ext`` R18 2027+.
    ``fx_depreciation_pct`` is the B5/B6 R58 shock in the second projection
    year. The following year uses unscaled baseline R18 minus
    ``net_exports_elasticity`` times real depreciation (B5/B6 E43), not the
    nominal shock size.

    Shock-window R21/R24 are % of **shocked** GDP (like R20), except the B6
    combo sheet in the cached workbook divides by baseline GDP when FX and
    export shocks co-occur — that special case is matched explicitly.

    When ``historical_averages`` is true (A1), R17 / R24 are pinned to the
    10-year historical means for every year from the second projection year,
    R18 stays on the baseline % of GDP path, and the baseline residual (R30)
    is copied unscaled.

    Pass ``resfin_interest`` (PV Stress R99) to feed ResFin interest into R25;
    ``scenario._converged_external_gap`` iterates until gap and overlay agree.
    ``additional_borrowing_interest`` adds B6 combo R112 (``PV_Base-add.cost.mkt``).
    """
    years = baseline_macro.inputs.years
    first = baseline_macro.inputs.first_projection_year
    year_list = list(years)
    gdp_b = _align(baseline_macro.gdp_usd(), years)
    gdp_s = _align(shocked_macro.gdp_usd(), years)
    r12_b = hybrid_external_debt_to_gdp(baseline_macro)
    r82 = (r12_b / 100.0 * gdp_b).astype(float)
    r12_b_map = {int(y): float(r12_b.loc[y]) for y in year_list}

    g_b = _growth_pct(_align(baseline_macro.inputs.gdp_constant, years))
    defl_b = _growth_pct(
        gdp_b / _align(baseline_macro.inputs.gdp_constant, years).replace(0.0, pd.NA)
    )
    g_s = _growth_pct(_align(shocked_macro.inputs.gdp_constant, years))
    defl_s = _growth_pct(
        gdp_s / _align(shocked_macro.inputs.gdp_constant, years).replace(0.0, pd.NA)
    )
    dep_b = depreciation_of_nc_pct(baseline_macro.inputs)
    dep_s = depreciation_of_nc_pct(shocked_macro.inputs)
    gdp_c_b = _align(baseline_macro.inputs.gdp_constant, years).replace(0.0, pd.NA)
    lcu_g = _growth_pct(gdp_b * _align(baseline_macro.inputs.fx_pa, years) / gdp_c_b)
    if baseline_macro.inputs.foreign_gdp_deflator is not None:
        foreign_g = _growth_pct(
            _align(baseline_macro.inputs.foreign_gdp_deflator, years)
        )
    else:
        foreign_g = pd.Series(0.0, index=year_list, dtype=float)

    exp_s = _pct_of_gdp(_align(shocked_macro.exports(), years), gdp_s)
    exp_b = _pct_of_gdp(_align(baseline_macro.exports(), years), gdp_b)
    imp_b = _pct_of_gdp(_align(baseline_macro.inputs.imports, years), gdp_b)
    exp_usd_b = _align(baseline_macro.exports(), years)
    exp_usd_s = _align(shocked_macro.exports(), years)
    tr_b = -_pct_of_gdp(
        _align(baseline_macro.inputs.current_transfers_net, years), gdp_b
    )
    fdi_b = -_pct_of_gdp(_align(baseline_macro.inputs.fdi, years), gdp_b)
    # Baseline R17 = −(CA + external interest) / GDP × 100.
    r17_b = -_pct_of_gdp(
        _align(baseline_macro.inputs.current_account, years)
        + _align(baseline_macro.external_interest(), years),
        gdp_b,
    )
    r18_b = (imp_b - exp_b).astype(float)
    r21_b = tr_b
    r23_b = (r17_b - r18_b - r21_b).astype(float)
    r24_b = fdi_b
    lc_share = _lc_share_of_total(baseline_macro)

    proj = [y for y in year_list if y >= first]
    shock_window = proj[1:3]
    fx_year = proj[1] if len(proj) >= 2 else None
    nx_year = proj[2] if len(proj) >= 3 else None

    r30_b: dict[int, float] = {year_list[0]: 0.0}
    for year in year_list[1:]:
        prev = year - 1
        gg = float(g_b.loc[year]) if pd.notna(g_b.loc[year]) else 0.0
        dg = float(defl_b.loc[year]) if pd.notna(defl_b.loc[year]) else 0.0
        dep = float(dep_b.loc[year]) if pd.notna(dep_b.loc[year]) else 0.0
        r25 = _endogenous(
            prev_r12=r12_b_map[prev],
            prev_nom=float(r82.loc[prev]),
            real_g=gg,
            deflator_g=dg,
            dep=dep,
            interest_usd=float(baseline_macro.external_interest().loc[year]),
            lc_share=float(lc_share.loc[prev]),
        )
        r16 = (
            float(r17_b.loc[year]) + float(r24_b.loc[year]) + r25
            if pd.notna(r17_b.loc[year])
            else r25
        )
        r15 = r12_b_map[year] - r12_b_map[prev]
        r30_b[year] = r15 - r16

    r12s: dict[int, float] = {}
    r84s: dict[int, float] = {}
    extra = pd.Series(0.0, index=year_list, dtype=float)
    for year in year_list:
        gdp = float(gdp_s.loc[year])
        if year < first or year == first:
            r12s[year] = r12_b_map[year]
            r84s[year] = r12s[year] / 100.0 * gdp
            extra.loc[year] = r84s[year] - float(r82.loc[year])
            continue
        prev = year - 1
        gg = float(g_s.loc[year]) if pd.notna(g_s.loc[year]) else 0.0
        dg = float(defl_s.loc[year]) if pd.notna(defl_s.loc[year]) else 0.0
        if fx_year is not None and year == fx_year and fx_depreciation_pct:
            dep = float(fx_depreciation_pct)
        else:
            dep = float(dep_s.loc[year]) if pd.notna(dep_s.loc[year]) else 0.0
        if resfin_interest is not None:
            interest = float(shocked_macro.external_interest().loc[year]) + float(
                resfin_interest.loc[year]
            )
        else:
            interest = float(shocked_macro.external_interest().loc[year]) + (
                residual_interest_rate * float(extra.loc[prev])
            )
        if additional_borrowing_interest is not None:
            interest += float(additional_borrowing_interest.loc[year])
        r25 = _endogenous(
            prev_r12=r12s[prev],
            prev_nom=r84s[prev],
            real_g=gg,
            deflator_g=dg,
            dep=dep,
            interest_usd=interest,
            lc_share=float(lc_share.loc[prev]),
        )
        if historical_averages:
            r17 = float(hist_ca_deficit_pct) if hist_ca_deficit_pct is not None else 0.0
            r24 = float(hist_fdi_pct) if hist_fdi_pct is not None else 0.0
            r16 = r17 + r24 + r25
            r30 = r30_b[year]
            r15 = r16 + r30
            r12s[year] = r12s[prev] + r15
            r84s[year] = r12s[year] / 100.0 * gdp
            extra.loc[year] = r84s[year] - float(r82.loc[year])
            continue
        scale = float(gdp_b.loc[year]) / gdp if gdp else 1.0
        if shock_window and year > shock_window[-1]:
            # B3: keep baseline goods-deficit USD (r18_b × gdp_b/gdp_s).
            # C3: copy baseline R18 % onto shocked GDP (Excel R18 2027+).
            r18 = float(r18_b.loc[year]) * (
                1.0 if post_shock_r18_unscaled else scale
            )
        elif nx_year is not None and year == nx_year and fx_depreciation_pct:
            fg = 0.0
            lg = 0.0
            gap_g = 0.0
            if fx_year is not None:
                if pd.notna(foreign_g.loc[fx_year]):
                    fg = float(foreign_g.loc[fx_year])
                if pd.notna(lcu_g.loc[fx_year]):
                    lg = float(lcu_g.loc[fx_year])
                gb = float(g_b.loc[fx_year]) if pd.notna(g_b.loc[fx_year]) else 0.0
                gs = float(g_s.loc[fx_year]) if pd.notna(g_s.loc[fx_year]) else 0.0
                gap_g = gb - gs
            real_dep = real_depreciation_pct(
                nominal_dep=float(fx_depreciation_pct),
                foreign_deflator_growth=fg,
                lcu_deflator_growth=lg,
                passthrough=fx_passthrough,
                real_growth_gap=gap_g,
                inflation_elasticity=inflation_elasticity,
            )
            r18 = float(r18_b.loc[year]) - net_exports_elasticity * real_dep
        else:
            r18 = _bsheet_r18_shock_window(
                year=year,
                imp_b=float(imp_b.loc[year]),
                exp_b=float(exp_b.loc[year]),
                exp_s=float(exp_s.loc[year]),
                exp_usd_b=float(exp_usd_b.loc[year]),
                exp_usd_s=float(exp_usd_s.loc[year]),
                gdp_b=float(gdp_b.loc[year]),
                gdp_s=gdp,
            )
        if year in shock_window:
            # B1/B3/B5: % of shocked GDP (same as R20 = import USD / shocked GDP).
            # B6 combo sheet uniquely divides R21/R24 by baseline GDP in the
            # cached workbook — match that when FX + export shocks co-occur.
            tr_s = float(shocked_macro.inputs.current_transfers_net.loc[year])
            fdi_s = float(shocked_macro.inputs.fdi.loc[year])
            combo = bool(fx_depreciation_pct) and _exports_shocked(
                float(exp_usd_b.loc[year]), float(exp_usd_s.loc[year])
            )
            denom = float(gdp_b.loc[year]) if combo else gdp
            r21 = -100.0 * tr_s / denom if denom else 0.0
            r24 = -100.0 * fdi_s / denom if denom else 0.0
        else:
            r21 = float(r21_b.loc[year]) * scale if pd.notna(r21_b.loc[year]) else 0.0
            r24 = float(r24_b.loc[year]) * scale if pd.notna(r24_b.loc[year]) else 0.0
        r23 = float(r23_b.loc[year]) * scale if pd.notna(r23_b.loc[year]) else 0.0
        r17 = r18 + r21 + r23
        r16 = r17 + r24 + r25
        r15 = r16 + r30_b[year] * scale
        r12s[year] = r12s[prev] + r15
        r84s[year] = r12s[year] / 100.0 * gdp
        extra.loc[year] = r84s[year] - float(r82.loc[year])

    gap = pd.Series(0.0, index=year_list, dtype=float)
    for year in year_list:
        if year <= first:
            continue
        gap.loc[year] = (r84s[year] - r84s[year - 1]) - (
            float(r82.loc[year]) - float(r82.loc[year - 1])
        )
    return gap.astype(float)


# Excel C1 combined CL: external PPG residual ≈ 40.7% of the one-off CL (10% GDP).
CL_EXTERNAL_PPG_SHARE = 0.407


def external_cl_gap_usd(
    baseline_macro: MacroDebtBook,
    shocked_macro: MacroDebtBook,
    *,
    share: float = CL_EXTERNAL_PPG_SHARE,
) -> pd.Series:
    """Map a one-off CL flow (LCU) to external PPG gap (USD) in the shock year."""
    years = baseline_macro.inputs.years
    first = baseline_macro.inputs.first_projection_year
    year_list = list(years)
    proj = [y for y in year_list if y >= first]
    shock_year = proj[1] if len(proj) >= 2 else None
    out = pd.Series(0.0, index=year_list, dtype=float)
    if shock_year is None or share <= 0.0:
        return out
    cl_b = _align(baseline_macro.inputs.contingent_liabilities, years)
    cl_s = _align(shocked_macro.inputs.contingent_liabilities, years)
    delta_lcu = float(cl_s.loc[shock_year]) - float(cl_b.loc[shock_year])
    if abs(delta_lcu) < 1e-6:
        return out
    fx = float(_align(shocked_macro.inputs.fx_pa, years).loc[shock_year])
    if fx == 0.0:
        return out
    out.loc[shock_year] = (delta_lcu / fx) * float(share)
    return out.astype(float)
