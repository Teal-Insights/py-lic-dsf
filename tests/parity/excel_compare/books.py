"""Workbook → core books loader for legacy CSV compare modules."""

from __future__ import annotations

from functools import lru_cache

from lic_dsf.load.core import load_core


@lru_cache(maxsize=4)
def books(path: str):
    """Return ``(macro, external, ext_base, pub_base)`` for ``path``."""
    return load_core(path)
