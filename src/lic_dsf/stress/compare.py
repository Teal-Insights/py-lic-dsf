"""Excel vs Python comparison for Outputs 2-1/3-1 and 2-2/3-2."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.dsa.compare import (
    pair_frame,
    record_cell,
    write_comparison_csv,
    year_cols,
)
from lic_dsf.load.core import load_core
from lic_dsf.load.input6 import load_input6_standard
from lic_dsf.load.input7 import load_input7_residual_params
from lic_dsf.load.rating import load_ci_summary
from lic_dsf.stress import (
    run_a1_historical_external,
    run_b1_gdp_public,
    run_standard_external_stress,
)

OUTPUT31_SHEET = "Output 3-1 Stress-external"
OUTPUT32_SHEET = "Output 3-2 Stress-public"

_OUTPUT31_YEAR_ROW = 6
_OUTPUT31_FIRST_COL = 3
_OUTPUT31_LABEL_COL = 1
_OUTPUT32_YEAR_ROW = 8
_OUTPUT32_FIRST_COL = 4
_OUTPUT32_LABEL_COL = 2

_EXT_SECTIONS = {
    "pv of debt-to gdp ratio": "PV of debt-to GDP ratio",
    "pv of debt-to-exports ratio": "PV of debt-to-exports ratio",
    "debt service-to-exports ratio": "Debt service-to-exports ratio",
    "debt service-to-revenue ratio": "Debt service-to-revenue ratio",
}

_PUB_SECTIONS = {
    "pv of debt-to-gdp ratio": "PV of Debt-to-GDP Ratio",
    "pv of debt-to-revenue ratio": "PV of Debt-to-Revenue Ratio",
    "debt service-to-revenue ratio": "Debt Service-to-Revenue Ratio",
    "debt service-to-gdp ratio": "Debt Service-to-GDP Ratio",
}

_SCENARIO_KEYS = {
    "baseline": "Baseline",
    "a1. key variables at their historical averages in 2024-2034 2/": "A1 historical",
    "a2. alternative scenario": "A2 custom",
    "b1. real gdp growth": "B1. Real GDP growth",
    "b2. primary balance": "B2. Primary balance",
    "b3. exports": "B3. Exports",
    "b4. other flows 3/": "B4. Other flows",
    "b5. depreciation": "B5. Depreciation",
    "b6. combination of b1-b5": "B6. Combination of B1-B5",
    "c1. combined contingent liabilities": "C1. Combined contingent liabilities",
    "c2. natural disaster": "C2. Natural disaster",
    "c3. commodity price": "C3. Commodity price",
    "c4. market financing": "C4. Market Financing",
    "threshold": "Threshold",
    "total public debt benchmark": "Threshold",
}

_EXT_METHODS = {
    "PV of debt-to GDP ratio": ("pv_ppg_external_to_gdp", "pv_debt_to_gdp"),
    "PV of debt-to-exports ratio": (
        "pv_ppg_external_to_exports",
        "pv_debt_to_exports",
    ),
    "Debt service-to-exports ratio": (
        "ppg_debt_service_to_exports",
        "debt_service_to_exports",
    ),
    "Debt service-to-revenue ratio": (
        "ppg_debt_service_to_revenue",
        "debt_service_to_revenue",
    ),
}

_PUB_METHODS = {
    "PV of Debt-to-GDP Ratio": "pv_public_debt_to_gdp",
    "PV of Debt-to-Revenue Ratio": "pv_public_debt_to_revenue_grants",
    "Debt Service-to-Revenue Ratio": "debt_service_to_revenue_grants",
}

_EXT_SCENARIO_IDS = {
    "B1. Real GDP growth": "B1_GDP",
    "B2. Primary balance": "B2_PrimaryBalance",
    "B3. Exports": "B3_Exports",
    "B4. Other flows": "B4_OtherFlows",
    "B5. Depreciation": "B5_FX",
    "B6. Combination of B1-B5": "B6_Combo",
}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _constant(value: float, years: list[int]) -> pd.Series:
    return pd.Series(float(value), index=years, dtype=float)


def _read_scenario_table(
    path: Path,
    *,
    sheet: str,
    year_row: int,
    first_col: int,
    label_col: int,
    sections: dict[str, str],
    allowed_keys: set[str],
) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        cols = year_cols(ws, year_row, first_col)
        records: list[dict[str, Any]] = []
        section = ""
        for row in range(1, (ws.max_row or 0) + 1):
            raw = ws.cell(row, label_col).value
            header = _norm(raw)
            if header in sections:
                section = sections[header]
                continue
            key = _SCENARIO_KEYS.get(header)
            if key is None or not section or key not in allowed_keys:
                continue
            label = str(raw).strip()
            for year, col in cols.items():
                value = ws.cell(row, col).value
                if not _is_number(value):
                    continue
                records.append(
                    record_cell(
                        sheet=sheet,
                        row=row,
                        col=col,
                        year=year,
                        section=section,
                        series_code=key,
                        label=label,
                        match_key=key,
                        value=float(value),
                    )
                )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


@dataclass(frozen=True, slots=True)
class _StressBundle:
    ext_base: Any
    pub_base: Any
    external_stress: dict[str, Any]
    historical: Any
    public_b1: Any
    thresholds: dict[str, float]


@lru_cache(maxsize=4)
def _stress_bundle(path: str) -> _StressBundle:
    macro, external, ext_base, pub_base = load_core(path)
    input6 = load_input6_standard(path)
    residual = load_input7_residual_params(path)
    return _StressBundle(
        ext_base=ext_base,
        pub_base=pub_base,
        external_stress=run_standard_external_stress(
            macro, external, input6, residual, workbook_path=path
        ),
        historical=run_a1_historical_external(macro, external, residual),
        public_b1=run_b1_gdp_public(macro, external, input6, residual),
        thresholds=load_ci_summary(path).thresholds.as_dict(),
    )


def compute_output21_31_outputs(
    path: str | Path,
) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 2-1 / 3-1 paths keyed by `(section, match_key)`."""
    stress = _stress_bundle(str(Path(path)))
    years = [int(y) for y in stress.ext_base.years]
    store: dict[tuple[str, str], pd.Series] = {}
    for section, (method, thresh_key) in _EXT_METHODS.items():
        store[(section, "Baseline")] = getattr(stress.ext_base, method)()
        store[(section, "A1 historical")] = getattr(stress.historical, method)()
        for key, sid in _EXT_SCENARIO_IDS.items():
            store[(section, key)] = getattr(stress.external_stress[sid], method)()
        store[(section, "Threshold")] = _constant(
            float(stress.thresholds[thresh_key]), years
        )
    return store


def compute_output22_32_outputs(
    path: str | Path,
) -> dict[tuple[str, str], pd.Series]:
    """Compute Output 2-2 / 3-2 paths keyed by `(section, match_key)`."""
    stress = _stress_bundle(str(Path(path)))
    years = [int(y) for y in stress.pub_base.years]
    thresh = float(stress.thresholds["public_pv_debt_to_gdp"])
    store: dict[tuple[str, str], pd.Series] = {}
    for section, method in _PUB_METHODS.items():
        store[(section, "Baseline")] = getattr(stress.pub_base, method)()
        store[(section, "B1. Real GDP growth")] = getattr(stress.public_b1, method)()
        if section == "PV of Debt-to-GDP Ratio":
            store[(section, "Threshold")] = _constant(thresh, years)
    return store


def build_output21_31_comparison(path: str | Path) -> pd.DataFrame:
    """Build Excel vs Python table for Output 2-1 charts / 3-1 tables."""
    path = Path(path)
    excel = _read_scenario_table(
        path,
        sheet=OUTPUT31_SHEET,
        year_row=_OUTPUT31_YEAR_ROW,
        first_col=_OUTPUT31_FIRST_COL,
        label_col=_OUTPUT31_LABEL_COL,
        sections=_EXT_SECTIONS,
        allowed_keys={
            "Baseline",
            "A1 historical",
            *_EXT_SCENARIO_IDS,
            "Threshold",
        },
    )
    return pair_frame(excel, compute_output21_31_outputs(path))


def build_output22_32_comparison(path: str | Path) -> pd.DataFrame:
    """Build Excel vs Python table for Output 2-2 charts / 3-2 tables."""
    path = Path(path)
    excel = _read_scenario_table(
        path,
        sheet=OUTPUT32_SHEET,
        year_row=_OUTPUT32_YEAR_ROW,
        first_col=_OUTPUT32_FIRST_COL,
        label_col=_OUTPUT32_LABEL_COL,
        sections=_PUB_SECTIONS,
        allowed_keys={"Baseline", "B1. Real GDP growth", "Threshold"},
    )
    return pair_frame(excel, compute_output22_32_outputs(path))


def write_output21_31_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 2-1 / 3-1 comparison table to `output`."""
    return write_comparison_csv(build_output21_31_comparison(workbook), output)


def write_output22_32_comparison_csv(workbook: str | Path, output: str | Path) -> Path:
    """Write the Output 2-2 / 3-2 comparison table to `output`."""
    return write_comparison_csv(build_output22_32_comparison(workbook), output)
