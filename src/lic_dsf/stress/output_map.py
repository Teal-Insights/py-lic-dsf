"""Map stress results onto Output 3-1 / 3-2 Excel geometry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook
from lic_dsf.stress.result import StressScenarioResult

EXT_INDICATORS: tuple[tuple[str, str], ...] = (
    ("PV of debt-to GDP ratio", "pv_ppg_external_to_gdp"),
    ("PV of debt-to-exports ratio", "pv_ppg_external_to_exports"),
    ("Debt service-to-exports ratio", "ppg_debt_service_to_exports"),
    ("Debt service-to-revenue ratio", "ppg_debt_service_to_revenue"),
)

PUB_INDICATORS: tuple[tuple[str, str], ...] = (
    ("PV of Debt-to-GDP Ratio", "pv_public_debt_to_gdp"),
    ("PV of Debt-to-Revenue Ratio", "pv_public_debt_to_revenue_grants"),
    ("Debt Service-to-Revenue Ratio", "debt_service_to_revenue_grants"),
    ("Debt Service-to-GDP Ratio", "debt_service_to_gdp"),
)

EXT_SCENARIO_LABELS: dict[str, str] = {
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

# Back-compat private aliases used by older call sites.
_EXT_INDICATORS = EXT_INDICATORS
_PUB_INDICATORS = PUB_INDICATORS
_EXT_SCENARIO_LABELS = EXT_SCENARIO_LABELS

# Output 3-1 rows wired from public-book external-ratio methods (not *_ext).
OUTPUT31_EXTERNAL_EXCLUDE = frozenset({"B2_PrimaryBalance", "C1_CombinedCL"})

# Excel ``Baseline - public`` R91/R92/R93: B3/B4/C4 public Output 3-2 is
# baseline public PV/DS plus the scenario's external PV/DS adjustment
# (ext R89 / C4 R77 × FX_eop; ext R98 / C4 R89 × FX_pa). No dedicated
# B3/B4/C4 ``*_pub`` stress sheet for these rows.
_OUTPUT32_EXTERNAL_RESFIN_OVERLAY = frozenset(
    {"B3_Exports", "B4_OtherFlows", "C4_Market"}
)


def to_output31_rows(
    ratios: Any,
    *,
    scenario_id: str,
) -> dict[tuple[str, str], pd.Series]:
    """Return ``(indicator, scenario_label) → series`` for one book/ratios object."""
    label = EXT_SCENARIO_LABELS.get(scenario_id, scenario_id)
    out: dict[tuple[str, str], pd.Series] = {}
    for indicator, method in EXT_INDICATORS:
        getter = getattr(ratios, method, None)
        if getter is None:
            continue
        out[(indicator, label)] = getter().astype(float)
    return out


def to_output32_rows(
    ratios: Any,
    *,
    scenario_id: str,
) -> dict[tuple[str, str], pd.Series]:
    """Return ``(indicator, scenario_label) → series`` for public Output 3-2."""
    label = EXT_SCENARIO_LABELS.get(scenario_id, scenario_id)
    out: dict[tuple[str, str], pd.Series] = {}
    # Chart indicators only (first three); DS/GDP is optional.
    for indicator, method in PUB_INDICATORS[:3]:
        getter = getattr(ratios, method, None)
        if getter is None:
            continue
        out[(indicator, label)] = getter().astype(float)
    return out


def _baseline_public_debt_service_lcu(pub_base: BaselinePublicBook) -> pd.Series:
    """Baseline public DS in LCU (Excel ``Baseline - public`` R87)."""
    macro = pub_base.macro
    prior_dom_st = pd.Series(macro.domestic_st().shift(1), dtype=float).fillna(0.0)
    return (
        macro.interest_expenditure()
        + prior_dom_st
        + (macro.domestic_amortization() + macro.ppg_amortization()) * macro.fx_pa()
    ).astype(float)


def to_output32_rows_external_resfin_overlay(
    pub_base: BaselinePublicBook,
    result: StressScenarioResult,
    *,
    scenario_id: str,
) -> dict[tuple[str, str], pd.Series]:
    """B3/B4/C4 Output 3-2 via Excel ``Baseline - public`` R91–R93 / R105–R107.

    ``PV/GDP = (baseline_PV_LCU + adj_PV_USD × FX_eop) / GDP_LCU × 100``
    ``DS/rev = (baseline_DS_LCU + adj_DS_USD × FX_pa) / revenue × 100``
    ``PV/rev = (PV/GDP) / (revenue+grants)/GDP × 100``

    ``adj_PV`` is external ResFin PV plus optional C4 commercial PV Δ.
    ``adj_DS`` is ResFin debt service plus optional C4 commercial DS Δ and
    market-financing add.int.
    """
    if result.resfin.external is None:
        raise ValueError(
            f"{scenario_id}: external ResFin overlay required for Output 3-2"
        )
    label = EXT_SCENARIO_LABELS.get(scenario_id, scenario_id)
    years = list(pub_base.years)
    gdp = pub_base.gdp_lcu().reindex(years).astype(float)
    # Excel R91–R93 convert PV adj at FX(eop); R100–R102 convert DS at FX(pa).
    fx_eop = pub_base.macro.fx_eop().reindex(years).fillna(1.0).astype(float)
    fx_pa = pub_base.macro.fx_pa().reindex(years).fillna(1.0).astype(float)
    rev = pub_base.macro.revenues_incl_grants().reindex(years).astype(float)
    rev_gdp = pub_base.revenues_incl_grants_to_gdp().reindex(years).astype(float)

    base_pv_lcu = (
        pub_base.macro.pv_external_lcu() + pub_base.macro.public_domestic_debt()
    ).reindex(years).astype(float)
    base_ds_lcu = _baseline_public_debt_service_lcu(pub_base).reindex(years)

    overlay = result.resfin.external
    ext_pv = overlay.pv.reindex(years).fillna(0.0).astype(float)
    ext_ds = (
        overlay.interest.reindex(years).fillna(0.0)
        + overlay.amortization.reindex(years).fillna(0.0)
    ).astype(float)

    ratios = result.external_ratios
    if ratios is not None:
        if ratios.commercial_pv_delta is not None:
            ext_pv = ext_pv + ratios.commercial_pv_delta.reindex(years).fillna(0.0)
        if ratios.commercial_ds_delta is not None:
            ext_ds = ext_ds + ratios.commercial_ds_delta.reindex(years).fillna(0.0)
        if ratios.additional_borrowing_interest is not None:
            ext_ds = ext_ds + ratios.additional_borrowing_interest.reindex(
                years
            ).fillna(0.0)
        if ratios.c4_pv_stress is not None:
            ext_pv = ext_pv + ratios.c4_pv_stress.reindex(years).fillna(0.0)
        if ratios.c4_ds_stress is not None:
            ext_ds = ext_ds + ratios.c4_ds_stress.reindex(years).fillna(0.0)

    pv_gdp = (
        (base_pv_lcu + ext_pv * fx_eop) / gdp.replace(0.0, pd.NA) * 100.0
    ).astype(float)
    ds_rev = (
        (base_ds_lcu + ext_ds * fx_pa) / rev.replace(0.0, pd.NA) * 100.0
    ).astype(float)
    pv_rev = (pv_gdp / rev_gdp.replace(0.0, pd.NA) * 100.0).astype(float)

    return {
        ("PV of Debt-to-GDP Ratio", label): pv_gdp.clip(lower=0.0),
        ("PV of Debt-to-Revenue Ratio", label): pv_rev.clip(lower=0.0),
        ("Debt Service-to-Revenue Ratio", label): ds_rev.clip(lower=0.0),
    }


def build_output31_external_table(
    ext_base: BaselineExternalBook,
    results: Mapping[str, StressScenarioResult],
    *,
    public_results: Mapping[str, StressScenarioResult] | None = None,
    thresholds: dict[str, float] | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Build an Output 3-1 MultiIndex table from baseline + external results.

    When ``public_results`` includes B2 / C1, their public external-ratio
    methods fill Output 3-1 rows. Tailored A2/C3/C4 come from ``results``.
    """
    year_list = years or [int(y) for y in ext_base.years]
    store: dict[tuple[str, str], pd.Series] = {}
    store.update(to_output31_rows(ext_base, scenario_id="Baseline"))
    for sid, result in results.items():
        if sid in OUTPUT31_EXTERNAL_EXCLUDE:
            continue
        if result.external_ratios is None:
            continue
        store.update(
            to_output31_rows(result.external_ratios, scenario_id=str(sid))
        )
    if public_results is not None:
        for sid, result in public_results.items():
            if result is not None and result.public_ratios is not None:
                store.update(
                    to_output31_rows(result.public_ratios, scenario_id=str(sid))
                )

    thresh_keys = {
        "PV of debt-to GDP ratio": "pv_debt_to_gdp",
        "PV of debt-to-exports ratio": "pv_debt_to_exports",
        "Debt service-to-exports ratio": "debt_service_to_exports",
        "Debt service-to-revenue ratio": "debt_service_to_revenue",
    }
    if thresholds is not None:
        for indicator, key in thresh_keys.items():
            if key in thresholds:
                store[(indicator, "Threshold")] = pd.Series(
                    float(thresholds[key]), index=year_list, dtype=float
                )

    for key, series in list(store.items()):
        store[key] = series.reindex(year_list).astype(float)

    table = pd.DataFrame(store).T
    table.index.names = ["indicator", "scenario"]
    return table


def build_output32_table(
    pub_base: BaselinePublicBook,
    results: Mapping[str, StressScenarioResult],
    *,
    public_threshold: float | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Build an Output 3-2 MultiIndex table from baseline + public results.

    B3/B4 use the Excel external-ResFin overlay on baseline public (no
    ``*_pub`` sheet); pass external scenario results for those ids.
    """
    year_list = years or [int(y) for y in pub_base.years]
    store: dict[tuple[str, str], pd.Series] = {}
    store.update(to_output32_rows(pub_base, scenario_id="Baseline"))
    for sid, result in results.items():
        key = str(sid)
        if key in _OUTPUT32_EXTERNAL_RESFIN_OVERLAY:
            if result.resfin.external is None:
                continue
            store.update(
                to_output32_rows_external_resfin_overlay(
                    pub_base, result, scenario_id=key
                )
            )
            continue
        if result.public_ratios is None:
            continue
        store.update(to_output32_rows(result.public_ratios, scenario_id=key))
    if public_threshold is not None:
        store[("PV of Debt-to-GDP Ratio", "Threshold")] = pd.Series(
            float(public_threshold), index=year_list, dtype=float
        )
    for key, series in list(store.items()):
        store[key] = series.reindex(year_list).astype(float)
    table = pd.DataFrame(store).T
    table.index.names = ["indicator", "scenario"]
    return table


def result_as_legacy_external_book(result: StressScenarioResult) -> Any:
    """Adapt a scenario result to ``StressExternalBook`` for legacy APIs."""
    from lic_dsf.stress.scenario import StressExternalBook

    if result.resfin.external is None or result.external_ratios is None:
        raise ValueError("result missing external ResFin overlay or ratios")
    overlay = result.resfin.external
    return StressExternalBook(
        macro=result.path.shocked,
        external=result.external_ratios.external,
        resfin_pv=overlay.pv,
        resfin_interest=overlay.interest,
        resfin_amortization=overlay.amortization,
        residual_borrowing=result.external_gap.gap,
        scenario_id=result.scenario_id,
        baseline_macro=result.path.baseline,
        fx_depreciation_pct=float(result.path.metadata.fx_depreciation_pct),
        additional_borrowing_interest=(
            result.external_ratios.additional_borrowing_interest
        ),
    )


def result_as_legacy_public_book(result: StressScenarioResult) -> Any:
    """Adapt a public scenario result to ``StressPublicBook``."""
    if result.public_ratios is None or result.resfin.public is None:
        raise ValueError("result missing public ratios / ResFin overlay")
    return result.public_ratios._book()


__all__ = [
    "EXT_INDICATORS",
    "EXT_SCENARIO_LABELS",
    "OUTPUT31_EXTERNAL_EXCLUDE",
    "PUB_INDICATORS",
    "build_output31_external_table",
    "build_output32_table",
    "result_as_legacy_external_book",
    "result_as_legacy_public_book",
    "to_output31_rows",
    "to_output32_rows",
    "to_output32_rows_external_resfin_overlay",
]
