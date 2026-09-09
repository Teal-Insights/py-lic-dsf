"""Excel vs Python comparison for Outputs 5-1, 5-2, 6, and 7."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.rating.sut_outputs import (
    compute_output51_outputs,
    compute_output52_outputs,
    compute_output6_outputs,
    compute_output7_outputs,
)
from tests.parity.excel_compare.cells import a1 as _a1, as_year as _as_year, year_int as _year_int

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


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_unfilled_final(value: object) -> bool:
    """True when Output 7 yellow cells are still the `(select)` placeholder."""
    return _norm_text(value) in {"(select)", "select", ""}


def _norm_text(value: object) -> str:
    return str(value).strip().lower()


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
