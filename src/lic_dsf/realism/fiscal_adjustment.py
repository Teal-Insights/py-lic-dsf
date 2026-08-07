"""Realism 4 — planned fiscal adjustment vs LIC program histogram."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.realism.types import LicProgramDistribution

# Embedded LIC program histogram from Excel ``Realism 4 - Fiscal adjustment``
# (Fund-supported LIC programs since 1990, excluding emergency financing).
# Rows R23–R50: category 1 is the open left bin (freq 23); then -4.5 … 8, more.
_DEFAULT_BINS: tuple[float | str, ...] = (
    -4.5,  # category 1 open left uses display edge -4.5 for charting
    -4.5,
    -4.0,
    -3.5,
    -3.0,
    -2.5,
    -2.0,
    -1.5,
    -1.0,
    -0.5,
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
    5.5,
    6.0,
    6.5,
    7.0,
    7.5,
    8.0,
    "more",
)

_DEFAULT_FREQ: tuple[float, ...] = (
    23,
    2,
    5,
    8,
    6,
    6,
    9,
    11,
    14,
    21,
    15,
    13,
    14,
    9,
    10,
    8,
    9,
    13,
    4,
    1,
    6,
    6,
    0,
    0,
    3,
    2,
    0,
    9,
)

_DEFAULT_PCT: tuple[float, ...] = (
    10.13215859030837,
    0.881057268722467,
    2.2026431718061676,
    3.524229074889868,
    2.643171806167401,
    2.643171806167401,
    3.9647577092511015,
    4.845814977973569,
    6.167400881057269,
    9.251101321585903,
    6.607929515418502,
    5.726872246696035,
    6.167400881057269,
    3.9647577092511015,
    4.405286343612335,
    3.524229074889868,
    3.9647577092511015,
    5.726872246696035,
    1.762114537444934,
    0.4405286343612335,
    2.643171806167401,
    2.643171806167401,
    0.0,
    0.0,
    1.3215859030837005,
    0.881057268722467,
    0.0,
    3.9647577092511015,
)

_DEFAULT_CUM: tuple[float, ...] = (
    10.13215859030837,
    11.013215859030836,
    13.215859030837004,
    16.740088105726873,
    19.383259911894275,
    22.026431718061676,
    25.99118942731278,
    30.837004405286347,
    37.00440528634361,
    46.25550660792952,
    52.86343612334802,
    58.590308370044056,
    64.75770925110132,
    68.72246696035242,
    73.12775330396475,
    76.65198237885463,
    80.61674008810573,
    86.34361233480176,
    88.10572687224669,
    88.54625550660792,
    91.18942731277532,
    93.83259911894272,
    93.83259911894272,
    93.83259911894272,
    95.15418502202643,
    96.0352422907489,
    96.0352422907489,
    100.0,
)

DEFAULT_LIC_PROGRAM_DISTRIBUTION = LicProgramDistribution(
    bins=_DEFAULT_BINS,
    frequencies=_DEFAULT_FREQ,
    percent_of_sample=_DEFAULT_PCT,
    cumulative_percent=_DEFAULT_CUM,
)


def three_year_fiscal_adjustment(primary_deficit_pct: pd.Series) -> pd.Series:
    """Compute 3-year fiscal adjustment (ppt of GDP, (+) = improvement).

    Excel Realism 4 R10: ``PD_{t-3} − PD_t`` where ``PD`` is primary deficit
    % GDP (positive = deficit).

    Args:
        primary_deficit_pct: Primary deficit / GDP series indexed by year.

    Returns:
        Series of 3-year adjustments (NaN where ``t-3`` is unavailable).
    """
    pd_pct = primary_deficit_pct.astype(float).sort_index()
    prior = pd_pct.shift(3)
    return (prior - pd_pct).astype(float)


@dataclass(frozen=True, slots=True)
class FiscalAdjustmentPlacement:
    """Where the projected 3-year adjustment sits in the LIC histogram."""

    adjustment: float
    bin_edge: float | str
    bin_index: int
    category: int
    percent_of_sample: float
    cumulative_percent: float


def place_in_lic_histogram(
    adjustment: float,
    distribution: LicProgramDistribution | None = None,
) -> FiscalAdjustmentPlacement:
    """Map a 3-year adjustment into the LIC program histogram bin.

    Excel Realism 4 places the projected adjustment on the matching bin edge
    (e.g. 4.64 → bin 4.5, category 20, height 0.44% of sample).

    Args:
        adjustment: Projected 3-year fiscal adjustment (ppt of GDP).
        distribution: Histogram; defaults to the embedded LIC program table.

    Returns:
        Bin placement metadata for Output 4-2.
    """
    dist = distribution or DEFAULT_LIC_PROGRAM_DISTRIBUTION
    # Skip category-1 open left duplicate at index 0; use edges from index 1.
    numeric: list[tuple[int, float]] = []
    for i, edge in enumerate(dist.bins):
        if i == 0:
            continue
        if isinstance(edge, (int, float)):
            numeric.append((i, float(edge)))

    if adjustment > numeric[-1][1]:
        idx = list(dist.bins).index("more")
        edge: float | str = "more"
    else:
        chosen = numeric[0]
        for i, e in numeric:
            if e <= adjustment:
                chosen = (i, e)
            else:
                break
        idx, edge = chosen

    return FiscalAdjustmentPlacement(
        adjustment=float(adjustment),
        bin_edge=edge,
        bin_index=idx,
        category=idx + 1,  # Excel category is 1-based over R23–R50
        percent_of_sample=float(dist.percent_of_sample[idx]),
        cumulative_percent=float(dist.cumulative_percent[idx]),
    )


def projected_three_year_adjustment(
    primary_deficit_pct: pd.Series,
    first_projection_year: int,
) -> float:
    """Projected 3-yr adjustment evaluated at ``first_projection_year + 2``.

    Excel Realism 4 uses the adjustment in the third projection year (first
    projection year + 2).

    Args:
        primary_deficit_pct: Primary deficit / GDP series.
        first_projection_year: First projection year (Macro / Baseline).

    Returns:
        Scalar 3-year adjustment at the projected horizon.
    """
    adj = three_year_fiscal_adjustment(primary_deficit_pct)
    target = first_projection_year + 2
    if target not in adj.index or pd.isna(adj.loc[target]):
        raise ValueError(f"3-year adjustment unavailable for projection year {target}")
    return float(adj.loc[target])
