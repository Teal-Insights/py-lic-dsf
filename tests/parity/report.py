"""Aggregate parity case comparison reports for the identity claim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tests.parity.case_schema import CASES_ROOT, discover_cases
from tests.parity.compare import write_parity_csv
from tests.parity.run_case import run_case


def summarize_frame(frame: pd.DataFrame, *, case_id: str) -> dict[str, object]:
    """Return pass counts for one comparison frame."""
    n = len(frame)
    passed = int(frame["passed"].sum()) if n and "passed" in frame.columns else 0
    missing = (
        int(frame["missing_sut"].sum()) if n and "missing_sut" in frame.columns else 0
    )
    failed = n - passed
    by_sheet: dict[str, dict[str, int]] = {}
    if n and "sheet" in frame.columns:
        for sheet, group in frame.groupby("sheet", sort=True):
            by_sheet[str(sheet)] = {
                "probes": len(group),
                "passed": int(group["passed"].sum()),
                "failed": int((~group["passed"]).sum()),
            }
    return {
        "case_id": case_id,
        "probes": n,
        "passed": passed,
        "failed": failed,
        "missing_sut": missing,
        "by_sheet": by_sheet,
    }


def run_corpus(
    cases_root: str | Path | None = None,
    *,
    write_csv_dir: str | Path | None = None,
) -> dict[str, object]:
    """Run every case and return an aggregate identity-claim summary."""
    root = Path(cases_root) if cases_root is not None else CASES_ROOT
    summaries: list[dict[str, object]] = []
    total_probes = 0
    total_passed = 0
    for case in discover_cases(root):
        frame = run_case(case)
        if write_csv_dir is not None:
            out = Path(write_csv_dir) / f"{case.id}.csv"
            write_parity_csv(frame, out)
        summary = summarize_frame(frame, case_id=case.id)
        summaries.append(summary)
        total_probes += int(summary["probes"])
        total_passed += int(summary["passed"])
    return {
        "cases": len(summaries),
        "probes": total_probes,
        "passed": total_passed,
        "failed": total_probes - total_passed,
        "pass_rate": (total_passed / total_probes) if total_probes else 1.0,
        "case_summaries": summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate parity case report")
    parser.add_argument("--cases-root", type=Path, default=CASES_ROOT)
    parser.add_argument("--csv-dir", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run_corpus(args.cases_root, write_csv_dir=args.csv_dir)
    text = json.dumps(report, indent=2)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
