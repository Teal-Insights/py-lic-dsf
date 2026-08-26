"""Output 3-x stress panels and Excel-geometry tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook
from lic_dsf.stress.public import StressPublicBook
from lic_dsf.stress.scenario import StressExternalBook

OUTPUT31_SHEET = "Output 3-1 Stress-external"
OUTPUT32_SHEET = "Output 3-2 Stress-public"

_EXT_INDICATORS: tuple[tuple[str, str], ...] = (
    ("PV of debt-to GDP ratio", "pv_ppg_external_to_gdp"),
    ("PV of debt-to-exports ratio", "pv_ppg_external_to_exports"),
    ("Debt service-to-exports ratio", "ppg_debt_service_to_exports"),
    ("Debt service-to-revenue ratio", "ppg_debt_service_to_revenue"),
)

_PUB_INDICATORS: tuple[tuple[str, str], ...] = (
    ("PV of Debt-to-GDP Ratio", "pv_public_debt_to_gdp"),
    ("PV of Debt-to-Revenue Ratio", "pv_public_debt_to_revenue_grants"),
    ("Debt Service-to-Revenue Ratio", "debt_service_to_revenue_grants"),
    ("Debt Service-to-GDP Ratio", "debt_service_to_gdp"),
)

_EXT_SCENARIO_LABELS: dict[str, str] = {
    "Baseline": "Baseline",
    "A1_Historical": "A1 historical",
    "A2_Custom": "A2 custom",
    "B1_GDP": "B1. Real GDP growth",
    "B2_PrimaryBalance": "B2. Primary balance",
    "B3_Exports": "B3. Exports",
    "B4_OtherFlows": "B4. Other flows",
    "B5_FX": "B5. Depreciation",
    "B6_Combo": "B6. Combination of B1-B5",
    "C1_CombinedCL": "C1. Combined contingent liabilities",
    "C2_NaturalDisaster": "C2. Natural disaster",
    "C3_Commodity": "C3. Commodity price",
    "C4_Market": "C4. Market Financing",
    "Threshold": "Threshold",
}


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


def stress_public_panel(book: StressPublicBook) -> pd.DataFrame:
    """Output 1-2-shaped public stress sustainability rows."""
    return pd.DataFrame(
        {
            "Public sector debt / GDP": book.public_sector_debt_to_gdp(),
            "PV of public debt / GDP": book.pv_public_debt_to_gdp(),
            "PV of public debt / revenue+grants": (
                book.pv_public_debt_to_revenue_grants()
            ),
            "Debt service / revenue+grants": book.debt_service_to_revenue_grants(),
            "Public GFN (LCU)": book.public_gfn(),
        }
    ).T


def _years_from(*books: Any) -> list[int]:
    for book in books:
        if book is not None:
            return [int(y) for y in book.years]
    return []


def output_31_table(
    ext_base: BaselineExternalBook,
    *,
    historical: StressExternalBook | None = None,
    external_stress: dict[str, Any] | None = None,
    tailored: dict[str, Any] | None = None,
    thresholds: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Output 3-1 MultiIndex table ``(indicator, scenario) × years``.

    Args:
        ext_base: Baseline external book.
        historical: Optional A1 book.
        external_stress: B-test id → book (from ``run_standard_external_stress``).
        tailored: A2/C* id → book (from ``run_tailored_external_stress``).
        thresholds: CI threshold map (``pv_debt_to_gdp``, …).

    Returns:
        DataFrame with a two-level index.
    """
    years = _years_from(ext_base)
    store: dict[tuple[str, str], pd.Series] = {}
    books: dict[str, Any] = {"Baseline": ext_base}
    if historical is not None:
        books["A1_Historical"] = historical
    if external_stress:
        books.update(external_stress)
    if tailored:
        books.update(tailored)
    thresh_keys = {
        "PV of debt-to GDP ratio": "pv_debt_to_gdp",
        "PV of debt-to-exports ratio": "pv_debt_to_exports",
        "Debt service-to-exports ratio": "debt_service_to_exports",
        "Debt service-to-revenue ratio": "debt_service_to_revenue",
    }
    for indicator, method in _EXT_INDICATORS:
        for sid, book in books.items():
            label = _EXT_SCENARIO_LABELS.get(sid, sid)
            getter = getattr(book, method, None)
            if getter is None:
                continue
            store[(indicator, label)] = getter().reindex(years).astype(float)
        if thresholds is not None and indicator in thresh_keys:
            key = thresh_keys[indicator]
            if key in thresholds:
                store[(indicator, "Threshold")] = pd.Series(
                    float(thresholds[key]), index=years, dtype=float
                )
    table = pd.DataFrame(store).T
    table.index.names = ["indicator", "scenario"]
    return table


def output_32_table(
    pub_base: BaselinePublicBook,
    *,
    public_stress: dict[str, StressPublicBook] | None = None,
    public_threshold: float | None = None,
) -> pd.DataFrame:
    """Output 3-2 MultiIndex table ``(indicator, scenario) × years``."""
    years = _years_from(pub_base)
    store: dict[tuple[str, str], pd.Series] = {}
    books: dict[str, Any] = {"Baseline": pub_base}
    if public_stress:
        books.update(public_stress)
    for indicator, method in _PUB_INDICATORS:
        for sid, book in books.items():
            label = _EXT_SCENARIO_LABELS.get(sid, sid)
            getter = getattr(book, method, None)
            if getter is None:
                continue
            store[(indicator, label)] = getter().reindex(years).astype(float)
        if (
            public_threshold is not None
            and indicator == "PV of Debt-to-GDP Ratio"
        ):
            store[(indicator, "Threshold")] = pd.Series(
                float(public_threshold), index=years, dtype=float
            )
    table = pd.DataFrame(store).T
    table.index.names = ["indicator", "scenario"]
    return table
