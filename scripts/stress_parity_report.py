#!/usr/bin/env python3
"""Stress-layer differential testing coverage report.

Usage:
    uv run python scripts/stress_parity_report.py
    uv run python scripts/stress_parity_report.py --layer bsheet_ext --sut legacy
    uv run python scripts/stress_parity_report.py --layer output31 --sut v2
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_WB = REPO / "data" / "lic-dsf-template-2025-08-12.xlsx"
LAYERS = ("output31", "output32", "bsheet_ext", "bsheet_pub", "resfin")


def _scenario_of(key: object) -> str:
    if isinstance(key, tuple) and len(key) >= 2:
        # Output catalogs: (indicator, scenario); B-sheet: (scenario_id, row, year)
        if len(key) == 3:
            return str(key[0])
        return str(key[1])
    return str(key)


def _summarize(report) -> None:
    total = len(report)
    missing = int(report["missing_sut"].sum()) if "missing_sut" in report.columns else 0
    passed = int(report["passed"].sum()) if "passed" in report.columns else 0
    failed = total - passed
    diffs = report["abs_diff"].dropna() if "abs_diff" in report.columns else report.iloc[0:0]
    max_all = float(diffs.max()) if len(diffs) else 0.0
    print(f"  total={total}  passed={passed}  failed={failed}  missing_sut={missing}  max_abs_diff={max_all:.6g}")
    by: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0, "passed": 0, "failed": 0, "missing": 0, "max_abs": 0.0}
    )
    for _, row in report.iterrows():
        sid = _scenario_of(row.get("sut_key"))
        bucket = by[sid]
        bucket["count"] += 1
        if bool(row.get("missing_sut")):
            bucket["missing"] += 1
        if bool(row.get("passed")):
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
        diff = row.get("abs_diff")
        try:
            val = float(diff)
        except (TypeError, ValueError):
            continue
        if math.isfinite(val):
            bucket["max_abs"] = max(bucket["max_abs"], val)
    print(f"  {'scenario':<45} {'n':>6} {'pass':>6} {'fail':>6} {'miss':>6} {'max_abs':>12}")
    print("  " + "-" * 85)
    for sid in sorted(by, key=lambda k: -by[k]["failed"]):
        b = by[sid]
        print(
            f"  {sid:<45} {int(b['count']):6} {int(b['passed']):6} "
            f"{int(b['failed']):6} {int(b['missing']):6} {b['max_abs']:12.6g}"
        )


def _report_layer(layer: str, sut: str, workbook: Path) -> None:
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "src"))
    from tests.parity import compare_probes, read_cached_output
    from tests.parity.stress_sut import build_sut, probes_for_layer

    probes = probes_for_layer(layer, workbook)  # type: ignore[arg-type]
    excel = read_cached_output(workbook, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    mapping = build_sut(layer, sut, workbook)  # type: ignore[arg-type]
    frame = compare_probes(excel, mapping)
    print(f"\n[{layer}] sut={sut}  workbook={workbook.name}")
    _summarize(frame)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stress parity coverage (pass / fail / missing_sut)"
    )
    parser.add_argument("workbook", nargs="?", type=Path, default=DEFAULT_WB)
    parser.add_argument(
        "--layer",
        choices=LAYERS,
        help="One catalog layer (default: all)",
    )
    parser.add_argument(
        "--sut",
        choices=("legacy", "v2"),
        default="legacy",
        help="SUT builder (legacy runners or v2 suite; Phase 8 cutover)",
    )
    args = parser.parse_args()
    layers = (args.layer,) if args.layer else LAYERS
    for layer in layers:
        _report_layer(layer, args.sut, args.workbook)


if __name__ == "__main__":
    main()
