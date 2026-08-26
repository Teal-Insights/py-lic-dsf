"""Live Microsoft Excel oracle and cached-value reader for Output probes.

The Python SUT must not call these helpers when computing tables. Tests and
the parity runner use them as the golden master.

Live Excel requires Windows + Microsoft Excel + the optional ``excel`` extra
(``xlwings``). When Excel is absent, ``excel_available`` is False and
``read_live_output`` raises ``ExcelNotAvailable``.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from tests.parity.probes import Probe, a1


class ExcelNotAvailable(RuntimeError):
    """Raised when live Excel cannot be started."""


def excel_available() -> bool:
    """Return True when live Excel can be driven (opt-in + xlwings + Excel).

    Set ``LIC_DSF_EXCEL=1`` to attempt a live connection. Without that flag
    this is always False so Linux CI never tries to start Excel.
    """
    if os.environ.get("LIC_DSF_EXCEL", "").strip() not in {"1", "true", "yes"}:
        return False
    try:
        import xlwings  # noqa: F401
    except ImportError:
        return False
    try:
        import xlwings as xw

        app = xw.App(visible=False, add_book=False)
        app.quit()
        return True
    except Exception:
        return False


def _require_excel() -> None:
    if not excel_available():
        raise ExcelNotAvailable(
            "live Excel is not available (install the 'excel' extra, set "
            "LIC_DSF_EXCEL=1, and run on Windows with Microsoft Excel)"
        )


def read_live_output(workbook: str | Path, probes: Sequence[Probe]) -> pd.DataFrame:
    """Open a temp copy of ``workbook`` in Excel, calculate, and read probes.

    Args:
        workbook: Path to the LIC-DSF ``.xlsm`` (never mutated).
        probes: Cells to read after a full calculate.

    Returns:
        DataFrame with probe metadata and ``excel_value``.
    """
    _require_excel()
    import xlwings as xw

    src = Path(workbook)
    records: list[dict[object, object]] = []
    tmp_dir = tempfile.mkdtemp(prefix="lic-dsf-excel-")
    tmp_path = Path(tmp_dir) / src.name
    try:
        shutil.copy2(src, tmp_path)
        app = xw.App(visible=False, add_book=False)
        try:
            app.display_alerts = False
            app.screen_updating = False
            book = app.books.open(str(tmp_path), update_links=False, read_only=True)
            try:
                book.app.calculate()
                for probe in probes:
                    if probe.col is None:
                        raise ValueError(f"probe {probe!r} missing col")
                    sheet = book.sheets[probe.sheet]
                    value = sheet.range(a1(probe.row, probe.col)).value
                    records.append(_record(probe, value))
            finally:
                book.close()
        finally:
            app.quit()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return pd.DataFrame.from_records(records)


def read_cached_output(workbook: str | Path, probes: Sequence[Probe]) -> pd.DataFrame:
    """Read last-saved cached values (``data_only``). Not the live-Excel oracle.

    Use this in unit tests on machines without Excel. Values are only as
    fresh as the last save of ``workbook``.
    """
    from fastpyxl import load_workbook

    path = Path(workbook)
    grouped: dict[str, list[Probe]] = {}
    for probe in probes:
        grouped.setdefault(probe.sheet, []).append(probe)
    records: list[dict[object, object]] = []
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        for sheet_name, sheet_probes in grouped.items():
            ws = wb[sheet_name]
            for probe in sheet_probes:
                if probe.col is None:
                    raise ValueError(f"probe {probe!r} missing col")
                records.append(_record(probe, ws.cell(probe.row, probe.col).value))
    finally:
        wb.close()
    return pd.DataFrame.from_records(records)


def _record(probe: Probe, value: object) -> dict[object, object]:
    col = probe.col if probe.col is not None else 0
    return {
        "sheet": probe.sheet,
        "cell": a1(probe.row, col) if probe.col is not None else "",
        "row": probe.row,
        "col": probe.col,
        "year": probe.year,
        "section": probe.section,
        "label": probe.label,
        "sut_key": probe.sut_key,
        "excel_value": value,
    }
