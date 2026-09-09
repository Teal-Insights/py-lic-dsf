"""Output 5 / 6 / 7 SUT key stores (cell-keyed panels for ``lic_dsf.output``)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook
from lic_dsf.load.input6 import load_input6_standard
from lic_dsf.load.input7 import load_input7_residual_params
from lic_dsf.load.probability import load_distress_covariates
from lic_dsf.load.rating import load_ci_summary, load_input1_market, load_trigger_flags
from lic_dsf.output.scenario import probability_panel
from lic_dsf.books.external.book import ExternalDebtBook
from lic_dsf.books.macro.book import MacroDebtBook
from lic_dsf.rating.chart_data import (
    ChartDataRegistry,
    MechanicalRatingResult,
    compute_mechanical_ratings,
    most_extreme_shock_id,
)
from lic_dsf.rating.market import MarketFinancingInputs, assess_market_financing
from lic_dsf.rating.moderate import moderate_panel, moderate_space_from_headroom
from lic_dsf.rating.summary import RiskRatingSummary, risk_summary_panel
from lic_dsf.rating.workbook import CiSummarySnapshot, TriggerFlags
from lic_dsf.load.core import load_core
from lic_dsf.scenario.probability import ProbabilityAssumptions, borderline_bands
from lic_dsf.stress import (
    StressExternalBook,
    StressPublicBook,
    run_a1_historical_external,
    run_b1_gdp_public,
    run_standard_external_stress,
)


def _books(path: str):
    return load_core(path)


_EXTERNAL_RATIO_METHODS: tuple[tuple[str, str], ...] = (
    ("pv_debt_to_gdp", "pv_ppg_external_to_gdp"),
    ("pv_debt_to_exports", "pv_ppg_external_to_exports"),
    ("debt_service_to_exports", "ppg_debt_service_to_exports"),
    ("debt_service_to_revenue", "ppg_debt_service_to_revenue"),
)

_PROB_INDICATORS: tuple[tuple[str, str, str], ...] = (
    ("PV of debt-to GDP ratio", "pv_ppg_external_to_gdp", "pv_debt_to_gdp"),
    ("PV of debt-to-exports ratio", "pv_ppg_external_to_exports", "pv_debt_to_exports"),
    (
        "Debt service-to-exports ratio",
        "ppg_debt_service_to_exports",
        "debt_service_to_exports",
    ),
    (
        "Debt service-to-revenue ratio",
        "ppg_debt_service_to_revenue",
        "debt_service_to_revenue",
    ),
)

@dataclass(frozen=True, slots=True)
class _CoreBundle:
    """Baseline books plus CI / market-access inputs."""

    macro: MacroDebtBook
    external: ExternalDebtBook
    ext_base: BaselineExternalBook
    pub_base: BaselinePublicBook
    ci: CiSummarySnapshot
    trigger: TriggerFlags | None
    first_proj: int
    proj_years: list[int]
    market_access_input1: bool
    embi_spread: float | None

@dataclass(frozen=True, slots=True)
class _StressBundle:
    """Standard B-tests plus mechanical ratings."""

    core: _CoreBundle
    external_stress: dict[str, StressExternalBook]
    public_b1: StressPublicBook
    mechanical: MechanicalRatingResult
    historical: StressExternalBook

def _scalar(value: object) -> pd.Series:
    return pd.Series({0: value})

def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"

def _liquidity_label(*, gfn_breach: bool, embi_breach: bool) -> str:
    n = int(gfn_breach) + int(embi_breach)
    if n >= 2:
        return "High"
    if n == 1:
        return "Moderate"
    return "Low"

@lru_cache(maxsize=4)
def _core_bundle(path: str) -> _CoreBundle:
    macro, external, ext_base, pub_base = _books(path)
    ci = load_ci_summary(path)
    trigger = load_trigger_flags(path, ci.country_code)
    first_proj = int(macro.inputs.first_projection_year)
    proj_years = list(range(first_proj, first_proj + 11))
    access, embi = load_input1_market(path)
    return _CoreBundle(
        macro=macro,
        external=external,
        ext_base=ext_base,
        pub_base=pub_base,
        ci=ci,
        trigger=trigger,
        first_proj=first_proj,
        proj_years=proj_years,
        market_access_input1=access,
        embi_spread=embi,
    )

def _register_paths(
    *,
    ext_base: BaselineExternalBook,
    pub_base: BaselinePublicBook,
    years: list[int],
    external_stress: dict[str, StressExternalBook] | None = None,
    public_b1: StressPublicBook | None = None,
) -> ChartDataRegistry:
    registry = ChartDataRegistry()
    for indicator, method in _EXTERNAL_RATIO_METHODS:
        registry.register_series(
            indicator,
            "baseline",
            getattr(ext_base, method)().reindex(years),
            is_baseline=True,
        )
        if external_stress is None:
            continue
        for sid, book in external_stress.items():
            registry.register_series(
                indicator,
                sid,
                getattr(book, method)().reindex(years),
                is_shock=True,
            )
    registry.register_series(
        "public_pv_debt_to_gdp",
        "baseline",
        pub_base.pv_public_debt_to_gdp().reindex(years),
        is_baseline=True,
    )
    if public_b1 is not None:
        registry.register_series(
            "public_pv_debt_to_gdp",
            "B1_GDP",
            public_b1.pv_public_debt_to_gdp().reindex(years),
            is_shock=True,
        )
    return registry

@lru_cache(maxsize=4)
def _stress_bundle(path: str) -> _StressBundle:
    core = _core_bundle(path)
    input6 = load_input6_standard(path)
    residual = load_input7_residual_params(path)
    external_stress = run_standard_external_stress(
        core.macro, core.external, input6, residual
    )
    public_b1 = run_b1_gdp_public(core.macro, core.external, input6, residual)
    historical = run_a1_historical_external(core.macro, core.external, residual)
    registry = _register_paths(
        ext_base=core.ext_base,
        pub_base=core.pub_base,
        years=core.proj_years,
        external_stress=external_stress,
        public_b1=public_b1,
    )
    mechanical = compute_mechanical_ratings(
        registry, core.ci.thresholds, years=core.proj_years
    )
    return _StressBundle(
        core=core,
        external_stress=external_stress,
        public_b1=public_b1,
        mechanical=mechanical,
        historical=historical,
    )

def _baseline_mechanical(core: _CoreBundle) -> MechanicalRatingResult:
    registry = _register_paths(
        ext_base=core.ext_base,
        pub_base=core.pub_base,
        years=core.proj_years,
    )
    return compute_mechanical_ratings(
        registry, core.ci.thresholds, years=core.proj_years
    )

def _most_extreme_id(
    stress: dict[str, StressExternalBook],
    years: list[int],
    threshold: float,
) -> str:
    """Chart Data MX selector (peak over years 2–11, drop 1-year-only)."""
    paths = {sid: book.pv_ppg_external_to_gdp() for sid, book in stress.items()}
    return most_extreme_shock_id(paths, threshold, years)

def compute_output51_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 5-1 panel values keyed by `(section, match_key)`."""
    core = _core_bundle(str(Path(path)))
    mechanical = _baseline_mechanical(core)
    baseline = (
        core.ext_base.pv_ppg_external_to_gdp().reindex(core.proj_years).astype(float)
    )
    panel = moderate_panel(
        mechanical_external=mechanical.external,
        baseline_pv_gdp=baseline,
        threshold_pv_gdp=core.ci.thresholds.pv_debt_to_gdp,
        rating_years=core.proj_years,
    )["Output 5-1"]
    peak = float(panel.loc["Baseline peak PV/GDP"])
    peak_year = int(baseline.idxmax())
    unconstrained = moderate_space_from_headroom(
        peak, core.ci.thresholds.pv_debt_to_gdp
    )
    store: dict[tuple[str, str], pd.Series] = {
        ("Output 5-1", "Mechanical external"): _scalar(
            str(panel.loc["Mechanical external"])
        ),
        ("Output 5-1", "Baseline peak PV/GDP"): pd.Series({peak_year: peak}),
        ("Output 5-1", "Threshold PV/GDP"): _scalar(
            float(panel.loc["Threshold PV/GDP"])
        ),
        ("Output 5-1", "Space to absorb shock"): _scalar(
            str(panel.loc["Space to absorb shock"])
        ),
        ("Output 5-1", "Space (unconstrained)"): _scalar(unconstrained.value),
    }
    return store

def compute_output52_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 5-2 market-module values keyed by `(section, match_key)`."""
    core = _core_bundle(str(Path(path)))
    gfn = core.pub_base.public_gfn_to_gdp().reindex(
        list(range(core.first_proj, core.first_proj + 3))
    )
    inputs = MarketFinancingInputs(
        market_access=core.market_access_input1,
        gfn_to_gdp=gfn,
        embi_spread=core.embi_spread,
    )
    result = assess_market_financing(inputs)
    max_gfn = float(result.max_gfn_to_gdp or 0.0)
    gfn_breach = result.gfn_breach
    embi_breach = result.embi_breach
    return {
        ("Output 5-2", "Applicable"): _scalar(_yes_no(result.applicable)),
        ("Output 5-2", "GFN benchmark"): _scalar(inputs.gfn_benchmark),
        ("Output 5-2", "Max GFN / GDP"): _scalar(max_gfn),
        ("Output 5-2", "GFN breach"): _scalar(_yes_no(gfn_breach)),
        ("Output 5-2", "EMBI benchmark"): _scalar(inputs.embi_benchmark),
        ("Output 5-2", "EMBI spread"): _scalar(core.embi_spread),
        ("Output 5-2", "EMBI breach"): _scalar(_yes_no(embi_breach)),
        ("Output 5-2", "Heightened liquidity needs"): _scalar(
            _liquidity_label(gfn_breach=gfn_breach, embi_breach=embi_breach)
        ),
    }

def compute_output6_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 6 probability-approach values keyed by `(section, match_key)`."""
    stress = _stress_bundle(str(Path(path)))
    core = stress.core
    years = [int(y) for y in core.ext_base.years if int(y) >= core.first_proj]
    mx_sid = _most_extreme_id(
        stress.external_stress,
        core.proj_years,
        float(core.ci.thresholds.pv_debt_to_gdp),
    )
    mx_book = stress.external_stress[mx_sid]
    assumptions = ProbabilityAssumptions(bandwidth=0.1)
    covariates = load_distress_covariates(path)
    thresh = core.ci.thresholds.as_dict()
    store: dict[tuple[str, str], pd.Series] = {
        ("Assumptions", "Borderline Bandwidth"): _scalar(assumptions.bandwidth),
    }
    for section, method, indicator in _PROB_INDICATORS:
        threshold = float(thresh[indicator])
        baseline = getattr(core.ext_base, method)().reindex(years).astype(float)
        historical = getattr(stress.historical, method)().reindex(years).astype(float)
        mx_shock = getattr(mx_book, method)().reindex(years).astype(float)
        panel = probability_panel(
            {
                "baseline": baseline,
                "historical": historical,
                "mx_shock": mx_shock,
            },
            threshold,
            indicator=indicator,
            assumptions=assumptions,
            covariates=covariates,
        )
        lower, upper = borderline_bands(threshold, assumptions.bandwidth)
        store[(section, "Baseline")] = panel.loc["baseline level"]
        store[(section, "Historical scenario")] = panel.loc["historical level"]
        store[(section, "MX shock Standard&Tailored")] = panel.loc["mx_shock level"]
        store[(section, "Threshold")] = pd.Series(threshold, index=years, dtype=float)
        store[(section, "Lower Band")] = pd.Series(lower, index=years, dtype=float)
        store[(section, "Upper Band")] = pd.Series(upper, index=years, dtype=float)
        store[(section, "Baseline probability")] = panel.loc["baseline prob"] * 100.0
        store[(section, "Historical scenario probability")] = (
            panel.loc["historical prob"] * 100.0
        )
        store[(section, "MX shock Standard&Tailored probability")] = (
            panel.loc["mx_shock prob"] * 100.0
        )
    return store

def compute_output7_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 7 summary values keyed by `(section, match_key)`."""
    stress = _stress_bundle(str(Path(path)))
    core = stress.core
    out_5_1 = moderate_panel(
        mechanical_external=stress.mechanical.external,
        baseline_pv_gdp=core.ext_base.pv_ppg_external_to_gdp(),
        threshold_pv_gdp=core.ci.thresholds.pv_debt_to_gdp,
        rating_years=core.proj_years,
    )
    gfn = core.pub_base.public_gfn_to_gdp().reindex(
        list(range(core.first_proj, core.first_proj + 3))
    )
    market_inputs = MarketFinancingInputs(
        market_access=core.market_access_input1,
        gfn_to_gdp=gfn,
        embi_spread=core.embi_spread,
    )
    result = assess_market_financing(market_inputs)
    gfn_breach = result.gfn_breach
    embi_breach = result.embi_breach
    summary = RiskRatingSummary(
        mechanical=stress.mechanical,
        thresholds=core.ci.thresholds,
        dcc=core.ci.dcc,
        ci_score=core.ci.ci_score,
        moderate_granularity=str(out_5_1.loc["Space to absorb shock", "Output 5-1"]),
    )
    panel = risk_summary_panel(summary)["Output 7"]
    mech = stress.mechanical
    return {
        ("Output 7", "Country"): _scalar(core.ci.country),
        ("Output 7", "Country Code"): _scalar(core.ci.country_code),
        ("Output 7", "Mechanical external"): _scalar(
            str(panel.loc["Mechanical external"])
        ),
        ("Output 7", "Final external"): _scalar(str(panel.loc["Final external"])),
        ("Output 7", "Judgement applied"): _scalar(str(panel.loc["Judgement applied"])),
        ("Output 7", "Mechanical fiscal"): _scalar(str(panel.loc["Mechanical fiscal"])),
        ("Output 7", "Mechanical overall"): _scalar(
            str(panel.loc["Mechanical overall"])
        ),
        ("Output 7", "Final overall"): _scalar(str(panel.loc["Final overall"])),
        ("Output 7", "Debt carrying capacity"): _scalar(
            str(panel.loc["Debt carrying capacity"])
        ),
        ("Output 7", "CI score"): _scalar(float(panel.loc["CI score"])),
        ("Output 7", "Threshold PV/GDP"): _scalar(float(panel.loc["Threshold PV/GDP"])),
        ("Output 7", "Moderate granularity"): _scalar(
            str(panel.loc["Moderate granularity"])
        ),
        ("Output 7", "Market-Financing Pressures"): _scalar(
            _liquidity_label(gfn_breach=gfn_breach, embi_breach=embi_breach)
        ),
        ("Chart Data signals", "external_baseline_breach"): _scalar(
            float(mech.external_baseline_breach)
        ),
        ("Chart Data signals", "external_shock_breach"): _scalar(
            float(mech.external_shock_breach)
        ),
        ("Chart Data signals", "fiscal_baseline_breach"): _scalar(
            float(mech.fiscal_baseline_breach)
        ),
        ("Chart Data signals", "fiscal_shock_breach"): _scalar(
            float(mech.fiscal_shock_breach)
        ),
    }

