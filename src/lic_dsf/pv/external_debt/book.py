"""Ext_Debt_Data book: existing debt + new portfolio + headlines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from lic_dsf.pv.external_debt.existing_debt import (
    existing_mlt_nominal,
    existing_mlt_pv,
)
from lic_dsf.pv.external_debt.residual import (
    ResidualFinancingOverrides,
    ResidualFinancingParams,
    calculate_residual_defaults,
    resolve_residual_params,
)

if TYPE_CHECKING:
    from lic_dsf.pv.external_debt.types import ExternalDebtInputs
    from lic_dsf.pv.portfolio import PVPortfolio


@dataclass(slots=True)
class ExternalDebtBook:
    """PPG external debt book (Excel ``Ext_Debt_Data``).

    New MLT panels come from ``portfolio``; existing MLT NPV / stock,
    locally-issued Input 5 series, and Ext headlines come from ``inputs``.
    """

    portfolio: PVPortfolio
    inputs: ExternalDebtInputs

    def new_debt_service(self) -> pd.DataFrame:
        """Interest + amortization portfolio totals (new MLT)."""
        return self.portfolio.new_debt_service()

    def new_mlt_pv(self) -> pd.Series:
        """PV of new MLT debt (Ext R279)."""
        return self._align(self.portfolio.pv().sum(axis=0))

    def new_mlt_nominal(self) -> pd.Series:
        """Nominal stock of new MLT debt (Ext R329)."""
        return self._align(self.portfolio.stock().sum(axis=0))

    def existing_mlt_pv(self) -> pd.DataFrame:
        """PV of existing MLT debt by creditor + Total (Ext R242)."""
        return existing_mlt_pv(self.inputs)

    def existing_mlt_nominal(self) -> pd.Series:
        """Nominal existing MLT stock excluding arrears (Ext R67)."""
        return existing_mlt_nominal(self.inputs)

    def total_st_external(self) -> pd.Series:
        """Total ST external debt including locally-issued ST (Ext R386)."""
        years = list(self.inputs.years)
        return self.inputs.short_term_external.reindex(years).fillna(
            0.0
        ) + self.inputs.locally_issued_st.reindex(years).fillna(0.0)

    def total_pv_of_debt(self) -> pd.Series:
        """Total PV of PPG external debt (Ext R391)."""
        years = list(self.inputs.years)
        existing = self.existing_mlt_pv().loc["Total"].reindex(years).fillna(0.0)
        arrears = self.inputs.arrears.reindex(years).fillna(0.0)
        new_pv = self.new_mlt_pv().reindex(years).fillna(0.0)
        st = self.total_st_external().reindex(years).fillna(0.0)
        sdr = self.inputs.sdr_pv.reindex(years).fillna(0.0)
        return existing + arrears + new_pv + st + sdr

    def total_public_debt_service(self) -> pd.DataFrame:
        """Public debt service totals (Ext R394–396).

        Includes existing external + locally-issued service, new MLT service,
        ST principal/interest, and SDR interest.
        """
        years = list(self.inputs.years)
        service = self.inputs.existing_debt_service.reindex(columns=years).fillna(0.0)
        existing_total = service.sum(axis=0)
        principal_existing = self.inputs.existing_principal.reindex(years).fillna(0.0)
        interest_existing = existing_total - principal_existing

        local_principal = self.inputs.locally_issued_principal.reindex(years).fillna(
            0.0
        )
        local_interest = self.inputs.locally_issued_interest.reindex(years).fillna(0.0)

        new_service = self.new_debt_service()
        new_principal = new_service.loc["Amortization"].reindex(years).fillna(0.0)
        new_interest = new_service.loc["Interest"].reindex(years).fillna(0.0)

        st = self.inputs.short_term_external.reindex(years).fillna(0.0)
        local_st_principal = self.inputs.locally_issued_st_principal.reindex(
            years
        ).fillna(0.0)
        local_st_interest = self.inputs.locally_issued_st_interest.reindex(
            years
        ).fillna(0.0)
        st_rate = float(self.inputs.short_term_interest_rate)

        st_principal = pd.Series(0.0, index=years, dtype=float)
        st_interest = pd.Series(0.0, index=years, dtype=float)
        for i, year in enumerate(years):
            if i == 0:
                st_principal.loc[year] = float(local_st_principal.loc[year])
                st_interest.loc[year] = float(local_st_interest.loc[year])
            else:
                prev = years[i - 1]
                # Ext R387 / R380: prior external ST + current local ST bits.
                st_principal.loc[year] = float(st.loc[prev]) + float(
                    local_st_principal.loc[year]
                )
                st_interest.loc[year] = float(st.loc[prev]) * st_rate + float(
                    local_st_interest.loc[year]
                )

        sdr_interest = self.inputs.sdr_interest.reindex(years).fillna(0.0)
        principal = principal_existing + local_principal + new_principal + st_principal
        interest = (
            interest_existing
            + local_interest
            + new_interest
            + st_interest
            + sdr_interest
        )
        return pd.DataFrame(
            [
                principal + interest,
                principal,
                interest,
            ],
            index=[
                "Total public debt service",
                "    of which: principal",
                "    of which: interest",
            ],
        )

    def nominal_ppg_check(self) -> pd.Series:
        """Consistency vs Macro PPG stock (Ext R393).

        Uses external ST excluding locally-issued ST (Ext R379), matching Excel.
        """
        years = list(self.inputs.years)
        return (
            self.inputs.macro_ppg_external.reindex(years).fillna(0.0)
            - self.new_mlt_nominal().reindex(years).fillna(0.0)
            - self.existing_mlt_nominal().reindex(years).fillna(0.0)
            - self.inputs.short_term_external.reindex(years).fillna(0.0)
            - self.inputs.arrears.reindex(years).fillna(0.0)
        )

    def residual_defaults(
        self, *, average_years: int = 11
    ) -> ResidualFinancingParams:
        """Input 7 default shares/terms (Ext ``C126–C128``, ``C131–C133``)."""
        return calculate_residual_defaults(self, average_years=average_years)

    def residual_params(
        self,
        overrides: ResidualFinancingOverrides | None = None,
        *,
        average_years: int = 11,
    ) -> ResidualFinancingParams:
        """Defaults with optional Input 7-style per-field overrides."""
        return resolve_residual_params(
            self.residual_defaults(average_years=average_years),
            overrides,
        )

    def summary(self) -> pd.DataFrame:
        """Ext_Debt-shaped headline table (totals)."""
        years = list(self.inputs.years)
        ds = self.total_public_debt_service()
        rows = {
            "PV of existing MLT debt": self.existing_mlt_pv().loc["Total"],
            "PV of existing arrears": self.inputs.arrears,
            "PV of new MLT debt": self.new_mlt_pv(),
            "Total ST external debt": self.total_st_external(),
            "    of which: locally-issued ST": self.inputs.locally_issued_st,
            "PV of net use of SDRs": self.inputs.sdr_pv,
            "Total PV of debt": self.total_pv_of_debt(),
            "Nominal value of new MLT": self.new_mlt_nominal(),
            "Nominal PPG debt check": self.nominal_ppg_check(),
            "Total public debt service": ds.loc["Total public debt service"],
            "    of which: principal": ds.loc["    of which: principal"],
            "    of which: interest": ds.loc["    of which: interest"],
            "Locally-issued MLT stock": self.inputs.locally_issued_debt_stock,
            "Locally-issued principal": self.inputs.locally_issued_principal,
            "Locally-issued interest": self.inputs.locally_issued_interest,
        }
        frame = pd.DataFrame(rows).T
        return frame.reindex(columns=years).fillna(0.0)

    def _align(self, series: pd.Series) -> pd.Series:
        return series.reindex(list(self.inputs.years)).fillna(0.0)
