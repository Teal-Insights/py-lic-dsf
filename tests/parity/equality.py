"""Numerical equality rule for Output-panel differential tests.

A comparison passes when the absolute difference is at most ``1e-6`` or the
relative difference is at most ``1e-12`` (agreement to 12 significant digits).
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

ABS_TOL = 1e-6
REL_TOL = 1e-12

_EXCEL_BLANK = frozenset({"", "...", "…"})
_EXCEL_NA = frozenset({"n.a.", "n.a", "na", "#n/a", "#n/a!"})
_EXCEL_ERROR_PREFIX = "#"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and pd.notna(
        value
    )


def _is_blank(value: Any) -> bool:
    if value is None or value is pd.NA:
        return True
    try:
        # ``bool(pd.NA)`` raises; compare ``pd.isna`` to True instead.
        if pd.isna(value) is True:
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip().lower() in _EXCEL_BLANK:
        return True
    return False


def error_class(value: Any) -> str | None:
    """Return a normalized Excel error class, or None if ``value`` is not an error."""
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    if text.startswith(_EXCEL_ERROR_PREFIX):
        return text.split("!")[0] + "!" if "!" in text else text
    if text.lower() in _EXCEL_NA:
        return "#N/A"
    return None


def close(left: Any, right: Any) -> bool:
    """Return True when ``left`` and ``right`` agree under the parity rule.

    Args:
        left: Excel-side value.
        right: Python-side value.

    Returns:
        True when both are blank, both share an error class, or numeric values
        satisfy ``abs <= 1e-6`` or relative difference ``<= 1e-12``.
    """
    if _is_blank(left) and _is_blank(right):
        return True
    left_err = error_class(left)
    right_err = error_class(right)
    if left_err is not None or right_err is not None:
        return left_err == right_err
    if isinstance(left, str) or isinstance(right, str):
        return str(left).strip() == str(right).strip()
    if not _is_number(left) or not _is_number(right):
        return left == right
    a = float(left)
    b = float(right)
    if math.isnan(a) and math.isnan(b):
        return True
    delta = abs(a - b)
    if delta <= ABS_TOL:
        return True
    scale = max(abs(a), abs(b))
    if scale == 0.0:
        return True
    return delta / scale <= REL_TOL


def abs_diff(left: Any, right: Any) -> float | None:
    """Absolute difference for two numeric values, else None."""
    if not _is_number(left) or not _is_number(right):
        return None
    return abs(float(left) - float(right))
