#!/usr/bin/env python3
"""Phase 13 localization: C1/C3/C4 Output 3-1 (+ optional public B-sheet).

Usage::

    PYTHONPATH=src:. .venv/bin/python scripts/stress_phase13_localize.py
    PYTHONPATH=src:. .venv/bin/python scripts/stress_phase13_localize.py --years 2024-2028
"""

from __future__ import annotations

import argparse

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


def _parse_years(text: str) -> range:
    if "-" in text:
        a, b = text.split("-", 1)
        return range(int(a), int(b) + 1)
    return range(int(text), int(text) + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2024-2028")
    args = parser.parse_args()
    years = _parse_years(args.years)

    ctx = StressContext.from_workbook(WORKBOOK_XLSX)
    runner = ExternalScenarioRunner(context=ctx)
    for sid, label in _LABELS.items():
        result = runner.run(ScenarioRegistry.get(sid))  # type: ignore[arg-type]
        public = {}
        results = {}
        if sid == "C1_CombinedCL" and result.public_ratios is not None:
            public[sid] = result
        else:
            results[sid] = result
        v2 = build_output31_external_table(
            ctx.ext_base, results, public_results=public
        )
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
        fails = report[~report["passed"]].copy()
        print(f"\n=== {sid}: {len(fails)}/{len(report)} fails ({args.years}) ===")
        if fails.empty:
            print("ALL PASS")
            continue
        fails["indicator"] = fails["sut_key"].map(
            lambda k: k[0] if isinstance(k, tuple) else str(k)
        )
        print(
            fails[
                ["year", "indicator", "excel_value", "computed_value", "abs_diff"]
            ]
            .sort_values("abs_diff", ascending=False)
            .head(12)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
