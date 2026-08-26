"""Input 7-style residual financing defaults and overrides."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook


@dataclass(slots=True)
class ResidualFinancingParams:
    """Resolved residual / marginal financing assumptions (Input 7).

    Shares mirror Ext ``C126–C128`` (decade averages) or Input 7 public
    value-used ``J9–J11``. ``avg_interest_rate`` is in **percent** (Ext
    ``C131`` ≈ 8 means 8%); Input 7 ``E14`` stores a decimal and is converted
    on load. Grace / maturity averages are unrounded; ``*_rounded`` match Ext
    ``ROUNDDOWN`` / Input 7 ``E16`` / ``E17``.

    Domestic public-DSA fields use Input 7 decimals / integers (``J19–J23``).
    """

    external_mlt_share: float
    domestic_mlt_share: float
    domestic_st_share: float
    avg_interest_rate: float
    avg_grace: float
    avg_maturity: float
    avg_grace_rounded: int
    avg_maturity_rounded: int
    domestic_mlt_real_rate: float = 0.0
    domestic_mlt_maturity: int = 1
    domestic_mlt_grace: int = 0
    domestic_st_real_rate: float = 0.0
    discount_rate: float = 0.05


@dataclass(slots=True)
class ResidualFinancingOverrides:
    """Optional per-field overrides (``None`` = keep the calculated default)."""

    external_mlt_share: float | None = None
    domestic_mlt_share: float | None = None
    domestic_st_share: float | None = None
    avg_interest_rate: float | None = None
    avg_grace: float | None = None
    avg_maturity: float | None = None
    avg_grace_rounded: int | None = None
    avg_maturity_rounded: int | None = None
    domestic_mlt_real_rate: float | None = None
    domestic_mlt_maturity: int | None = None
    domestic_mlt_grace: int | None = None
    domestic_st_real_rate: float | None = None
    discount_rate: float | None = None


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


def resolve_residual_params(
    defaults: ResidualFinancingParams,
    overrides: ResidualFinancingOverrides | None = None,
) -> ResidualFinancingParams:
    """Apply Input 7-style ``IF(ISNUMBER(user), user, default)`` per field.

    When either external or domestic MLT share is overridden and domestic ST
    is left ``None``, ST is set to ``1 - external - domestic_mlt`` (Input 7
    public-DSA ``I11``).
    """
    if overrides is None:
        return defaults

    external = (
        overrides.external_mlt_share
        if overrides.external_mlt_share is not None
        else defaults.external_mlt_share
    )
    domestic_mlt = (
        overrides.domestic_mlt_share
        if overrides.domestic_mlt_share is not None
        else defaults.domestic_mlt_share
    )
    share_override = (
        overrides.external_mlt_share is not None
        or overrides.domestic_mlt_share is not None
    )
    if overrides.domestic_st_share is not None:
        domestic_st = overrides.domestic_st_share
    elif share_override:
        domestic_st = 1.0 - external - domestic_mlt
    else:
        domestic_st = defaults.domestic_st_share

    avg_interest = (
        overrides.avg_interest_rate
        if overrides.avg_interest_rate is not None
        else defaults.avg_interest_rate
    )
    avg_grace = (
        overrides.avg_grace if overrides.avg_grace is not None else defaults.avg_grace
    )
    avg_maturity = (
        overrides.avg_maturity
        if overrides.avg_maturity is not None
        else defaults.avg_maturity
    )

    if overrides.avg_grace_rounded is not None:
        grace_rounded = overrides.avg_grace_rounded
    elif overrides.avg_grace is not None:
        grace_rounded = math.floor(avg_grace)
    else:
        grace_rounded = defaults.avg_grace_rounded

    if overrides.avg_maturity_rounded is not None:
        maturity_rounded = overrides.avg_maturity_rounded
    elif overrides.avg_maturity is not None:
        maturity_rounded = math.floor(avg_maturity)
    else:
        maturity_rounded = defaults.avg_maturity_rounded

    return ResidualFinancingParams(
        external_mlt_share=external,
        domestic_mlt_share=domestic_mlt,
        domestic_st_share=domestic_st,
        avg_interest_rate=avg_interest,
        avg_grace=avg_grace,
        avg_maturity=avg_maturity,
        avg_grace_rounded=grace_rounded,
        avg_maturity_rounded=maturity_rounded,
        domestic_mlt_real_rate=(
            overrides.domestic_mlt_real_rate
            if overrides.domestic_mlt_real_rate is not None
            else defaults.domestic_mlt_real_rate
        ),
        domestic_mlt_maturity=(
            overrides.domestic_mlt_maturity
            if overrides.domestic_mlt_maturity is not None
            else defaults.domestic_mlt_maturity
        ),
        domestic_mlt_grace=(
            overrides.domestic_mlt_grace
            if overrides.domestic_mlt_grace is not None
            else defaults.domestic_mlt_grace
        ),
        domestic_st_real_rate=(
            overrides.domestic_st_real_rate
            if overrides.domestic_st_real_rate is not None
            else defaults.domestic_st_real_rate
        ),
        discount_rate=(
            overrides.discount_rate
            if overrides.discount_rate is not None
            else defaults.discount_rate
        ),
    )


def public_dsa_residual_params(
    params: ResidualFinancingParams,
) -> ResidualFinancingParams:
    """Return params for public DSA residual fill (keep J-column shares)."""
    return replace(params)
