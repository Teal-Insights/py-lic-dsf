"""Tests for ``lic_dsf.rating`` (CI, Chart Data, Output 5/7)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lic_dsf.rating import (
    ChartDataRegistry,
    MarketFinancingInputs,
    RiskRating,
    RiskRatingSummary,
    assess_market_financing,
    classify_ci,
    compute_mechanical_ratings,
    load_ci_summary,
    load_input1_market,
    load_trigger_flags,
    market_panel,
    mechanical_rating_from_breaches,
    moderate_panel,
    most_extreme_shock_id,
    multi_year_breach,
    risk_summary_panel,
    thresholds_for,
    thresholds_from_ci,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"


def test_classify_ci_cutoffs() -> None:
    assert classify_ci(2.5).value == "Weak"
    assert classify_ci(2.69).value == "Medium"
    assert classify_ci(3.05).value == "Medium"
    assert classify_ci(3.06).value == "Strong"


def test_ci_summary_parity() -> None:
    snap = load_ci_summary(WORKBOOK)
    assert snap.country == "Ghana"
    assert snap.country_code == 652
    assert snap.dcc.value == "Medium"
    assert snap.ci_score == pytest.approx(2.7398858732625286, rel=1e-6)
    assert snap.thresholds.pv_debt_to_gdp == pytest.approx(40.0)
    assert snap.thresholds.pv_debt_to_exports == pytest.approx(180.0)
    assert snap.thresholds.debt_service_to_exports == pytest.approx(15.0)
    assert snap.thresholds.debt_service_to_revenue == pytest.approx(18.0)
    assert snap.thresholds.public_pv_debt_to_gdp == pytest.approx(55.0)
    matrix = thresholds_for("Medium")
    assert matrix.pv_debt_to_gdp == 40.0
    flags = load_trigger_flags(WORKBOOK, 652)
    assert flags is not None
    assert flags.isocode == "GHA"


def test_load_input1_market_ghana() -> None:
    access, embi = load_input1_market(WORKBOOK)
    assert access is True
    assert embi == pytest.approx(350.0)


def test_multi_year_breach_excludes_one_year() -> None:
    path = pd.Series({2024: 41.0, 2025: 39.0, 2026: 38.0, 2027: 37.0})
    assert multi_year_breach(path, 40.0) is False
    path2 = pd.Series({2024: 41.0, 2025: 42.0, 2026: 38.0})
    assert multi_year_breach(path2, 40.0) is True


def test_most_extreme_shock_id_chart_data_rule() -> None:
    years = list(range(2024, 2035))
    exports = pd.Series({y: 45.0 for y in years})
    exports.loc[2026] = 55.8
    one_year = pd.Series({y: 39.0 for y in years})
    one_year.loc[2028] = 80.0
    late = pd.Series({y: 41.0 for y in years})
    late.loc[2044] = 90.0
    paths = {"B3_Exports": exports, "one_year": one_year, "late": late}
    assert most_extreme_shock_id(paths, 40.0, years) == "B3_Exports"


def test_mechanical_ratings_chart_data_rule() -> None:
    assert (
        mechanical_rating_from_breaches(baseline_breach=True, shock_breach=True)
        == RiskRating.HIGH
    )
    assert (
        mechanical_rating_from_breaches(baseline_breach=False, shock_breach=True)
        == RiskRating.MODERATE
    )
    assert (
        mechanical_rating_from_breaches(baseline_breach=False, shock_breach=False)
        == RiskRating.LOW
    )

    registry = ChartDataRegistry()
    # Baseline multi-year breach on PV/GDP → High external
    registry.register_series(
        "pv_debt_to_gdp",
        "baseline",
        pd.Series({2024: 45.0, 2025: 44.0, 2026: 38.0, 2027: 37.0}),
        is_baseline=True,
    )
    registry.register_series(
        "pv_debt_to_exports",
        "baseline",
        pd.Series({2024: 100.0, 2025: 110.0}),
        is_baseline=True,
    )
    registry.register_series(
        "debt_service_to_exports",
        "baseline",
        pd.Series({2024: 5.0, 2025: 6.0}),
        is_baseline=True,
    )
    registry.register_series(
        "debt_service_to_revenue",
        "baseline",
        pd.Series({2024: 5.0, 2025: 6.0}),
        is_baseline=True,
    )
    registry.register_series(
        "public_pv_debt_to_gdp",
        "baseline",
        pd.Series({2024: 60.0, 2025: 58.0, 2026: 50.0}),
        is_baseline=True,
    )
    # Shock path also breaching
    registry.register_series(
        "pv_debt_to_gdp",
        "B3",
        pd.Series({2024: 50.0, 2025: 55.0}),
        is_shock=True,
    )

    thresholds = thresholds_from_ci(2.74)
    result = compute_mechanical_ratings(registry, thresholds)
    assert result.external == RiskRating.HIGH
    assert result.fiscal == RiskRating.HIGH
    assert result.overall == RiskRating.HIGH
    assert result.external_baseline_breach is True


def test_chart_data_template_signal_high() -> None:
    """Template Ghana Chart Data signals High for external/fiscal/overall."""
    from fastpyxl import load_workbook

    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        cd = wb["Chart Data"]
        assert cd.cell(10, 4).value == "High"
        assert cd.cell(10, 9).value == "High"
        assert cd.cell(10, 12).value == "High"
        assert int(cd.cell(11, 4).value) == 3
    finally:
        wb.close()

    # Reconstruct from baseline PV/GDP path vs Medium threshold 40.
    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        cd = wb["Chart Data"]
        years = list(range(2023, 2034))
        # R38 baseline PV/GDP starts col D = 2023
        values = {}
        for i, y in enumerate(years):
            v = cd.cell(38, 4 + i).value
            if isinstance(v, (int, float)):
                values[y] = float(v)
        registry = ChartDataRegistry()
        registry.register_series(
            "pv_debt_to_gdp", "baseline", pd.Series(values), is_baseline=True
        )
        # Minimal other indicators below threshold so PV/GDP drives external.
        z = pd.Series({y: 0.0 for y in values})
        for ind in (
            "pv_debt_to_exports",
            "debt_service_to_exports",
            "debt_service_to_revenue",
        ):
            registry.register_series(ind, "baseline", z, is_baseline=True)
        # Public PV — use Chart Data fiscal baseline if present; synthetic breach.
        registry.register_series(
            "public_pv_debt_to_gdp",
            "baseline",
            pd.Series({y: 60.0 for y in list(values)[:4]}),
            is_baseline=True,
        )
        thresholds = thresholds_for("Medium")
        result = compute_mechanical_ratings(registry, thresholds)
        assert result.external == RiskRating.HIGH
        assert result.overall == RiskRating.HIGH
    finally:
        wb.close()


def test_output7_summary_and_judgement() -> None:
    snap = load_ci_summary(WORKBOOK)
    registry = ChartDataRegistry()
    registry.register_series(
        "pv_debt_to_gdp",
        "baseline",
        pd.Series({2024: 45.0, 2025: 44.0}),
        is_baseline=True,
    )
    for ind in (
        "pv_debt_to_exports",
        "debt_service_to_exports",
        "debt_service_to_revenue",
    ):
        registry.register_series(
            ind, "baseline", pd.Series({2024: 1.0, 2025: 1.0}), is_baseline=True
        )
    registry.register_series(
        "public_pv_debt_to_gdp",
        "baseline",
        pd.Series({2024: 60.0, 2025: 58.0}),
        is_baseline=True,
    )
    mech = compute_mechanical_ratings(registry, snap.thresholds)
    summary = RiskRatingSummary(
        mechanical=mech,
        thresholds=snap.thresholds,
        dcc=snap.dcc,
        ci_score=snap.ci_score,
    )
    panel = risk_summary_panel(summary)
    assert panel.loc["Mechanical external", "Output 7"] == "High"
    assert panel.loc["Final external", "Output 7"] == "High"
    assert panel.loc["Judgement applied", "Output 7"] == "No"
    judged = summary.apply_judgement(
        final_external=RiskRating.MODERATE, note="staff judgement"
    )
    assert judged.judgement_applied is True
    assert judged.final_external == RiskRating.MODERATE


def test_output5_moderate_and_market() -> None:
    baseline = pd.Series({2024: 38.0, 2025: 37.0, 2026: 36.0})
    panel = moderate_panel(
        mechanical_external=RiskRating.MODERATE,
        baseline_pv_gdp=baseline,
        threshold_pv_gdp=40.0,
    )
    assert "Space to absorb shock" in panel.index
    market = assess_market_financing(
        MarketFinancingInputs(
            market_access=True,
            gfn_to_gdp=pd.Series({2024: 16.0, 2025: 12.0}),
            embi_spread=700.0,
        )
    )
    assert market.gfn_breach is True
    assert market.embi_breach is True
    assert market.heightened_liquidity_needs is True
    assert "GFN breach" in market_panel(market).index
    assert MarketFinancingInputs(
        market_access=True, gfn_to_gdp=pd.Series({2024: 10.0})
    ).embi_benchmark == pytest.approx(570.0)
