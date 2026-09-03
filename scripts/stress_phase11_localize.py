"""Phase 11 W0 helper: first-failing C1/C3/C4 Output 3-1 cells vs Excel.

Usage::

    PYTHONPATH=src .venv/bin/python scripts/stress_phase11_localize.py
"""

from __future__ import annotations

from lic_dsf.stress import ExternalScenarioRunner, ScenarioRegistry, StressContext
from lic_dsf.stress.output_map import build_output31_external_table
from tests.conftest import WORKBOOK_XLSX
from tests.parity import compare_probes, read_cached_output
from tests.parity.catalogs.output_3 import output_31_probes

_LABELS = {
    "C1_CombinedCL": "C1. Combined contingent liabilities",
    "C3_Commodity": "C3. Commodity price",
    "C4_Market": "C4. Market Financing",
}


def main() -> None:
    ctx = StressContext.from_workbook(WORKBOOK_XLSX)
    runner = ExternalScenarioRunner(context=ctx)
    years = range(2024, 2029)
    for sid, label in _LABELS.items():
        result = runner.run(ScenarioRegistry.get(sid))  # type: ignore[arg-type]
        v2 = build_output31_external_table(ctx.ext_base, {sid: result})
        probes = tuple(
            p
            for p in output_31_probes(WORKBOOK_XLSX)
            if isinstance(p.sut_key, tuple)
            and p.sut_key[1] == label
            and p.year in years
        )
        excel = read_cached_output(WORKBOOK_XLSX, probes)
        excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
        report = compare_probes(excel, v2, probes=probes)
        fails = report[~report["passed"]]
        print(f"\n=== {sid}: {len(fails)}/{len(report)} fails (2024–2028) ===")
        if fails.empty:
            print("ALL PASS")
        else:
            print(
                fails[
                    ["year", "label", "excel_value", "computed_value", "abs_diff"]
                ]
                .sort_values("abs_diff", ascending=False)
                .head(12)
                .to_string(index=False)
            )


if __name__ == "__main__":
    main()
