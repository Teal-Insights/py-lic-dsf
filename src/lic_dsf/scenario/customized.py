"""Customized Scenario shock applicator for Chart Data registration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pandas as pd

from lic_dsf.rating.chart_data import ChartDataRegistry

if TYPE_CHECKING:
    from lic_dsf.pv.macro_debt.types import MacroDebtInputs


@dataclass(frozen=True, slots=True)
class CustomizedScenarioSpec:
    """Named customized scenario with percent-of-GDP deltas.

    Attributes:
        name: Scenario display name.
        short_name: Short id for Chart Data registration.
        revenue_delta_pct_gdp: Optional delta to revenues/GDP (ppt).
        primary_expenditure_delta_pct_gdp: Optional delta to primary exp/GDP.
        real_growth_delta: Optional ppt add to real growth.
        export_delta_pct_gdp: Optional ppt add to exports/GDP.
        include_in_charts: Whether to register the path in Chart Data.
    """

    name: str
    short_name: str = "custom"
    revenue_delta_pct_gdp: pd.Series | None = None
    primary_expenditure_delta_pct_gdp: pd.Series | None = None
    real_growth_delta: pd.Series | None = None
    export_delta_pct_gdp: pd.Series | None = None
    include_in_charts: bool = True


def apply_customized_deltas(
    inputs: MacroDebtInputs,
    spec: CustomizedScenarioSpec,
) -> MacroDebtInputs:
    """Apply customized scenario deltas onto a Macro inputs copy.

    Deltas are in ppt of GDP and converted to levels using baseline GDP_USD
    (exports) or GDP_LCU proxy ``GDP_USD × FX`` (fiscal). Real growth deltas
    are applied to ``gdp_constant`` via a cumulative growth adjustment.

    Args:
        inputs: Baseline Macro debt inputs.
        spec: Customized scenario deltas.

    Returns:
        New `MacroDebtInputs` with shocked series.
    """
    years = list(inputs.years)
    gdp_usd = inputs.gdp_usd.reindex(years).astype(float)
    fx = inputs.fx_pa.reindex(years).astype(float)
    gdp_lcu = gdp_usd * fx

    revenues = inputs.revenues_incl_grants.reindex(years).astype(float)
    primary_exp = inputs.primary_expenditure.reindex(years).astype(float)
    exports = inputs.exports.reindex(years).astype(float)
    gdp_const = inputs.gdp_constant.reindex(years).astype(float)

    if spec.revenue_delta_pct_gdp is not None:
        delta = spec.revenue_delta_pct_gdp.reindex(years).fillna(0.0) / 100.0
        revenues = revenues + delta * gdp_lcu
    if spec.primary_expenditure_delta_pct_gdp is not None:
        delta = (
            spec.primary_expenditure_delta_pct_gdp.reindex(years).fillna(0.0) / 100.0
        )
        primary_exp = primary_exp + delta * gdp_lcu
    if spec.export_delta_pct_gdp is not None:
        delta = spec.export_delta_pct_gdp.reindex(years).fillna(0.0) / 100.0
        exports = exports + delta * gdp_usd
    if spec.real_growth_delta is not None:
        # Scale constant-price GDP by cumulative (1 + Δg/100).
        growth_delta = spec.real_growth_delta.reindex(years).fillna(0.0) / 100.0
        scale = (1.0 + growth_delta).cumprod()
        gdp_const = gdp_const * scale

    return replace(
        inputs,
        revenues_incl_grants=revenues,
        primary_expenditure=primary_exp,
        exports=exports,
        gdp_constant=gdp_const,
    )


def register_custom_path(
    registry: ChartDataRegistry,
    *,
    indicator: str,
    values: pd.Series,
    spec: CustomizedScenarioSpec,
) -> None:
    """Register a customized scenario ratio path in Chart Data.

    Args:
        registry: Chart Data path registry.
        indicator: Indicator id.
        values: Ratio series under the customized scenario.
        spec: Scenario metadata.
    """
    if not spec.include_in_charts:
        return
    registry.register_series(
        indicator,
        spec.short_name,
        values,
        is_baseline=False,
        is_shock=True,
    )
