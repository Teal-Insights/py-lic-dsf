"""Phase 9 W0 helper: first-failing B3/B5/B6 B-sheet cells vs Excel.

Usage::

    .venv/bin/python scripts/stress_phase9_localize.py
"""

from __future__ import annotations

from lic_dsf.stress import ExternalScenarioRunner, ScenarioRegistry, StressContext
from tests.conftest import WORKBOOK_XLSX
from tests.parity import compare_probes, read_cached_output
from tests.parity.catalogs.bsheet_external import bsheet_external_probes


def main() -> None:
    ctx = StressContext.from_workbook(WORKBOOK_XLSX)
    runner = ExternalScenarioRunner(context=ctx)
    years = range(2024, 2029)
    for sid in ("B3_Exports", "B5_FX", "B6_Combo"):
        result = runner.run(ScenarioRegistry.get(sid))
        probes = tuple(
            p
            for p in bsheet_external_probes(WORKBOOK_XLSX, sid)
            if p.year in years and p.row in (86, 87, 35, 36, 39, 40)
        )
        excel = read_cached_output(WORKBOOK_XLSX, probes)
        excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
        ratios = result.external_ratios
        assert ratios is not None
        series = {
            35: ratios.pv_ppg_external_to_gdp(),
            36: ratios.pv_ppg_external_to_exports(),
            39: ratios.ppg_debt_service_to_exports(),
            40: ratios.ppg_debt_service_to_revenue(),
            86: result.external_gap.gap,
            87: result.external_gap.gap,
        }
        sut = {p.sut_key: float(series[p.row].loc[p.year]) for p in probes}
        report = compare_probes(excel, sut, probes=probes)
        fails = report[~report["passed"]]
        print(f"\n=== {sid}: {len(fails)}/{len(report)} fails ===")
        if fails.empty:
            print("ALL PASS")
        else:
            print(
                fails[["year", "row", "label", "excel_value", "computed_value", "abs_diff"]]
                .head(15)
                .to_string(index=False)
            )


if __name__ == "__main__":
    main()
