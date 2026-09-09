"""Input 7-style residual financing params, overrides, and DSA-mode variants."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace


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


def external_dsa_residual_params(
    params: ResidualFinancingParams,
) -> ResidualFinancingParams:
    """Return Input 7 *external DSA* terms (100% external PPG MLT fill)."""
    return replace(
        params,
        external_mlt_share=1.0,
        domestic_mlt_share=0.0,
        domestic_st_share=0.0,
    )


def public_dsa_residual_params(
    params: ResidualFinancingParams,
) -> ResidualFinancingParams:
    """Return params for public DSA residual fill (keep J-column shares)."""
    return replace(params)
