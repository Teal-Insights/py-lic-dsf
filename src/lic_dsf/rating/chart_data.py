"""Chart Data breach aggregation and mechanical risk ratings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import pandas as pd

from lic_dsf.rating.classification import ApplicableThresholds


class RiskRating(IntEnum):
    """Mechanical risk rating: 1=Low, 2=Moderate, 3=High."""

    LOW = 1
    MODERATE = 2
    HIGH = 3

    @property
    def label(self) -> str:
        """Excel Chart Data label."""
        return {1: "Low", 2: "Moderate", 3: "High"}[int(self)]


@dataclass(slots=True)
class RatioPath:
    """One ratio trajectory registered for breach detection.

    Attributes:
        indicator: Indicator id (e.g. ``pv_debt_to_gdp``).
        scenario_id: Path id (``baseline``, ``B3``, ``custom``, …).
        values: Ratio series (percent) indexed by year.
        is_baseline: Whether this path is the baseline.
        is_shock: Whether this path is a stress / tailored shock.
    """

    indicator: str
    scenario_id: str
    values: pd.Series
    is_baseline: bool = False
    is_shock: bool = False


@dataclass(slots=True)
class ChartDataRegistry:
    """Registry of baseline + stress ratio paths for Chart Data."""

    paths: list[RatioPath] = field(default_factory=list)

    def register(self, path: RatioPath) -> None:
        """Add a ratio path."""
        self.paths.append(path)

    def register_series(
        self,
        indicator: str,
        scenario_id: str,
        values: pd.Series,
        *,
        is_baseline: bool = False,
        is_shock: bool = False,
    ) -> None:
        """Convenience wrapper around `register`."""
        self.register(
            RatioPath(
                indicator=indicator,
                scenario_id=scenario_id,
                values=values.astype(float),
                is_baseline=is_baseline,
                is_shock=is_shock,
            )
        )


def annual_breaches(
    values: pd.Series,
    threshold: float,
    years: list[int] | None = None,
) -> pd.Series:
    """Return 0/1 breach flags for each year (value > threshold).

    Args:
        values: Ratio series.
        threshold: Applicable threshold.
        years: Optional year subset (defaults to series index).

    Returns:
        Integer series of breach flags.
    """
    series = values.astype(float)
    if years is not None:
        series = series.reindex(years)
    return (series > threshold).astype(int)


def multi_year_breach(
    values: pd.Series,
    threshold: float,
    years: list[int] | None = None,
) -> bool:
    """True if the path breaches in two or more years (excludes 1-year-only).

    Excel Chart Data rule: a single one-year breach does not determine the
    mechanical risk rating.

    Args:
        values: Ratio series.
        threshold: Applicable threshold.
        years: Optional rating horizon years.

    Returns:
        Whether a multi-year breach is present.
    """
    flags = annual_breaches(values, threshold, years)
    return int(flags.sum()) >= 2


def most_extreme_shock_id(
    paths: dict[str, pd.Series],
    threshold: float,
    years: list[int],
) -> str:
    """Chart Data most-extreme shock (``D63`` / ``MATCH(1, AJ40:AJ50)``).

    Rank eligible shocks by peak ratio over years 2–11 of the rating window
    (Excel ``MAX(E:N)``). A path whose only tail breach is a single year, and
    that does not also breach in year 1, is dropped (Excel ``AC`` / ``AD``).

    Args:
        paths: Scenario id → ratio series (standard + tailored shocks).
        threshold: Applicable threshold for the ranking indicator (PV/GDP).
        years: 11-year rating window (year 1 = first projection year).

    Returns:
        Scenario id of the rank-1 shock.

    Raises:
        ValueError: If `paths` is empty.
    """
    if not paths:
        raise ValueError("most_extreme_shock_id requires at least one path")
    if len(years) < 2:
        return max(
            paths,
            key=lambda sid: float(paths[sid].reindex(years).max()),
        )
    year1 = years[0]
    tail = years[1:]
    ranked: list[tuple[float, str]] = []
    for sid, series in paths.items():
        tail_vals = series.reindex(tail).astype(float)
        n_breach = int((tail_vals > threshold).fillna(False).sum())
        y1 = series.reindex([year1])
        y1_val = float(y1.iloc[0]) if len(y1) and pd.notna(y1.iloc[0]) else float("nan")
        y1_breach = pd.notna(y1_val) and y1_val > threshold
        if n_breach == 1 and not y1_breach:
            continue
        peak = float(tail_vals.max()) if tail_vals.notna().any() else float("-inf")
        ranked.append((peak, sid))
    if not ranked:
        ranked = [
            (
                float(series.reindex(tail).max())
                if series.reindex(tail).notna().any()
                else float("-inf"),
                sid,
            )
            for sid, series in paths.items()
        ]
    return max(ranked)[1]


def indicator_breach_any_path(
    registry: ChartDataRegistry,
    indicator: str,
    threshold: float,
    *,
    baseline_only: bool = False,
    shock_only: bool = False,
    years: list[int] | None = None,
) -> bool:
    """True if any matching path has a multi-year breach."""
    for path in registry.paths:
        if path.indicator != indicator:
            continue
        if baseline_only and not path.is_baseline:
            continue
        if shock_only and not path.is_shock:
            continue
        if multi_year_breach(path.values, threshold, years):
            return True
    return False


@dataclass(frozen=True, slots=True)
class MechanicalRatingResult:
    """Mechanical external / fiscal / overall ratings."""

    external: RiskRating
    fiscal: RiskRating
    overall: RiskRating
    external_baseline_breach: bool
    external_shock_breach: bool
    fiscal_baseline_breach: bool
    fiscal_shock_breach: bool


def mechanical_rating_from_breaches(
    *,
    baseline_breach: bool,
    shock_breach: bool,
) -> RiskRating:
    """Map breach flags to Low / Moderate / High.

    Rule: baseline multi-year breach → High; else shock breach → Moderate;
    else Low.
    """
    if baseline_breach:
        return RiskRating.HIGH
    if shock_breach:
        return RiskRating.MODERATE
    return RiskRating.LOW


def compute_mechanical_ratings(
    registry: ChartDataRegistry,
    thresholds: ApplicableThresholds,
    *,
    external_indicators: tuple[str, ...] = (
        "pv_debt_to_gdp",
        "pv_debt_to_exports",
        "debt_service_to_exports",
        "debt_service_to_revenue",
    ),
    fiscal_indicators: tuple[str, ...] = ("public_pv_debt_to_gdp",),
    years: list[int] | None = None,
) -> MechanicalRatingResult:
    """Compute mechanical external, fiscal, and overall ratings.

    Overall = max(external, fiscal) on the 1/2/3 scale.

    Args:
        registry: Registered baseline + shock paths.
        thresholds: Applicable CI thresholds.
        external_indicators: External indicator ids to check.
        fiscal_indicators: Fiscal indicator ids to check.
        years: Optional rating horizon.

    Returns:
        Mechanical rating result.
    """
    thresh = thresholds.as_dict()

    def _side(indicators: tuple[str, ...]) -> tuple[bool, bool, RiskRating]:
        base = False
        shock = False
        for ind in indicators:
            t = thresh[ind]
            if indicator_breach_any_path(
                registry, ind, t, baseline_only=True, years=years
            ):
                base = True
            if indicator_breach_any_path(
                registry, ind, t, shock_only=True, years=years
            ):
                shock = True
        return (
            base,
            shock,
            mechanical_rating_from_breaches(baseline_breach=base, shock_breach=shock),
        )

    ext_base, ext_shock, ext_rating = _side(external_indicators)
    fis_base, fis_shock, fis_rating = _side(fiscal_indicators)
    overall = RiskRating(max(int(ext_rating), int(fis_rating)))
    return MechanicalRatingResult(
        external=ext_rating,
        fiscal=fis_rating,
        overall=overall,
        external_baseline_breach=ext_base,
        external_shock_breach=ext_shock,
        fiscal_baseline_breach=fis_base,
        fiscal_shock_breach=fis_shock,
    )
