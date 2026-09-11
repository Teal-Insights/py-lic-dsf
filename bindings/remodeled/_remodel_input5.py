#!/usr/bin/env python3
"""Reshape-to-keys prototype for Input 5 (LIC-DSF) series bindings.

Reads the four source catalogs, lifts one-series-per-instrument (and per
vintage issuance year) members onto semantic keys, and writes:

  bindings/remodeled/input5.bindings.yaml
  bindings/remodeled/input5-audit.md

Does not modify lic_dsf packages or original binding shards.
"""
from __future__ import annotations

import copy
import re
from collections import defaultdict
from pathlib import Path

import yaml

SHEET = "Input 5 - Local-debt Financing"
SCHEMA_VERSION = "1.13.0"
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ROW_SPEC_RE = re.compile(r"^[1-9][0-9]*(:[1-9][0-9]*)?$")
COL_RE = re.compile(r"^\$?([A-Za-z]+)\$?(\d+)$")

ROOT = Path("/workspace/bindings")
SOURCES = [
    ROOT / "internals-input5.bindings.yaml",
    ROOT / "inputs.bindings.yaml",
    ROOT / "constants.bindings.yaml",
    ROOT / "internals-graph-coverage.bindings.yaml",
]
OUT_YAML = ROOT / "remodeled" / "input5.bindings.yaml"
OUT_AUDIT = ROOT / "remodeled" / "input5-audit.md"

LIFT_DIMS = ("INSTRUMENT", "HOLDER", "ISSUANCE_YEAR")
VINTAGE_OUTPUT_IDS = {
    "Stock of debt": "input5_vintage_stock",
    "Principal Payments": "input5_vintage_principal",
    "Interest Payments": "input5_vintage_interest",
}
# Same INDICATOR appears as input: and as internal: — keep both, prefix internals.
OVERLAP_INDICATORS = {
    "Interest rate on domestic debt",
    "Grace period",
    "Maturity",
}


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
    m = COL_RE.match(token.replace("$", ""))
    if not m:
        raise ValueError(token)
    return col_to_num(m.group(1)), int(m.group(2))


def split_sheet_range(data_range: str) -> tuple[str | None, str]:
    raw = data_range.strip()
    if "!" in raw:
        sheet, a1 = raw.split("!", 1)
        return sheet.strip().strip("'"), a1.strip().strip("'")
    return None, raw


def expand_a1(a1: str) -> set[tuple[int, int]]:
    a1 = a1.replace("$", "").strip()
    if ":" in a1:
        start, end = a1.split(":", 1)
        c1, r1 = parse_a1_cell(start)
        c2, r2 = parse_a1_cell(end)
        return {
            (c, r)
            for r in range(min(r1, r2), max(r1, r2) + 1)
            for c in range(min(c1, c2), max(c1, c2) + 1)
        }
    return {parse_a1_cell(a1)}


def cells_to_a1(cells: set[tuple[int, int]]) -> str:
    cs = [c for c, _ in cells]
    rs = [r for _, r in cells]
    c1, c2, r1, r2 = min(cs), max(cs), min(rs), max(rs)
    start = f"{num_to_col(c1)}{r1}"
    end = f"{num_to_col(c2)}{r2}"
    return start if start == end else f"{start}:{end}"


def format_data_range(a1: str) -> str:
    return f"'{SHEET}'!{a1}"


def direction_of(series: dict) -> str:
    if "input" in series:
        return "input"
    if "constant" in series:
        return "constant"
    if "output" in series:
        return "output"
    return "internal"


def compress_ranges(nums: list[int]) -> list[tuple[int, int]]:
    if not nums:
        return []
    nums = sorted(set(nums))
    out: list[tuple[int, int]] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        out.append((start, prev))
        start = prev = n
    out.append((start, prev))
    return out


def range_to_spec(a: int, b: int) -> int | str:
    return a if a == b else f"{a}:{b}"


def specs_from_rows(rows: list[int]) -> int | str | list:
    ranges = compress_ranges(rows)
    specs = [range_to_spec(a, b) for a, b in ranges]
    if len(specs) == 1:
        return specs[0]
    return specs


def exclude_row_specs(rows: list[int]) -> list[int | str]:
    return [range_to_spec(a, b) for a, b in compress_ranges(rows)]


def slug(text: str | None, max_len: int = 100) -> str:
    if not text:
        return ""
    t = text.lower()
    t = t.replace("%", "pct").replace("&", "and")
    t = t.replace("o/w", "ow").replace("o / w", "ow")
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    if len(t) > max_len:
        t = t[:max_len].rstrip("_")
    return t


PREFERRED_KEY_ORDER = (
    "INSTRUMENT",
    "HOLDER",
    "ISSUANCE_YEAR",
    "INDICATOR",
    "VARIANT",
    "TIME_PERIOD",
)


def order_key(candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for k in list(PREFERRED_KEY_ORDER) + list(candidates):
        if k in candidates and k not in seen:
            out.append(k)
            seen.add(k)
    return out


def order_dims(dims: list[dict], key: list[str]) -> list[dict]:
    by_id = {(d.get("id") or d.get("concept")): d for d in dims}
    ordered: list[dict] = []
    seen: set[str] = set()
    for k in key:
        if k in by_id and k not in seen:
            ordered.append(by_id[k])
            seen.add(k)
    for d in dims:
        i = d.get("id") or d.get("concept")
        if i not in seen:
            ordered.append(d)
            seen.add(i)
    return ordered


def extract_member(raw: dict, source: str) -> dict:
    sheet2, a1 = split_sheet_range(raw["data_range"])
    cells = expand_a1(a1)
    ctx = raw.get("series_context") or {}
    struct = raw.get("structure") or {}
    dims = struct.get("dimensions") or []
    measure = struct.get("measure") or {}
    mb = measure.get("bind") or {}
    rows = sorted({r for _, r in cells})
    cols = sorted({c for c, _ in cells})
    return {
        "raw": raw,
        "source": source,
        "id": raw["id"],
        "direction": direction_of(raw),
        "layout": raw.get("layout"),
        "data_range": raw["data_range"],
        "a1": a1,
        "cells": cells,
        "rows": rows,
        "cols": cols,
        "n_cells": len(cells),
        "ctx": ctx,
        "TABLE": ctx.get("TABLE"),
        "INDICATOR": ctx.get("INDICATOR"),
        "VARIANT": ctx.get("VARIANT"),
        "INSTRUMENT": ctx.get("INSTRUMENT"),
        "HOLDER": ctx.get("HOLDER"),
        "ISSUANCE_YEAR": ctx.get("ISSUANCE_YEAR"),
        "PARAMETER": ctx.get("PARAMETER"),
        "key": list(raw.get("key") or []),
        "dims": copy.deepcopy(dims),
        "dtype": measure.get("dtype"),
        "measure_read": mb.get("read"),
        "measure": copy.deepcopy(measure),
        "notes": raw.get("notes"),
        "input": copy.deepcopy(raw.get("input")),
        "exclude_rows": list(raw.get("exclude_rows") or []),
        "exclude_columns": list(raw.get("exclude_columns") or []),
    }


def load_input5_series() -> tuple[list[dict], dict]:
    concept_scheme = None
    members: list[dict] = []
    for path in SOURCES:
        doc = yaml.safe_load(path.read_text())
        if path.name == "internals-input5.bindings.yaml":
            concept_scheme = doc["concept_scheme"]
        for s in doc.get("series") or []:
            sheet = s.get("sheet") or ""
            dr = s.get("data_range") or ""
            sheet2, _ = split_sheet_range(dr)
            if sheet != SHEET and sheet2 != SHEET:
                continue
            members.append(extract_member(s, path.name))
    if concept_scheme is None:
        raise RuntimeError("concept_scheme missing from internals-input5.bindings.yaml")
    return members, concept_scheme


def group_key(m: dict) -> tuple:
    return (m["INDICATOR"], m["VARIANT"], m["TABLE"], m["layout"], m["direction"])


def existing_dim_ids(dims: list[dict]) -> set[str]:
    return {(d.get("id") or d.get("concept")) for d in dims}


def value_map_dim(dim_id: str, values: dict, read: str) -> dict:
    return {
        "id": dim_id,
        "concept": dim_id,
        "role": "key",
        "scope": "cell",
        "bind": {
            "kind": "value_map",
            "values": values,
            "read": read,
        },
    }


def row_label_dim(dim_id: str, label_column: str, read: str) -> dict:
    return {
        "id": dim_id,
        "concept": dim_id,
        "role": "key",
        "scope": "cell",
        "bind": {
            "kind": "row_label",
            "label_column": label_column,
            "read": read,
        },
    }


def build_field_value_map(members: list[dict], field: str) -> dict:
    val_to_rows: dict[object, set[int]] = defaultdict(set)
    for m in members:
        val = m["ctx"].get(field)
        if val is None:
            continue
        val_to_rows[val].update(m["rows"])
    return {val: specs_from_rows(sorted(rows)) for val, rows in val_to_rows.items()}


def mixed_presence(members: list[dict], field: str) -> bool:
    flags = [m["ctx"].get(field) is not None for m in members]
    return any(flags) and not all(flags)


def header_rows_of(members: list[dict], concept: str) -> set:
    found = set()
    for m in members:
        for d in m["dims"]:
            if d.get("concept") == concept or d.get("id") == concept:
                found.add((d.get("bind") or {}).get("header_row"))
    return found


def should_lift_group(members: list[dict]) -> tuple[bool, str]:
    """Return (lift?, reason if not)."""
    table = members[0]["TABLE"]
    if table is None:
        return False, "graph-coverage / no TABLE"
    # Public GFN line items are already one series per indicator.
    if table == "input5.public_gfns" and members[0]["INDICATOR"] != "share":
        if len(members) == 1:
            return False, "public GFN line item (already one series per indicator)"
    has_lift = any(m["ctx"].get(d) is not None for m in members for d in LIFT_DIMS)
    if not has_lift:
        return False, "no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context"
    if len({m["dtype"] for m in members}) != 1:
        return False, "mixed measure dtypes"
    tp_hrs = header_rows_of(members, "TIME_PERIOD")
    if len(tp_hrs) > 1:
        return False, f"mixed TIME_PERIOD header_row {tp_hrs}"
    for field in LIFT_DIMS:
        if mixed_presence(members, field):
            # Allow ISSUANCE_YEAR mixed? Vintage output all have it.
            return False, f"mixed presence of {field}"
    return True, "ok"


def bbox_and_holes(members: list[dict]) -> tuple[set[tuple[int, int]], list[int], str]:
    cells: set[tuple[int, int]] = set()
    for m in members:
        cells |= m["cells"]
    a1 = cells_to_a1(cells)
    min_c, min_r = parse_a1_cell(a1.split(":")[0])
    max_c, max_r = parse_a1_cell(a1.split(":")[-1])
    member_rows = {r for m in members for r in m["rows"]}
    hole_rows = [r for r in range(min_r, max_r + 1) if r not in member_rows]
    bbox_cells = {
        (c, r)
        for r in range(min_r, max_r + 1)
        if r in member_rows
        for c in range(min_c, max_c + 1)
    }
    # bbox_cells here already drops hole rows; full rectangle extras include holes
    # but those are excluded via exclude_rows, so remodeled cells = bbox_cells.
    return cells, hole_rows, a1


def make_id(members: list[dict], lifted: bool) -> str:
    m0 = members[0]
    direction, table, indicator, variant, layout = (
        m0["direction"],
        m0["TABLE"],
        m0["INDICATOR"],
        m0["VARIANT"],
        m0["layout"],
    )
    if (
        lifted
        and table == "input5.vintage_output"
        and indicator in VINTAGE_OUTPUT_IDS
    ):
        return VINTAGE_OUTPUT_IDS[indicator]

    table_s = ""
    if table:
        table_s = slug(table.replace("input5.", "").replace("input_5.", ""))

    # Well-known short names.
    special = {
        ("input", "gfn_allocation", "share", None, "series"): "input5_gfn_share",
        ("input", "gfn_allocation", "domestic_financing_from_macro_framework_0_input_here_1", None, "scalar"): "input5_domestic_financing_source",
        ("input", "public_gfns", None, None, "series"): "input5_public_gfns_other_adjustment",
        ("internal", "vintage_terms", None, None, "matrix"): "input5_vintage_terms",
        ("internal", "vintage_terms", "issuance_year", None, "series"): "input5_vintage_issuance_year",
        ("internal", "vintage_terms", "instrument_label", None, "series"): "input5_vintage_instrument_label",
        ("internal", "vintage_terms", "instrument_label", None, "scalar"): "input5_vintage_instrument_title",
        ("internal", "new_issuance", "new_issuance", None, "series"): "input5_new_issuance",
        ("internal", "vintage_projection_years", "year", "principal_payments_header", "series"): "input5_vintage_projection_years_principal",
        ("internal", "vintage_projection_years", "year", "interest_payments_header", "series"): "input5_vintage_projection_years_interest",
        ("input", "instrument_terms", "interest_rate_on_domestic_debt", None, "series"): "input5_interest_rate_on_domestic_debt",
        ("internal", "instrument_terms", "interest_rate_on_domestic_debt", None, "series"): "input5_internal_interest_rate_on_domestic_debt",
        ("input", "instrument_terms", "grace_period", None, "scalar"): "input5_grace_period",
        ("internal", "instrument_terms", "grace_period", None, "scalar"): "input5_internal_grace_period",
        ("constant", "instrument_terms", "grace_period", None, "scalar"): "input5_constant_grace_period",
        ("input", "instrument_terms", "maturity", None, "scalar"): "input5_maturity",
        ("internal", "instrument_terms", "maturity", None, "scalar"): "input5_internal_maturity",
        ("constant", "instrument_terms", "maturity", None, "scalar"): "input5_constant_maturity",
        ("internal", "instrument_terms", "instrument_label", None, "series"): "input5_instrument_terms_instrument_label",
        ("internal", "projection_years", "year", "header", "series"): "input5_projection_years",
        ("internal", "controls", "definition_of_external_domestic_debt", None, "scalar"): "input5_definition_of_external_domestic_debt",
        ("internal", "controls", "blue_cells_are_populated_automatically", None, "scalar"): "input5_blue_cells_note",
    }
    ind_s = slug(indicator) if indicator else None
    look = (direction, table_s, ind_s, slug(variant) if variant else None, layout)
    # public GFN other-adjustment indicator slug is huge; match prefix.
    if direction == "input" and table_s == "public_gfns" and layout == "series":
        return "input5_public_gfns_other_adjustment"
    if look in special:
        return special[look]

    if not table:
        cell = slug(m0["a1"].replace(":", "_"))
        param = slug(m0["PARAMETER"] or m0["id"].replace("in5_lcfin_", "").replace("in5_", ""))
        return f"input5_graph_{param}_{cell}"

    prefix = "input5"
    # Only the data series (not VARIANT=header labels) share an INDICATOR with inputs.
    if direction == "internal" and indicator in OVERLAP_INDICATORS and not variant:
        prefix = "input5_internal"
    elif direction == "constant" and indicator in OVERLAP_INDICATORS and not variant:
        prefix = "input5_constant"
    elif direction == "input":
        prefix = "input5"

    parts = [prefix]
    if table_s and table_s not in ("", "controls"):
        # Avoid input5_input5_...
        if not prefix.endswith(table_s):
            parts.append(table_s)
    if ind_s:
        # Drop table echo in indicator.
        parts.append(ind_s)
    if variant:
        parts.append(slug(variant))
    if not ind_s and m0["PARAMETER"]:
        parts.append(slug(m0["PARAMETER"]))
    if not ind_s and not m0["PARAMETER"]:
        parts.append(slug(m0["id"].replace("in5_", "").replace("input5_", "").replace("input_5_", "")))

    sid = "_".join(p for p in parts if p)
    sid = re.sub(r"_+", "_", sid).strip("_")
    # De-echo "input5_instrument_terms_instrument_terms_..."
    sid = sid.replace("input5_instrument_terms_instrument_terms_", "input5_instrument_terms_")
    if not ID_RE.match(sid):
        sid = "s_" + re.sub(r"[^a-z0-9_]", "_", sid.lower()).strip("_")
    return sid


def synthesize_notes(members: list[dict], lifted: bool, extra: str | None = None) -> str:
    m0 = members[0]
    ind = m0["INDICATOR"] or m0["PARAMETER"] or m0["id"]
    table = m0["TABLE"] or "untabled"
    if not lifted:
        return m0["notes"] or f"{ind} on Input 5 ({table})."
    n = len(members)
    inst = sorted({m["INSTRUMENT"] for m in members if m["INSTRUMENT"]})
    holders = sorted({str(m["HOLDER"]) for m in members if m["HOLDER"] is not None})
    bits = [
        f"Lifted from {n} {m0['direction']} series on {table}: {ind}.",
    ]
    if inst:
        bits.append(f"Instruments ({len(inst)}): {', '.join(inst)}.")
    if holders:
        bits.append(f"Holders: {', '.join(holders)}.")
    if extra:
        bits.append(extra)
    return " ".join(bits)


def lift_group(members: list[dict]) -> tuple[dict, dict]:
    """Return (series_yaml, audit_record)."""
    members = sorted(members, key=lambda m: (m["rows"][0], m["cols"][0], m["id"]))
    m0 = members[0]
    lift, reason = should_lift_group(members)

    # Vintage output always lifts when grouped (has the dims).
    is_vintage_output = m0["TABLE"] == "input5.vintage_output"
    is_vintage_terms_matrix = m0["TABLE"] == "input5.vintage_terms" and m0["layout"] == "matrix"
    use_issuance_row_label = is_vintage_output or is_vintage_terms_matrix

    orig_cells: set[tuple[int, int]] = set()
    for m in members:
        orig_cells |= m["cells"]

    if not lift:
        # Passthrough: one series per original member (caller handles n>1 unlifted).
        raise AssertionError("lift_group called on unlifted multi/passthrough path")

    orig_union, hole_rows, a1 = bbox_and_holes(members)
    assert orig_union == orig_cells
    remodeled_cells = set()
    min_c, min_r = parse_a1_cell(a1.split(":")[0])
    max_c, max_r = parse_a1_cell(a1.split(":")[-1])
    member_rows = {r for m in members for r in m["rows"]}
    for r in range(min_r, max_r + 1):
        if r not in member_rows:
            continue
        for c in range(min_c, max_c + 1):
            remodeled_cells.add((c, r))
    extras = remodeled_cells - orig_cells
    missing = orig_cells - remodeled_cells
    if missing:
        raise RuntimeError(f"dropped original cells for {m0['INDICATOR']}: {sorted(missing)[:12]}")

    dims = copy.deepcopy(m0["dims"])
    have = existing_dim_ids(dims)
    new_keys: list[str] = []

    # INSTRUMENT / HOLDER from member rows (preserve original strings).
    for field, read in (("INSTRUMENT", "string"), ("HOLDER", "string")):
        if field in have:
            continue
        if not any(m["ctx"].get(field) is not None for m in members):
            continue
        values = build_field_value_map(members, field)
        if not values:
            continue
        dims.insert(len(new_keys), value_map_dim(field, values, read))
        new_keys.append(field)
        have.add(field)

    # ISSUANCE_YEAR: row_label from column B for vintage blocks; else value_map.
    if "ISSUANCE_YEAR" not in have and any(
        m["ctx"].get("ISSUANCE_YEAR") is not None for m in members
    ):
        if use_issuance_row_label:
            dims.insert(len(new_keys), row_label_dim("ISSUANCE_YEAR", "B", "int"))
        else:
            # Coerce year keys to int when possible.
            raw_map = build_field_value_map(members, "ISSUANCE_YEAR")
            values = {}
            for k, v in raw_map.items():
                try:
                    values[int(k)] = v
                except (TypeError, ValueError):
                    values[k] = v
            dims.insert(len(new_keys), value_map_dim("ISSUANCE_YEAR", values, "int"))
        new_keys.append("ISSUANCE_YEAR")
        have.add("ISSUANCE_YEAR")

    # Existing keys (TIME_PERIOD, VARIANT, INDICATOR, ISSUANCE_YEAR already on member).
    old_keys = [k for k in m0["key"] if k in have or k in existing_dim_ids(dims)]
    key = order_key(new_keys + [k for k in old_keys if k not in new_keys])
    dims = order_dims(dims, key)

    layout = m0["layout"]
    # One cell per key tuple without TIME_PERIOD stays scalar.
    if layout == "scalar" and "TIME_PERIOD" not in key:
        layout = "scalar"
    elif layout == "matrix":
        layout = "matrix"
    elif "TIME_PERIOD" in key or "VARIANT" in key:
        layout = "series"
    elif "ISSUANCE_YEAR" in key and "INDICATOR" in key and m0["layout"] == "matrix":
        layout = "matrix"
    else:
        layout = m0["layout"]

    sid = make_id(members, lifted=True)

    triangle_on_member_rows = 0
    for c, r in extras:
        if r in member_rows:
            triangle_on_member_rows += 1

    extra_note = None
    if extras:
        extra_note = (
            f"Bounding rectangle adds {len(extras)} cells not in the original "
            f"per-member ranges ({triangle_on_member_rows} on member rows: "
            f"triangular / trailing blanks)."
        )

    series: dict = {
        "id": sid,
        "sheet": SHEET,
        "data_range": format_data_range(a1),
        "layout": layout,
    }
    if m0["direction"] == "input":
        setter_name = f"set_{sid}"
        inp = copy.deepcopy(m0["input"]) or {}
        setter = inp.get("setter") or {}
        setter["name"] = setter_name
        setter.setdefault("record_contract", "records")
        setter.setdefault("strict", True)
        inp["setter"] = setter
        # Keep domain only when every member shares the same domain.
        domains = [((m["raw"].get("input") or {}).get("domain")) for m in members]
        if all(d == domains[0] for d in domains) and domains[0] is not None:
            inp["domain"] = copy.deepcopy(domains[0])
        elif "domain" in inp and not all(d == domains[0] for d in domains):
            inp.pop("domain", None)
        series["input"] = inp
    elif m0["direction"] == "constant":
        series["constant"] = {}
    else:
        series["internal"] = {}

    if hole_rows:
        series["exclude_rows"] = exclude_row_specs(hole_rows)

    series["structure"] = {
        "measure": copy.deepcopy(m0["measure"]),
        "dimensions": dims,
    }
    series["key"] = key

    ctx = {}
    if m0["TABLE"]:
        ctx["TABLE"] = m0["TABLE"]
    if m0["INDICATOR"]:
        ctx["INDICATOR"] = m0["INDICATOR"]
    if m0["VARIANT"]:
        ctx["VARIANT"] = m0["VARIANT"]
    series["series_context"] = ctx
    series["notes"] = synthesize_notes(members, True, extra_note)

    audit = {
        "id": sid,
        "lifted": True,
        "reason": reason,
        "n_members": len(members),
        "member_ids": [m["id"] for m in members],
        "direction": m0["direction"],
        "layout": layout,
        "TABLE": m0["TABLE"],
        "INDICATOR": m0["INDICATOR"],
        "VARIANT": m0["VARIANT"],
        "key": key,
        "orig_cells": len(orig_cells),
        "remodeled_cells": len(remodeled_cells),
        "extras": len(extras),
        "triangle_extras": triangle_on_member_rows,
        "exclude_rows": hole_rows,
        "a1": a1,
        "instruments": sorted({m["INSTRUMENT"] for m in members if m["INSTRUMENT"]}),
        "holders": sorted({str(m["HOLDER"]) for m in members if m["HOLDER"] is not None}),
    }
    return series, audit, remodeled_cells, orig_cells


def passthrough_series(m: dict) -> tuple[dict, dict, set, set]:
    sid = make_id([m], lifted=False)
    # Graph-coverage / unique GFN / headers: keep original structure, new id.
    raw = m["raw"]
    series: dict = {
        "id": sid,
        "sheet": SHEET,
        "data_range": m["data_range"] if m["data_range"].startswith("'") or "!" in m["data_range"] else format_data_range(m["a1"]),
        "layout": m["layout"],
    }
    # Normalize data_range quoting.
    _, a1 = split_sheet_range(series["data_range"])
    series["data_range"] = format_data_range(a1)

    if m["direction"] == "input":
        inp = copy.deepcopy(m["input"]) or {}
        setter = inp.get("setter") or {}
        setter["name"] = f"set_{sid}"
        setter.setdefault("record_contract", "records")
        setter.setdefault("strict", True)
        inp["setter"] = setter
        series["input"] = inp
    elif m["direction"] == "constant":
        series["constant"] = {}
    else:
        series["internal"] = {}

    if m["exclude_rows"]:
        series["exclude_rows"] = list(m["exclude_rows"])
    if m["exclude_columns"]:
        series["exclude_columns"] = list(m["exclude_columns"])

    series["structure"] = {
        "measure": copy.deepcopy(m["measure"]),
        "dimensions": copy.deepcopy(m["dims"]),
    }
    series["key"] = list(m["key"])
    ctx = dict(m["ctx"])
    series["series_context"] = ctx
    series["notes"] = m["notes"] or f"{m['INDICATOR'] or m['PARAMETER'] or sid} on Input 5."

    audit = {
        "id": sid,
        "lifted": False,
        "reason": "passthrough",
        "n_members": 1,
        "member_ids": [m["id"]],
        "direction": m["direction"],
        "layout": m["layout"],
        "TABLE": m["TABLE"],
        "INDICATOR": m["INDICATOR"],
        "VARIANT": m["VARIANT"],
        "key": list(m["key"]),
        "orig_cells": m["n_cells"],
        "remodeled_cells": m["n_cells"],
        "extras": 0,
        "triangle_extras": 0,
        "exclude_rows": [],
        "a1": a1,
        "instruments": [m["INSTRUMENT"]] if m["INSTRUMENT"] else [],
        "holders": [str(m["HOLDER"])] if m["HOLDER"] is not None else [],
    }
    return series, audit, set(m["cells"]), set(m["cells"])


# ---------------------------------------------------------------------------
# YAML emitter (stable, readable, schema-friendly)
# ---------------------------------------------------------------------------

def yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    s = str(value)
    if s == "" or re.search(r"[:#{}[\],&*!|>'\"%@`]", s) or s.strip() != s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if s.lower() in {"true", "false", "null", "yes", "no", "on", "off", "y", "n"}:
        return '"' + s + '"'
    if re.match(r"^[-0-9]", s):
        return '"' + s + '"'
    return s


def emit_simple_map(d: dict, indent: int) -> list[str]:
    sp = " " * indent
    lines = []
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{sp}{k}:")
            lines.extend(emit_simple_map(v, indent + 2))
        elif isinstance(v, list):
            if not v:
                lines.append(f"{sp}{k}: []")
            elif all(not isinstance(x, (dict, list)) for x in v):
                # flow-ish block list
                lines.append(f"{sp}{k}:")
                for x in v:
                    lines.append(f"{sp}  - {yaml_scalar(x)}")
            else:
                lines.append(f"{sp}{k}:")
                for x in v:
                    if isinstance(x, dict):
                        first = True
                        for ik, iv in x.items():
                            prefix = "- " if first else "  "
                            first = False
                            if isinstance(iv, dict):
                                lines.append(f"{sp}  {prefix}{ik}:")
                                lines.extend(emit_simple_map(iv, indent + 6))
                            elif isinstance(iv, list):
                                lines.append(f"{sp}  {prefix}{ik}:")
                                for item in iv:
                                    lines.append(f"{sp}      - {yaml_scalar(item)}")
                            else:
                                lines.append(f"{sp}  {prefix}{ik}: {yaml_scalar(iv)}")
                    else:
                        lines.append(f"{sp}  - {yaml_scalar(x)}")
        else:
            lines.append(f"{sp}{k}: {yaml_scalar(v)}")
    return lines


def emit_value_map_values(values: dict, indent: int) -> list[str]:
    sp = " " * indent
    lines = [f"{sp}values:"]
    vsp = " " * (indent + 2)
    for k, v in values.items():
        key = yaml_scalar(k)
        if isinstance(v, list):
            lines.append(f"{vsp}{key}:")
            for item in v:
                lines.append(f"{vsp}  - {yaml_scalar(item)}")
        else:
            lines.append(f"{vsp}{key}: {yaml_scalar(v)}")
    return lines


def emit_bind(bind: dict, indent: int) -> list[str]:
    sp = " " * indent
    lines = [f"{sp}bind:"]
    b2 = indent + 2
    sp2 = " " * b2
    lines.append(f"{sp2}kind: {yaml_scalar(bind['kind'])}")
    for k, v in bind.items():
        if k == "kind":
            continue
        if k == "values" and isinstance(v, dict):
            lines.extend(emit_value_map_values(v, b2))
        elif isinstance(v, dict):
            lines.append(f"{sp2}{k}:")
            lines.extend(emit_simple_map(v, b2 + 2))
        elif isinstance(v, list):
            lines.append(f"{sp2}{k}:")
            for item in v:
                lines.append(f"{sp2}  - {yaml_scalar(item)}")
        else:
            lines.append(f"{sp2}{k}: {yaml_scalar(v)}")
    return lines


def emit_dimension(dim: dict, indent: int, first: bool) -> list[str]:
    sp = " " * indent
    prefix = "- " if first else "  "
    # first line is id
    lines = [f"{sp}{prefix}id: {yaml_scalar(dim['id'])}"]
    body = " " * (indent + 2)
    for k, v in dim.items():
        if k == "id":
            continue
        if k == "bind" and isinstance(v, dict):
            lines.extend(emit_bind(v, indent + 2))
        elif isinstance(v, dict):
            lines.append(f"{body}{k}:")
            lines.extend(emit_simple_map(v, indent + 4))
        else:
            lines.append(f"{body}{k}: {yaml_scalar(v)}")
    return lines


def emit_series(series: dict) -> list[str]:
    lines = [f"- id: {series['id']}"]
    indent = 2
    sp = " " * indent
    order = [
        "sheet",
        "data_range",
        "layout",
        "input",
        "internal",
        "constant",
        "exclude_rows",
        "exclude_columns",
        "structure",
        "key",
        "series_context",
        "notes",
    ]
    for k in order:
        if k not in series:
            continue
        v = series[k]
        if k == "structure":
            lines.append(f"{sp}structure:")
            meas = v["measure"]
            lines.append(f"{sp}  measure:")
            lines.extend(emit_simple_map(meas, indent + 4))
            dims = v.get("dimensions") or []
            if not dims:
                lines.append(f"{sp}  dimensions: []")
            else:
                lines.append(f"{sp}  dimensions:")
                for i, dim in enumerate(dims):
                    lines.extend(emit_dimension(dim, indent + 4, first=True))
        elif k in ("input", "internal", "constant", "series_context"):
            if v == {}:
                lines.append(f"{sp}{k}: {{}}")
            else:
                lines.append(f"{sp}{k}:")
                lines.extend(emit_simple_map(v, indent + 2))
        elif k == "key":
            if not v:
                lines.append(f"{sp}key: []")
            else:
                lines.append(f"{sp}key:")
                for item in v:
                    lines.append(f"{sp}  - {yaml_scalar(item)}")
        elif k == "exclude_rows":
            lines.append(f"{sp}exclude_rows:")
            for item in v:
                lines.append(f"{sp}  - {yaml_scalar(item)}")
        elif isinstance(v, dict):
            lines.append(f"{sp}{k}:")
            lines.extend(emit_simple_map(v, indent + 2))
        else:
            lines.append(f"{sp}{k}: {yaml_scalar(v)}")
    return lines


def emit_concept_scheme(cs: dict) -> list[str]:
    lines = ["concept_scheme:", f"  id: {cs.get('id')}"]
    lines.append("  concepts:")
    for c in cs["concepts"]:
        lines.append(f"  - id: {c['id']}")
        if "name" in c:
            lines.append(f"    name: {yaml_scalar(c['name'])}")
        if "dtype" in c:
            lines.append(f"    dtype: {c['dtype']}")
        if "sdmx_concept" in c:
            lines.append(f"    sdmx_concept: {c['sdmx_concept']}")
        if "description" in c:
            lines.append(f"    description: {yaml_scalar(c['description'])}")
    return lines


def unique_id(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base
    i = 2
    while f"{base}_{i}" in used:
        i += 1
    sid = f"{base}_{i}"
    used.add(sid)
    return sid


def min_row_of_series(series: dict) -> int:
    _, a1 = split_sheet_range(series["data_range"])
    cells = expand_a1(a1)
    return min(r for _, r in cells)


def write_audit(
    original_members: list[dict],
    audits: list[dict],
    orig_cells: set[tuple[int, int]],
    rem_cells: set[tuple[int, int]],
    unlifted: list[dict],
    overlap_pairs: list[dict],
    n_original: int,
    n_remodeled: int,
) -> str:
    extras = rem_cells - orig_cells
    missing = orig_cells - rem_cells
    lifted = [a for a in audits if a["lifted"]]
    passthrough = [a for a in audits if not a["lifted"]]

    lines: list[str] = []
    lines.append("# Input 5 remodel audit")
    lines.append("")
    lines.append("Prototype reshape-to-keys pass for `Input 5 - Local-debt Financing`.")
    lines.append("Original catalogs: `internals-input5.bindings.yaml` (1062),")
    lines.append("`inputs.bindings.yaml` (41), `constants.bindings.yaml` (8),")
    lines.append("`internals-graph-coverage.bindings.yaml` (14).")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Original series: **{n_original}**")
    lines.append(f"- Remodeled series: **{n_remodeled}**")
    lines.append(f"- Lifted groups (one series each): **{len(lifted)}**")
    lines.append(f"- Passthrough series: **{len(passthrough)}**")
    lines.append(
        f"- Headline vintage_output: **871 → 3** "
        f"(`input5_vintage_stock`, `input5_vintage_principal`, `input5_vintage_interest`)"
    )
    lines.append("")
    lines.append("## Cell coverage")
    lines.append("")
    lines.append(f"- Original unique cells: **{len(orig_cells)}**")
    lines.append(f"- Remodeled unique cells: **{len(rem_cells)}**")
    lines.append(f"- Original ⊆ remodeled: **{not missing}**")
    lines.append(f"- Missing original cells: **{len(missing)}**")
    lines.append(f"- Extra remodeled cells: **{len(extras)}**")
    lines.append("")
    vintage_audits = [a for a in lifted if a["TABLE"] == "input5.vintage_output"]
    if vintage_audits:
        lines.append("### Vintage output extras (expected triangular / trailing blanks)")
        lines.append("")
        lines.append("| id | original members | original cells | remodeled cells | extras | of which on member rows | excluded hole rows |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for a in vintage_audits:
            lines.append(
                f"| `{a['id']}` | {a['n_members']} | {a['orig_cells']} | "
                f"{a['remodeled_cells']} | {a['extras']} | {a['triangle_extras']} | "
                f"{len(a['exclude_rows'])} |"
            )
        lines.append("")
        lines.append(
            "Issuance year *t* occupies a lower triangle: 2024 is `I230:AC230` (stock), "
            "2025 is `J231:AC231` (range starts one column later), and similarly for "
            "principal (`AE:AY` / `AF:AY`) and interest (`BA:BU` / `BB:BU`). "
            "The remodeled `data_range` is the bounding rectangle of all members, "
            "so cells west of the per-year start column (and, for some non-resident "
            "bands, column `AC`/`AY` past the original end) are extra blanks. "
            "No original cell is dropped. `exclude_rows` carves instrument-block "
            "separators out of the bbox; it cannot remove intra-row triangle blanks."
        )
        lines.append("")

    other_extras = [a for a in lifted if a["extras"] and a["TABLE"] != "input5.vintage_output"]
    if other_extras:
        lines.append("### Other bounding-rectangle extras")
        lines.append("")
        lines.append("| id | extras | note |")
        lines.append("|---|---:|---|")
        for a in other_extras:
            extra_note = (
                "holes excluded via `exclude_rows`; remaining extras are blank cells "
                "on member rows inside the bbox"
            )
            if a["id"] == "input5_internal_interest_rate_on_domestic_debt":
                extra_note = (
                    "resident rows are originally `O:AC` (projection) while non-resident "
                    "rows are `I:AC`; the one-rectangle bbox fills resident `I:N` "
                    "(54 cells) that are already the **input** interest series. "
                    "`exclude_columns: I:N` would drop original non-resident `I:N` cells"
                )
            lines.append(f"| `{a['id']}` | {a['extras']} | {extra_note} |")
        lines.append("")

    lines.append("## Lifted series (id → keys)")
    lines.append("")
    lines.append("| id | n | direction | layout | TABLE | INDICATOR | keys |")
    lines.append("|---|---:|---|---|---|---|---|")
    for a in sorted(lifted, key=lambda x: (x["TABLE"] or "", x["INDICATOR"] or "", x["id"])):
        keys = ", ".join(a["key"]) if a["key"] else "∅"
        ind = (a["INDICATOR"] or "").replace("|", "/")
        lines.append(
            f"| `{a['id']}` | {a['n_members']} | {a['direction']} | {a['layout']} | "
            f"`{a['TABLE']}` | {ind} | `{keys}` |"
        )
    lines.append("")

    lines.append("## Inputs vs internals (same INDICATOR, not smashed)")
    lines.append("")
    if overlap_pairs:
        lines.append("| INDICATOR | TABLE | input id | internal id |")
        lines.append("|---|---|---|---|")
        for p in overlap_pairs:
            lines.append(
                f"| {p['INDICATOR']} | `{p['TABLE']}` | `{p['input_id']}` | `{p['internal_id']}` |"
            )
        lines.append("")
        lines.append(
            "Constants for T-bill grace/maturity (`input5_constant_grace_period`, "
            "`input5_constant_maturity`) stay on `constant: {}` and are not merged "
            "with the input or internal series of the same INDICATOR."
        )
        lines.append("")
        lines.append(
            "Merged inputs expose a single setter `set_<id>` "
            "(e.g. `set_input5_gfn_share`, `set_input5_grace_period`)."
        )
    else:
        lines.append("None found.")
    lines.append("")

    lines.append("## Issuance-year series")
    lines.append("")
    lines.append(
        "Kept `input5_vintage_issuance_year` as a published series (column B of each "
        "vintage block). Those cells are the ISSUANCE_YEAR `row_label` source for "
        "`input5_vintage_stock` / `_principal` / `_interest` and `input5_vintage_terms`. "
        "Dropping the series would lose column-B cells from the inventory because "
        "row_label sources are not in those series' `data_range`. "
        "The observation *is* the year, so the key is `[INSTRUMENT, HOLDER, ISSUANCE_YEAR]` "
        "(ISSUANCE_YEAR via `data_cell`, same as the original per-block series) — "
        "`[INSTRUMENT, HOLDER]` alone would collide across the 21 vintage rows."
    )
    lines.append("")

    lines.append("## Groups not lifted")
    lines.append("")
    if unlifted:
        lines.append("| original id | direction | layout | TABLE | INDICATOR | reason |")
        lines.append("|---|---|---|---|---|---|")
        for u in unlifted:
            ind = (u["INDICATOR"] or u.get("PARAMETER") or "").replace("|", "/")
            lines.append(
                f"| `{u['id']}` | {u['direction']} | {u['layout']} | "
                f"`{u['TABLE']}` | {ind} | {u['reason']} |"
            )
    else:
        lines.append("All groups with INSTRUMENT/HOLDER/ISSUANCE_YEAR in context were lifted.")
    lines.append("")
    lines.append(
        "Public GFN line items (`input5.public_gfns`) stay one year-keyed series per "
        "indicator; they are not instrument copies. Graph-coverage scalars with no "
        "TABLE (column-A GFN labels, vintage header anchors `I222`/`AE222`/`BA222`, "
        "and `C130`/`C137` average-rate seeds) are not attached to another series' "
        "cells — mixing label/header dtypes into numeric `data_range`s would be wrong, "
        "and those cells are not members of the nearby numeric series."
    )
    lines.append("")

    lines.append("## Holder strings")
    lines.append("")
    lines.append(
        "Original strings are preserved. Internals use `residents` / `non-residents`; "
        "GFN-share **inputs** use `residents` / `non_residents` (underscore). "
        "Those input and internal series are not smashed, so both spellings remain."
    )
    lines.append("")

    lines.append("## Schema notes")
    lines.append("")
    lines.append("- `schema_version: 1.13.0`; `concept_scheme` copied from internals-input5 (includes ISSUANCE_YEAR, HOLDER, INSTRUMENT).")
    lines.append("- `value_map` values are a row number, a `\"230:250\"` range, or a list of those for disjoint bands (excel-grapher BindValueMap).")
    lines.append("- `exclude_rows` uses the same RowSpec (`251` or `\"251:253\"`) for bbox holes between instrument blocks.")
    lines.append("- Ids match `^[a-z][a-z0-9_]*$` (schema 1.13.0; stricter than the authoring prompt's mixed-case class).")
    lines.append("- `layout: matrix` only for vintage_terms (ISSUANCE_YEAR × INDICATOR rectangle). Vintage output stays `series` with keys `[INSTRUMENT, HOLDER, ISSUANCE_YEAR, TIME_PERIOD]`.")
    lines.append("- One YAML entry per lifted series (no shared-id shards).")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    members, concept_scheme = load_input5_series()
    print(f"Loaded {len(members)} Input 5 series")

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for m in members:
        groups[group_key(m)].append(m)

    used_ids: set[str] = set()
    series_out: list[dict] = []
    audits: list[dict] = []
    unlifted_rows: list[dict] = []
    orig_cells: set[tuple[int, int]] = set()
    rem_cells: set[tuple[int, int]] = set()
    all_orig: set[tuple[int, int]] = set()
    for m in members:
        all_orig |= m["cells"]

    for gkey, gmembers in sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
        lift, reason = should_lift_group(gmembers)
        # Always lift vintage_output groups (they have the dims).
        if gmembers[0]["TABLE"] == "input5.vintage_output":
            lift = True
        if lift and len(gmembers) >= 1:
            series, audit, rcells, ocells = lift_group(gmembers)
            series["id"] = unique_id(series["id"], used_ids)
            audit["id"] = series["id"]
            series_out.append(series)
            audits.append(audit)
            rem_cells |= rcells
            orig_cells |= ocells
            continue

        # Unlifted: emit one passthrough per member.
        for m in gmembers:
            series, audit, rcells, ocells = passthrough_series(m)
            audit["reason"] = reason
            series["id"] = unique_id(series["id"], used_ids)
            audit["id"] = series["id"]
            series_out.append(series)
            audits.append(audit)
            rem_cells |= rcells
            orig_cells |= ocells
            unlifted_rows.append(
                {
                    "id": m["id"],
                    "new_id": series["id"],
                    "direction": m["direction"],
                    "layout": m["layout"],
                    "TABLE": m["TABLE"],
                    "INDICATOR": m["INDICATOR"],
                    "PARAMETER": m["PARAMETER"],
                    "reason": reason,
                }
            )

    # Sort remodeled series by sheet order.
    series_out.sort(key=lambda s: (min_row_of_series(s), s["id"]))

    missing = all_orig - rem_cells
    if missing:
        sample = ", ".join(f"{num_to_col(c)}{r}" for c, r in sorted(missing)[:20])
        raise SystemExit(f"Original cells missing from remodeled: {len(missing)} e.g. {sample}")
    if orig_cells != all_orig:
        raise SystemExit("orig_cells tracking drifted from union of members")

    # Overlap input vs internal INDICATOR (same TABLE).
    by_ind_table_dir: dict[tuple, list[dict]] = defaultdict(list)
    for a in audits:
        if a["INDICATOR"] and a["TABLE"]:
            by_ind_table_dir[(a["INDICATOR"], a["TABLE"], a["direction"])].append(a)
    overlap_pairs = []
    seen_ov = set()
    for a in audits:
        ind, table = a["INDICATOR"], a["TABLE"]
        if not ind or not table:
            continue
        ins = by_ind_table_dir.get((ind, table, "input")) or []
        ints = by_ind_table_dir.get((ind, table, "internal")) or []
        if ins and ints:
            key = (ind, table)
            if key in seen_ov:
                continue
            seen_ov.add(key)
            overlap_pairs.append(
                {
                    "INDICATOR": ind,
                    "TABLE": table,
                    "input_id": ins[0]["id"],
                    "internal_id": ints[0]["id"],
                }
            )

    # Duplicate id check.
    ids = [s["id"] for s in series_out]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"duplicate ids: {[i for i in ids if ids.count(i)>1]}")
    for sid in ids:
        if not ID_RE.match(sid):
            raise SystemExit(f"bad id: {sid}")

    header = [
        f"schema_version: {SCHEMA_VERSION}",
        "workbook: workbook.xlsm",
    ]
    header.extend(emit_concept_scheme(concept_scheme))
    header.append("series:")
    body: list[str] = []
    for s in series_out:
        body.extend(emit_series(s))
    text = "\n".join(header + body) + "\n"
    OUT_YAML.write_text(text)

    # Parse back to confirm YAML.
    parsed = yaml.safe_load(text)
    assert parsed["schema_version"] == SCHEMA_VERSION
    assert len(parsed["series"]) == len(series_out)
    parsed_ids = [s["id"] for s in parsed["series"]]
    assert parsed_ids == ids

    audit_text = write_audit(
        members,
        audits,
        all_orig,
        rem_cells,
        unlifted_rows,
        overlap_pairs,
        n_original=len(members),
        n_remodeled=len(series_out),
    )
    OUT_AUDIT.write_text(audit_text)

    extras = rem_cells - all_orig
    print(f"Wrote {OUT_YAML} ({len(series_out)} series)")
    print(f"Wrote {OUT_AUDIT}")
    print(f"original cells={len(all_orig)} remodeled={len(rem_cells)} extras={len(extras)} missing={len(missing)}")
    print("lifted:", sum(1 for a in audits if a["lifted"]), "passthrough:", sum(1 for a in audits if not a["lifted"]))
    print("vintage:", [a["id"] for a in audits if a["id"].startswith("input5_vintage_")])


if __name__ == "__main__":
    main()
