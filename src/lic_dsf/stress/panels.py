"""Output-shaped stress sustainability panels."""

from __future__ import annotations

import pandas as pd

from lic_dsf.stress.scenario import StressExternalBook


def stress_external_panel(book: StressExternalBook) -> pd.DataFrame:
    """Output 1-1-shaped sustainability rows for a stress scenario."""
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
