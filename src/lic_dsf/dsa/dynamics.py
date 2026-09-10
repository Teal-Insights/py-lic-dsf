"""Shared public automatic debt-dynamics identities (Baseline / Realism 1).

Used by Output 1-2 and Realism 1 forecast-error panels. Not realism-specific.
"""

from __future__ import annotations

import pandas as pd


def _float_series(series: pd.Series, index: pd.Index) -> pd.Series:
    """Coerce to float and align, turning non-numeric / NA values into NaN."""
    return pd.to_numeric(series, errors="coerce").reindex(index)


def public_automatic_debt_dynamics(
    *,
    public_debt_to_gdp: pd.Series,
    fc_debt_to_gdp: pd.Series,
    real_gdp_growth: pd.Series,
    gdp_deflator_growth: pd.Series,
    us_deflator_growth: pd.Series,
    fx_eop: pd.Series,
    interest_rate_external: pd.Series,
    interest_rate_domestic: pd.Series,
    public_interest_rate: pd.Series | None = None,
) -> pd.DataFrame:
    """Baseline-public automatic dynamics (`DUCIR` / `DUCGDPR` / `DUCER`).

    Identities match ``Baseline - public`` R29–R31 (denominator `1 + g`, not
    `(1+g)(1+π)`):

    * real domestic rate ``(i_dom − π) / (1+π)``
    * real external rate ``(i_ext − π_US) / (1+π_US)``
    * average real rate weighted by lagged FC share of public debt
    * real FX depreciation from eop LC-per-USD and the two deflators
    * ``DUCER = ε_real / 100 × lagged FC debt/GDP × (1 + r_ext) / (1+g)``

    When `interest_rate_external` is 0, Excel substitutes the blended public
    rate (`R54`). Missing domestic rates also fall back to that blended rate.

    Args:
        public_debt_to_gdp: Public debt / GDP (percent), Baseline R12.
        fc_debt_to_gdp: FC-denominated public debt / GDP (percent), R14.
        real_gdp_growth: Real GDP growth (percent), Macro R107.
        gdp_deflator_growth: LCU GDP-deflator inflation (percent), R109.
        us_deflator_growth: US GDP-deflator inflation (percent), R112.
        fx_eop: End-of-period LC per USD (Baseline R60 / Macro R59).
        interest_rate_external: Average nominal external rate (percent).
        interest_rate_domestic: Average nominal domestic rate (percent).
        public_interest_rate: Blended public rate (percent) used as fallback.

    Returns:
        DataFrame indexed by `DUCIR_GDP`, `DUCGDPR_GDP`, `DUCER_GDP`.
    """
    du = _float_series(public_debt_to_gdp, public_debt_to_gdp.index)
    d_fc = _float_series(fc_debt_to_gdp, du.index)
    g = _float_series(real_gdp_growth, du.index)
    pi = _float_series(gdp_deflator_growth, du.index)
    pi_us = _float_series(us_deflator_growth, du.index)
    fx = _float_series(fx_eop, du.index)
    i_ext = _float_series(interest_rate_external, du.index)
    i_dom = _float_series(interest_rate_domestic, du.index)
    if public_interest_rate is not None:
        i_pub = _float_series(public_interest_rate, du.index)
        i_ext = i_ext.where(i_ext.fillna(0.0) != 0.0, i_pub)
        i_dom = i_dom.where(i_dom.notna(), i_pub)
    lag_d = du.shift(1)
    lag_fc = d_fc.shift(1)
    alpha = lag_fc / lag_d.replace(0.0, float("nan"))
    r_dom = (i_dom - pi) / (1.0 + pi / 100.0)
    r_ext = (i_ext - pi_us) / (1.0 + pi_us / 100.0)
    r_avg = alpha * r_ext + (1.0 - alpha) * r_dom
    den = 1.0 + g / 100.0
    nom_dep = 100.0 * (fx / fx.shift(1).replace(0.0, float("nan")) - 1.0)
    real_dep = (100.0 + nom_dep) * (1.0 + pi_us / 100.0) / (1.0 + pi / 100.0) - 100.0
    ducir = (r_avg / 100.0) * lag_d / den
    ducgdpr = -(g / 100.0) * lag_d / den
    ducer = (real_dep / 100.0) * lag_fc * (1.0 + r_ext / 100.0) / den
    return pd.DataFrame(
        {
            "DUCIR_GDP": pd.to_numeric(ducir, errors="coerce"),
            "DUCGDPR_GDP": pd.to_numeric(ducgdpr, errors="coerce"),
            "DUCER_GDP": pd.to_numeric(ducer, errors="coerce"),
        }
    ).T
