"""Tailored (C1–C4) and customized A2 stress shocks as Python runners.

Parameters are read from Input 6 Tailored Tests / Customized Scenario-External;
the SUT never reads materialized B-sheet ratios.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.pv.macro_debt.types import MacroDebtInputs
from lic_dsf.scenario.customized import CustomizedScenarioSpec
from lic_dsf.stress.macro_shocks import apply_fx_depreciation_shock
from lic_dsf.stress.public import StressPublicBook
from lic_dsf.stress.scenario import StressExternalBook
from lic_dsf.stress.types import Input6StandardParams


@dataclass(frozen=True, slots=True)
class TailoredParams:
    """Resolved Input 6 tailored-test sizes and On/Off flags."""

    natural_disaster: bool
    commodity: bool
    market: bool
    disaster_shock_pct_gdp: float
    commodity_close_years: float
    commodity_adj_share: float
    commodity_avg_price_shock: float
    market_cost_bps: float
    market_fx_depreciation_pct: float
    cl_shock_pct_gdp: float = 10.0  # Excel AA60 / Input 2 F25; loader overrides
    # C4 maturity/grace shorten (Input 6 H54–H56).
    market_maturity_cap: float = 5.0
    market_maturity_factor: float = 2.0 / 3.0
    market_grace_factor: float = 2.0 / 3.0
    # C3 real-GDP / revenue ppt shocks (Input 6 L26 / L27).
    commodity_gdp_shock_ppt: float = 0.0
    commodity_revenue_drop_ppt: float = 0.0


def _one_off_flow(
    inputs: MacroDebtInputs,
    pct_gdp: float,
    *,
    year_offset: int = 1,
    field: str = "contingent_liabilities",
) -> MacroDebtInputs:
    """Add ``pct_gdp`` of GDP as a one-off flow in projection year ``offset``."""
    years = inputs.years
    first = inputs.first_projection_year
    proj = [y for y in years if y >= first]
    if len(proj) <= year_offset:
        return inputs
    year = proj[year_offset]
    gdp = inputs.gdp_usd.reindex(list(years)).astype(float)
    fx = inputs.fx_pa.reindex(list(years)).astype(float)
    bump = float(gdp.loc[year]) * float(fx.loc[year]) * pct_gdp / 100.0
    series = getattr(inputs, field).reindex(list(years)).fillna(0.0).astype(float)
    series.loc[year] = float(series.loc[year]) + bump
    return replace(inputs, **{field: series})


def apply_combined_cl_shock(inputs: MacroDebtInputs, params: TailoredParams) -> MacroDebtInputs:
    """C1: one-off contingent-liability flow in the second projection year."""
    return _one_off_flow(inputs, params.cl_shock_pct_gdp, year_offset=1)


def apply_natural_disaster_shock(
    inputs: MacroDebtInputs, params: TailoredParams
) -> MacroDebtInputs:
    """C2: one-off external PPG/GDP shock in the second projection year."""
    return _one_off_flow(
        inputs,
        params.disaster_shock_pct_gdp,
        year_offset=1,
        field="other_debt_creating_flows",
    )


def apply_commodity_price_shock(
    inputs: MacroDebtInputs,
    params: TailoredParams,
    input6: Input6StandardParams,
) -> MacroDebtInputs:
    """C3: one-year export price shock, then fade the exports/GDP gap.

    Excel ``C3_Commodity prices_ext``:

    * R111 / exports: full shock in projection year 2 only; later years fade
      the **exports/GDP gap** vs baseline over ``commodity_close_years``.
    * R50 real GDP: subtract ``commodity_gdp_shock_ppt`` for years 2–4, then
      fade that ppt through the close window (not B3 export-growth ε).
    """
    years = list(inputs.years)
    first = inputs.first_projection_year
    proj = [y for y in years if y >= first]
    exports_b = inputs.exports.reindex(years).astype(float)
    gdp_b = inputs.gdp_usd.reindex(years).astype(float)
    share = float(params.commodity_adj_share)
    factor = 1.0 + share * share * float(params.commodity_avg_price_shock)
    close = max(int(params.commodity_close_years), 1)
    gdp_ppt = float(params.commodity_gdp_shock_ppt)
    rev_ppt = float(params.commodity_revenue_drop_ppt)

    exports = exports_b.copy()
    # Shock only the second projection year (Excel E111).
    if len(proj) >= 2:
        y1 = proj[1]
        exports.loc[y1] = float(exports_b.loc[y1]) * factor

    # Real GDP path: baseline − AA65 for years 2–4, then fade.
    real_g = _growth_pct_local(inputs.gdp_constant, years)
    shocked_real = real_g.copy()
    for i, year in enumerate(proj):
        if i == 0:
            continue
        base_rg = float(real_g.loc[year]) if pd.notna(real_g.loc[year]) else 0.0
        if i <= 3:
            shocked_real.loc[year] = base_rg - gdp_ppt
        elif i < 2 + close:
            # Fade after the three full-shock GDP years (Excel R50 2028+).
            n = i - 3
            denom = max(close - 2, 1)
            shocked_real.loc[year] = base_rg - gdp_ppt * max(close - 2 - n, 0) / denom
        else:
            shocked_real.loc[year] = base_rg

    from lic_dsf.stress.macro_shocks import (
        _align,
        _hold_nongrant_revenue_to_gdp,
        _rebuild_levels_from_growth,
    )

    gdp_constant = _rebuild_levels_from_growth(
        inputs.gdp_constant, tuple(years), first, shocked_real
    )
    deflator_g = _growth_pct_local(
        inputs.gdp_usd / inputs.gdp_constant.replace(0.0, pd.NA), years
    )
    usd_g = _growth_pct_local(inputs.gdp_usd, years)
    for year in years:
        if year == years[0]:
            continue
        if pd.isna(deflator_g.loc[year]) and pd.notna(usd_g.loc[year]):
            rg = float(real_g.loc[year]) if pd.notna(real_g.loc[year]) else 0.0
            deflator_g.loc[year] = 100.0 * (
                (1.0 + float(usd_g.loc[year]) / 100.0) / (1.0 + rg / 100.0) - 1.0
            )
    # Excel C3_Commodity prices_ext R51: reduce the USD deflator in the shock
    # year by the commodity-price interaction, then close that deflator gap
    # linearly over AA63 years. This GDP path also drives external R92, which
    # caps the external leg of the C3 public ResFin split.
    if len(proj) >= 2:
        shock_y = proj[1]
        ref_y = proj[0]
        x_gdp = (
            float(exports_b.loc[ref_y]) / float(gdp_b.loc[ref_y]) * 100.0
            if float(gdp_b.loc[ref_y])
            else 0.0
        )
        interaction = (
            float(params.commodity_adj_share)
            * float(params.commodity_avg_price_shock)
            * x_gdp
            / 100.0
        )
        deflator_g.loc[shock_y] = float(deflator_g.loc[shock_y]) * (
            1.0 + interaction
        )
        gap0 = (
            float(_growth_pct_local(
                inputs.gdp_usd / inputs.gdp_constant.replace(0.0, pd.NA), years
            ).loc[shock_y])
            - float(deflator_g.loc[shock_y])
        )
        for i, year in enumerate(proj):
            if i <= 1:
                continue
            k = i - 1
            if k < close:
                deflator_g.loc[year] = float(deflator_g.loc[year]) - (
                    gap0 * (close - k) / close
                )
    gdp_usd = _align(inputs.gdp_usd, tuple(years)).copy()
    for year in years:
        if year < first:
            continue
        prior = year - 1
        rg = float(shocked_real.loc[year]) if pd.notna(shocked_real.loc[year]) else 0.0
        dg = float(deflator_g.loc[year]) if pd.notna(deflator_g.loc[year]) else 0.0
        gdp_usd.loc[year] = (
            float(gdp_usd.loc[prior]) * (1.0 + rg / 100.0) * (1.0 + dg / 100.0)
        )

    # Fade exports/GDP gap after the shock year. Through ``close`` years Excel
    # interpolates R19 toward baseline; afterward R111 grows from the last
    # faded level at baseline export growth (not a jump back to baseline R19).
    if len(proj) >= 2:
        y1 = proj[1]
        base_r19_shock = (
            float(exports_b.loc[y1]) / float(gdp_b.loc[y1]) * 100.0
            if float(gdp_b.loc[y1])
            else 0.0
        )
        shock_r19 = (
            float(exports.loc[y1]) / float(gdp_usd.loc[y1]) * 100.0
            if float(gdp_usd.loc[y1])
            else 0.0
        )
        gap0 = base_r19_shock - shock_r19
        for i, year in enumerate(proj):
            if i <= 1:
                continue
            k = i - 1  # 1 at first fade year (2026)
            if k < close:
                fade = (close - k) / close
                base_r19 = (
                    float(exports_b.loc[year]) / float(gdp_b.loc[year]) * 100.0
                    if float(gdp_b.loc[year])
                    else 0.0
                )
                target_r19 = base_r19 - gap0 * fade
                exports.loc[year] = float(gdp_usd.loc[year]) * target_r19 / 100.0
            else:
                prior = year - 1
                prior_x = float(exports.loc[prior])
                prior_b = float(exports_b.loc[prior])
                cur_b = float(exports_b.loc[year])
                growth = (cur_b / prior_b - 1.0) if prior_b else 0.0
                exports.loc[year] = prior_x * (1.0 + growth)

    shortfall = exports_b - exports
    current_account = inputs.current_account.reindex(years).astype(float) - shortfall
    revenues = _hold_nongrant_revenue_to_gdp(
        inputs,
        old_gdp_usd=inputs.gdp_usd,
        new_gdp_usd=gdp_usd,
        from_year=first,
    )
    # Optional revenue-drop ppt (Input 6 L27) on non-grant revenue / GDP.
    if rev_ppt and len(proj) >= 2:
        for i, year in enumerate(proj):
            if i == 0:
                continue
            if i <= 3:
                drop = rev_ppt
            elif i < 2 + close:
                n = i - 3
                denom = max(close - 2, 1)
                drop = rev_ppt * max(close - 2 - n, 0) / denom
            else:
                drop = 0.0
            if drop:
                # Reduce revenues by drop ppt of GDP (USD → LCU via fx later in book).
                fx = float(inputs.fx_pa.reindex([year]).fillna(1.0).loc[year])
                revenues.loc[year] = float(revenues.loc[year]) - (
                    float(gdp_usd.loc[year]) * fx * drop / 100.0
                )

    return replace(
        inputs,
        exports=exports.astype(float),
        gdp_usd=gdp_usd.astype(float),
        gdp_constant=gdp_constant.astype(float),
        current_account=current_account.astype(float),
        revenues_incl_grants=revenues.astype(float),
    )


def commodity_public_lcu_deflator_growth(
    baseline: MacroDebtBook,
    params: TailoredParams,
) -> pd.Series:
    """Excel ``C3_commodity_prices_pub`` R54 LCU deflator growth path.

    * First projection year: baseline deflator.
    * Shock year (proj year 2): ``baseline × (1 + AA69 × hist_X/GDP / 100)``
      where ``AA69 = adj_share × avg_price_shock`` and hist X/GDP is the
      pre-projection exports/GDP ratio (Excel ``C3_Commodity prices_ext`` D19).
    * Later years: fade ``(baseline[proj3] − shock_year_deflator)`` over
      ``commodity_close_years`` (Excel R54 2026+).
    """
    years = list(baseline.inputs.years)
    first = baseline.inputs.first_projection_year
    proj = [y for y in years if y >= first]
    base_lcu = baseline.gdp_lcu().reindex(years).astype(float)
    base_const = baseline.gdp_constant().reindex(years).astype(float).replace(
        0.0, pd.NA
    )
    defl_b = _growth_pct_local(base_lcu / base_const, years)
    out = defl_b.copy()
    if len(proj) < 2:
        return out.astype(float)

    aa69 = float(params.commodity_adj_share) * float(
        params.commodity_avg_price_shock
    )
    close = max(int(params.commodity_close_years), 1)
    # Excel C3_Commodity prices_ext!D19: exports/GDP in the first projection
    # year (ext sheet places that year in column D).
    ref_year = proj[0]
    x_gdp = (
        float(baseline.exports().loc[ref_year])
        / float(baseline.gdp_usd().loc[ref_year])
        * 100.0
        if float(baseline.gdp_usd().loc[ref_year])
        else 0.0
    )
    factor = 1.0 + aa69 * x_gdp / 100.0
    shock_y = proj[1]
    out.loc[shock_y] = float(defl_b.loc[shock_y]) * factor
    if len(proj) < 3:
        return out.astype(float)
    fade_anchor = proj[2]
    gap0 = float(defl_b.loc[fade_anchor]) - float(out.loc[shock_y])
    for i, year in enumerate(proj):
        if i <= 1:
            continue
        k = i - 1
        if k < close:
            out.loc[year] = float(defl_b.loc[year]) - gap0 * (close - k) / close
        else:
            out.loc[year] = float(defl_b.loc[year])
    return out.astype(float)


def _growth_pct_local(level: pd.Series, years: list[int]) -> pd.Series:
    aligned = level.reindex(years).astype(float)
    prior = aligned.shift(1)
    return (100.0 * (aligned / prior.replace(0.0, pd.NA) - 1.0)).astype(float)


def apply_market_financing_shock(
    inputs: MacroDebtInputs,
    params: TailoredParams,
    input6: Input6StandardParams,
) -> MacroDebtInputs:
    """C4: temporary FX depreciation (market-financing cost proxy).

    Reuses the B5 FX/GDP deflator pass-through for stressed GDP (Excel
    ``C4_Market_financing`` R12/R15). Output 3-1 DS/revenue still uses
    *baseline* USD revenues (sheet R94); that switch lives on
    ``ShockMetadata.ds_revenue_uses_baseline``, not in this macro path.
    """
    shocked = replace(
        input6,
        fx_depreciation_pct=params.market_fx_depreciation_pct,
    )
    return apply_fx_depreciation_shock(inputs, shocked)


def run_tailored_external_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
    input6: Input6StandardParams,
    *,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> dict[str, StressExternalBook]:
    """A2 + C1 always; C2–C4 only when Input 6 marks them applicable."""
    from lic_dsf.stress.facade import run_tailored_external_stress as _run

    return _run(
        macro,
        external,
        residual_params,
        params,
        input6,
        custom_spec=custom_spec,
    )


def run_a2_custom_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    spec: CustomizedScenarioSpec | None,
) -> StressPublicBook:
    """Run the A2 customized public scenario."""
    from lic_dsf.stress.facade import _neutral_input6, run_public_scenario

    return run_public_scenario(
        "A2_Custom",
        macro,
        external,
        _neutral_input6(),
        residual_params,
        custom_spec=spec,
    )


def run_c1_combined_cl_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
) -> StressPublicBook:
    """Run the C1 combined CL public path."""
    from lic_dsf.stress.facade import _neutral_input6, run_public_scenario

    return run_public_scenario(
        "C1_CombinedCL",
        macro,
        external,
        _neutral_input6(),
        residual_params,
        tailored=params,
    )


def run_tailored_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
    input6: Input6StandardParams,
    *,
    custom_spec: CustomizedScenarioSpec | None = None,
) -> dict[str, StressPublicBook]:
    """A2 + C1 always; C2–C4 when Input 6 marks them applicable."""
    from lic_dsf.stress.facade import run_tailored_public_stress as _run

    return _run(
        macro,
        external,
        residual_params,
        params,
        input6,
        custom_spec=custom_spec,
    )
