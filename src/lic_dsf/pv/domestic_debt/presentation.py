"""Dom_Debt_Indicators presentation panels (chart windows + borrowing)."""

from __future__ import annotations

import pandas as pd

from lic_dsf.pv.domestic_debt.types import DomesticDebtInputs


def chart_year_window(
    years: tuple[int, ...],
    first_projection_year: int,
    *,
    hist_years: int = 5,
    proj_years: int = 10,
) -> list[int]:
    """Excel Dom_Debt_Indicators chart window ``J:Y`` (proj−5 … proj+10)."""
    start = first_projection_year - hist_years
    end = first_projection_year + proj_years
    available = set(years)
    return [year for year in range(start, end + 1) if year in available]


def indicator_charts(
    *,
    domestic_debt_to_gdp: pd.Series,
    peer_median_debt_to_gdp: pd.Series,
    domestic_ds_to_revenues: pd.Series,
    peer_median_ds_to_revenues: pd.Series,
    net_issuance_to_gdp: pd.Series,
    years: tuple[int, ...],
    first_projection_year: int,
) -> pd.DataFrame:
    """Three Dom_Debt_Indicators chart series over the J:Y year window."""
    window = chart_year_window(years, first_projection_year)
    return pd.DataFrame(
        {
            "Domestic debt / GDP": domestic_debt_to_gdp,
            "Peer median debt / GDP": peer_median_debt_to_gdp,
            "Domestic DS / revenues": domestic_ds_to_revenues,
            "Peer median DS / revenues": peer_median_ds_to_revenues,
            "Net domestic debt issuance / GDP": net_issuance_to_gdp,
        }
    ).T.reindex(columns=window)


def borrowing_assumptions(inputs: DomesticDebtInputs) -> pd.DataFrame:
    """Input 7 domestic borrowing shares and terms (Indicators F22–F30).

    Shares are domestic MLT/ST as a fraction of domestic residual financing
    (``H10/(H10+H11)`` and ``H11/(H10+H11)``).
    """
    mlt = float(inputs.residual_domestic_mlt_share)
    st = float(inputs.residual_domestic_st_share)
    total = mlt + st
    if total == 0.0:
        mlt_share = 0.0
        st_share = 0.0
    else:
        mlt_share = mlt / total
        st_share = st / total

    return pd.DataFrame(
        {
            "share": [mlt_share, st_share],
            "avg_interest": [
                float(inputs.domestic_mlt_avg_interest),
                float(inputs.domestic_st_avg_interest),
            ],
            "avg_maturity": [float(inputs.domestic_mlt_avg_maturity), float("nan")],
            "avg_grace": [float(inputs.domestic_mlt_avg_grace), float("nan")],
        },
        index=["Medium and long-term", "Short-term"],
    )
