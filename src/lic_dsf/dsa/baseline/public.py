"""Baseline - public sustainability ratios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.book import ExternalDebtBook
    from lic_dsf.pv.macro_debt.book import MacroDebtBook


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


@dataclass(slots=True)
class BaselinePublicBook:
    """Public DSA baseline ratios (Excel ``Baseline - public``).

    Consumes ``MacroDebtBook`` public debt / fiscal series. ``external`` is
    retained for API symmetry with ``BaselineExternalBook`` (Macro already
    stitches Ext into PV / service when constructed with an Ext book).
    """

    macro: MacroDebtBook
    external: ExternalDebtBook

    @property
    def years(self) -> tuple[int, ...]:
        """Projection / history years from Macro."""
        return self.macro.inputs.years

    def gdp_lcu(self) -> pd.Series:
        """Baseline R52: ``GDP_USD × FX(pa)``."""
        return self.macro.gdp_lcu()

    def public_sector_debt_to_gdp(self) -> pd.Series:
        """Baseline R12: ``100 × Macro R80 / GDP_LCU``."""
        return _pct(self.macro.total_public_debt(), self.gdp_lcu())

    def ppg_external_debt_to_gdp(self) -> pd.Series:
        """Baseline R20: ``100 × Macro R81 / GDP_LCU``."""
        return _pct(self.macro.public_external_debt_lcu(), self.gdp_lcu())

    def revenues_incl_grants_to_gdp(self) -> pd.Series:
        """Baseline R24: ``100 × revenues / GDP_LCU``."""
        return _pct(self.macro.revenues_incl_grants(), self.gdp_lcu())

    def primary_deficit_to_gdp(self) -> pd.Series:
        """Baseline R23: ``100 × (primary expenditure − revenues) / GDP_LCU``.

        Sign convention matches Excel Realism 4: (+) = deficit, (−) = surplus.
        """
        return _pct(
            -self.macro.primary_balance(),
            self.gdp_lcu(),
        )

    def grants_to_gdp(self) -> pd.Series:
        """Baseline R25: ``100 × grants / GDP_LCU``."""
        return _pct(self.macro.grants(), self.gdp_lcu())

    def pv_public_debt_to_gdp(self) -> pd.Series:
        """Baseline R42: ``100 × (Macro R92 + R82) / GDP_LCU``, clamped at 0."""
        numer = self.macro.pv_external_lcu() + self.macro.public_domestic_debt()
        return _clamp_nonnegative(_pct(numer, self.gdp_lcu()))

    def pv_public_debt_to_revenue_grants(self) -> pd.Series:
        """Baseline R43: ``R42 / R24 × 100``."""
        return (
            self.pv_public_debt_to_gdp() / self.revenues_incl_grants_to_gdp() * 100.0
        ).astype(float)

    def debt_service_to_revenue_grants(self) -> pd.Series:
        """Baseline R45 Dom feeder.

        ``100 × (interest_exp + prior dom ST + (dom amort + PPG amort) × FX)
        / revenues``, clamped at 0.
        """
        prior_dom_st = pd.Series(self.macro.domestic_st().shift(1), dtype=float).fillna(
            0.0
        )
        numer = (
            self.macro.interest_expenditure()
            + prior_dom_st
            + (self.macro.domestic_amortization() + self.macro.ppg_amortization())
            * self.macro.fx_pa()
        )
        return _clamp_nonnegative(_pct(numer, self.macro.revenues_incl_grants()))

    def public_gfn_to_gdp(self) -> pd.Series:
        """Baseline R47: ``100 × Macro R101 / GDP_LCU``."""
        return _pct(self.macro.public_gfn(), self.gdp_lcu())

    def public_gfn(self) -> pd.Series:
        """Macro R101 level (Baseline R48 uses / FX)."""
        return self.macro.public_gfn()

    def change_in_public_debt(self) -> pd.Series:
        """Output 1-2 R11."""
        series = self.public_sector_debt_to_gdp()
        return (series - series.shift(1)).astype(float)

    def primary_expenditure_to_gdp(self) -> pd.Series:
        """Output 1-2 R16."""
        return _pct(self.macro.primary_expenditure(), self.gdp_lcu())

    def domestic_debt_to_gdp(self) -> pd.Series:
        """Output 1-2 R10 when filled: local-currency public debt / GDP."""
        return _pct(self.macro.public_domestic_debt(), self.gdp_lcu())

    def privatization_to_gdp(self) -> pd.Series:
        """Output 1-2 R24 (negative receipts)."""
        return _pct(-self.macro.inputs.privatization, self.gdp_lcu())

    def contingent_liabilities_to_gdp(self) -> pd.Series:
        """Output 1-2 R25."""
        return _pct(self.macro.inputs.contingent_liabilities, self.gdp_lcu())

    def debt_relief_to_gdp(self) -> pd.Series:
        """Output 1-2 R26."""
        return _pct(-self.macro.inputs.debt_relief, self.gdp_lcu())

    def other_debt_creating_to_gdp(self) -> pd.Series:
        """Output 1-2 R27."""
        return _pct(self.macro.inputs.other_debt_creating_flows, self.gdp_lcu())

    def other_identified_flows_to_gdp(self) -> pd.Series:
        """Output 1-2 R23: CL + other − privatization − relief."""
        return (
            self.contingent_liabilities_to_gdp()
            + self.other_debt_creating_to_gdp()
            + self.privatization_to_gdp()
            + self.debt_relief_to_gdp()
        ).astype(float)

    def automatic_debt_dynamics(self) -> pd.DataFrame:
        """Output 1-2 R17–R21 via ``public_automatic_debt_dynamics``."""
        from lic_dsf.realism.forecast_error import public_automatic_debt_dynamics

        fc = _pct(
            self.macro.fc_public_debt_usd() * self.macro.fx_eop(),
            self.gdp_lcu(),
        )
        return public_automatic_debt_dynamics(
            public_debt_to_gdp=self.public_sector_debt_to_gdp(),
            fc_debt_to_gdp=fc,
            real_gdp_growth=self.macro.real_gdp_growth(),
            gdp_deflator_growth=self.macro.lcu_deflator_growth(),
            us_deflator_growth=self.macro.foreign_deflator_growth(),
            fx_eop=self.macro.fx_eop(),
            interest_rate_external=self.macro.interest_rate_external(),
            interest_rate_domestic=self.macro.interest_rate_domestic(),
            public_interest_rate=self.average_nominal_interest_public(),
        )

    def identified_debt_creating_flows(self) -> pd.Series:
        """Output 1-2 R12: primary deficit + automatic + other identified."""
        auto = self.automatic_debt_dynamics()
        auto_sum = (
            auto.loc["DUCIR_GDP"]
            + auto.loc["DUCGDPR_GDP"]
            + auto.loc["DUCER_GDP"]
        )
        return (
            self.primary_deficit_to_gdp()
            + auto_sum
            + self.other_identified_flows_to_gdp()
        ).astype(float)

    def residual_public_flows(self) -> pd.Series:
        """Output 1-2 R28."""
        return (self.change_in_public_debt() - self.identified_debt_creating_flows()).astype(
            float
        )

    def pv_public_debt_to_revenue(self) -> pd.Series:
        """Output 1-2 R33 hide: PV / revenues excl. grants."""
        rev = _pct(self.macro.revenues_excl_grants() * self.macro.fx_pa(), self.gdp_lcu())
        return (self.pv_public_debt_to_gdp() / rev.replace(0.0, pd.NA) * 100.0).astype(
            float
        )

    def debt_service_to_revenue(self) -> pd.Series:
        """Output 1-2 R36 hide."""
        return _clamp_nonnegative(
            _pct(
                self.debt_service_to_revenue_grants()
                / 100.0
                * self.macro.revenues_incl_grants(),
                self.macro.revenues_incl_grants() - self.macro.grants(),
            )
        )

    def public_gfn_usd(self) -> pd.Series:
        """Output 1-2 R38."""
        return self.public_gfn() / self.macro.fx_pa().replace(0.0, pd.NA)

    def debt_service_to_gdp(self) -> pd.Series:
        """Public DS / GDP (Output 3-2 last block)."""
        return (
            self.debt_service_to_revenue_grants()
            * self.revenues_incl_grants_to_gdp()
            / 100.0
        ).astype(float)

    def stabilizing_primary_deficit(self) -> pd.Series:
        """Output 1-2 R57: primary deficit that holds the debt ratio fixed."""
        return (self.primary_deficit_to_gdp() - self.change_in_public_debt()).astype(
            float
        )

    def pv_contingent_liabilities_to_gdp(self) -> pd.Series:
        """Output 1-2 R58: face value of CL / GDP when a PV is not separately stored."""
        return self.contingent_liabilities_to_gdp()

    def average_nominal_interest_public(self) -> pd.Series:
        """Output 1-2 R43 / Baseline R54: interest expenditure / prior public debt."""
        return _pct(
            self.macro.interest_expenditure(),
            self.macro.total_public_debt().shift(1),
        )

    def real_interest_domestic(self) -> pd.Series:
        """Output 1-2 R47: ``(i_dom − π) / (1+π)``."""
        i_dom = self.macro.interest_rate_domestic()
        pi = self.macro.lcu_deflator_growth()
        return ((i_dom - pi) / (1.0 + pi / 100.0)).astype(float)

    def real_interest_external(self) -> pd.Series:
        """Output 1-2 R48: ``(i_ext − π_US) / (1+π_US)`` with Macro R112."""
        i_ext = self.macro.interest_rate_external()
        pi_us = self.macro.foreign_deflator_growth()
        return ((i_ext - pi_us) / (1.0 + pi_us / 100.0)).astype(float)

    def fc_public_debt_to_gdp(self) -> pd.Series:
        """Baseline R14: Macro R83 FC public debt × FX(eop) / GDP_LCU."""
        return _pct(
            self.macro.fc_public_debt_usd() * self.macro.fx_eop(),
            self.gdp_lcu(),
        )

    def real_interest_public(self) -> pd.Series:
        """Output 1-2 R46: lagged FC-share weighted average real rate."""
        d_tot = self.public_sector_debt_to_gdp().shift(1).replace(0.0, pd.NA)
        d_fc = self.fc_public_debt_to_gdp().shift(1)
        alpha = d_fc / d_tot
        return (
            alpha * self.real_interest_external()
            + (1.0 - alpha) * self.real_interest_domestic()
        ).astype(float)

    def fx_dollar_per_lc(self) -> pd.Series:
        """Output 1-2 R51: ``1 / FX(eop)``."""
        return (1.0 / self.macro.fx_eop().replace(0.0, pd.NA)).astype(float)

    def depreciation_of_nc_eop(self) -> pd.Series:
        """Output 1-2 R50: percent change in FX(eop) (LC per USD)."""
        fx = self.macro.fx_eop()
        return (100.0 * (fx / fx.shift(1).replace(0.0, pd.NA) - 1.0)).astype(float)

    def nominal_appreciation(self) -> pd.Series:
        """Output 1-2 R52: growth of USD per LC (``1 / FX(eop)``)."""
        rate = self.fx_dollar_per_lc()
        return (100.0 * (rate / rate.shift(1).replace(0.0, pd.NA) - 1.0)).astype(float)

    def real_exchange_rate_depreciation(self) -> pd.Series:
        """Output 1-2 R53: real depreciation from eop FX and the two deflators."""
        nom = self.depreciation_of_nc_eop()
        pi = self.macro.lcu_deflator_growth()
        pi_us = self.macro.foreign_deflator_growth()
        return (
            (100.0 + nom) * (1.0 + pi_us / 100.0) / (1.0 + pi / 100.0) - 100.0
        ).astype(float)

    def real_primary_spending_growth(self) -> pd.Series:
        """Output 1-2 R56 / Macro R100: growth of primary exp / LCU deflator index."""
        defl = self.macro.gdp_lcu() / self.macro.gdp_constant().replace(0.0, pd.NA)
        real = self.macro.primary_expenditure() / defl.replace(0.0, pd.NA)
        return (100.0 * (real / real.shift(1).replace(0.0, pd.NA) - 1.0)).astype(float)
