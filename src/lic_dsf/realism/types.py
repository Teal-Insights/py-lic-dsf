"""Shared assumption types for realism engines."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class MultiplierAssumptions:
    """Fiscal multiplier assumptions (Realism 2).

    Attributes:
        m: Impact multiplier on growth.
        persistence: Persistence factor ``p`` (Excel default 0.6).
    """

    m: float
    persistence: float = 0.6


@dataclass(frozen=True, slots=True)
class CapitalAssumptions:
    """Government capital stock assumptions (Realism 3).

    Attributes:
        depreciation: Annual depreciation rate ``d``.
        efficiency: Investment efficiency ``φ`` (FAD φF/φH product).
        beta: Output elasticity of government capital ``β``.
        initial_capital_to_gdp: Starting ``G/Y`` ratio (fraction, not percent).
    """

    depreciation: float = 0.05
    efficiency: float = 1.0
    beta: float = 0.15
    initial_capital_to_gdp: float = 0.5


@dataclass(frozen=True, slots=True)
class LicProgramDistribution:
    """LIC program 3-year fiscal-adjustment histogram (Realism 4).

    Attributes:
        bins: Lower edges of histogram bins (Excel ``Bin`` column).
        frequencies: Sample counts per bin.
        percent_of_sample: Share of sample in each bin (0–100).
        cumulative_percent: Cumulative percent of sample (Excel col E).
    """

    bins: tuple[float | str, ...]
    frequencies: tuple[float, ...]
    percent_of_sample: tuple[float, ...]
    cumulative_percent: tuple[float, ...]

    def as_frame(self) -> pd.DataFrame:
        """Return the histogram as a DataFrame."""
        return pd.DataFrame(
            {
                "bin": list(self.bins),
                "frequency": list(self.frequencies),
                "percent_of_sample": list(self.percent_of_sample),
                "cumulative_percent": list(self.cumulative_percent),
            }
        )
