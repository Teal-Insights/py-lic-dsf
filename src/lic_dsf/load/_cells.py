"""Shared Excel cell coercions for workbook loaders.

Not part of the public ``lic_dsf.load`` API.
"""

from __future__ import annotations

from typing import Any


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def _prefer_user(default: Any, user: Any) -> float:
    """Return user column when numeric, else default."""
    user_n = _as_float(user)
    if user_n is not None:
        return user_n
    default_n = _as_float(default)
    if default_n is None:
        raise ValueError(f"expected numeric Input 6 cell, got {default!r}/{user!r}")
    return default_n


def _tailored_applicability(ws: Any) -> dict[str, bool]:
    """Read tailored-test On/Off flags from Input 6 - Tailored Tests."""
    flags: dict[str, bool] = {}
    for row, key in ((9, "C2_NaturalDisaster"), (10, "C3_Commodity"), (11, "C4_Market")):
        raw = ws.cell(row, 3).value
        flags[key] = str(raw or "").strip().lower() == "yes"
    return flags
