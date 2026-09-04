"""Excel vs Python comparison for Realism 3 (invest / growth)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.dsa.compare import write_comparison_csv
from lic_dsf.realism.compare import _a1, _as_year, _books, _year_int
from lic_dsf.output.realism import invest_growth_panel
from lic_dsf.load.realism import load_capital_assumptions

REALISM3_SHEET = "Realism 3 - Invest-Growth"
_CURR_DSA_LABEL = "Real GDP growth - Curr. DSA"
_CHART_YEAR_HEADER_ROW = 19
_CHART_YEAR_FIRST_COL = 3
# Excel chart-block series Python currently owns for this comparison.
_COMPARED_SERIES: dict[str, tuple[str, str]] = {
    _CURR_DSA_LABEL: ("Chart series", _CURR_DSA_LABEL),
}
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


def _year_cols(ws) -> dict[int, int]:
    """Map calendar year → column from the chart-block header row."""
    cols: dict[int, int] = {}
    col = _CHART_YEAR_FIRST_COL
    while True:
        year = _as_year(ws.cell(_CHART_YEAR_HEADER_ROW, col).value)
        if year is None:
            break
        cols[year] = col
        col += 1
    return cols


def _row_label(ws, row: int) -> str:
    for col in (1, 2, 3, 4, 5):
        raw = ws.cell(row, col).value
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _read_excel(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[REALISM3_SHEET]
        year_cols = _year_cols(ws)
        records: list[dict[object, object]] = []
        for row in range(1, (ws.max_row or 0) + 1):
            label = _row_label(ws, row)
            mapping = _COMPARED_SERIES.get(label)
            if mapping is None or not year_cols:
                continue
            section, match_label = mapping
            for year, col in year_cols.items():
                value = ws.cell(row, col).value
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                records.append(
                    {
                        "sheet": REALISM3_SHEET,
                        "cell": _a1(row, col),
                        "row": row,
                        "col": col,
                        "year": year,
                        "section": section,
                        "series_code": label,
                        "label": match_label,
                        "match_key": match_label,
                        "excel_value": float(value),
                    }
                )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


def compute_realism3_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Invest/growth series including current-DSA real GDP growth."""
    path = Path(path)
    macro, _ext, _eb, _pb = _books(str(path))
    growth = macro.real_gdp_growth()
    invest = (
        100.0
        * macro.primary_expenditure().reindex(list(macro.inputs.years)).astype(float)
        / macro.gdp_lcu().replace(0.0, pd.NA)
    )
    panel = invest_growth_panel(
        invest.fillna(0.0), growth, load_capital_assumptions(path)
    )
    store: dict[tuple[str, str], pd.Series] = {
        ("Chart series", _CURR_DSA_LABEL): growth,
    }
    # Invest-growth keys kept for future formula parity; not dual-stuffed under
    # Chart series (avoids accidental label collisions with the allowlisted row).
    for label, row in panel.iterrows():
        store[("Invest-growth", str(label))] = row
    return store


def build_realism3_comparison(path: str | Path) -> pd.DataFrame:
    """Build Excel vs Python table for Realism 3 chart series."""
    path = Path(path)
    excel = _read_excel(path)
    computed = compute_realism3_outputs(path)
    values: list[object] = []
    diffs: list[float | None] = []
    for section, label, year, excel_value in zip(
        excel["section"], excel["label"], excel["year"], excel["excel_value"], strict=True
    ):
        series = computed.get((str(section), str(label)))
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


def write_realism3_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Realism 3 comparison table."""
    return write_comparison_csv(build_realism3_comparison(workbook), output)
