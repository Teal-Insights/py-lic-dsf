"""Local-currency → USD conversion helpers for Ext_Debt Input 5 series."""

from __future__ import annotations

import pandas as pd


def lc_to_usd(values_lc: pd.Series, fx: pd.Series) -> pd.Series:
    """Divide LC amounts by FX (NC per USD); zero when FX missing or zero."""
    aligned_lc = values_lc.astype(float)
    aligned_fx = fx.reindex(aligned_lc.index).astype(float)
    out = pd.Series(0.0, index=aligned_lc.index, dtype=float)
    for year in aligned_lc.index:
        rate = float(aligned_fx.loc[year]) if year in aligned_fx.index else 0.0
        amount = float(aligned_lc.loc[year])
        out.loc[year] = 0.0 if rate == 0.0 else amount / rate
    return out


def sum_rows_lc(rows: list[pd.Series]) -> pd.Series:
    """Elementwise sum of LC series (missing → 0)."""
    if not rows:
        return pd.Series(dtype=float)
    total = rows[0].astype(float).copy()
    for row in rows[1:]:
        total = total.add(row.astype(float), fill_value=0.0)
    return total.fillna(0.0)
