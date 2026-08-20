"""Load realism assumptions from the LIC-DSF workbook template."""

from __future__ import annotations

from pathlib import Path

from fastpyxl import load_workbook

from lic_dsf.realism.fiscal_adjustment import DEFAULT_LIC_PROGRAM_DISTRIBUTION
from lic_dsf.realism.types import (
    CapitalAssumptions,
    LicProgramDistribution,
    MultiplierAssumptions,
)


def load_multiplier_grid(
    path: str | Path,
) -> list[MultiplierAssumptions]:
    """Load Realism 2 multiplier grid (``m`` columns with shared ``p``).

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        List of `MultiplierAssumptions` for each ``m`` column.
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Realism 2 - Fiscal multiplier"]
        out: list[MultiplierAssumptions] = []
        for c in range(4, 9):
            m = ws.cell(15, c).value
            p = ws.cell(16, c).value
            if isinstance(m, (int, float)) and isinstance(p, (int, float)):
                out.append(MultiplierAssumptions(m=float(m), persistence=float(p)))
        return out
    finally:
        wb.close()


def load_capital_assumptions(path: str | Path) -> CapitalAssumptions:
    """Load Realism 3 FAD capital stock assumptions.

    Args:
        path: Path to the LIC-DSF Excel workbook.

    Returns:
        `CapitalAssumptions` (initial ``G/Y`` left at default; pass via
        fixture when a vintage capital stock is available).
    """
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Realism 3 - Invest-Growth"]
        d = float(ws.cell(10, 3).value)
        phi = float(ws.cell(11, 3).value)
        beta = float(ws.cell(14, 3).value)
        initial_gy_raw = ws.cell(70, 3).value
        initial_gy = float(initial_gy_raw) if initial_gy_raw is not None else 0.5
        return CapitalAssumptions(
            depreciation=d,
            efficiency=phi,
            beta=beta,
            initial_capital_to_gdp=initial_gy,
        )
    finally:
        wb.close()


def load_lic_program_distribution(
    path: str | Path | None = None,
) -> LicProgramDistribution:
    """Load the LIC program histogram (embedded default; path optional).

    The histogram is fixed in the template; when ``path`` is given the
    frequencies are re-read for parity checks.

    Args:
        path: Optional workbook path. When ``None``, returns the embedded
            default distribution.

    Returns:
        `LicProgramDistribution`.
    """
    if path is None:
        return DEFAULT_LIC_PROGRAM_DISTRIBUTION

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["Realism 4 - Fiscal adjustment"]
        bins: list[float | str] = []
        freqs: list[float] = []
        pcts: list[float] = []
        cum: list[float] = []
        # R23–R50 categories (skip R22 sentinel -99 / freq 0).
        for r in range(23, 51):
            b = ws.cell(r, 1).value
            f = ws.cell(r, 2).value
            p = ws.cell(r, 4).value
            c = ws.cell(r, 5).value
            if f is None:
                continue
            if b is None and r == 23:
                bins.append(-4.5)  # open left display edge
            elif isinstance(b, str):
                bins.append(b)
            elif isinstance(b, (int, float)):
                bins.append(float(b))
            else:
                continue
            freqs.append(float(f))
            pcts.append(float(p) if isinstance(p, (int, float)) else 0.0)
            cum.append(float(c) if isinstance(c, (int, float)) else 0.0)
        return LicProgramDistribution(
            bins=tuple(bins),
            frequencies=tuple(freqs),
            percent_of_sample=tuple(pcts),
            cumulative_percent=tuple(cum),
        )
    finally:
        wb.close()
