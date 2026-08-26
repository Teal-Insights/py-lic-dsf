"""Baseline - external sustainability ratios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.book import MacroDebtBook


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


def _lc_share_of_total_external(macro: MacroDebtBook) -> pd.Series:
    """LC-denominated external share of total external USD (Macro R85 / 100).

    History uses Input 3 row 208 / total external. Projection uses locally-issued
    stock plus LC-NR instrument stocks over total external (Macro R6).
    """
    from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument
    from lic_dsf.pv.macro_debt import stocks as _stocks

    years = macro.inputs.years
    total = _stocks.total_external(macro.inputs, macro.external)
    total = total.reindex(list(years)).replace(0.0, pd.NA)
    hist_usd = macro.inputs.lc_external_usd
    if hist_usd is None:
        hist = pd.Series(0.0, index=list(years), dtype=float)
    else:
        hist = (hist_usd.reindex(list(years)).fillna(0.0) / total).astype(float)

    local = pd.Series(0.0, index=list(years), dtype=float)
    if macro.external is not None:
        local = (
            macro.external.inputs.locally_issued_debt_stock.reindex(list(years))
            .fillna(0.0)
            .astype(float)
        )
        for inst in macro.external.portfolio.instruments:
            if not isinstance(inst, LocalCurrencyNonResidentInstrument):
                continue
            stock = inst.external().loc["Stock of new forex debt (in USD)"]
            for year in years:
                if year in stock.index:
                    local.loc[year] = float(local.loc[year]) + float(stock.loc[year])
    proj = (local / total).astype(float)
    return _stocks.hist_proj(
        hist, proj, years, macro.inputs.first_projection_year
    ).fillna(0.0)


@dataclass(slots=True)
class BaselineExternalBook:
    """External DSA baseline ratios (Excel ``Baseline - external``).

    Consumes ``MacroDebtBook`` denominators and ``ExternalDebtBook`` PPG PV /
    service. Year horizon follows Macro.
    """

    macro: MacroDebtBook
    external: ExternalDebtBook

    @property
    def years(self) -> tuple[int, ...]:
        """Projection / history years from Macro."""
        return self.macro.inputs.years

    def pv_ppg_usd(self) -> pd.Series:
        """PPG external PV in USD (Ext R391 / Baseline R50)."""
        return _align(self.external.total_pv_of_debt(), self.years)

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """Baseline R35: ``100 × PV / GDP``, clamped at 0."""
        return _clamp_nonnegative(_pct(self.pv_ppg_usd(), self.macro.gdp_usd()))

    def exports_to_gdp(self) -> pd.Series:
        """Baseline R19: exports / GDP × 100."""
        return _pct(self.macro.exports(), self.macro.gdp_usd())

    def revenues_to_gdp(self) -> pd.Series:
        """Baseline R60: Macro R98 = revenues excl. grants / GDP × 100."""
        return _pct(self.macro.revenues_excl_grants(), self.macro.gdp_usd())

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """Baseline R36: ``R35 / R19 × 100`` (= ``100 × PV / exports``)."""
        return (self.pv_ppg_external_to_gdp() / self.exports_to_gdp() * 100.0).astype(
            float
        )

    def pv_ppg_external_to_revenue(self) -> pd.Series:
        """Baseline R37: ``R35 / R60 × 100``."""
        return (self.pv_ppg_external_to_gdp() / self.revenues_to_gdp() * 100.0).astype(
            float
        )

    def total_external_debt_service_to_exports(self) -> pd.Series:
        """Baseline R38: ``100 × (prior priv ST + ext interest + ext amort) / exports``."""
        prior_priv_st = pd.Series(
            self.macro.private_st_external().shift(1), dtype=float
        ).fillna(0.0)
        numer = (
            prior_priv_st
            + self.macro.external_interest()
            + self.macro.external_amortization()
        )
        return _pct(numer, self.macro.exports())

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """Baseline R39: ``max(0, R38 − private DS/exports)``."""
        return _clamp_nonnegative(
            self.total_external_debt_service_to_exports()
            - self.macro.private_debt_service_to_exports()
        )

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """Baseline R40: ``max(0, R39 × exports / revenues_excl_grants)``."""
        # R39 is already a percent; Excel does (R39 * exports) / R95
        # = PPG_DS/exports*100 * exports / rev = 100 * PPG_DS / rev.
        raw = (
            self.ppg_debt_service_to_exports()
            * self.macro.exports()
            / self.macro.revenues_excl_grants().replace(0.0, pd.NA)
        )
        return _clamp_nonnegative(
            raw.replace([float("inf"), float("-inf")], pd.NA).astype(float)
        )

    def external_gfn_usd(self) -> pd.Series:
        """Baseline R41: Macro R74."""
        return self.macro.external_gfn()

    def external_debt_to_gdp(self) -> pd.Series:
        """Output 1-1 R8 / Baseline R12: hybrid external debt / GDP × 100."""
        return self.macro.hybrid_external_debt_to_gdp()

    def ppg_external_to_gdp_nominal(self) -> pd.Series:
        """Output 1-1 R9 / Baseline R13: hybrid PPG external / GDP × 100."""
        return self.macro.hybrid_ppg_external_to_gdp()

    def change_in_external_debt(self) -> pd.Series:
        """Output 1-1 R11: Δ of R8."""
        series = self.external_debt_to_gdp()
        return (series - series.shift(1)).astype(float)

    def non_interest_cad_to_gdp(self) -> pd.Series:
        """Output 1-1 R13: non-interest current-account deficit / GDP."""
        numer = -(self.macro.current_account() + self.macro.external_interest())
        return _pct(numer, self.macro.gdp_usd())

    def goods_services_deficit_to_gdp(self) -> pd.Series:
        """Output 1-1 R14: (imports − exports) / GDP × 100."""
        return _pct(
            self.macro.imports() - self.macro.exports(), self.macro.gdp_usd()
        )

    def imports_to_gdp(self) -> pd.Series:
        """Output 1-1 R16."""
        return _pct(self.macro.imports(), self.macro.gdp_usd())

    def net_transfers_to_gdp(self) -> pd.Series:
        """Output 1-1 R17 (negative = inflow)."""
        return _pct(-self.macro.current_transfers_net(), self.macro.gdp_usd())

    def official_transfers_to_gdp(self) -> pd.Series:
        """Output 1-1 R18 (negative = inflow)."""
        return _pct(-self.macro.current_transfers_official(), self.macro.gdp_usd())

    def other_current_account_to_gdp(self) -> pd.Series:
        """Output 1-1 R19: CAD residual after G&S and transfers."""
        return (
            self.non_interest_cad_to_gdp()
            - self.goods_services_deficit_to_gdp()
            - self.net_transfers_to_gdp()
        ).astype(float)

    def net_fdi_to_gdp(self) -> pd.Series:
        """Output 1-1 R20 (negative = inflow)."""
        return _pct(-self.macro.fdi(), self.macro.gdp_usd())

    def exceptional_financing_to_gdp(self) -> pd.Series:
        """Output 1-1 R27 (negative = inflow)."""
        return _pct(-self.macro.exceptional_financing(), self.macro.gdp_usd())

    def endogenous_denominator(self) -> pd.Series:
        """Output 1-1 R22: ``1 + g + ρ + gρ``."""
        g = self.macro.real_gdp_growth() / 100.0
        rho = self.macro.usd_deflator_growth() / 100.0
        return (1.0 + g + rho + g * rho).astype(float)

    def endogenous_debt_dynamics(self) -> pd.DataFrame:
        """Output 1-1 R21 / R23–R25 endogenous contributions.

        Uses the Baseline-external identity
        ``[r − g − ρ(1+g) + εα(1+r)] / (1+g+ρ+gρ) × prior debt/GDP``,
        where ``r`` is Baseline R54 (ext interest / prior hybrid stock).
        """
        years = self.years
        prev = _align(self.external_debt_to_gdp().shift(1), years)
        den = self.endogenous_denominator()
        real_g = _align(self.macro.real_gdp_growth(), years)
        defl = _align(self.macro.usd_deflator_growth(), years)
        dep = _align(self.macro.depreciation_of_nc(), years)
        rate = _align(self.effective_interest_rate_external(), years)
        # Baseline R29 uses prior-year LC share (O43), not the current year.
        alpha = (
            _lc_share_of_total_external(self.macro)
            .reindex(list(years))
            .fillna(0.0)
            .shift(1)
        )
        r23 = (rate / 100.0) * prev / den
        r24 = -(real_g / 100.0) * prev / den
        r25 = (
            -(defl / 100.0 * (1.0 + real_g / 100.0)) * prev / den
            + alpha * (-dep / 100.0) * (1.0 + rate / 100.0) * prev / den
        )
        r21 = r23 + r24 + r25
        return pd.DataFrame(
            {
                "endogenous": r21,
                "interest": r23,
                "real_gdp": r24,
                "price_fx": r25,
            }
        )

    def identified_net_debt_creating_flows(self) -> pd.Series:
        """Output 1-1 R12: CAD + FDI + endogenous dynamics."""
        endog = self.endogenous_debt_dynamics()["endogenous"]
        return (
            self.non_interest_cad_to_gdp() + self.net_fdi_to_gdp() + endog
        ).astype(float)

    def residual_debt_creating_flows(self) -> pd.Series:
        """Output 1-1 R26: change in debt − identified flows."""
        return (
            self.change_in_external_debt() - self.identified_net_debt_creating_flows()
        ).astype(float)

    def stabilizing_non_interest_cad(self) -> pd.Series:
        """Output 1-1 R59: non-interest CAD that holds the debt ratio fixed."""
        return (
            self.non_interest_cad_to_gdp() - self.change_in_external_debt()
        ).astype(float)

    def grants_usd(self) -> pd.Series:
        """Grants in USD (LCU grants / FX(pa))."""
        return self.macro.grants() / self.macro.fx_pa().replace(0.0, pd.NA)

    def aid_flows_usd(self) -> pd.Series:
        """Output 1-1 R45: grants + concessional loans (USD)."""
        return (self.grants_usd() + self.macro.concessional_loans()).astype(float)

    def grant_equivalent_to_gdp(self) -> pd.Series:
        """Output 1-1 R48: (GE dollars + grants) / GDP × 100."""
        ge = self.external.grant_element_value()
        numer = _align(ge, self.years).fillna(0.0) + _align(
            self.grants_usd(), self.years
        ).fillna(0.0)
        return _pct(numer, self.macro.gdp_usd())

    def grant_equivalent_to_external_financing(self) -> pd.Series:
        """Output 1-1 R49: ``(grants + GE$) / (grants + new MLT disb)`` × 100."""
        ge = _align(self.external.grant_element_value(), self.years).fillna(0.0)
        grants = _align(self.grants_usd(), self.years).fillna(0.0)
        disb = (
            self.external.portfolio.aggregate_external()
            .loc["New forex borrowing (gross, USD)"]
            .reindex(list(self.years))
            .fillna(0.0)
        )
        return _pct(ge + grants, grants + disb)

    def effective_interest_rate_external(self) -> pd.Series:
        """Output 1-1 R40 / Baseline R54: ext interest / prior hybrid stock × 100."""
        interest = _align(self.macro.external_interest(), self.years)
        prior_ratio = _align(self.external_debt_to_gdp().shift(1), self.years) / 100.0
        prior_gdp = _align(self.macro.gdp_usd().shift(1), self.years)
        stock = (prior_ratio * prior_gdp).replace(0.0, pd.NA)
        return (100.0 * interest / stock).astype(float)

    def pv_total_external_to_gdp(self) -> pd.Series:
        """Output 1-1 R54: PPG PV + private face / GDP × 100."""
        numer = self.pv_ppg_usd() + self.macro.private_external()
        return _pct(numer, self.macro.gdp_usd())

    def pv_total_external_to_exports(self) -> pd.Series:
        """Output 1-1 R55."""
        return (
            self.pv_total_external_to_gdp() / self.exports_to_gdp() * 100.0
        ).astype(float)

    def pv_change_over_prior_gdp(self) -> pd.Series:
        """Output 1-1 R58: ``(PV_t − PV_{t-1}) / GDP_{t-1}`` × 100."""
        pv = self.pv_ppg_usd()
        gdp = self.macro.gdp_usd()
        return _pct(pv - pv.shift(1), gdp.shift(1))

    def export_growth(self) -> pd.Series:
        """Output 1-1 R41: USD export growth."""
        level = self.macro.exports()
        return (100.0 * (level / level.shift(1).replace(0.0, pd.NA) - 1.0)).astype(
            float
        )

    def import_growth(self) -> pd.Series:
        """Output 1-1 R42: USD import growth."""
        level = self.macro.imports()
        return (100.0 * (level / level.shift(1).replace(0.0, pd.NA) - 1.0)).astype(
            float
        )

    def nominal_dollar_gdp_growth(self) -> pd.Series:
        """Output 1-1 R51."""
        level = self.macro.gdp_usd()
        return (100.0 * (level / level.shift(1).replace(0.0, pd.NA) - 1.0)).astype(
            float
        )
