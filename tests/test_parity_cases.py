"""Parametrized Excel-oracle parity cases under ``data/parity/cases/``."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity.case_schema import CaseSpec, discover_cases, load_expected
from tests.parity.run_case import assert_case_passed, run_case

_CASES = discover_cases()


def _case_ids() -> list[str]:
    return [c.id for c in _CASES]


@pytest.mark.parametrize("case", _CASES, ids=_case_ids() or ["no-cases"])
def test_parity_case_has_minted_oracle(case: CaseSpec) -> None:
    assert case.expected_path.is_file(), f"mint expected.json for {case.id}"
    expected = load_expected(case.expected_path)
    assert expected.oracle.minted_at, f"{case.id} missing oracle.minted_at"
    assert expected.oracle.excel_build in {"cached", "live", "grapher"}
    assert expected.oracle.template_sha
    assert len(expected.probes) > 0


@pytest.mark.parametrize("case", _CASES, ids=_case_ids() or ["no-cases"])
def test_parity_case_python_matches_excel_golden(case: CaseSpec) -> None:
    frame = assert_case_passed(case)
    assert len(frame) > 0


def test_discover_cases_nonempty() -> None:
    assert _CASES, "expected data/parity/cases/*/case.json"
    ids = {c.id for c in _CASES}
    assert "template-baseline-output11" in ids


def test_run_case_refuses_unminted(tmp_path: Path) -> None:
    case_dir = tmp_path / "unminted"
    case_dir.mkdir()
    (case_dir / "case.json").write_text(
        """
        {
          "id": "unminted",
          "workbook": "data/lic-dsf-template-2025-08-12.xlsx",
          "description": "fixture",
          "inputs": {"overlays": []},
          "probes": {"catalog": "output_11", "years": [2024]},
          "oracle": {"minted_at": null, "template_sha": null, "excel_build": null}
        }
        """,
        encoding="utf-8",
    )
    (case_dir / "expected.json").write_text(
        """
        {
          "oracle": {"minted_at": null, "template_sha": null, "excel_build": null},
          "probes": []
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mint"):
        run_case(case_dir)
