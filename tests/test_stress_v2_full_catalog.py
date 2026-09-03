"""Phase 8 full Output 3-1 / 3-2 catalog acceptance (v2 suite)."""

from __future__ import annotations

import pytest

from lic_dsf.stress.suite import (
    build_output31_from_v2_suite,
    build_output32_from_v2_suite,
)
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.output_3 import output_31_probes, output_32_probes

WORKBOOK = WORKBOOK_XLSX

# Scenarios / indicators still drifting vs cached Excel (KNOWN_GAPS). Catalog
# tests assert zero missing_sut and pass the Excel-green subset.
_OUTPUT31_EXCEL_GREEN = frozenset(
    {
        "Baseline",
        "A1 historical",
        "B1. Real GDP growth",
        "B2. Primary balance",
        "B3. Exports",
        "B4. Other flows",
        "B5. Depreciation",
        "B6. Combination of B1-B5",
        "C3. Commodity price",
        "C4. Market Financing",
    }
)
_OUTPUT31_EXCEL_GREEN_INDICATORS = frozenset(
    {
        "PV of debt-to GDP ratio",
        "PV of debt-to-exports ratio",
    }
)
_OUTPUT32_EXCEL_GREEN = frozenset(
    {
        "Baseline",
        "A1 historical",
        "B1. Real GDP growth",
        "B2. Primary balance",
        "B3. Exports",
        "B4. Other flows",
        "B5. Depreciation",
        "B6. Combination of B1-B5",
        "Threshold",
        "C1. Combined contingent liabilities",
        "C4. Market Financing",
        "A2 custom",
    }
)


@pytest.fixture(scope="module")
def output31_v2():
    return build_output31_from_v2_suite(WORKBOOK)


@pytest.fixture(scope="module")
def output32_v2():
    return build_output32_from_v2_suite(WORKBOOK)


def test_output_31_full_catalog_no_missing_sut(output31_v2) -> None:
    """Every Output 3-1 probe that Excel materializes has a SUT row."""
    probes = output_31_probes(WORKBOOK)
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, output31_v2)
    missing = report[report["missing_sut"]]
    assert missing.empty, missing[["sut_key", "year"]].head(20).to_string()


def test_output_31_excel_green_subset(output31_v2) -> None:
    """Excel-aligned Output 3-1 scenarios pass at global 1e-6 (PV indicators)."""
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] in _OUTPUT31_EXCEL_GREEN
        and p.sut_key[0] in _OUTPUT31_EXCEL_GREEN_INDICATORS
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output31_v2))


def test_b2_output31_ds_excel_green(output31_v2) -> None:
    """B2 Output 3-1 all indicators 2024–2034, including later-year DS."""
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == "B2. Primary balance"
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output31_v2))


def test_output_32_full_catalog_no_missing_sut(output32_v2) -> None:
    """Every Output 3-2 probe that Excel materializes has a SUT row."""
    probes = output_32_probes(WORKBOOK)
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, output32_v2)
    missing = report[report["missing_sut"]]
    assert missing.empty, missing[["sut_key", "year"]].head(20).to_string()


def test_output_32_excel_green_subset(output32_v2) -> None:
    """Excel-aligned Output 3-2 scenarios pass at global 1e-6 (Phase 10/12)."""
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] in _OUTPUT32_EXCEL_GREEN
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output32_v2))


def test_a2_output32_excel_green(output32_v2) -> None:
    """A2 Output 3-2 uses Customized Scenario - public R121/R123 identity."""
    probes = tuple(
        p
        for p in output_32_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == "A2 custom"
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    assert_all_passed(compare_probes(excel, output32_v2))


def test_tailored_external_present_in_output31(output31_v2) -> None:
    """A2 / C1 (and applicable C*) appear in the v2 Output 3-1 table."""
    labels = {idx[1] for idx in output31_v2.index}
    assert "A2 custom" in labels
    assert "C1. Combined contingent liabilities" in labels
