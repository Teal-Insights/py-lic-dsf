"""Phase 12 W0 helper: first-failing public B-sheet cells vs Excel.

Usage::

    PYTHONPATH=src:. .venv/bin/python scripts/stress_phase12_localize.py
    PYTHONPATH=src:. .venv/bin/python scripts/stress_phase12_localize.py --list-sheets
    PYTHONPATH=src:. .venv/bin/python scripts/stress_phase12_localize.py --intermediate
"""

from __future__ import annotations

import argparse

from fastpyxl import load_workbook

from lic_dsf.stress import PublicScenarioRunner, ScenarioRegistry, StressContext
from tests.conftest import WORKBOOK_XLSX
from tests.parity import compare_probes, read_cached_output
from tests.parity.catalogs.bsheet_public import FIRST_COL, PUBLIC_SHEETS, YEAR_ROW
from tests.parity.catalogs.layout import probes_for_metric_rows

# Rows accepted before Output 3-2 (Phase 10 / 12 ladder).
_ROWS: tuple[tuple[int, str], ...] = (
    (41, "gdp_lcu"),
    (90, "public_gfn"),
    (13, "pv_public_to_gdp"),
    (95, "pv_public_to_revenue"),
    (93, "ds_to_revenue"),
)

_INTERMEDIATE_ROWS: tuple[tuple[int, str], ...] = (
    (42, "real_gdp_growth"),
    (54, "lcu_deflator_growth"),
)

_CANDIDATE_SHEETS: dict[str, tuple[str, ...]] = {
    "A1_Historical": ("A1_historical_pub", "A1_Historical_pub"),
    "A2_Custom": ("A2_custom_pub", "A2_Custom_pub"),
    "B1_GDP": ("B1_GDP_pub",),
    "B2_PrimaryBalance": (
        "B2_PB_mkt_pub",
        "B2_PB_pub",
        "B2_primary balance_pub",
        "B2_PrimaryBalance_pub",
    ),
    "B3_Exports": ("B3_Exports_pub", "B3_exports_pub"),
    "B4_OtherFlows": (
        "B4_other flows_pub",
        "B4_OtherFlows_pub",
        "B4_other_flows_pub",
    ),
    "B5_FX": ("B5_depreciation_pub", "B5_FX_pub", "B5_depreciation_mkt_pub"),
    "B6_Combo": ("B6_Combo_mkt_pub", "B6_Combo_pub", "B6_combo_mkt_pub"),
}


def _list_sheets() -> list[str]:
    wb = load_workbook(WORKBOOK_XLSX, data_only=True, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def _resolve_sheet(names: list[str], scenario_id: str) -> str | None:
    if scenario_id in PUBLIC_SHEETS and PUBLIC_SHEETS[scenario_id] in names:
        return PUBLIC_SHEETS[scenario_id]
    for candidate in _CANDIDATE_SHEETS.get(scenario_id, ()):
        if candidate in names:
            return candidate
    return None


def _series_map(result, *, intermediate: bool = False) -> dict[int, object]:
    ratios = result.public_ratios
    assert ratios is not None
    out: dict[int, object] = {
        41: ratios.gdp_lcu(),
        90: ratios.public_gfn(),
        13: ratios.pv_public_debt_to_gdp(),
        95: ratios.pv_public_debt_to_revenue_grants(),
        93: ratios.debt_service_to_revenue_grants(),
    }
    if intermediate:
        from lic_dsf.stress.public import _public_real_and_lcu_deflator

        real_s, defl_s = _public_real_and_lcu_deflator(
            result.path.baseline,
            result.path.shocked,
            ratios.inflation_elasticity,
            historical=False,
            fx_passthrough=ratios.fx_passthrough,
            fx_depreciation_pct=float(result.path.metadata.fx_depreciation_pct),
        )
        out[42] = real_s
        out[54] = defl_s
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-sheets", action="store_true")
    parser.add_argument(
        "--years",
        default="2024-2028",
        help="Inclusive year range, e.g. 2024-2028",
    )
    parser.add_argument(
        "--intermediate",
        action="store_true",
        help="Also compare R42 (real GDP) and R54 (LCU deflator)",
    )
    args = parser.parse_args()
    names = _list_sheets()
    if args.list_sheets:
        print("=== sheets matching pub / B* / A* ===")
        for name in names:
            lowered = name.lower()
            if "pub" in lowered or lowered.startswith(("a1", "a2", "b1", "b2", "b3", "b4", "b5", "b6")):
                print(f"  {name!r}")
        return

    lo, hi = (int(x) for x in args.years.split("-", 1))
    years = range(lo, hi + 1)
    ctx = StressContext.from_workbook(WORKBOOK_XLSX)
    runner = PublicScenarioRunner(context=ctx)

    print("resolved public B-sheets:")
    resolved: dict[str, str] = {}
    for sid in (
        "A1_Historical",
        "B1_GDP",
        "B3_Exports",
        "B5_FX",
        "B6_Combo",
        "B4_OtherFlows",
        "B2_PrimaryBalance",
        "A2_Custom",
    ):
        sheet = _resolve_sheet(names, sid)
        print(f"  {sid}: {sheet}")
        if sheet is not None:
            resolved[sid] = sheet

    rows = _ROWS + (_INTERMEDIATE_ROWS if args.intermediate else ())

    for sid, sheet in resolved.items():
        result = runner.run(ScenarioRegistry.get(sid))
        probes = probes_for_metric_rows(
            path=WORKBOOK_XLSX,
            sheet=sheet,
            year_row=YEAR_ROW,
            first_col=FIRST_COL,
            scenario_id=sid,
            rows=rows,
        )
        probes = tuple(p for p in probes if p.year in years)
        excel = read_cached_output(WORKBOOK_XLSX, probes)
        excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
        series = _series_map(result, intermediate=args.intermediate)
        sut = {}
        for p in probes:
            ser = series[p.row]
            if p.year in ser.index:
                sut[p.sut_key] = float(ser.loc[p.year])
        report = compare_probes(excel, sut, probes=probes)
        fails = report[~report["passed"]]
        print(f"\n=== {sid} ({sheet}): {len(fails)}/{len(report)} fails ===")
        if fails.empty:
            print("ALL PASS")
            continue
        first = fails.sort_values(["year", "row"]).iloc[0]
        print(
            f"first fail: R{int(first['row'])} @ {int(first['year'])}  "
            f"excel={first['excel_value']!r}  py={first['computed_value']!r}  "
            f"abs={first['abs_diff']}"
        )
        print(
            fails.sort_values(["year", "row"])[
                ["year", "row", "label", "excel_value", "computed_value", "abs_diff"]
            ]
            .head(20)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
