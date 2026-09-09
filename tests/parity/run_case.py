"""Run a parity case: materialize workbook → Python SUT → compare to expected.json."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tests.parity.case_schema import (
    REPO_ROOT,
    CaseSpec,
    ExpectedBundle,
    load_case,
    load_expected,
)
from tests.parity.catalog_registry import resolve_sut
from tests.parity.compare import assert_all_passed, compare_probes
from tests.parity.overlays import materialize_workbook


def expected_frame(bundle: ExpectedBundle) -> pd.DataFrame:
    """Build a ``compare_probes``-compatible Excel frame from goldens."""
    return pd.DataFrame(
        [
            {
                "sheet": p.sheet,
                "cell": p.cell,
                "row": p.row,
                "col": p.col,
                "year": p.year,
                "section": p.section,
                "label": p.label,
                "sut_key": p.sut_key,
                "excel_value": p.excel_value,
            }
            for p in bundle.probes
        ]
    )


def run_case(
    case: CaseSpec | str | Path,
    *,
    repo_root: Path | None = None,
    expected: ExpectedBundle | None = None,
) -> pd.DataFrame:
    """Compare Python SUT for ``case`` against Excel-minted ``expected.json``.

    Args:
        case: CaseSpec or path to the case directory.
        repo_root: Repo root for resolving relative workbook paths.
        expected: Optional preloaded goldens (defaults to case ``expected.json``).

    Returns:
        Comparison frame from ``compare_probes``.

    Raises:
        FileNotFoundError: When ``expected.json`` is missing.
        ValueError: When oracle metadata is incomplete (unminted case).
    """
    root = repo_root or REPO_ROOT
    if not isinstance(case, CaseSpec):
        case = load_case(case)
    if expected is None:
        if not case.expected_path.is_file():
            raise FileNotFoundError(
                f"missing {case.expected_path}; mint with "
                "`uv run python -m tests.parity.mint --case "
                f"{case.id}`"
            )
        expected = load_expected(case.expected_path)
    if expected.oracle.minted_at is None or expected.oracle.excel_build is None:
        raise ValueError(
            f"case {case.id!r} expected.json missing oracle mint metadata; "
            "refuse to treat unminted goldens as Excel oracle"
        )
    workbook = materialize_workbook(
        case.workbook_path(root),
        case.inputs.resolved_overlays(),
    )
    sut = resolve_sut(case, workbook)
    frame = compare_probes(expected_frame(expected), sut)
    return frame


def assert_case_passed(
    case: CaseSpec | str | Path,
    *,
    repo_root: Path | None = None,
) -> pd.DataFrame:
    """Run ``case`` and raise if any probe fails."""
    frame = run_case(case, repo_root=repo_root)
    assert_all_passed(frame)
    return frame
