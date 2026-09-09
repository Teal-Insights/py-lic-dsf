"""Residual-financing overlay / fill dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lic_dsf.pv import PresentValueInstrument


@dataclass(slots=True)
class ResFinOverlay:
    """PV / debt-service series for residual external MLT under stress."""

    pv: pd.Series
    interest: pd.Series
    amortization: pd.Series
    debt_service: pd.Series
    instrument: PresentValueInstrument


@dataclass(slots=True)
class ResidualFill:
    """Three-way residual financing disbursements (public DSA)."""

    external_mlt_usd: pd.Series
    domestic_mlt_lcu: pd.Series
    domestic_st_lcu: pd.Series


@dataclass(slots=True)
class DomMltOverlay:
    """Domestic MLT residual schedule in LCU (``PV_ResFin_pub`` R85–R91)."""

    stock: pd.Series
    interest: pd.Series
    amortization: pd.Series
    debt_service: pd.Series
    pv: pd.Series
    disbursements: pd.Series


@dataclass(slots=True)
class DomStOverlay:
    """Domestic ST residual rollover in LCU (``PV_ResFin_pub`` R98–R99)."""

    stock: pd.Series
    interest: pd.Series
    disbursements: pd.Series


@dataclass(slots=True)
class PublicResFinOverlay:
    """Bundled public residual financing overlays."""

    fill: ResidualFill
    ext: ResFinOverlay
    dom_mlt: DomMltOverlay
    dom_st: DomStOverlay
