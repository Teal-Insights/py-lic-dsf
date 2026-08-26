"""Excel vs Python comparison for Outputs 5-1, 5-2, 6, and 7."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.dsa.baseline.external import BaselineExternalBook
from lic_dsf.dsa.baseline.public import BaselinePublicBook
from lic_dsf.load.input6 import load_input6_standard
from lic_dsf.load.input7 import load_input7_residual_params
from lic_dsf.load.probability import load_distress_covariates
from lic_dsf.load.rating import load_ci_summary, load_input1_market, load_trigger_flags
from lic_dsf.output.scenario import probability_panel
from lic_dsf.pv.external_debt.book import ExternalDebtBook
from lic_dsf.pv.macro_debt.book import MacroDebtBook
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
from lic_dsf.realism.compare import _a1, _as_year, _books, _year_int
from lic_dsf.scenario.probability import ProbabilityAssumptions, borderline_bands
from lic_dsf.stress import (
    StressExternalBook,
    StressPublicBook,
    run_a1_historical_external,
    run_b1_gdp_public,
    run_standard_external_stress,
)

OUTPUT51_SHEET = "Output 5-1 Moderate risk"
OUTPUT52_SHEET = "Output 5-2 Market module"
OUTPUT6_SHEET = "Output 6 - Prob (if applicable)"
OUTPUT7_SHEET = "Output 7 - Risk rating summary"
CHART_DATA_SHEET = "Chart Data"
PROBABILITY_SHEET = "Probability approach"
INPUT1_SHEET = "Input 1 - Basics"

_CSV_COLS = [
    "sheet",
    "cell",
    "row",
    "col",
    "year",
    "section",
    "series_code",
    "label",
    "excel_value",
    "computed_value",
    "abs_diff",
]

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


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scalar(value: object) -> pd.Series:
    return pd.Series({0: value})


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _is_unfilled_final(value: object) -> bool:
    """True when Output 7 yellow cells are still the `(select)` placeholder."""
    return _norm_text(value) in {"(select)", "select", ""}


def _norm_text(value: object) -> str:
    return str(value).strip().lower()


def _liquidity_label(*, gfn_breach: bool, embi_breach: bool) -> str:
    n = int(gfn_breach) + int(embi_breach)
    if n >= 2:
        return "High"
    if n == 1:
        return "Moderate"
    return "Low"


def _abs_diff(excel: object, computed: object) -> float | None:
    if excel is None or computed is None:
        return None
    if isinstance(excel, float) and pd.isna(excel):
        return None
    if isinstance(computed, float) and pd.isna(computed):
        return None
    if _is_number(excel) and _is_number(computed):
        return abs(float(excel) - float(computed))
    return 0.0 if _norm_text(excel) == _norm_text(computed) else 1.0


def _lookup(
    computed: dict[tuple[str, str], pd.Series],
    section: object,
    match_key: object,
    year: object,
) -> object | None:
    series = computed.get((str(section), str(match_key)))
    if series is None:
        return None
    if year is None or (isinstance(year, float) and pd.isna(year)):
        raw = series.iloc[0] if len(series) else None
    else:
        year_i = _year_int(year)
        raw = series.loc[year_i] if year_i in series.index else None
    if raw is None:
        return None
    if not isinstance(raw, str) and pd.isna(raw):
        return None
    return raw


def _pair_frame(
    excel: pd.DataFrame,
    computed: dict[tuple[str, str], pd.Series],
    *,
    extra_sheet: str,
) -> pd.DataFrame:
    """Attach Python values to Excel rows and append unmatched panel extras."""
    computed_values: list[object] = []
    diffs: list[float | None] = []
    for section, match_key, year, excel_value in zip(
        excel["section"].tolist(),
        excel["match_key"].tolist(),
        excel["year"].tolist(),
        excel["excel_value"].tolist(),
        strict=True,
    ):
        value = _lookup(computed, section, match_key, year)
        computed_values.append(value if value is not None else pd.NA)
        diffs.append(_abs_diff(excel_value, value))
    excel = excel.copy()
    excel["computed_value"] = computed_values
    excel["abs_diff"] = diffs

    excel_keys = set(
        zip(excel["section"], excel["match_key"], excel["year"], strict=True)
    )
    extra_rows: list[dict[str, Any]] = []
    for (section, key), series in computed.items():
        if not str(section).startswith("Python panel"):
            continue
        for year_key, value in series.items():
            if not isinstance(value, str) and pd.isna(value):
                continue
            year_i: object
            try:
                year_i = _year_int(year_key)
            except (TypeError, ValueError):
                year_i = pd.NA
            if (section, key, year_i) in excel_keys:
                continue
            extra_rows.append(
                {
                    "sheet": extra_sheet,
                    "cell": "",
                    "row": pd.NA,
                    "col": pd.NA,
                    "year": year_i,
                    "section": section,
                    "series_code": "",
                    "label": key,
                    "match_key": key,
                    "excel_value": pd.NA,
                    "computed_value": value,
                    "abs_diff": pd.NA,
                }
            )
    if extra_rows:
        excel = pd.concat([excel, pd.DataFrame(extra_rows)], ignore_index=True)
    return excel.sort_values(
        ["row", "col", "section", "year"], na_position="last"
    ).reset_index(drop=True)


def _write_csv(frame: pd.DataFrame, output: str | Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, _CSV_COLS].to_csv(output, index=False)
    return output


def _record(
    *,
    sheet: str,
    row: int,
    col: int,
    year: int | None,
    section: str,
    series_code: str,
    label: str,
    match_key: str,
    value: object,
) -> dict[str, Any]:
    return {
        "sheet": sheet,
        "cell": _a1(row, col),
        "row": row,
        "col": col,
        "year": year,
        "section": section,
        "series_code": series_code,
        "label": label,
        "match_key": match_key,
        "excel_value": value,
    }


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


def _chart_data_years(ws: Any) -> dict[int, int]:
    years: dict[int, int] = {}
    for col in range(1, (ws.max_column or 1) + 1):
        year = _as_year(ws.cell(35, col).value)
        if year is not None:
            years[year] = col
    return years


def _argmax_cell(
    ws: Any, row: int, year_cols: dict[int, int], years: list[int]
) -> tuple[int, int, float]:
    best_year = years[0]
    best_col = year_cols[best_year]
    best_val = float(ws.cell(row, best_col).value)
    for year in years:
        col = year_cols[year]
        raw = ws.cell(row, col).value
        if not _is_number(raw):
            continue
        if float(raw) > best_val:
            best_val = float(raw)
            best_year = year
            best_col = col
    return best_year, best_col, best_val


def _read_output51_rows(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        chart = wb[CHART_DATA_SHEET]
        out7 = wb[OUTPUT7_SHEET]
        year_cols = _chart_data_years(chart)
        proj_years = sorted(year_cols)[:11]
        peak_year, peak_col, peak_val = _argmax_cell(chart, 61, year_cols, proj_years)
        records = [
            _record(
                sheet=CHART_DATA_SHEET,
                row=10,
                col=4,
                year=None,
                section="Output 5-1",
                series_code="Mechanical external",
                label="Mechanical external",
                match_key="Mechanical external",
                value=chart.cell(10, 4).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=61,
                col=peak_col,
                year=peak_year,
                section="Output 5-1",
                series_code="Baseline peak PV/GDP",
                label="Baseline peak PV/GDP",
                match_key="Baseline peak PV/GDP",
                value=peak_val,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=66,
                col=4,
                year=None,
                section="Output 5-1",
                series_code="Threshold PV/GDP",
                label="Threshold PV/GDP",
                match_key="Threshold PV/GDP",
                value=chart.cell(66, 4).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=73,
                col=5,
                year=None,
                section="Output 5-1",
                series_code="Space to absorb shock",
                label="Space to absorb shock",
                match_key="Space to absorb shock",
                value=out7.cell(73, 5).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=23,
                col=4,
                year=None,
                section="Output 5-1",
                series_code="Space (unconstrained)",
                label="Space to absorb shock (Chart Data)",
                match_key="Space (unconstrained)",
                value=chart.cell(23, 4).value,
            ),
        ]
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


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


def build_output51_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Output 5-1."""
    path = Path(path)
    return _pair_frame(
        _read_output51_rows(path),
        compute_output51_outputs(path),
        extra_sheet=OUTPUT51_SHEET,
    )


def write_output51_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 5-1 comparison table to `output`."""
    return _write_csv(build_output51_comparison(workbook), output)


def _read_output52_rows(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[OUTPUT52_SHEET]
        inp = wb[INPUT1_SHEET]
        records = [
            _record(
                sheet=OUTPUT52_SHEET,
                row=8,
                col=28,
                year=None,
                section="Output 5-2",
                series_code="GFN benchmark",
                label="GFN benchmark",
                match_key="GFN benchmark",
                value=ws.cell(8, 28).value,
            ),
            _record(
                sheet=OUTPUT52_SHEET,
                row=9,
                col=28,
                year=None,
                section="Output 5-2",
                series_code="Max GFN / GDP",
                label="Max GFN / GDP",
                match_key="Max GFN / GDP",
                value=ws.cell(9, 28).value,
            ),
            _record(
                sheet=OUTPUT52_SHEET,
                row=10,
                col=28,
                year=None,
                section="Output 5-2",
                series_code="GFN breach",
                label="GFN breach",
                match_key="GFN breach",
                value=ws.cell(10, 28).value,
            ),
            _record(
                sheet=OUTPUT52_SHEET,
                row=8,
                col=50,
                year=None,
                section="Output 5-2",
                series_code="EMBI benchmark",
                label="EMBI benchmark",
                match_key="EMBI benchmark",
                value=ws.cell(8, 50).value,
            ),
            _record(
                sheet=OUTPUT52_SHEET,
                row=9,
                col=50,
                year=None,
                section="Output 5-2",
                series_code="EMBI spread",
                label="EMBI spread",
                match_key="EMBI spread",
                value=ws.cell(9, 50).value,
            ),
            _record(
                sheet=OUTPUT52_SHEET,
                row=10,
                col=50,
                year=None,
                section="Output 5-2",
                series_code="EMBI breach",
                label="EMBI breach",
                match_key="EMBI breach",
                value=ws.cell(10, 50).value,
            ),
            _record(
                sheet=OUTPUT52_SHEET,
                row=12,
                col=28,
                year=None,
                section="Output 5-2",
                series_code="Heightened liquidity needs",
                label="Potential heightened liquidity needs",
                match_key="Heightened liquidity needs",
                value=ws.cell(12, 28).value,
            ),
            _record(
                sheet=INPUT1_SHEET,
                row=27,
                col=3,
                year=None,
                section="Output 5-2",
                series_code="Applicable",
                label="Market access (Input 1)",
                match_key="Applicable",
                value=inp.cell(27, 3).value,
            ),
        ]
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


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


def build_output52_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Output 5-2."""
    path = Path(path)
    return _pair_frame(
        _read_output52_rows(path),
        compute_output52_outputs(path),
        extra_sheet=OUTPUT52_SHEET,
    )


def write_output52_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 5-2 comparison table to `output`."""
    return _write_csv(build_output52_comparison(workbook), output)


def _prob_year_cols(ws: Any) -> dict[int, int]:
    years: dict[int, int] = {}
    for col in range(1, (ws.max_column or 1) + 1):
        year = _as_year(ws.cell(24, col).value)
        if year is not None:
            years[year] = col
    return years


def _read_output6_rows(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[PROBABILITY_SHEET]
        year_cols = _prob_year_cols(ws)
        records: list[dict[str, Any]] = [
            _record(
                sheet=PROBABILITY_SHEET,
                row=8,
                col=9,
                year=None,
                section="Assumptions",
                series_code="bandwidth",
                label="Borderline Bandwidth",
                match_key="Borderline Bandwidth",
                value=ws.cell(8, 9).value,
            )
        ]
        section = ""
        for row in range(26, 57):
            header = ws.cell(row, 1).value
            if isinstance(header, str) and header.strip():
                section = header.strip()
                continue
            label = str(ws.cell(row, 2).value or "").strip()
            if not label or label.lower().startswith("most extreme"):
                continue
            for year, col in year_cols.items():
                value = ws.cell(row, col).value
                if not _is_number(value):
                    continue
                records.append(
                    _record(
                        sheet=PROBABILITY_SHEET,
                        row=row,
                        col=col,
                        year=year,
                        section=section,
                        series_code=label,
                        label=label,
                        match_key=label,
                        value=float(value),
                    )
                )
        for row in range(83, 106):
            header = ws.cell(row, 1).value
            label = str(ws.cell(row, 2).value or "").strip()
            if label not in {
                "Baseline",
                "Historical scenario",
                "MX shock Standard&Tailored",
            }:
                if isinstance(header, str) and header.strip():
                    section = header.strip()
                continue
            for year, col in year_cols.items():
                value = ws.cell(row, col).value
                if not _is_number(value):
                    continue
                records.append(
                    _record(
                        sheet=PROBABILITY_SHEET,
                        row=row,
                        col=col,
                        year=year,
                        section=section,
                        series_code=f"{label} probability",
                        label=f"{label} probability",
                        match_key=f"{label} probability",
                        value=float(value),
                    )
                )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


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


def build_output6_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Output 6."""
    path = Path(path)
    return _pair_frame(
        _read_output6_rows(path),
        compute_output6_outputs(path),
        extra_sheet=OUTPUT6_SHEET,
    )


def write_output6_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 6 comparison table to `output`."""
    return _write_csv(build_output6_comparison(workbook), output)


def _read_output7_rows(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[OUTPUT7_SHEET]
        chart = wb[CHART_DATA_SHEET]
        final_ext = ws.cell(49, 5).value
        final_overall = ws.cell(55, 5).value
        records = [
            _record(
                sheet=OUTPUT7_SHEET,
                row=5,
                col=5,
                year=None,
                section="Output 7",
                series_code="Country",
                label="Country",
                match_key="Country",
                value=ws.cell(5, 5).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=6,
                col=5,
                year=None,
                section="Output 7",
                series_code="Country Code",
                label="Country Code",
                match_key="Country Code",
                value=ws.cell(6, 5).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=48,
                col=5,
                year=None,
                section="Output 7",
                series_code="Mechanical external",
                label="Mechanical external debt distress rating",
                match_key="Mechanical external",
                value=ws.cell(48, 5).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=10,
                col=9,
                year=None,
                section="Output 7",
                series_code="Mechanical fiscal",
                label="Mechanical fiscal debt distress rating",
                match_key="Mechanical fiscal",
                value=chart.cell(10, 9).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=54,
                col=5,
                year=None,
                section="Output 7",
                series_code="Mechanical overall",
                label="Mechanical overall debt distress rating",
                match_key="Mechanical overall",
                value=ws.cell(54, 5).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=65,
                col=4,
                year=None,
                section="Output 7",
                series_code="Debt carrying capacity",
                label="Debt carrying capacity (final)",
                match_key="Debt carrying capacity",
                value=ws.cell(65, 4).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=66,
                col=5,
                year=None,
                section="Output 7",
                series_code="CI score",
                label="CI score (current vintage)",
                match_key="CI score",
                value=ws.cell(66, 5).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=66,
                col=4,
                year=None,
                section="Output 7",
                series_code="Threshold PV/GDP",
                label="Threshold PV/GDP",
                match_key="Threshold PV/GDP",
                value=chart.cell(66, 4).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=73,
                col=5,
                year=None,
                section="Output 7",
                series_code="Moderate granularity",
                label="Space to absorb shock",
                match_key="Moderate granularity",
                value=ws.cell(73, 5).value,
            ),
            _record(
                sheet=OUTPUT7_SHEET,
                row=75,
                col=5,
                year=None,
                section="Output 7",
                series_code="Market-Financing Pressures",
                label="Market-Financing Pressures",
                match_key="Market-Financing Pressures",
                value=ws.cell(75, 5).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=12,
                col=4,
                year=None,
                section="Chart Data signals",
                series_code="external_baseline_breach",
                label="External baseline breach",
                match_key="external_baseline_breach",
                value=chart.cell(12, 4).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=13,
                col=4,
                year=None,
                section="Chart Data signals",
                series_code="external_shock_breach",
                label="External shock breach",
                match_key="external_shock_breach",
                value=chart.cell(13, 4).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=12,
                col=9,
                year=None,
                section="Chart Data signals",
                series_code="fiscal_baseline_breach",
                label="Fiscal baseline breach",
                match_key="fiscal_baseline_breach",
                value=chart.cell(12, 9).value,
            ),
            _record(
                sheet=CHART_DATA_SHEET,
                row=13,
                col=9,
                year=None,
                section="Chart Data signals",
                series_code="fiscal_shock_breach",
                label="Fiscal shock breach",
                match_key="fiscal_shock_breach",
                value=chart.cell(13, 9).value,
            ),
        ]
        if not _is_unfilled_final(final_ext):
            records.extend(
                [
                    _record(
                        sheet=OUTPUT7_SHEET,
                        row=49,
                        col=5,
                        year=None,
                        section="Output 7",
                        series_code="Final external",
                        label="Final external debt distress rating",
                        match_key="Final external",
                        value=final_ext,
                    ),
                    _record(
                        sheet=OUTPUT7_SHEET,
                        row=50,
                        col=5,
                        year=None,
                        section="Output 7",
                        series_code="Judgement applied",
                        label="Judgement was applied (external)",
                        match_key="Judgement applied",
                        value=ws.cell(50, 5).value,
                    ),
                ]
            )
        if not _is_unfilled_final(final_overall):
            records.append(
                _record(
                    sheet=OUTPUT7_SHEET,
                    row=55,
                    col=5,
                    year=None,
                    section="Output 7",
                    series_code="Final overall",
                    label="Final overall debt distress rating",
                    match_key="Final overall",
                    value=final_overall,
                )
            )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


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


def build_output7_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Output 7."""
    path = Path(path)
    return _pair_frame(
        _read_output7_rows(path),
        compute_output7_outputs(path),
        extra_sheet=OUTPUT7_SHEET,
    )


def write_output7_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 7 comparison table to `output`."""
    return _write_csv(build_output7_comparison(workbook), output)
