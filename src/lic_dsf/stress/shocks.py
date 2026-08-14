"""Apply Input 6 standard shocks to ``MacroDebtInputs`` series."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from lic_dsf.pv.macro_debt.types import MacroDebtInputs
from lic_dsf.stress.types import Input6StandardParams, ThresholdRule


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _growth_pct(level: pd.Series, years: tuple[int, ...]) -> pd.Series:
    """Percent growth of ``level`` (NA in the first year)."""
    aligned = _align(level, years)
    prior = aligned.shift(1)
    out = 100.0 * (aligned / prior.replace(0.0, pd.NA) - 1.0)
    return out.astype(float)


def _hist_mean_sd(
    growth: pd.Series,
    years: tuple[int, ...],
    first_projection_year: int,
    window: int = 10,
) -> tuple[float, float]:
    """Sample mean / SD of growth over the last ``window`` history years."""
    hist_years = [y for y in years if y < first_projection_year]
    if not hist_years:
        return 0.0, 0.0
    use = hist_years[-window:]
    values = [float(growth.loc[y]) for y in use if pd.notna(growth.loc[y])]
    if not values:
        return 0.0, 0.0
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    if len(arr) < 2:
        return mean, 0.0
    return mean, float(arr.std(ddof=1))


def _shocked_growth(
    baseline_growth: float,
    hist_avg: float,
    hist_sd: float,
    shock_sd: float,
    rule: ThresholdRule,
) -> float:
    """Apply Input 6 threshold rule for a single shock year."""
    hist_path = hist_avg - shock_sd * hist_sd
    base_path = baseline_growth - shock_sd * hist_sd
    if rule == "historical_average":
        return hist_path
    if rule == "baseline_projection":
        return base_path
    return min(hist_path, base_path)


def _projection_shock_years(
    years: tuple[int, ...], first_projection_year: int
) -> tuple[int, int] | None:
    """Return the second and third projection years (Excel shock window)."""
    proj = [y for y in years if y >= first_projection_year]
    if len(proj) < 3:
        return None
    return proj[1], proj[2]


def _rebuild_levels_from_growth(
    baseline_level: pd.Series,
    years: tuple[int, ...],
    first_projection_year: int,
    shocked_growth: pd.Series,
) -> pd.Series:
    """Compound ``shocked_growth`` (%) from the last pre-shock level onward."""
    out = _align(baseline_level, years).copy()
    for year in years:
        if year < first_projection_year:
            continue
        prior = year - 1
        if prior not in out.index or pd.isna(out.loc[prior]):
            continue
        g = float(shocked_growth.loc[year])
        if pd.isna(g):
            g = 0.0
        out.loc[year] = float(out.loc[prior]) * (1.0 + g / 100.0)
    return out.astype(float)


def apply_real_gdp_shock(
    inputs: MacroDebtInputs,
    params: Input6StandardParams,
    *,
    shock_sd: float | None = None,
    inflation_elasticity: float | None = None,
) -> MacroDebtInputs:
    """Shock real GDP growth in projection years 2–3 (B1 / combo GDP block).

    Rebuilds ``gdp_constant`` from shocked real growth and ``gdp_usd`` from
    shocked real growth plus the Input 6 inflation-elasticity adjustment to the
    GDP deflator (B1 ``R50`` / ``R51`` / ``R46``). Absolute exports are left
    unchanged (B1 holds export levels and rescales exports/GDP).

    Args:
        inputs: Baseline Macro inputs.
        params: Input 6 standard parameters.
        shock_sd: Override SD multiple (combo uses half size).
        inflation_elasticity: Override elasticity (0 when interactions off).

    Returns:
        New ``MacroDebtInputs`` with shocked GDP paths.
    """
    years = inputs.years
    first = inputs.first_projection_year
    sd = params.gdp_shock_sd if shock_sd is None else shock_sd
    elasticity = (
        params.inflation_elasticity
        if inflation_elasticity is None
        else inflation_elasticity
    )
    if not params.interactions_on:
        elasticity = 0.0

    real_g = _growth_pct(inputs.gdp_constant, years)
    deflator_g = _growth_pct(
        inputs.gdp_usd / inputs.gdp_constant.replace(0.0, pd.NA), years
    )
    # Equivalent deflator from USD vs constant paths when ratio is clean:
    usd_g = _growth_pct(inputs.gdp_usd, years)
    for year in years:
        if year == years[0]:
            continue
        rg = real_g.loc[year]
        if pd.isna(deflator_g.loc[year]) and pd.notna(usd_g.loc[year]) and pd.notna(rg):
            deflator_g.loc[year] = 100.0 * (
                (1.0 + float(usd_g.loc[year]) / 100.0) / (1.0 + float(rg) / 100.0) - 1.0
            )

    hist_avg, hist_sd = _hist_mean_sd(real_g, years, first)
    shocked_real = real_g.copy()
    shocked_deflator = deflator_g.copy()
    window = _projection_shock_years(years, first)
    if window is not None:
        y2, y3 = window
        hist_path = hist_avg - sd * hist_sd
        # Year 2: apply threshold rule.
        base_g2 = float(real_g.loc[y2])
        new_g2 = _shocked_growth(base_g2, hist_avg, hist_sd, sd, params.threshold_rule)
        shocked_real.loc[y2] = new_g2
        shocked_deflator.loc[y2] = (
            float(deflator_g.loc[y2]) - (base_g2 - new_g2) * elasticity
        )
        # Year 3 (B1 F50): if year 2 used the historical path, keep it;
        # otherwise shock the baseline projection path.
        base_g3 = float(real_g.loc[y3])
        if abs(new_g2 - hist_path) < 1e-12:
            new_g3 = hist_path
        else:
            new_g3 = base_g3 - sd * hist_sd
        shocked_real.loc[y3] = new_g3
        shocked_deflator.loc[y3] = (
            float(deflator_g.loc[y3]) - (base_g3 - new_g3) * elasticity
        )

    gdp_constant = _rebuild_levels_from_growth(
        inputs.gdp_constant, years, first, shocked_real
    )
    # USD GDP compounds real × deflator from the year before first projection.
    gdp_usd = _align(inputs.gdp_usd, years).copy()
    for year in years:
        if year < first:
            continue
        prior = year - 1
        rg = float(shocked_real.loc[year])
        dg = float(shocked_deflator.loc[year])
        if pd.isna(rg):
            rg = 0.0
        if pd.isna(dg):
            dg = 0.0
        gdp_usd.loc[year] = (
            float(gdp_usd.loc[prior]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
        )

    return replace(inputs, gdp_usd=gdp_usd.astype(float), gdp_constant=gdp_constant)


def apply_exports_shock(
    inputs: MacroDebtInputs,
    params: Input6StandardParams,
    *,
    shock_sd: float | None = None,
    gdp_elasticity: float | None = None,
) -> MacroDebtInputs:
    """Shock nominal export growth in projection years 2–3 (B3).

    Also applies the Input 6 real-GDP elasticity to export growth when
    interactions are on. FDI / transfers are unchanged.
    """
    years = inputs.years
    first = inputs.first_projection_year
    sd = params.exports_shock_sd if shock_sd is None else shock_sd
    elasticity = (
        params.exports_gdp_elasticity if gdp_elasticity is None else gdp_elasticity
    )
    if not params.interactions_on:
        elasticity = 0.0

    exp_g = _growth_pct(inputs.exports, years)
    hist_avg, hist_sd = _hist_mean_sd(exp_g, years, first)
    shocked_exp_g = exp_g.copy()
    window = _projection_shock_years(years, first)
    if window is not None:
        for year in window:
            base_g = float(exp_g.loc[year])
            shocked_exp_g.loc[year] = _shocked_growth(
                base_g, hist_avg, hist_sd, sd, params.threshold_rule
            )

    exports = _rebuild_levels_from_growth(inputs.exports, years, first, shocked_exp_g)

    # GDP interaction (B3 R50):
    # - if shocked export growth < 0: base_gdp + ε × shocked_exp_g × prior exp/GDP
    # - else: base_gdp − ε × (base_exp_g − shocked_exp_g) × prior exp/GDP
    real_g = _growth_pct(inputs.gdp_constant, years)
    shocked_real = real_g.copy()
    if window is not None and elasticity:
        gdp = _align(inputs.gdp_usd, years)
        exports_base = _align(inputs.exports, years)
        for year in window:
            prior = year - 1
            share = (
                float(exports_base.loc[prior] / gdp.loc[prior])
                if gdp.loc[prior]
                else 0.0
            )
            shocked_eg = float(shocked_exp_g.loc[year])
            base_eg = float(exp_g.loc[year])
            base_rg = float(real_g.loc[year])
            if shocked_eg < 0.0:
                shocked_real.loc[year] = base_rg + elasticity * shocked_eg * share
            else:
                shocked_real.loc[year] = (
                    base_rg - elasticity * (base_eg - shocked_eg) * share
                )

    # Keep baseline deflator; rebuild USD from shocked real × baseline deflator.
    deflator_g = _growth_pct(
        inputs.gdp_usd / inputs.gdp_constant.replace(0.0, pd.NA), years
    )
    usd_g = _growth_pct(inputs.gdp_usd, years)
    for year in years:
        if year == years[0]:
            continue
        if pd.isna(deflator_g.loc[year]) and pd.notna(usd_g.loc[year]):
            rg = float(real_g.loc[year])
            deflator_g.loc[year] = 100.0 * (
                (1.0 + float(usd_g.loc[year]) / 100.0) / (1.0 + rg / 100.0) - 1.0
            )

    gdp_constant = _rebuild_levels_from_growth(
        inputs.gdp_constant, years, first, shocked_real
    )
    gdp_usd = _align(inputs.gdp_usd, years).copy()
    for year in years:
        if year < first:
            continue
        rg = float(shocked_real.loc[year]) if pd.notna(shocked_real.loc[year]) else 0.0
        dg = float(deflator_g.loc[year]) if pd.notna(deflator_g.loc[year]) else 0.0
        gdp_usd.loc[year] = (
            float(gdp_usd.loc[year - 1]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
        )

    # Current account: reduce by export shortfall (financing need channel).
    shortfall = _align(inputs.exports, years) - exports
    current_account = _align(inputs.current_account, years) - shortfall

    return replace(
        inputs,
        exports=exports.astype(float),
        gdp_usd=gdp_usd.astype(float),
        gdp_constant=gdp_constant.astype(float),
        current_account=current_account.astype(float),
    )


def _shock_ratio_to_gdp(
    series: pd.Series,
    gdp: pd.Series,
    years: tuple[int, ...],
    first: int,
    shock_sd: float,
    rule: ThresholdRule,
) -> pd.Series:
    """Shock a flow/GDP ratio in projection years 2–3, return new flow levels."""
    ratio = 100.0 * _align(series, years) / _align(gdp, years).replace(0.0, pd.NA)
    growth_proxy = ratio  # shock the ratio level vs hist mean/sd of ratio
    hist_avg, hist_sd = _hist_mean_sd(growth_proxy, years, first)
    shocked_ratio = ratio.copy()
    window = _projection_shock_years(years, first)
    if window is not None:
        for year in window:
            base = float(ratio.loc[year]) if pd.notna(ratio.loc[year]) else 0.0
            shocked_ratio.loc[year] = _shocked_growth(
                base, hist_avg, hist_sd, shock_sd, rule
            )
    return (_align(gdp, years) * shocked_ratio / 100.0).astype(float)


def apply_other_flows_shock(
    inputs: MacroDebtInputs,
    params: Input6StandardParams,
    *,
    transfers_sd: float | None = None,
    fdi_sd: float | None = None,
) -> MacroDebtInputs:
    """Shock transfers/GDP and FDI/GDP in projection years 2–3 (B4)."""
    years = inputs.years
    first = inputs.first_projection_year
    t_sd = params.transfers_shock_sd if transfers_sd is None else transfers_sd
    f_sd = params.fdi_shock_sd if fdi_sd is None else fdi_sd
    transfers = _shock_ratio_to_gdp(
        inputs.current_transfers_net,
        inputs.gdp_usd,
        years,
        first,
        t_sd,
        params.threshold_rule,
    )
    # Keep official share of net transfers when possible.
    official_share = (
        _align(inputs.current_transfers_official, years)
        / _align(inputs.current_transfers_net, years).replace(0.0, pd.NA)
    ).fillna(0.0)
    official = (transfers * official_share).astype(float)
    fdi = _shock_ratio_to_gdp(
        inputs.fdi, inputs.gdp_usd, years, first, f_sd, params.threshold_rule
    )
    # CA worsens by transfers shortfall; FDI shortfall is a financing item.
    tr_short = _align(inputs.current_transfers_net, years) - transfers
    current_account = _align(inputs.current_account, years) - tr_short
    return replace(
        inputs,
        current_transfers_net=transfers,
        current_transfers_official=official,
        fdi=fdi.astype(float),
        current_account=current_account.astype(float),
    )


def apply_fx_depreciation_shock(
    inputs: MacroDebtInputs,
    params: Input6StandardParams,
    *,
    depreciation_pct: float | None = None,
) -> MacroDebtInputs:
    """One-time FX depreciation (B5 deflator pass-through).

    Matches the template's B5 layout: the depreciation size is applied to the
    GDP deflator in the **second** projection year (column E), leaving the
    first projection year on the baseline GDP path. ``fx_eop`` / ``fx_pa``
    scale from that shock year onward.
    """
    years = inputs.years
    first = inputs.first_projection_year
    dep = params.fx_depreciation_pct if depreciation_pct is None else depreciation_pct
    passthrough = params.fx_passthrough if params.interactions_on else 0.0
    proj = [y for y in years if y >= first]
    shock_year = proj[1] if len(proj) >= 2 else (proj[0] if proj else None)

    fx_eop = _align(inputs.fx_eop, years).copy()
    fx_pa = _align(inputs.fx_pa, years).copy()
    factor = 1.0 + dep / 100.0
    if shock_year is not None:
        for year in years:
            if year >= shock_year:
                fx_eop.loc[year] = float(fx_eop.loc[year]) * factor
                fx_pa.loc[year] = float(fx_pa.loc[year]) * factor

    real_g = _growth_pct(inputs.gdp_constant, years)
    deflator_g = _growth_pct(
        inputs.gdp_usd / inputs.gdp_constant.replace(0.0, pd.NA), years
    )
    usd_g = _growth_pct(inputs.gdp_usd, years)
    for year in years:
        if year == years[0]:
            continue
        if pd.isna(deflator_g.loc[year]) and pd.notna(usd_g.loc[year]):
            rg = float(real_g.loc[year])
            deflator_g.loc[year] = 100.0 * (
                (1.0 + float(usd_g.loc[year]) / 100.0) / (1.0 + rg / 100.0) - 1.0
            )
    # B5 E51: baseline deflator − (1 − passthrough) × depreciation.
    if shock_year is not None and shock_year in deflator_g.index:
        base_d = float(deflator_g.loc[shock_year])
        deflator_g.loc[shock_year] = base_d - (1.0 - passthrough) * dep

    gdp_usd = _align(inputs.gdp_usd, years).copy()
    for year in years:
        if year < first:
            continue
        rg = float(real_g.loc[year]) if pd.notna(real_g.loc[year]) else 0.0
        dg = float(deflator_g.loc[year]) if pd.notna(deflator_g.loc[year]) else 0.0
        gdp_usd.loc[year] = (
            float(gdp_usd.loc[year - 1]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
        )

    return replace(
        inputs,
        fx_eop=fx_eop.astype(float),
        fx_pa=fx_pa.astype(float),
        gdp_usd=gdp_usd.astype(float),
    )


def apply_primary_balance_shock(
    inputs: MacroDebtInputs,
    params: Input6StandardParams,
    *,
    shock_sd: float | None = None,
) -> MacroDebtInputs:
    """Shock primary balance / GDP in projection years 2–3 (B2 / combo PB).

    Lowers the primary-balance-to-GDP ratio with the Input 6 threshold rule,
    then raises ``primary_expenditure`` so revenues minus spending hit the
    shocked balance.
    """
    years = inputs.years
    first = inputs.first_projection_year
    sd = params.primary_balance_shock_sd if shock_sd is None else shock_sd
    gdp = _align(inputs.gdp_usd, years)
    revenue = _align(inputs.revenues_incl_grants, years)
    expenditure = _align(inputs.primary_expenditure, years)
    pb_pct = 100.0 * (revenue - expenditure) / gdp.replace(0.0, pd.NA)
    hist_avg, hist_sd = _hist_mean_sd(pb_pct, years, first)
    shocked_pct = pb_pct.copy()
    window = _projection_shock_years(years, first)
    if window is not None:
        for year in window:
            base = float(pb_pct.loc[year]) if pd.notna(pb_pct.loc[year]) else 0.0
            shocked_pct.loc[year] = _shocked_growth(
                base, hist_avg, hist_sd, sd, params.threshold_rule
            )
    new_pb = gdp * shocked_pct / 100.0
    new_expenditure = (revenue - new_pb).astype(float)
    return replace(inputs, primary_expenditure=new_expenditure)


def apply_combo_shock(
    inputs: MacroDebtInputs, params: Input6StandardParams
) -> MacroDebtInputs:
    """Apply B6 half-size combination of GDP, PB, exports, other flows, and FX.

    GDP / primary balance / exports / transfers / FDI use half-size Input 6
    magnitudes. FX levels are scaled from the second projection year by the
    half-size depreciation, and the GDP deflator picks up
    ``passthrough × (baseline NC depreciation − shock size)`` in that year
    (B6 ``E51`` FX term) without the full B5 ``(1 − passthrough) × dep`` rewrite.
    """
    out = apply_real_gdp_shock(
        inputs,
        params,
        shock_sd=params.combo_gdp_shock_sd,
        inflation_elasticity=params.inflation_elasticity,
    )
    out = apply_primary_balance_shock(
        out,
        params,
        shock_sd=params.combo_primary_balance_shock_sd,
    )
    out = apply_exports_shock(
        out,
        params,
        shock_sd=params.combo_exports_shock_sd,
        gdp_elasticity=params.exports_gdp_elasticity,
    )
    out = apply_other_flows_shock(
        out,
        params,
        transfers_sd=params.combo_transfers_shock_sd,
        fdi_sd=params.combo_fdi_shock_sd,
    )

    years = out.years
    first = out.first_projection_year
    dep = params.combo_fx_depreciation_pct
    passthrough = params.fx_passthrough if params.interactions_on else 0.0
    proj = [y for y in years if y >= first]
    shock_year = proj[1] if len(proj) >= 2 else (proj[0] if proj else None)

    fx_eop = _align(out.fx_eop, years).copy()
    fx_pa = _align(out.fx_pa, years).copy()
    factor = 1.0 + dep / 100.0
    if shock_year is not None:
        for year in years:
            if year >= shock_year:
                fx_eop.loc[year] = float(fx_eop.loc[year]) * factor
                fx_pa.loc[year] = float(fx_pa.loc[year]) * factor

    # Baseline NC depreciation (Macro R114) for the FX term in B6 E51.
    baseline_dep = depreciation_of_nc_pct(inputs)
    real_g = _growth_pct(out.gdp_constant, years)
    deflator_g = _growth_pct(out.gdp_usd / out.gdp_constant.replace(0.0, pd.NA), years)
    if shock_year is not None and shock_year in deflator_g.index:
        base_nc_dep = (
            float(baseline_dep.loc[shock_year])
            if shock_year in baseline_dep.index
            and pd.notna(baseline_dep.loc[shock_year])
            else 0.0
        )
        deflator_g.loc[shock_year] = float(deflator_g.loc[shock_year]) + passthrough * (
            base_nc_dep - dep
        )

    gdp_usd = _align(out.gdp_usd, years).copy()
    # Rebuild from the year before the FX shock so prior combo GDP is kept.
    rebuild_from = shock_year if shock_year is not None else first
    for year in years:
        if rebuild_from is None or year < rebuild_from:
            continue
        rg = float(real_g.loc[year]) if pd.notna(real_g.loc[year]) else 0.0
        dg = float(deflator_g.loc[year]) if pd.notna(deflator_g.loc[year]) else 0.0
        gdp_usd.loc[year] = (
            float(gdp_usd.loc[year - 1]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
        )

    return replace(
        out,
        fx_eop=fx_eop.astype(float),
        fx_pa=fx_pa.astype(float),
        gdp_usd=gdp_usd.astype(float),
    )


def depreciation_of_nc_pct(inputs: MacroDebtInputs) -> pd.Series:
    """Macro R114-style NC depreciation (%) from FX(pa)."""
    years = inputs.years
    fx = _align(inputs.fx_pa, years)
    dollar_per_nc = (1.0 / fx.replace(0.0, pd.NA)).astype(float)
    prior = dollar_per_nc.shift(1)
    return (-100.0 * (dollar_per_nc / prior.replace(0.0, pd.NA) - 1.0)).astype(float)


def real_depreciation_pct(
    *,
    nominal_dep: float,
    foreign_deflator_growth: float,
    lcu_deflator_growth: float,
    passthrough: float,
    real_growth_gap: float = 0.0,
    inflation_elasticity: float = 0.0,
) -> float:
    """B5/B6 E43 real depreciation implied by a nominal FX shock.

    Excel: `(100+dep)*(100+Macro R112) / (100+Macro R109 + passthrough*dep
    - (g_baseline - g_shock)*inflation elasticity) - 100`. Combo subtracts
    the real-growth gap term; B5 has `g_baseline = g_shock` so it is zero.
    """
    denom = (
        100.0
        + lcu_deflator_growth
        + passthrough * nominal_dep
        - real_growth_gap * inflation_elasticity
    )
    if denom == 0.0:
        return 0.0
    return (100.0 + nominal_dep) * (100.0 + foreign_deflator_growth) / denom - 100.0
