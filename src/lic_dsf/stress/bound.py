"""B-sheet external debt-dynamics identity (residual gross borrowing)."""

from __future__ import annotations

import pandas as pd

from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.pv.macro_debt import stocks as _stocks
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.shocks import depreciation_of_nc_pct, real_depreciation_pct


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


def hybrid_external_debt_to_gdp(macro: MacroDebtBook) -> pd.Series:
    """Baseline R12: PPG in LCU/GDP LCU plus private USD/GDP USD.

    Excel uses ``100 × Macro R81 / (GDP_USD × FX_pa)`` for PPG (eop LCU over
    period-average GDP LCU) plus private external / GDP.
    """
    years = macro.inputs.years
    gdp = _align(macro.gdp_usd(), years)
    fx_eop = _align(macro.fx_eop(), years)
    fx_pa = _align(macro.fx_pa(), years).replace(0.0, pd.NA)
    ppg = _align(macro.ppg_external(), years)
    priv = _align(_stocks.private_external(macro.inputs), years)
    r13 = 100.0 * ppg * fx_eop / (gdp * fx_pa)
    r14 = 100.0 * priv / gdp.replace(0.0, pd.NA)
    return (r13 + r14).astype(float)


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
    """
    years = macro.inputs.years
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
    total = _align(_stocks.total_external(macro.inputs, macro.external), years)
    return (local / total.replace(0.0, pd.NA)).fillna(0.0).astype(float)


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
    net_exports_elasticity: float = 0.0,
    historical_averages: bool = False,
    hist_ca_deficit_pct: float | None = None,
    hist_fdi_pct: float | None = None,
) -> pd.Series:
    """USD residual PPG MLT fill (Excel B-sheet residual gross borrowing).

    Evolves the external debt/GDP identity (B-sheet R12–R30) under the shocked
    Macro path, then residual = Δ stressed hybrid stock − Δ baseline stock.

    After the two-year shock window, the trade-balance term (R18) returns to
    the baseline USD deficit scaled by shocked GDP — Excel does not keep the
    export shortfall in the identity forever. ``fx_depreciation_pct`` is the
    B5/B6 R58 shock in the second projection year. The following year uses
    unscaled baseline R18 minus ``net_exports_elasticity`` times real
    depreciation (B5/B6 E43), not the nominal shock size.

    When ``historical_averages`` is true (A1), R17 / R24 are pinned to the
    10-year historical means for every year from the second projection year,
    R18 stays on the baseline % of GDP path, and the baseline residual (R30)
    is copied unscaled.
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
    imp_s = _pct_of_gdp(_align(baseline_macro.inputs.imports, years), gdp_s)
    tr_s = -_pct_of_gdp(
        _align(shocked_macro.inputs.current_transfers_net, years), gdp_s
    )
    fdi_s = -_pct_of_gdp(_align(shocked_macro.inputs.fdi, years), gdp_s)
    exp_b = _pct_of_gdp(_align(baseline_macro.exports(), years), gdp_b)
    imp_b = _pct_of_gdp(_align(baseline_macro.inputs.imports, years), gdp_b)
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
        interest = float(shocked_macro.external_interest().loc[year]) + (
            residual_interest_rate * float(extra.loc[prev])
        )
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
            r18 = float(r18_b.loc[year]) * scale
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
            r18 = float(imp_s.loc[year] - exp_s.loc[year])
        r21 = float(tr_s.loc[year])
        r23 = float(r23_b.loc[year]) * scale if pd.notna(r23_b.loc[year]) else 0.0
        r24 = float(fdi_s.loc[year])
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
