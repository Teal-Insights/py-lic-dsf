"""Shared pytest fixtures and live-Excel skip helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.parity import excel_available

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_XLSX = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsx"
WORKBOOK_XLSM = REPO_ROOT / "data" / "lic-dsf-template-2025-08-12.xlsm"


def stress_v2_enabled() -> bool:
    """Legacy flag name; stress rewrite is the only SUT now."""
    return True


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live_excel: tests that drive live Microsoft Excel (Windows + xlwings)",
    )
    config.addinivalue_line(
        "markers",
        "stress: tests that compare the stress SUT against Excel",
    )


@pytest.fixture
def stress_sut_kind() -> str:
    """Always the stress package SUT (legacy package removed)."""
    return "v2"


skip_without_excel = pytest.mark.skipif(
    not excel_available(),
    reason="live Excel not available (set LIC_DSF_EXCEL=1 on Windows with xlwings)",
)
