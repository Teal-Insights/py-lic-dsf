"""Tailored (C1–C4) and customized A2 stress shocks as Python runners.

These replace ``CachedStressExternalBook`` as the Output 3-x SUT. Parameters
are read from Input 6 Tailored Tests / Customized Scenario-External; the
SUT never reads materialized B-sheet ratios.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.residual import ResidualFinancingParams
from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.pv.macro_debt.types import MacroDebtInputs
from lic_dsf.scenario.customized import CustomizedScenarioSpec, apply_customized_deltas
from lic_dsf.stress.public import StressPublicBook, _run_public_stress
from lic_dsf.stress.scenario import StressExternalBook, _build_book, _converged_external_gap
from lic_dsf.stress.shocks import apply_fx_depreciation_shock
from lic_dsf.stress.types import Input6StandardParams
from lic_dsf.stress.workbook import _prefer_user, _tailored_applicability


def _safe_prefer(default: object, user: object, fallback: float = 0.0) -> float:
    try:
        return _prefer_user(default, user)
    except ValueError:
        return fallback


_TAILORED_SHEET = "Input 6 - Tailored Tests"
_CUSTOMIZED_EXTERNAL_SHEET = "Customized Scenario-External"


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
    cl_shock_pct_gdp: float = 10.0


def load_tailored_params(path: str | Path) -> TailoredParams:
    """Load tailored-test flags and sizes from Input 6 - Tailored Tests."""
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = workbook[_TAILORED_SHEET]
        flags = _tailored_applicability(ws)
        avg_shock = _safe_prefer(ws.cell(46, 7).value, ws.cell(46, 8).value)
        adj_share = _safe_prefer(ws.cell(30, 7).value, ws.cell(30, 8).value)
        return TailoredParams(
            natural_disaster=flags["C2_NaturalDisaster"],
            commodity=flags["C3_Commodity"],
            market=flags["C4_Market"],
            disaster_shock_pct_gdp=_safe_prefer(
                ws.cell(21, 7).value, ws.cell(21, 8).value
            ),
            commodity_close_years=_safe_prefer(
                ws.cell(26, 7).value, ws.cell(26, 8).value
            ),
            commodity_adj_share=adj_share,
            commodity_avg_price_shock=avg_shock,
            market_cost_bps=_safe_prefer(ws.cell(52, 7).value, ws.cell(52, 8).value),
            market_fx_depreciation_pct=_safe_prefer(
                ws.cell(58, 7).value, ws.cell(58, 8).value
            ),
        )
    finally:
        workbook.close()


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
    inputs: MacroDebtInputs, params: TailoredParams
) -> MacroDebtInputs:
    """C3: scale exports by commodity share × average price shock, then fade."""
    years = list(inputs.years)
    first = inputs.first_projection_year
    proj = [y for y in years if y >= first]
    exports = inputs.exports.reindex(years).astype(float)
    factor = 1.0 + params.commodity_adj_share * params.commodity_avg_price_shock
    close = max(int(params.commodity_close_years), 1)
    for i, year in enumerate(proj):
        if i == 0:
            continue
        if i <= 2:
            scale = factor
        elif i < 2 + close:
            t = (i - 2) / close
            scale = factor + (1.0 - factor) * t
        else:
            scale = 1.0
        exports.loc[year] = float(exports.loc[year]) * scale
    return replace(inputs, exports=exports)


def apply_market_financing_shock(
    inputs: MacroDebtInputs,
    params: TailoredParams,
    input6: Input6StandardParams,
) -> MacroDebtInputs:
    """C4: temporary FX depreciation (market-financing cost proxy)."""
    shocked = replace(
        input6,
        fx_depreciation_pct=params.market_fx_depreciation_pct,
    )
    return apply_fx_depreciation_shock(inputs, shocked)


def _external_runner(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    shocked_inputs: MacroDebtInputs,
    scenario_id,
    *,
    fx_depreciation_pct: float = 0.0,
) -> StressExternalBook:
    shocked_macro = MacroDebtBook(inputs=shocked_inputs, external=external)
    gap = _converged_external_gap(macro, shocked_macro, external, residual_params)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked_macro,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id=scenario_id,
        fx_depreciation_pct=fx_depreciation_pct,
    )


def run_c1_combined_cl_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
) -> StressExternalBook:
    """C1 combined contingent-liability external path."""
    return _external_runner(
        macro,
        external,
        residual_params,
        apply_combined_cl_shock(macro.inputs, params),
        "C1_CombinedCL",
    )


def run_c2_natural_disaster_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
) -> StressExternalBook:
    """C2 natural-disaster external path (caller must check applicability)."""
    return _external_runner(
        macro,
        external,
        residual_params,
        apply_natural_disaster_shock(macro.inputs, params),
        "C2_NaturalDisaster",
    )


def run_c3_commodity_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
) -> StressExternalBook:
    """C3 commodity-price external path."""
    return _external_runner(
        macro,
        external,
        residual_params,
        apply_commodity_price_shock(macro.inputs, params),
        "C3_Commodity",
    )


def run_c4_market_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
    input6: Input6StandardParams,
) -> StressExternalBook:
    """C4 market-financing external path."""
    return _external_runner(
        macro,
        external,
        residual_params,
        apply_market_financing_shock(macro.inputs, params, input6),
        "C4_Market",
        fx_depreciation_pct=params.market_fx_depreciation_pct,
    )


def run_a2_custom_external(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    spec: CustomizedScenarioSpec | None,
) -> StressExternalBook:
    """A2 customized scenario; baseline path when ``spec`` is None or off."""
    if spec is None:
        years = macro.inputs.years
        gap = pd.Series(0.0, index=list(years), dtype=float)
        return _build_book(
            baseline_macro=macro,
            shocked_macro=macro,
            external=external,
            residual_params=residual_params,
            gap=gap,
            scenario_id="A2_Custom",
        )
    shocked = MacroDebtBook(
        inputs=apply_customized_deltas(macro.inputs, spec), external=external
    )
    gap = _converged_external_gap(macro, shocked, external, residual_params)
    return _build_book(
        baseline_macro=macro,
        shocked_macro=shocked,
        external=external,
        residual_params=residual_params,
        gap=gap,
        scenario_id="A2_Custom",
    )


def load_customized_spec(path: str | Path) -> CustomizedScenarioSpec | None:
    """Load A2 spec when Customized Scenario-External D3 is Yes; else None."""
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[_CUSTOMIZED_EXTERNAL_SHEET]
        on = str(ws.cell(3, 4).value or "").strip().lower() == "yes"
        if not on:
            return None
        title = str(ws.cell(2, 4).value or "Custom").strip()
        return CustomizedScenarioSpec(name=title, short_name="A2")
    finally:
        wb.close()


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
    out: dict[str, StressExternalBook] = {
        "A2_Custom": run_a2_custom_external(
            macro, external, residual_params, custom_spec
        ),
        "C1_CombinedCL": run_c1_combined_cl_external(
            macro, external, residual_params, params
        ),
    }
    if params.natural_disaster:
        out["C2_NaturalDisaster"] = run_c2_natural_disaster_external(
            macro, external, residual_params, params
        )
    if params.commodity:
        out["C3_Commodity"] = run_c3_commodity_external(
            macro, external, residual_params, params
        )
    if params.market:
        out["C4_Market"] = run_c4_market_external(
            macro, external, residual_params, params, input6
        )
    return out


def run_c1_combined_cl_public(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
) -> StressPublicBook:
    """C1 combined CL public path."""
    shocked = MacroDebtBook(
        inputs=apply_combined_cl_shock(macro.inputs, params), external=external
    )
    return _run_public_stress(
        macro, external, residual_params, shocked, "C1_CombinedCL_pub"
    )


def run_tailored_public_stress(
    macro: MacroDebtBook,
    external: ExternalDebtBook,
    residual_params: ResidualFinancingParams,
    params: TailoredParams,
    input6: Input6StandardParams,
) -> dict[str, StressPublicBook]:
    """Public C1 always; C2–C4 when applicable."""
    out: dict[str, StressPublicBook] = {
        "C1_CombinedCL": run_c1_combined_cl_public(
            macro, external, residual_params, params
        ),
    }
    if params.natural_disaster:
        shocked = MacroDebtBook(
            inputs=apply_natural_disaster_shock(macro.inputs, params),
            external=external,
        )
        out["C2_NaturalDisaster"] = _run_public_stress(
            macro, external, residual_params, shocked, "C2_NaturalDisaster_pub"
        )
    if params.commodity:
        shocked = MacroDebtBook(
            inputs=apply_commodity_price_shock(macro.inputs, params),
            external=external,
        )
        out["C3_Commodity"] = _run_public_stress(
            macro, external, residual_params, shocked, "C3_Commodity_pub"
        )
    if params.market:
        shocked = MacroDebtBook(
            inputs=apply_market_financing_shock(macro.inputs, params, input6),
            external=external,
        )
        out["C4_Market"] = _run_public_stress(
            macro, external, residual_params, shocked, "C4_Market_pub"
        )
    return out
