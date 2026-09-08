"""Full Output 3-1 / 3-2 catalog acceptance through :class:`StressSuite`."""

from __future__ import annotations

import pytest

from lic_dsf.stress.suite import build_output31_from_suite, build_output32_from_suite
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes

WORKBOOK = WORKBOOK_XLSX

# Excel parity is asserted on this horizon; later years are only required to
# have a SUT value.
_FIRST_YEAR, _LAST_YEAR = 2024, 2034


@pytest.fixture(scope="module")
def output31():
    return build_output31_from_suite(WORKBOOK)


@pytest.fixture(scope="module")
def output32():
    return build_output32_from_suite(WORKBOOK)


def _numeric_excel(probes):
    excel = read_cached_output(WORKBOOK, probes)
    return excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]


def _in_horizon(probes):
    return tuple(
        p
        for p in probes
        if p.year is not None and _FIRST_YEAR <= int(p.year) <= _LAST_YEAR
    )


def test_output_31_full_catalog_no_missing_sut(output31) -> None:
    """Every Output 3-1 probe that Excel materializes has a SUT row."""
    report = compare_probes(_numeric_excel(output_31_probes(WORKBOOK)), output31)
    missing = report[report["missing_sut"]]
    assert missing.empty, missing[["sut_key", "year"]].head(20).to_string()


def test_output_31_matches_excel(output31) -> None:
    """All Output 3-1 scenarios and indicators match Excel at global tolerance."""
    excel = _numeric_excel(_in_horizon(output_31_probes(WORKBOOK)))
    assert_all_passed(compare_probes(excel, output31))


def test_output_32_full_catalog_no_missing_sut(output32) -> None:
    """Every Output 3-2 probe that Excel materializes has a SUT row."""
    report = compare_probes(_numeric_excel(output_32_probes(WORKBOOK)), output32)
    missing = report[report["missing_sut"]]
    assert missing.empty, missing[["sut_key", "year"]].head(20).to_string()


def test_output_32_matches_excel(output32) -> None:
    """All Output 3-2 scenarios (incl. A2 / C* / Threshold) match Excel."""
    excel = _numeric_excel(_in_horizon(output_32_probes(WORKBOOK)))
    assert_all_passed(compare_probes(excel, output32))
