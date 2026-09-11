"""Write ``OutputBook`` panels to a new multi-sheet workbook.

Does not overwrite the official LIC-DSF template; produces a sidecar ``.xlsx``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import Workbook
from fastpyxl.utils.dataframe import dataframe_to_rows

from lic_dsf.run import OutputBook, compute_outputs

_INVALID_SHEET_CHARS = set(r"\/*?:[]")


def sanitize_sheet_title(title: str, *, max_len: int = 31) -> str:
    """Return an Excel-safe sheet title (≤31 chars, no illegal characters)."""
    cleaned = "".join("_" if ch in _INVALID_SHEET_CHARS else ch for ch in title)
    cleaned = cleaned.strip() or "Sheet"
    return cleaned[:max_len]


def _flatten_for_excel(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy a frame with MultiIndex index/columns flattened to strings."""
    out = frame.copy()
    if isinstance(out.index, pd.MultiIndex):
        out.index = [
            " | ".join(str(part) for part in key) for key in out.index.to_list()
        ]
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [
            " | ".join(str(part) for part in key) for key in out.columns.to_list()
        ]
    return out


def _excel_scalar(value: Any) -> Any:
    """Coerce pandas/numpy scalars to plain Python values for fastpyxl."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    return value


def _rows_for_sheet(frame: pd.DataFrame) -> list[list[Any]]:
    """Build Excel rows from a DataFrame, dropping blank separator rows."""
    flat = _flatten_for_excel(frame)
    rows: list[list[Any]] = []
    for raw in dataframe_to_rows(flat, index=True, header=True):
        coerced = [_excel_scalar(cell) for cell in raw]
        if all(cell is None or cell == "" for cell in coerced):
            continue
        rows.append(coerced)
    return rows


def to_workbook(book: OutputBook, path: str | Path) -> Path:
    """Write each panel in ``book`` to a sheet of a new ``.xlsx``.

    Args:
        book: Computed output panels.
        path: Destination workbook path (created or overwritten).

    Returns:
        Resolved destination path.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    # Remove the default empty sheet after the first real sheet is added.
    default = wb.active
    first = True
    used_titles: set[str] = set()

    for title, frame in book.sheets.items():
        safe = sanitize_sheet_title(title)
        base = safe
        suffix = 1
        while safe.lower() in used_titles:
            tail = f"_{suffix}"
            safe = sanitize_sheet_title(base[: max(1, 31 - len(tail))] + tail)
            suffix += 1
        used_titles.add(safe.lower())

        if first:
            ws = default
            ws.title = safe
            first = False
        else:
            ws = wb.create_sheet(title=safe)

        for row in _rows_for_sheet(frame):
            ws.append(row)

    if first:
        # No sheets requested — keep a stub so the file is valid.
        default.title = "Empty"

    # Optional metadata sheet (does not collide with Output titles).
    meta_ws = wb.create_sheet(title="Engine meta")
    meta_ws.append(["key", "value"])
    for key, value in book.meta.items():
        meta_ws.append([key, _excel_scalar(value)])

    wb.save(destination)
    return destination.resolve()


def to_workbook_from_path(
    path_in: str | Path,
    path_out: str | Path,
    *,
    include: set[str] | frozenset[str] | list[str] | tuple[str, ...] | None = None,
) -> Path:
    """Compute Output panels from ``path_in`` and write them to ``path_out``.

    Args:
        path_in: LIC-DSF country workbook.
        path_out: Destination sidecar ``.xlsx``.
        include: Optional subset of sheet titles (see ``lic_dsf.run.OUTPUT_SHEET_ORDER``).

    Returns:
        Resolved destination path.
    """
    book = compute_outputs(path_in, include=include)
    return to_workbook(book, path_out)
