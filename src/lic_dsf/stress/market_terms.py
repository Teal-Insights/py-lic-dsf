"""C4 market-financing maturity/grace shortening (Excel ``C4_Market_financing``)."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.external_debt.creditor_groups import creditor_group_for_name
from lic_dsf.pv.external_debt.residual import (
    ResidualFinancingOverrides,
    ResidualFinancingParams,
    resolve_residual_params,
)
from lic_dsf.pv.instrument import PresentValueInstrument
from lic_dsf.stress.tailored_params import TailoredParams


@dataclass(frozen=True, slots=True)
class ShortenedLoanTerms:
    """Excel F/G/H/I for one commercial loan under C4 stress."""

    maturity: float
    grace: float
    maturity_rounded: int
    grace_rounded: int
    bullet: bool


def shorten_loan_terms(
    *,
    original_maturity: float,
    original_grace: float,
    maturity_cap: float,
    maturity_factor: float,
    grace_factor: float,
) -> ShortenedLoanTerms:
    """Apply Excel ``C4_Market_financing`` F35:I35 shortening rules.

    ``maturity_cap`` / ``maturity_factor`` / ``grace_factor`` are Input 6 H54–H56
    (defaults 5, 2/3, 2/3).
    """
    d = float(original_maturity)
    c = float(original_grace)
    bullet = (d - c) <= 1.0
    if d > float(maturity_cap):
        f = float(maturity_cap)
    else:
        f = float(maturity_factor) * d
    if bullet:
        g = f - 1.0
    else:
        g = min(float(grace_factor) * f, c)
    h = int(floor(f))
    i = int(floor(g))
    if h <= i:
        h = i + 1
    return ShortenedLoanTerms(
        maturity=f,
        grace=g,
        maturity_rounded=h,
        grace_rounded=i,
        bullet=bullet,
    )


def commercial_instruments(
    external: ExternalDebtBook,
) -> list[PresentValueInstrument]:
    """Commercial PPG instruments (Input 4 Eurobond / COM* rows)."""
    out: list[PresentValueInstrument] = []
    for inst in external.portfolio.instruments:
        if not isinstance(inst, PresentValueInstrument):
            continue
        if creditor_group_for_name(str(inst.name)) != "Commercial":
            continue
        out.append(inst)
    return out


def shortened_terms_for_instrument(
    inst: PresentValueInstrument,
    params: TailoredParams,
) -> ShortenedLoanTerms:
    """Shorten one commercial instrument using tailored Input 6 factors."""
    return shorten_loan_terms(
        original_maturity=float(inst.maturity),
        original_grace=float(inst.grace),
        maturity_cap=float(params.market_maturity_cap),
        maturity_factor=float(params.market_maturity_factor),
        grace_factor=float(params.market_grace_factor),
    )


def commercial_weighted_resfin_terms(
    external: ExternalDebtBook,
    params: TailoredParams,
    *,
    years: tuple[int, ...],
    first_projection_year: int,
    shock_years: int = 3,
) -> tuple[float, float, int, int]:
    """Excel H41/I41: disbursement-weighted avg shortened maturity/grace."""
    year_list = list(years)
    proj = [y for y in year_list if y >= first_projection_year]
    weight_years = set(proj[1 : 1 + int(shock_years)]) if len(proj) > 1 else set()
    w_sum = 0.0
    mat_acc = 0.0
    grace_acc = 0.0
    for inst in commercial_instruments(external):
        terms = shortened_terms_for_instrument(inst, params)
        disb = pd.Series(
            list(inst.disbursements),
            index=list(inst.years)[: len(inst.disbursements)],
            dtype=float,
        )
        w = float(
            sum(float(disb.reindex([y]).fillna(0.0).loc[y]) for y in weight_years)
        )
        if w <= 0.0:
            continue
        w_sum += w
        mat_acc += terms.maturity * w
        grace_acc += terms.grace * w
    if w_sum <= 0.0:
        cap = float(params.market_maturity_cap)
        gf = float(params.market_grace_factor)
        return cap, cap * gf, int(floor(cap)), int(floor(cap * gf))
    mat = mat_acc / w_sum
    grace = grace_acc / w_sum
    mat_r = int(floor(mat))
    grace_r = int(floor(grace))
    if mat_r <= grace_r:
        mat_r = grace_r + 1
    return mat, grace, mat_r, grace_r


def commercial_weighted_interest_rate(
    external: ExternalDebtBook,
    *,
    years: tuple[int, ...],
    first_projection_year: int,
    shock_years: int = 3,
) -> float:
    """Excel K41: disbursement-weighted avg interest rate of shock-window commercial loans."""
    year_list = list(years)
    proj = [y for y in year_list if y >= first_projection_year]
    weight_years = set(proj[1 : 1 + int(shock_years)]) if len(proj) > 1 else set()
    w_sum = 0.0
    rate_acc = 0.0
    for inst in commercial_instruments(external):
        disb = pd.Series(
            list(inst.disbursements),
            index=list(inst.years)[: len(inst.disbursements)],
            dtype=float,
        )
        w = float(
            sum(float(disb.reindex([y]).fillna(0.0).loc[y]) for y in weight_years)
        )
        if w <= 0.0:
            continue
        w_sum += w
        rate_acc += float(inst.interest_rate) * w
    if w_sum <= 0.0:
        return 0.0
    return rate_acc / w_sum


def c4_residual_overrides(
    external: ExternalDebtBook,
    params: TailoredParams,
    *,
    years: tuple[int, ...],
    first_projection_year: int,
) -> ResidualFinancingOverrides:
    """ResidualFinancingOverrides for C4 ResFin (Excel H41/I41)."""
    mat, grace, mat_r, grace_r = commercial_weighted_resfin_terms(
        external,
        params,
        years=years,
        first_projection_year=first_projection_year,
    )
    return ResidualFinancingOverrides(
        avg_maturity=mat,
        avg_grace=grace,
        avg_maturity_rounded=mat_r,
        avg_grace_rounded=grace_r,
    )


def apply_c4_residual_overrides(
    residual: ResidualFinancingParams,
    external: ExternalDebtBook,
    params: TailoredParams,
    *,
    years: tuple[int, ...],
    first_projection_year: int,
) -> ResidualFinancingParams:
    """Return residual params with C4 shortened maturity/grace."""
    return resolve_residual_params(
        residual,
        c4_residual_overrides(
            external,
            params,
            years=years,
            first_projection_year=first_projection_year,
        ),
    )


def _panel_row(panel: pd.DataFrame, *names: str) -> str | None:
    for name in names:
        if name in panel.index:
            return name
    return None


def commercial_pv_delta_usd(
    external: ExternalDebtBook,
    params: TailoredParams,
    *,
    years: tuple[int, ...],
    first_projection_year: int,
    shock_years: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """PV and debt-service delta from shortening shock-window commercial terms.

    Excel C4 revises commercial PV as ``stress_com − baseline_com`` on new
    borrowing in the market-financing window (same 3 years as the 400 bps cost).
    """
    year_list = list(years)
    proj = [y for y in year_list if y >= first_projection_year]
    shock = set(proj[1 : 1 + int(shock_years)]) if len(proj) > 1 else set()
    pv_delta = pd.Series(0.0, index=year_list, dtype=float)
    ds_delta = pd.Series(0.0, index=year_list, dtype=float)
    if not shock:
        return pv_delta, ds_delta

    for inst in commercial_instruments(external):
        terms = shortened_terms_for_instrument(inst, params)
        if (
            terms.maturity_rounded == int(inst.maturity)
            and terms.grace_rounded == int(inst.grace)
        ):
            continue
        disb_map = {
            y: float(v)
            for y, v in zip(
                list(inst.years)[: len(inst.disbursements)],
                inst.disbursements,
                strict=False,
            )
        }
        shock_disb = [disb_map.get(y, 0.0) if y in shock else 0.0 for y in year_list]
        if not any(abs(v) > 0.0 for v in shock_disb):
            continue
        base_inst = PresentValueInstrument(
            name=str(inst.name),
            interest_rate=float(inst.interest_rate),
            grace=int(inst.grace),
            maturity=int(inst.maturity),
            discount_rate=float(inst.discount_rate),
            years=tuple(year_list),
            disbursements=tuple(shock_disb),
        )
        short_inst = PresentValueInstrument(
            name=str(inst.name),
            interest_rate=float(inst.interest_rate),
            grace=terms.grace_rounded,
            maturity=terms.maturity_rounded,
            discount_rate=float(inst.discount_rate),
            years=tuple(year_list),
            disbursements=tuple(shock_disb),
        )
        base_panel = base_inst.external()
        short_panel = short_inst.external()
        pv_key = _panel_row(
            base_panel,
            f"PV of debt   {inst.name}",
            "PV of debt",
            "Present value of debt",
        )
        i_key = _panel_row(base_panel, "Interest")
        a_key = _panel_row(base_panel, "Amortization")
        short_pv_key = _panel_row(
            short_panel,
            f"PV of debt   {inst.name}",
            "PV of debt",
            "Present value of debt",
        )
        for y in year_list:
            if y not in base_panel.columns or y not in short_panel.columns:
                continue
            if pv_key is not None and short_pv_key is not None:
                pv_delta.loc[y] = float(pv_delta.loc[y]) + (
                    float(short_panel.loc[short_pv_key, y])
                    - float(base_panel.loc[pv_key, y])
                )
            bi = float(base_panel.loc[i_key, y]) if i_key else 0.0
            ba = float(base_panel.loc[a_key, y]) if a_key else 0.0
            si = float(short_panel.loc[i_key, y]) if i_key else 0.0
            sa = float(short_panel.loc[a_key, y]) if a_key else 0.0
            ds_delta.loc[y] = float(ds_delta.loc[y]) + (si + sa) - (bi + ba)
    return pv_delta.astype(float), ds_delta.astype(float)


def compute_c4_pv_stress_usd(
    years: tuple[int, ...],
    first_projection_year: int,
    commercial_ds_delta: pd.Series,
    additional_borrowing_interest: pd.Series,
    *,
    rate1: float,
    rate2: float,
    grace1: int,
    maturity1: int,
    grace2: int,
    maturity2: int,
    shock_years: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Compute Excel PV Stress R150/R164 (PV) and R152/R166 (DS) components for C4.

    R150/R152 use ``additional_borrowing_interest`` as disbursements for the
    shock window (grace1, maturity1, rate1).
    R164/R166 use ``commercial_ds_delta + additional_borrowing_interest`` as
    disbursements for post-shock years (grace2, maturity2, rate2).
    """
    year_list = list(years)
    proj = [y for y in year_list if y >= first_projection_year]
    shock = set(proj[1 : 1 + int(shock_years)]) if len(proj) > 1 else set()

    abi = additional_borrowing_interest.reindex(year_list).fillna(0.0)
    cds = commercial_ds_delta.reindex(year_list).fillna(0.0)
    cds_abi = cds + abi

    abi_shock = pd.Series(
        {y: float(abi.loc[y]) if y in shock else 0.0 for y in year_list}
    )
    cds_abi_post = pd.Series(
        {y: float(cds_abi.loc[y]) if y not in shock else 0.0 for y in year_list}
    )

    # R150 / R152: abi shock years
    r148 = abi_shock.cumsum()
    r149 = pd.Series(0.0, index=year_list, dtype=float)
    r152 = pd.Series(0.0, index=year_list, dtype=float)
    grace_period1 = grace1 + 1
    maturity_period1 = maturity1 + 1
    amort_periods1 = maturity1 - grace1
    for y in year_list:
        r157 = float(r148.get(y - grace_period1, 0.0))
        r159 = float(r148.get(y - maturity_period1, 0.0))
        r154 = (r157 - r159) / float(amort_periods1) if amort_periods1 > 0 else 0.0
        r149.loc[y] = float(r149.get(y - 1, 0.0)) + float(abi_shock.loc[y]) - r154
        r153 = float(r149.get(y - 1, 0.0)) * rate1
        r152.loc[y] = r153 + r154

    # R164 / R166: cds+abi post-shock
    r162 = cds_abi_post.cumsum()
    r163 = pd.Series(0.0, index=year_list, dtype=float)
    r166 = pd.Series(0.0, index=year_list, dtype=float)
    grace_period2 = grace2 + 1
    maturity_period2 = maturity2 + 1
    amort_periods2 = maturity2 - grace2
    for y in year_list:
        r171 = float(r162.get(y - grace_period2, 0.0))
        r173 = float(r162.get(y - maturity_period2, 0.0))
        r168 = (r171 - r173) / float(amort_periods2) if amort_periods2 > 0 else 0.0
        r163.loc[y] = float(r163.get(y - 1, 0.0)) + float(cds_abi_post.loc[y]) - r168
        r167 = float(r163.get(y - 1, 0.0)) * rate2
        r166.loc[y] = r167 + r168

    # Excel ``PV Stress`` R150/R164 copy the residual stock (R149/R163);
    # the 5% USD discount rate is unused for these C4 blocks.
    c4_pv_stress = r149 + r163
    c4_ds_stress = r152 + r166

    return c4_pv_stress, c4_ds_stress


__all__ = [
    "ShortenedLoanTerms",
    "apply_c4_residual_overrides",
    "c4_residual_overrides",
    "commercial_instruments",
    "commercial_pv_delta_usd",
    "commercial_weighted_interest_rate",
    "commercial_weighted_resfin_terms",
    "compute_c4_pv_stress_usd",
    "shorten_loan_terms",
    "shortened_terms_for_instrument",
]
