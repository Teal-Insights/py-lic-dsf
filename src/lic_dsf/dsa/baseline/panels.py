"""Output 1-1 / 1-2 shaped sustainability panels (no i18n chrome)."""

from __future__ import annotations

import pandas as pd

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook


def external_dsa_panel(book: BaselineExternalBook) -> pd.DataFrame:
    """Output 1-1 sustainability rows over the Macro year horizon."""
    return pd.DataFrame(
        {
            "PV of PPG external debt / GDP": book.pv_ppg_external_to_gdp(),
            "PV of PPG external debt / exports": book.pv_ppg_external_to_exports(),
            "PV of PPG external debt / revenue": book.pv_ppg_external_to_revenue(),
            "PPG debt service / exports": book.ppg_debt_service_to_exports(),
            "PPG debt service / revenue": book.ppg_debt_service_to_revenue(),
            "External GFN (USD)": book.external_gfn_usd(),
        }
    ).T


def public_dsa_panel(book: BaselinePublicBook) -> pd.DataFrame:
    """Output 1-2 sustainability / Dom feeder rows over the Macro year horizon."""
    return pd.DataFrame(
        {
            "Public sector debt / GDP": book.public_sector_debt_to_gdp(),
            "PPG external debt / GDP": book.ppg_external_debt_to_gdp(),
            "PV of public debt / GDP": book.pv_public_debt_to_gdp(),
            "PV of public debt / revenue+grants": (
                book.pv_public_debt_to_revenue_grants()
            ),
            "Debt service / revenue+grants": book.debt_service_to_revenue_grants(),
            "Public GFN / GDP": book.public_gfn_to_gdp(),
        }
    ).T
