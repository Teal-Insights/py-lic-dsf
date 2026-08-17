"""Output 5-2 market-financing pressures module."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class MarketFinancingInputs:
    """Inputs for the market-financing risk module.

    Attributes:
        market_access: Whether the country has market access (Input 1).
        gfn_to_gdp: Gross financing needs / GDP over the near term.
        embi_spread: Latest EMBI spread (bps), if available.
        gfn_benchmark: GFN/GDP benchmark (default 14% for market LICs).
        embi_benchmark: EMBI spread benchmark (bps, default 570).
    """

    market_access: bool
    gfn_to_gdp: pd.Series
    embi_spread: float | None = None
    gfn_benchmark: float = 14.0
    embi_benchmark: float = 570.0


@dataclass(frozen=True, slots=True)
class MarketFinancingResult:
    """Market module breach flags."""

    applicable: bool
    max_gfn_to_gdp: float | None
    gfn_breach: bool
    embi_breach: bool
    heightened_liquidity_needs: bool


def assess_market_financing(inputs: MarketFinancingInputs) -> MarketFinancingResult:
    """Assess market-financing pressure indicators (Output 5-2).

    Args:
        inputs: Market-access flag, GFN path, optional EMBI.

    Returns:
        Breach flags; ``applicable=False`` when market access is off.
    """
    if not inputs.market_access:
        return MarketFinancingResult(
            applicable=False,
            max_gfn_to_gdp=None,
            gfn_breach=False,
            embi_breach=False,
            heightened_liquidity_needs=False,
        )
    gfn = inputs.gfn_to_gdp.astype(float).dropna()
    max_gfn = float(gfn.max()) if len(gfn) else 0.0
    gfn_breach = max_gfn > inputs.gfn_benchmark
    embi_breach = (
        inputs.embi_spread is not None and inputs.embi_spread > inputs.embi_benchmark
    )
    return MarketFinancingResult(
        applicable=True,
        max_gfn_to_gdp=max_gfn,
        gfn_breach=gfn_breach,
        embi_breach=embi_breach,
        heightened_liquidity_needs=gfn_breach or embi_breach,
    )


def market_panel(result: MarketFinancingResult) -> pd.DataFrame:
    """Output 5-2 shaped panel."""
    return pd.Series(
        {
            "Applicable": result.applicable,
            "Max GFN / GDP": result.max_gfn_to_gdp,
            "GFN breach": result.gfn_breach,
            "EMBI breach": result.embi_breach,
            "Heightened liquidity needs": result.heightened_liquidity_needs,
        },
        name="Output 5-2",
    ).to_frame()
