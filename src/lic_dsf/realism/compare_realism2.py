"""Excel vs Python comparison for Realism 2 (fiscal multiplier)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.dsa.compare import write_comparison_csv
from lic_dsf.realism.compare import _a1, _as_year, _books, _year_int
from lic_dsf.output.realism import fiscal_multiplier_panel
from lic_dsf.realism.workbook import load_multiplier_grid

REALISM2_SHEET = "Realism 2 - Fiscal multiplier"
_CSV_COLS = (
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
)
_IMPACT_START_ROW = 51
_IMPACT_FIRST_COL = 4
_UNDERLYING_FIRST_COL = 12
_M_HEADER_ROW = 15


def _m_key(m: float) -> str:
    return f"m={float(m):g}"


def _read_excel(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[REALISM2_SHEET]
        m_cols: list[tuple[int, float]] = []
        for col in range(_IMPACT_FIRST_COL, _IMPACT_FIRST_COL + 5):
            raw = ws.cell(_M_HEADER_ROW, col).value
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                m_cols.append((col, float(raw)))
        first_year = _as_year(ws.cell(_IMPACT_START_ROW, 1).value) or 2024
        records: list[dict[object, object]] = []
        for offset in range(0, 40):
            row = _IMPACT_START_ROW + offset
            year = _as_year(ws.cell(row, 1).value)
            if year is None:
                year = first_year + offset
            any_numeric = False
            for col, m in m_cols:
                key = _m_key(m)
                impact = ws.cell(row, col).value
                if isinstance(impact, (int, float)) and not isinstance(impact, bool):
                    any_numeric = True
                    records.append(
                        {
                            "sheet": REALISM2_SHEET,
                            "cell": _a1(row, col),
                            "row": row,
                            "col": col,
                            "year": year,
                            "section": "Impact on growth",
                            "series_code": key,
                            "label": f"Impact {key}",
                            "match_key": key,
                            "excel_value": float(impact),
                        }
                    )
                under_col = col + (_UNDERLYING_FIRST_COL - _IMPACT_FIRST_COL)
                under = ws.cell(row, under_col).value
                if isinstance(under, (int, float)) and not isinstance(under, bool):
                    any_numeric = True
                    records.append(
                        {
                            "sheet": REALISM2_SHEET,
                            "cell": _a1(row, under_col),
                            "row": row,
                            "col": under_col,
                            "year": year,
                            "section": "Underlying growth",
                            "series_code": key,
                            "label": f"Underlying {key}",
                            "match_key": key,
                            "excel_value": float(under),
                        }
                    )
            if not any_numeric:
                break
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


def compute_realism2_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Multiplier impact / underlying-growth series keyed by section and ``m=…``."""
    path = Path(path)
    macro, _ext, _eb, _pb = _books(str(path))
    pb_pct = 100.0 * macro.primary_balance() / macro.gdp_lcu().replace(0.0, pd.NA)
    panel = fiscal_multiplier_panel(
        pb_pct,
        macro.real_gdp_growth(),
        macro.inputs.first_projection_year,
        multipliers=load_multiplier_grid(path) or None,
    )
    store: dict[tuple[str, str], pd.Series] = {}
    for metric, m in panel.columns:
        section = (
            "Impact on growth" if metric == "impact" else "Underlying growth"
        )
        store[(section, _m_key(float(m)))] = panel[(metric, m)]
    return store


def build_realism2_comparison(path: str | Path) -> pd.DataFrame:
    """Build Excel vs Python table for Realism 2 impact cells."""
    path = Path(path)
    excel = _read_excel(path)
    computed = compute_realism2_outputs(path)
    values: list[object] = []
    diffs: list[float | None] = []
    for section, key, year, excel_value in zip(
        excel["section"],
        excel["series_code"],
        excel["year"],
        excel["excel_value"],
        strict=True,
    ):
        series = computed.get((str(section), str(key)))
        value = None
        year_i = _year_int(year)
        if series is not None and year_i in series.index and pd.notna(series.loc[year_i]):
            value = float(series.loc[year_i])
        values.append(value if value is not None else pd.NA)
        diffs.append(
            abs(float(excel_value) - float(value)) if value is not None else None
        )
    excel = excel.copy()
    excel["computed_value"] = values
    excel["abs_diff"] = diffs
    return excel


def write_realism2_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Realism 2 comparison table."""
    return write_comparison_csv(build_realism2_comparison(workbook), output)
