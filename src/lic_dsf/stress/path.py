"""Shocked macro path layer: Input 6 shocks only, no ResFin/ratios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from lic_dsf.pv.macro_debt.book import MacroDebtBook
from lic_dsf.stress.context import StressContext
from lic_dsf.stress.spec import ScenarioSpec
from lic_dsf.stress.types import ThresholdRule


@dataclass(frozen=True, slots=True)
class ShockMetadata:
    """Descriptors for the applied Input 6 shock window and flags."""

    shock_window_years: tuple[int, int]
    fx_depreciation_pct: float
    threshold_rule: ThresholdRule
    interactions_on: bool
    exports_shocked_in_levels: bool = False
    # Excel C4_Market_financing R94: DS/revenue uses baseline USD revenues
    # (baseline rev/GDP × baseline GDP), not FX-shocked revenues.
    ds_revenue_uses_baseline: bool = False
    # Excel C3_commodity_prices_pub R54 LCU deflator path (AA69 + close fade).
    lcu_deflator_growth: pd.Series | None = None
    # Excel C3 R20 divides baseline exp by B1_GDP_pub R41 (template quirk).
    primary_exp_gdp_denominator: pd.Series | None = None


@dataclass(frozen=True, slots=True)
class ShockedMacroPath:
    """Baseline vs shocked Macro books after an Input 6 path shock.

    Exposes denominators only. No ResFin overlays and no sustainability ratios.
    """

    baseline: MacroDebtBook
    shocked: MacroDebtBook
    metadata: ShockMetadata

    @property
    def years(self) -> tuple[int, ...]:
        return self.shocked.inputs.years

    @property
    def first_projection_year(self) -> int:
        return self.shocked.inputs.first_projection_year

    def gdp_usd(self) -> pd.Series:
        return self.shocked.gdp_usd()

    def gdp_lcu(self) -> pd.Series:
        """Baseline-style LCU GDP (``gdp_usd × fx_pa``). Public B1 R41 uses GFN GDP."""
        return self.shocked.gdp_lcu()

    def exports(self) -> pd.Series:
        return self.shocked.exports()

    def revenues_excl_grants(self) -> pd.Series:
        return self.shocked.revenues_excl_grants()

    def gdp_growth_pct(self) -> pd.Series:
        """Real GDP growth (%) on the shocked path (B-sheet R50)."""
        return self.shocked.real_gdp_growth()


class MacroShock(Protocol):
    """Apply one ``ShockKind`` to a :class:`StressContext`."""

    def apply(self, ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath:
        """Return shocked macro path for ``spec``."""


def projection_shock_window(
    years: tuple[int, ...], first_projection_year: int
) -> tuple[int, int]:
    """Return the second and third projection years (Excel Input 6 shock window)."""
    proj = [y for y in years if y >= first_projection_year]
    if len(proj) < 3:
        raise ValueError(
            f"need at least 3 projection years for shock window; got {proj!r}"
        )
    return proj[1], proj[2]
