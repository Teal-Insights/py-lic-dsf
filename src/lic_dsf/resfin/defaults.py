"""Ext decade-average residual financing defaults from an ExternalDebtBook."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
from lic_dsf.resfin.params import ResidualFinancingParams

if TYPE_CHECKING:
    from lic_dsf.books.external.book import ExternalDebtBook


def _projection_years(book: ExternalDebtBook, average_years: int) -> list[int]:
    """Ext ``AVERAGE(F:P)`` years: skip the current/history year, then take N."""
    years = list(book.inputs.years)
    if len(years) <= 1:
        return years[:average_years]
    return years[1 : 1 + average_years]


def _instrument_terms(
    instrument: Any,
    residual_interest_rates: dict[str, float],
) -> tuple[float, float, float]:
    """Return (interest decimal, grace, maturity) for residual weighting."""
    name = str(instrument.name)
    grace = float(instrument.grace)
    maturity = float(instrument.maturity)
    if isinstance(instrument, LocalCurrencyNonResidentInstrument):
        rate = residual_interest_rates.get(name)
        if rate is None:
            rates = [float(r) for r in instrument.interest_rates]
            rate = sum(rates) / len(rates) if rates else 0.0
        return rate, grace, maturity

    rate = residual_interest_rates.get(name, float(instrument.interest_rate))
    return rate, grace, maturity


def calculate_residual_defaults(
    book: ExternalDebtBook,
    *,
    average_years: int = 11,
) -> ResidualFinancingParams:
    """Compute Ext R122–R136 decade averages used as Input 7 defaults.

    Args:
        book: External debt book (portfolio + inputs).
        average_years: Number of projection years to average. Ext
            ``AVERAGE(F126:P126)`` spans **11** years (F–P); default matches that.

    Returns:
        Decade-average shares and disbursement-weighted terms. Domestic
        public-DSA rates default to 0 (load from Input 7 for stress fills).
    """
    if average_years < 1:
        raise ValueError(f"average_years must be >= 1, got {average_years}")

    years = _projection_years(book, average_years)
    if not years:
        raise ValueError("book has no projection years for residual defaults")

    inputs = book.inputs
    new_borrowing = book.portfolio.aggregate_external().loc[
        "New forex borrowing (gross, USD)"
    ]
    st = book.total_st_external()
    dom_mlt = inputs.domestic_mlt_disbursements_usd
    dom_st = inputs.domestic_st_disbursements_usd

    share_ext: list[float] = []
    share_dom_mlt: list[float] = []
    share_dom_st: list[float] = []
    yearly_interest: list[float] = []
    yearly_grace: list[float] = []
    yearly_maturity: list[float] = []

    for year in years:
        ext_mlt = float(new_borrowing.reindex([year]).fillna(0.0).loc[year])
        st_y = float(st.reindex([year]).fillna(0.0).loc[year])
        d_mlt = float(dom_mlt.reindex([year]).fillna(0.0).loc[year])
        d_st = float(dom_st.reindex([year]).fillna(0.0).loc[year])
        total = ext_mlt + st_y + d_mlt + d_st
        if total == 0.0:
            share_ext.append(0.0)
            share_dom_mlt.append(0.0)
            share_dom_st.append(0.0)
        else:
            share_ext.append(ext_mlt / total)
            share_dom_mlt.append(d_mlt / total)
            share_dom_st.append(d_st / total)

        num_i = 0.0
        num_g = 0.0
        num_m = 0.0
        den = 0.0
        for instrument in book.portfolio.instruments:
            disb = float(
                instrument.external()
                .loc["New forex borrowing (gross, USD)"]
                .reindex([year])
                .fillna(0.0)
                .loc[year]
            )
            if disb == 0.0:
                continue
            rate, grace, maturity = _instrument_terms(
                instrument, inputs.residual_interest_rates
            )
            num_i += rate * disb
            num_g += grace * disb
            num_m += maturity * disb
            den += disb
        if den == 0.0:
            yearly_interest.append(0.0)
            yearly_grace.append(0.0)
            yearly_maturity.append(0.0)
        else:
            yearly_interest.append((num_i / den) * 100.0)
            yearly_grace.append(num_g / den)
            yearly_maturity.append(num_m / den)

    n = float(len(years))
    avg_grace = sum(yearly_grace) / n
    avg_maturity = sum(yearly_maturity) / n
    discount = 0.05
    for instrument in book.portfolio.instruments:
        rate = getattr(instrument, "discount_rate", None)
        if rate is not None:
            discount = float(rate)
            break
    return ResidualFinancingParams(
        external_mlt_share=sum(share_ext) / n,
        domestic_mlt_share=sum(share_dom_mlt) / n,
        domestic_st_share=sum(share_dom_st) / n,
        avg_interest_rate=sum(yearly_interest) / n,
        avg_grace=avg_grace,
        avg_maturity=avg_maturity,
        avg_grace_rounded=math.floor(avg_grace),
        avg_maturity_rounded=math.floor(avg_maturity),
        discount_rate=discount,
    )
