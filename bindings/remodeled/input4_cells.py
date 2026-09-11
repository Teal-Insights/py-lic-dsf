#!/usr/bin/env python3
"""A1 range helpers and cell-coverage checks for remodeled Input 4 bindings."""
from __future__ import annotations

import re
from typing import Iterable

COL_RE = re.compile(r"^\$?([A-Za-z]+)\$?(\d+)$")
RANGE_RE = re.compile(r"^(\d+):(\d+)$")


def col_to_num(col: str) -> int:
    n = 0
    for c in col.upper():
        n = n * 26 + (ord(c) - 64)
    return n


def num_to_col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def parse_a1_cell(token: str) -> tuple[int, int]:
    m = COL_RE.match(token.replace("$", "").strip())
    if not m:
        raise ValueError(f"not an A1 cell: {token!r}")
    return col_to_num(m.group(1)), int(m.group(2))


def split_sheet_range(data_range: str) -> tuple[str | None, str]:
    raw = data_range.strip()
    if "!" in raw:
        sheet, a1 = raw.split("!", 1)
        return sheet.strip().strip("'"), a1.strip()
    return None, raw


def expand_a1(a1: str) -> list[tuple[int, int]]:
    a1 = a1.replace("$", "").strip()
    if ":" in a1:
        start, end = a1.split(":", 1)
        c1, r1 = parse_a1_cell(start)
        c2, r2 = parse_a1_cell(end)
        cells: list[tuple[int, int]] = []
        for r in range(min(r1, r2), max(r1, r2) + 1):
            for c in range(min(c1, c2), max(c1, c2) + 1):
                cells.append((c, r))
        return cells
    return [parse_a1_cell(a1)]


def cell_addr(col: int, row: int) -> str:
    return f"{num_to_col(col)}{row}"


def bbox(cells: Iterable[tuple[int, int]]) -> tuple[int, int, int, int]:
    cells = list(cells)
    cs = [c for c, _ in cells]
    rs = [r for _, r in cells]
    return min(cs), min(rs), max(cs), max(rs)


def bbox_a1(cells: Iterable[tuple[int, int]]) -> str:
    c1, r1, c2, r2 = bbox(cells)
    if (c1, r1) == (c2, r2):
        return cell_addr(c1, r1)
    return f"{cell_addr(c1, r1)}:{cell_addr(c2, r2)}"


def compact_row_specs(rows: Iterable[int]) -> list[int | str]:
    """Compress sorted 1-based row numbers to ints and 'start:end' strings."""
    ordered = sorted(set(int(r) for r in rows))
    if not ordered:
        return []
    out: list[int | str] = []
    start = prev = ordered[0]
    for r in ordered[1:]:
        if r == prev + 1:
            prev = r
            continue
        out.append(start if start == prev else f"{start}:{prev}")
        start = prev = r
    out.append(start if start == prev else f"{start}:{prev}")
    return out


def expand_row_specs(specs: Iterable[int | str] | None) -> set[int]:
    rows: set[int] = set()
    if not specs:
        return rows
    for spec in specs:
        if isinstance(spec, int):
            rows.add(spec)
            continue
        text = str(spec)
        m = RANGE_RE.match(text)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            rows.update(range(min(a, b), max(a, b) + 1))
        else:
            rows.add(int(text))
    return rows


def cells_of_range(data_range: str, exclude_rows: Iterable[int | str] | None = None) -> set[str]:
    _, a1 = split_sheet_range(data_range)
    excluded = expand_row_specs(exclude_rows)
    out: set[str] = set()
    for col, row in expand_a1(a1):
        if row in excluded:
            continue
        out.add(cell_addr(col, row))
    return out


def prove_coverage(
    original_ranges: list[str],
    remodeled: list[tuple[str, Iterable[int | str] | None]],
) -> dict:
    """Compare original A1 inventories to remodeled data_range minus exclude_rows."""
    orig: set[str] = set()
    for dr in original_ranges:
        orig |= cells_of_range(dr)
    rem: set[str] = set()
    for dr, exclude in remodeled:
        rem |= cells_of_range(dr, exclude)
    return {
        "original_cells": len(orig),
        "remodeled_cells": len(rem),
        "missing": sorted(orig - rem),
        "extra": sorted(rem - orig),
    }


def _sheet_of(series: dict) -> str:
    sheet = series.get("sheet") or ""
    dr = series.get("data_range") or ""
    if "!" in dr:
        return dr.split("!", 1)[0].strip().strip("'")
    return sheet


def main() -> None:
    """Prove remodeled Input 4 cell coverage against the original shards."""
    from pathlib import Path

    import yaml

    bindings = Path("/workspace/bindings")
    sources = [
        bindings / "inputs.bindings.yaml",
        bindings / "constants.bindings.yaml",
        bindings / "internals-graph-coverage.bindings.yaml",
        bindings / "internals-rest.bindings.yaml",
    ]
    original_ranges: list[str] = []
    for path in sources:
        doc = yaml.safe_load(path.read_text())
        for s in doc.get("series") or []:
            if _sheet_of(s).startswith("Input 4"):
                original_ranges.append(s["data_range"])
    remodeled_doc = yaml.safe_load((bindings / "remodeled" / "input4.bindings.yaml").read_text())
    remodeled = [(s["data_range"], s.get("exclude_rows")) for s in remodeled_doc["series"]]
    result = prove_coverage(original_ranges, remodeled)
    print(f"original cells: {result['original_cells']}")
    print(f"remodeled cells: {result['remodeled_cells']}")
    print(f"missing: {len(result['missing'])}")
    print(f"extra: {len(result['extra'])}")
    if result["missing"]:
        print("missing sample:", result["missing"][:20])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
