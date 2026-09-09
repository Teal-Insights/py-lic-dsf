"""Mint ``expected.json`` goldens from Excel live, cached cells, or excel-grapher.

Never imports or calls Python SUT builders.

Usage::

    uv run python -m tests.parity.mint --case template-baseline-output11
    uv run python -m tests.parity.mint --all --source cached
    uv run python -m tests.parity.mint --case overlay-fx50-output31 --source grapher
    LIC_DSF_EXCEL=1 uv run python -m tests.parity.mint --case ... --source live
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from tests.parity.case_schema import (
    CASES_ROOT,
    REPO_ROOT,
    CaseSpec,
    ExpectedBundle,
    ExpectedProbe,
    OracleMeta,
    discover_cases,
    dump_expected,
    file_sha256,
    load_case,
    update_case_oracle,
)
from tests.parity.catalog_registry import resolve_probes
from tests.parity.excel import (
    ExcelNotAvailable,
    excel_available,
    read_cached_output,
    read_live_output,
)
from tests.parity.grapher import (
    GrapherNotAvailable,
    grapher_available,
    read_grapher_output,
)
from tests.parity.probes import Probe


def _numeric_only(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["excel_value"].map(lambda v: isinstance(v, (int, float)))].copy()


def _probes_from_frame(frame: pd.DataFrame) -> tuple[ExpectedProbe, ...]:
    probes: list[ExpectedProbe] = []
    for row in frame.itertuples(index=False):
        probes.append(
            ExpectedProbe(
                sheet=str(row.sheet),
                cell=str(row.cell),
                row=int(row.row),
                col=int(row.col) if row.col is not None and not pd.isna(row.col) else None,
                year=int(row.year) if row.year is not None and not pd.isna(row.year) else None,
                section=str(row.section or ""),
                label=str(row.label or ""),
                sut_key=row.sut_key,
                excel_value=row.excel_value,
            )
        )
    return tuple(probes)


def read_oracle(
    workbook: Path,
    probes: tuple[Probe, ...],
    *,
    source: str,
    overlays: tuple = (),
) -> pd.DataFrame:
    """Read probe values from live Excel, grapher, or cached ``data_only`` cells."""
    if source == "live":
        if not excel_available():
            raise ExcelNotAvailable(
                "live mint requires LIC_DSF_EXCEL=1, the excel extra, and Windows Excel"
            )
        return read_live_output(workbook, probes, overlays=overlays)
    if source == "grapher":
        if not grapher_available():
            raise GrapherNotAvailable(
                "grapher mint requires the 'grapher' extra "
                "(excel-grapher + fastpyxl>=1.1)"
            )
        return read_grapher_output(workbook, probes, overlays=overlays)
    if source == "cached":
        if overlays:
            raise ValueError(
                "cached oracle cannot apply overlays (no recalculation); "
                "use --source grapher or --source live"
            )
        return read_cached_output(workbook, probes)
    raise ValueError(f"unknown source {source!r}")


def mint_case(
    case: CaseSpec,
    *,
    source: str = "cached",
    numeric_only: bool = True,
    repo_root: Path | None = None,
) -> ExpectedBundle:
    """Mint goldens for ``case`` and write ``expected.json`` + oracle metadata.

    Args:
        case: Case to mint.
        source: ``cached``, ``grapher`` (excel-grapher evaluator), or ``live``.
        numeric_only: Drop blank / non-numeric Excel cells from the golden.
        repo_root: Repo root for workbook resolution.

    Returns:
        The written expected bundle.
    """
    root = repo_root or REPO_ROOT
    overlays = case.inputs.resolved_overlays()
    if overlays and source == "cached":
        raise ValueError(
            f"case {case.id!r} has overlays; cached mint cannot recalculate "
            "formulas — use --source grapher or --source live"
        )
    src_workbook = case.workbook_path(root)
    workbook_for_oracle = src_workbook
    if source == "live" and src_workbook.suffix.lower() == ".xlsx":
        xlsm = src_workbook.with_suffix(".xlsm")
        if xlsm.is_file():
            workbook_for_oracle = xlsm

    probes = resolve_probes(case, src_workbook)
    if not probes:
        raise ValueError(f"case {case.id!r} resolved zero probes")

    if source == "live":
        frame = read_oracle(
            workbook_for_oracle, probes, source=source, overlays=overlays
        )
    elif source == "grapher":
        frame = read_oracle(src_workbook, probes, source=source, overlays=overlays)
    else:
        frame = read_oracle(src_workbook, probes, source=source)

    if numeric_only:
        frame = _numeric_only(frame)
    if frame.empty:
        raise ValueError(f"case {case.id!r} minted zero numeric probes")

    build = {"live": "live", "grapher": "grapher", "cached": "cached"}[source]
    oracle = OracleMeta(
        minted_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        template_sha=file_sha256(src_workbook),
        excel_build=build,  # type: ignore[arg-type]
    )
    bundle = ExpectedBundle(probes=_probes_from_frame(frame), oracle=oracle)
    dump_expected(bundle, case.expected_path)
    update_case_oracle(case, oracle)
    return bundle


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mint oracle expected.json for parity cases (no Python SUT)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="Case id under data/parity/cases/ (repeatable)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Mint every case under data/parity/cases/",
    )
    parser.add_argument(
        "--source",
        choices=("cached", "grapher", "live"),
        default="cached",
        help=(
            "Oracle source (default: cached). "
            "grapher = excel-grapher evaluator (fast proxy); "
            "live = Windows Excel COM."
        ),
    )
    parser.add_argument(
        "--keep-blanks",
        action="store_true",
        help="Keep non-numeric Excel cells in expected.json",
    )
    parser.add_argument(
        "--cases-root",
        type=Path,
        default=CASES_ROOT,
        help="Cases directory (default: data/parity/cases)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.all:
        cases = list(discover_cases(args.cases_root))
    else:
        cases = []
        for case_id in args.cases:
            path = args.cases_root / case_id
            if not path.is_dir():
                print(f"error: unknown case {case_id!r} ({path})", file=sys.stderr)
                return 2
            cases.append(load_case(path))
    if not cases:
        print("error: no cases found", file=sys.stderr)
        return 2

    failures = 0
    for case in cases:
        try:
            bundle = mint_case(
                case,
                source=args.source,
                numeric_only=not args.keep_blanks,
            )
        except (
            OSError,
            ValueError,
            KeyError,
            ExcelNotAvailable,
            GrapherNotAvailable,
            TypeError,
        ) as exc:
            print(f"FAIL {case.id}: {exc}", file=sys.stderr)
            failures += 1
            continue
        print(
            f"OK   {case.id}: {len(bundle.probes)} probes "
            f"({bundle.oracle.excel_build}) -> {case.expected_path}"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
