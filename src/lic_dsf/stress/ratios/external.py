"""External stress ratio projections (B-sheet R35/R36/R39/R40)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.stress.bound import bsheet_exports_to_gdp
from lic_dsf.stress.path import ShockedMacroPath
from lic_dsf.stress.residual_pv import ResFinOverlay


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _clamp_nonnegative(series: pd.Series) -> pd.Series:
    out = series.copy()
    mask = out.notna() & (out < 0)
    return out.where(~mask, 0.0)


def _pct(numer: pd.Series, denom: pd.Series) -> pd.Series:
    out = 100.0 * numer / denom.replace(0.0, pd.NA)
    return out.replace([float("inf"), float("-inf")], pd.NA).astype(float)


@dataclass(slots=True)
class StressExternalRatios:
    """External DSA ratios under stress (no shock / gap logic).

    Numerators: baseline Ext PPG PV / service + ResFin overlay.
    Denominators: shocked macro path (and B-sheet exports identity).
    """

    path: ShockedMacroPath
    external: ExternalDebtBook
    resfin: ResFinOverlay
    fx_depreciation_pct: float = 0.0
    additional_borrowing_interest: pd.Series | None = None
    commercial_pv_delta: pd.Series | None = None
    commercial_ds_delta: pd.Series | None = None
    c4_pv_stress: pd.Series | None = None
    c4_ds_stress: pd.Series | None = None

    @classmethod
    def from_path(
        cls,
        path: ShockedMacroPath,
        external: ExternalDebtBook,
        resfin: ResFinOverlay,
        *,
        additional_borrowing_interest: pd.Series | None = None,
        commercial_pv_delta: pd.Series | None = None,
        commercial_ds_delta: pd.Series | None = None,
        c4_pv_stress: pd.Series | None = None,
        c4_ds_stress: pd.Series | None = None,
    ) -> StressExternalRatios:
        """Build ratios using FX depreciation from path metadata."""
        return cls(
            path=path,
            external=external,
            resfin=resfin,
            fx_depreciation_pct=float(path.metadata.fx_depreciation_pct),
            additional_borrowing_interest=additional_borrowing_interest,
            commercial_pv_delta=commercial_pv_delta,
            commercial_ds_delta=commercial_ds_delta,
            c4_pv_stress=c4_pv_stress,
            c4_ds_stress=c4_ds_stress,
        )

    @property
    def years(self) -> tuple[int, ...]:
        """Year horizon from the shocked macro path."""
        return self.path.years

    def pv_ppg_usd(self) -> pd.Series:
        """Stressed PPG external PV (Ext R391 + ResFin PV [+ C4 commercial Δ])."""
        out = (
            _align(self.external.total_pv_of_debt(), self.years)
            + _align(self.resfin.pv, self.years).fillna(0.0)
        )
        if self.commercial_pv_delta is not None:
            out = out + _align(self.commercial_pv_delta, self.years).fillna(0.0)
        if self.c4_pv_stress is not None:
            out = out + _align(self.c4_pv_stress, self.years).fillna(0.0)
        return out.astype(float)

    def pv_ppg_external_to_gdp(self) -> pd.Series:
        """B-sheet R35."""
        return _clamp_nonnegative(_pct(self.pv_ppg_usd(), self.path.shocked.gdp_usd()))

    def exports_to_gdp(self) -> pd.Series:
        """Exports / GDP × 100 (B-sheet R19)."""
        return bsheet_exports_to_gdp(
            self.path.baseline,
            self.path.shocked,
            fx_depreciation_pct=self.fx_depreciation_pct,
        )

    def revenues_to_gdp(self) -> pd.Series:
        """Revenues excl. grants / GDP × 100."""
        return _pct(
            self.path.shocked.revenues_excl_grants(), self.path.shocked.gdp_usd()
        )

    def pv_ppg_external_to_exports(self) -> pd.Series:
        """B-sheet R36."""
        return (self.pv_ppg_external_to_gdp() / self.exports_to_gdp() * 100.0).astype(
            float
        )

    def pv_ppg_external_to_revenue(self) -> pd.Series:
        """B-sheet R37."""
        return (self.pv_ppg_external_to_gdp() / self.revenues_to_gdp() * 100.0).astype(
            float
        )

    def total_external_debt_service_to_exports(self) -> pd.Series:
        """Total external DS / exports including ResFin service."""
        macro = self.path.shocked
        prior_priv_st = pd.Series(
            macro.private_st_external().shift(1), dtype=float
        ).fillna(0.0)
        numer = (
            prior_priv_st
            + macro.external_interest()
            + macro.external_amortization()
            + _align(self.resfin.interest, self.years).fillna(0.0)
            + _align(self.resfin.amortization, self.years).fillna(0.0)
        )
        if self.additional_borrowing_interest is not None:
            numer = numer + _align(
                self.additional_borrowing_interest, self.years
            ).fillna(0.0)
        if self.commercial_ds_delta is not None:
            numer = numer + _align(self.commercial_ds_delta, self.years).fillna(0.0)
        if self.c4_ds_stress is not None:
            numer = numer + _align(self.c4_ds_stress, self.years).fillna(0.0)
        return _pct(numer, macro.exports())

    def ppg_debt_service_to_exports(self) -> pd.Series:
        """B-sheet R39."""
        return _clamp_nonnegative(
            self.total_external_debt_service_to_exports()
            - self.path.shocked.private_debt_service_to_exports()
        )

    def ppg_debt_service_to_revenue(self) -> pd.Series:
        """B-sheet R40 (C4: Excel ``C4_Market_financing`` R99 uses baseline rev)."""
        revenues = (
            self.path.baseline.revenues_excl_grants()
            if self.path.metadata.ds_revenue_uses_baseline
            else self.path.shocked.revenues_excl_grants()
        )
        raw = (
            self.ppg_debt_service_to_exports()
            * self.path.shocked.exports()
            / revenues.replace(0.0, pd.NA)
        )
        return _clamp_nonnegative(
            raw.replace([float("inf"), float("-inf")], pd.NA).astype(float)
        )

    def external_gfn_usd(self) -> pd.Series:
        """Macro external GFN under the shocked path."""
        return self.path.shocked.external_gfn()


__all__ = ["StressExternalRatios"]
