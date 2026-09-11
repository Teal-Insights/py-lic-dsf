#!/usr/bin/env python3
"""Reshape-to-keys prototype for PV_Base (and PV_Base-add.cost.mkt).

Reads original shards under bindings/ (not modified) and writes:

  bindings/remodeled/pv-base.bindings.yaml
  bindings/remodeled/pv-base-audit.md

Copied instrument blocks become one series per indicator, keyed by INSTRUMENT
(and HOLDER when FX local bonds repeat the same instrument for non-residents
vs residents). Graph-coverage leftovers are grouped by geometry (block labels,
block index row, column-A titles). Directions are not merged.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from input4_cells import (  # noqa: E402
    bbox_a1,
    compact_row_specs,
    expand_a1,
    num_to_col,
    split_sheet_range,
)

ROOT = Path("/workspace/bindings")
SOURCES = [
    ROOT / "internals-pv-base.bindings.yaml",
    ROOT / "constants.bindings.yaml",
    ROOT / "internals-graph-coverage.bindings.yaml",
    ROOT / "inputs.bindings.yaml",
]
OUT_YAML = ROOT / "remodeled" / "pv-base.bindings.yaml"
OUT_AUDIT = ROOT / "remodeled" / "pv-base-audit.md"
SHEETS = {"PV_Base", "PV_Base-add.cost.mkt"}
SCHEMA_VERSION = "1.13.0"
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
GRACE_RE = re.compile(r"^Grace (.+)$")
MATURITY_RE = re.compile(r"^Maturity (.+)$")

PREFERRED_KEY_ORDER = (
    "INSTRUMENT",
    "HOLDER",
    "INDICATOR",
    "VARIANT",
    "TIME_PERIOD",
)
OUTPUT_HEADER_ROW = {
    "PV_Base": 21,
    "PV_Base-add.cost.mkt": 2,
}
INDICATOR_SLUGS = {
    "t-g>0": "t_g_0",
}


def direction_of(series: dict) -> str:
    for d in ("input", "internal", "constant", "output"):
        if d in series:
            return d
    return "none"


def slug(text: str | None, max_len: int = 80) -> str:
    if not text:
        return ""
    t = text.lower()
    t = t.replace("%", "pct").replace("&", "and")
    t = t.replace(">", "gt").replace("<", "lt")
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    if len(t) > max_len:
        t = t[:max_len].rstrip("_")
    return t


def quote_sheet(sheet: str) -> str:
    return f"'{sheet}'"


def format_data_range(sheet: str, a1: str) -> str:
    return f"{quote_sheet(sheet)}!{a1}"


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


def existing_dim_ids(dims: list[dict]) -> set[str]:
    return {(d.get("id") or d.get("concept")) for d in dims}


def value_map_dim(dim_id: str, values: dict, read: str) -> dict:
    return {
        "id": dim_id,
        "concept": dim_id,
        "role": "key",
        "scope": "cell",
        "bind": {"kind": "value_map", "values": values, "read": read},
    }


def header_rows_of(members: list[dict], concept: str) -> set:
    found = set()
    for m in members:
        for d in m["dims"]:
            if d.get("concept") == concept or d.get("id") == concept:
                found.add((d.get("bind") or {}).get("header_row"))
    return found


def mixed_presence(members: list[dict], field: str) -> bool:
    flags = [m.get(field) is not None for m in members]
    return any(flags) and not all(flags)


def build_field_value_map(members: list[dict], field: str) -> dict:
    val_to_rows: dict[object, set[int]] = defaultdict(set)
    for m in members:
        val = m.get(field)
        if val is None:
            continue
        val_to_rows[val].update(m["rows"])
    return {val: specs_from_rows(sorted(rows)) for val, rows in val_to_rows.items()}


def extract_member(raw: dict, source: str) -> dict:
    sheet2, a1 = split_sheet_range(raw["data_range"])
    cells = set(expand_a1(a1))
    ctx = raw.get("series_context") or {}
    struct = raw.get("structure") or {}
    dims = struct.get("dimensions") or []
    measure = struct.get("measure") or {}
    mb = measure.get("bind") or {}
    rows = sorted({r for _, r in cells})
    cols = sorted({c for c, _ in cells})
    sheet = raw.get("sheet") or sheet2
    return {
        "raw": raw,
        "source": source,
        "id": raw["id"],
        "sheet": sheet,
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
        "family": "authored",
    }


def load_series() -> tuple[list[dict], dict]:
    concept_scheme = None
    members: list[dict] = []
    for path in SOURCES:
        doc = yaml.safe_load(path.read_text())
        if concept_scheme is None and path.name == "internals-pv-base.bindings.yaml":
            concept_scheme = doc["concept_scheme"]
        for s in doc.get("series") or []:
            sheet = s.get("sheet") or ""
            dr = s.get("data_range") or ""
            sheet2, _ = split_sheet_range(dr)
            if sheet not in SHEETS and sheet2 not in SHEETS:
                continue
            members.append(extract_member(s, path.name))
    if concept_scheme is None:
        raise RuntimeError("concept_scheme missing from internals-pv-base.bindings.yaml")
    return members, concept_scheme


def known_instruments(members: list[dict]) -> set[str]:
    known = {m["INSTRUMENT"] for m in members if m["INSTRUMENT"]}
    return known


def debt_stock_index(members: list[dict]) -> dict[str, list[tuple[str | None, int]]]:
    """instrument → [(holder, debt-stock row), ...]."""
    out: dict[str, list[tuple[str | None, int]]] = defaultdict(list)
    for m in members:
        if m["INDICATOR"] != "Debt stock" or m["VARIANT"] != "discount":
            continue
        if not m["INSTRUMENT"] or not m["rows"]:
            continue
        out[m["INSTRUMENT"]].append((m["HOLDER"], m["rows"][0]))
    return dict(out)


def infer_instrument(m: dict, known: set[str]) -> str | None:
    if m["INSTRUMENT"]:
        return m["INSTRUMENT"]
    for cand in (m["INDICATOR"], m["PARAMETER"]):
        if not cand:
            continue
        text = str(cand)
        if text in known:
            return text
        gm = GRACE_RE.match(text)
        if gm and gm.group(1) in known:
            return gm.group(1)
        mm = MATURITY_RE.match(text)
        if mm and mm.group(1) in known:
            return mm.group(1)
    return None


def infer_holder(
    m: dict, inst: str | None, ds_index: dict[str, list[tuple[str | None, int]]]
) -> str | None:
    if m["HOLDER"] is not None:
        return m["HOLDER"]
    if not inst or inst not in ds_index:
        return None
    options = ds_index[inst]
    if len(options) == 1:
        return options[0][0]
    row0 = m["rows"][0]
    holder, _ = min(options, key=lambda oh: abs(oh[1] - row0))
    return holder


def relative_to_debt_stock(
    m: dict, ds_index: dict[str, list[tuple[str | None, int]]]
) -> int | None:
    inst = m.get("INSTRUMENT")
    if not inst or inst not in ds_index or not m["rows"]:
        return None
    options = ds_index[inst]
    holder = m.get("HOLDER")
    matches = [r for h, r in options if h == holder]
    if not matches:
        matches = [r for _, r in options]
    ds_row = min(matches, key=lambda r: abs(r - m["rows"][0]))
    return m["rows"][0] - ds_row


def classify_family(
    m: dict, known: set[str], ds_index: dict[str, list[tuple[str | None, int]]]
) -> str:
    if m["TABLE"]:
        return "authored"
    inst = infer_instrument(m, known)
    cols = m["cols"]
    rows = m["rows"]
    if m["sheet"] == "PV_Base" and cols == [2] and m["layout"] == "series" and len(rows) >= 2:
        return "grace_labels"
    if (
        m["sheet"] == "PV_Base"
        and m["layout"] == "series"
        and "TIME_PERIOD" in m["key"]
        and inst
        and cols
        and min(cols) >= 4
        and relative_to_debt_stock(m, ds_index) == -3
    ):
        return "block_index"
    if m["sheet"] == "PV_Base" and m["layout"] == "scalar" and cols == [1] and inst:
        return "instrument_title"
    param = m["PARAMETER"] or ""
    if m["sheet"] == "PV_Base-add.cost.mkt" and m["layout"] == "scalar":
        if str(param).startswith("Grace "):
            return "add_cost_grace"
        if str(param).startswith("Maturity "):
            return "add_cost_maturity"
    return "passthrough"


def annotate(members: list[dict]) -> None:
    known = known_instruments(members)
    ds_index = debt_stock_index(members)
    for m in members:
        inst = infer_instrument(m, known)
        if inst:
            m["INSTRUMENT"] = inst
            inferred = infer_holder(m, inst, ds_index)
            if m["HOLDER"] is None:
                m["HOLDER"] = inferred
        m["family"] = classify_family(m, known, ds_index)


def group_key(m: dict) -> tuple:
    if m["family"] != "authored":
        return (m["sheet"], m["direction"], m["family"], m["layout"])
    return (
        m["sheet"],
        m["direction"],
        m["TABLE"],
        m["INDICATOR"],
        m["VARIANT"],
        m["layout"],
    )


def split_holder_groups(members: list[dict]) -> list[list[dict]]:
    if not mixed_presence(members, "HOLDER"):
        return [members]
    with_h = [m for m in members if m["HOLDER"] is not None]
    without = [m for m in members if m["HOLDER"] is None]
    return [g for g in (without, with_h) if g]


def sheet_prefix(sheet: str) -> str:
    if sheet == "PV_Base-add.cost.mkt":
        return "pv_base_add_cost_mkt"
    return "pv_base"


def make_id(members: list[dict], *, lifted: bool, fx: bool) -> str:
    m0 = members[0]
    prefix = sheet_prefix(m0["sheet"])
    family = m0["family"]
    if not lifted:
        if family == "passthrough" or not m0["TABLE"]:
            tail = slug(m0["id"].replace("pv_base_add_cost_mkt_", "").replace("pv_base_", ""))
            return f"{prefix}_{tail}" if not tail.startswith(prefix) else tail
    table = (m0["TABLE"] or "").replace("pv_base_add_cost_mkt.", "").replace("pv_base.", "")
    indicator = m0["INDICATOR"]
    variant = m0["VARIANT"]
    direction = m0["direction"]

    special = {
        ("authored", "opening_stock", "percent_of_face", None, "constant"): f"{prefix}_opening_percent_of_face",
        ("authored", "ida_scale", "scale_name", None, "constant"): f"{prefix}_ida_scale_name",
        ("authored", "ida_scale", "short_name", None, "constant"): f"{prefix}_ida_scale_short_name",
        ("authored", "ida_scale", "new_ida_product_count", None, "constant"): f"{prefix}_ida_scale_new_product_count",
        ("grace_labels", None, None, None, "internal"): f"{prefix}_block_labels",
        ("block_index", None, None, None, "internal"): f"{prefix}_block_index",
        ("instrument_title", None, None, None, "internal"): f"{prefix}_instrument_title",
        ("add_cost_grace", None, None, None, "internal"): f"{prefix}_grace",
        ("add_cost_maturity", None, None, None, "internal"): f"{prefix}_maturity",
    }
    look = (family, table, indicator, variant, direction)
    fam_look = (family, None, None, None, direction)
    if fam_look in special:
        sid = special[fam_look]
    elif look in special:
        sid = special[look]
    elif table == "discount_schedule" and indicator == "Schedule period":
        sid = (
            f"{prefix}_constant_discount_schedule_period"
            if direction == "constant"
            else f"{prefix}_discount_schedule_period"
        )
    else:
        parts = [prefix]
        if direction == "constant" and table == "new_loan_output":
            parts.append("constant_output")
        elif direction == "input" and table == "new_loan_output":
            parts.append("input_output")
        elif table == "discount_schedule" or variant == "discount":
            parts.append("discount")
        elif table == "new_loan_output" or variant == "output":
            parts.append("output")
        elif table == "ida_terms":
            parts.append("ida_terms")
        elif table == "ida_scale":
            parts.append("ida_scale")
        elif table == "market_financing_shock":
            parts.append("shock")
        elif table:
            parts.append(slug(table))
        if indicator:
            parts.append(INDICATOR_SLUGS.get(indicator) or slug(indicator))
        elif m0["PARAMETER"]:
            parts.append(slug(m0["PARAMETER"]))
        sid = re.sub(r"_+", "_", "_".join(p for p in parts if p)).strip("_")

    if fx:
        sid = f"{sid}_fx"
    if not ID_RE.match(sid):
        sid = "s_" + re.sub(r"[^a-z0-9_]", "_", sid.lower()).strip("_")
    return sid


def family_context(members: list[dict]) -> dict[str, str]:
    m0 = members[0]
    family = m0["family"]
    if family == "grace_labels":
        return {"TABLE": "pv_base.block_labels", "INDICATOR": "block_labels"}
    if family == "block_index":
        return {"TABLE": "pv_base.block_index", "INDICATOR": "schedule_index"}
    if family == "instrument_title":
        return {"TABLE": "pv_base.instrument_title", "INDICATOR": "instrument_name"}
    if family == "add_cost_grace":
        return {"TABLE": "pv_base_add_cost_mkt.block_labels", "INDICATOR": "Grace"}
    if family == "add_cost_maturity":
        return {"TABLE": "pv_base_add_cost_mkt.block_labels", "INDICATOR": "Maturity"}
    ctx: dict[str, str] = {}
    if m0["TABLE"]:
        ctx["TABLE"] = m0["TABLE"]
    if m0["INDICATOR"]:
        ctx["INDICATOR"] = m0["INDICATOR"]
    if m0["VARIANT"]:
        ctx["VARIANT"] = m0["VARIANT"]
    return ctx


def synthesize_notes(members: list[dict], lifted: bool, extra: str | None = None) -> str:
    m0 = members[0]
    if not lifted:
        return m0["notes"] or f"{m0['INDICATOR'] or m0['PARAMETER'] or m0['id']} on {m0['sheet']}."
    n = len(members)
    inst = sorted({m["INSTRUMENT"] for m in members if m["INSTRUMENT"]})
    holders = sorted({str(m["HOLDER"]) for m in members if m["HOLDER"] is not None})
    ind = m0["INDICATOR"] or m0["PARAMETER"] or m0["family"]
    table = m0["TABLE"] or m0["family"]
    bits = [f"Lifted from {n} {m0['direction']} series on {table}: {ind}."]
    if inst:
        bits.append(f"Instruments ({len(inst)}): {', '.join(inst)}.")
    if holders:
        bits.append(f"Holders: {', '.join(holders)}.")
    if extra:
        bits.append(extra)
    return " ".join(bits)


def unify_time_header(members: list[dict], dims: list[dict], corrections: list[dict], sid: str) -> None:
    hrs = {h for h in header_rows_of(members, "TIME_PERIOD") if h is not None}
    if len(hrs) <= 1:
        return
    sheet = members[0]["sheet"]
    table = members[0]["TABLE"] or ""
    variant = members[0]["VARIANT"]
    if variant == "output" or table.endswith("new_loan_output"):
        canonical = OUTPUT_HEADER_ROW[sheet]
    else:
        canonical = min(hrs)
    for d in dims:
        if d.get("concept") == "TIME_PERIOD" or d.get("id") == "TIME_PERIOD":
            bind = d.setdefault("bind", {})
            bind["header_row"] = canonical
    corrections.append(
        {
            "id": sid,
            "original": sorted(hrs),
            "remodeled": canonical,
            "reason": (
                "Each instrument block copies projection-year labels onto its own "
                "header row; the remodeled series reads TIME_PERIOD from the first "
                "block's header row."
            ),
        }
    )


def unify_measure(members: list[dict]) -> dict:
    measure = copy.deepcopy(members[0]["measure"])
    dtypes = {m["dtype"] for m in members}
    reads = {m["measure_read"] or m["dtype"] for m in members}
    if len(dtypes) == 1:
        return measure
    if dtypes <= {"int", "float"}:
        measure["dtype"] = "float"
        bind = measure.setdefault("bind", {})
        bind["read"] = "float"
        return measure
    if len(reads) == 1:
        return measure
    raise RuntimeError(
        f"mixed non-numeric dtypes {[m['id'] for m in members[:4]]}: {dtypes}"
    )


def should_lift(members: list[dict]) -> tuple[bool, str]:
    family = members[0]["family"]
    if family == "passthrough":
        return False, "graph leftover / no lift family"
    if not any(m["INSTRUMENT"] for m in members):
        return False, "no INSTRUMENT"
    dtypes = {m["dtype"] for m in members}
    if len(dtypes) > 1 and not dtypes <= {"int", "float"}:
        return False, f"mixed measure dtypes {dtypes}"
    return True, "ok"


def bbox_cells(members: list[dict]) -> tuple[set[tuple[int, int]], list[int], str]:
    cells: set[tuple[int, int]] = set()
    for m in members:
        cells |= m["cells"]
    a1 = bbox_a1(cells)
    min_c = min(c for c, _ in cells)
    min_r = min(r for _, r in cells)
    max_c = max(c for c, _ in cells)
    max_r = max(r for _, r in cells)
    member_rows = {r for m in members for r in m["rows"]}
    hole_rows = [r for r in range(min_r, max_r + 1) if r not in member_rows]
    remodeled = {
        (c, r)
        for r in range(min_r, max_r + 1)
        if r in member_rows
        for c in range(min_c, max_c + 1)
    }
    return remodeled, hole_rows, a1


def lift_group(members: list[dict], corrections: list[dict]) -> tuple[dict, dict, set, set]:
    members = sorted(members, key=lambda m: (m["rows"][0], m["cols"][0], m["id"]))
    m0 = members[0]
    lift, reason = should_lift(members)
    if not lift:
        raise AssertionError(f"lift_group on unliftable: {reason}")

    orig_cells: set[tuple[int, int]] = set()
    for m in members:
        orig_cells |= m["cells"]
    remodeled_cells, hole_rows, a1 = bbox_cells(members)
    missing = orig_cells - remodeled_cells
    if missing:
        sample = sorted(missing)[:8]
        raise RuntimeError(f"dropped original cells for {m0['id']}: {sample}")
    extras = remodeled_cells - orig_cells
    member_rows = {r for m in members for r in m["rows"]}
    triangle = sum(1 for c, r in extras if r in member_rows)

    fx = all(m["HOLDER"] is not None for m in members)
    sid = make_id(members, lifted=True, fx=fx)

    dims = copy.deepcopy(m0["dims"])
    have = existing_dim_ids(dims)
    new_keys: list[str] = []
    for field, read in (("INSTRUMENT", "string"), ("HOLDER", "string")):
        if field in have:
            continue
        if not any(m.get(field) is not None for m in members):
            continue
        if field == "HOLDER" and not all(m.get("HOLDER") is not None for m in members):
            continue
        values = build_field_value_map(members, field)
        if not values:
            continue
        dims.insert(len(new_keys), value_map_dim(field, values, read))
        new_keys.append(field)
        have.add(field)

    unify_time_header(members, dims, corrections, sid)

    old_keys = [k for k in m0["key"] if k in have or k in existing_dim_ids(dims)]
    key = order_key(new_keys + [k for k in old_keys if k not in new_keys])
    dims = order_dims(dims, key)

    layout = m0["layout"]
    if "TIME_PERIOD" in key:
        layout = "series"
    elif layout == "matrix":
        layout = "matrix"
    elif layout == "scalar":
        layout = "scalar"
    else:
        layout = "series" if key else m0["layout"]

    extra_note = None
    if extras:
        extra_note = (
            f"Bounding rectangle adds {len(extras)} cells not in the original "
            f"per-member ranges ({triangle} on member rows: ragged year widths)."
        )
    if any(c["id"] == sid for c in corrections):
        corr = next(c for c in corrections if c["id"] == sid)
        extra_note = (
            (extra_note + " " if extra_note else "")
            + f"TIME_PERIOD header_row unified {corr['original']} → {corr['remodeled']}."
        )

    series: dict = {
        "id": sid,
        "sheet": m0["sheet"],
        "data_range": format_data_range(m0["sheet"], a1),
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

    series["structure"] = {"measure": unify_measure(members), "dimensions": dims}
    series["key"] = key
    series["series_context"] = family_context(members)
    series["notes"] = synthesize_notes(members, True, extra_note)

    audit = {
        "id": sid,
        "lifted": True,
        "reason": reason,
        "n_members": len(members),
        "member_ids": [m["id"] for m in members],
        "direction": m0["direction"],
        "layout": layout,
        "sheet": m0["sheet"],
        "TABLE": series["series_context"].get("TABLE"),
        "INDICATOR": series["series_context"].get("INDICATOR"),
        "VARIANT": m0["VARIANT"],
        "key": key,
        "orig_cells": len(orig_cells),
        "remodeled_cells": len(remodeled_cells),
        "extras": len(extras),
        "triangle_extras": triangle,
        "exclude_rows": hole_rows,
        "a1": a1,
        "instruments": sorted({m["INSTRUMENT"] for m in members if m["INSTRUMENT"]}),
        "holders": sorted({str(m["HOLDER"]) for m in members if m["HOLDER"] is not None}),
        "family": m0["family"],
        "source": m0["source"],
    }
    return series, audit, remodeled_cells, orig_cells


def passthrough_series(m: dict) -> tuple[dict, dict, set, set]:
    sid = make_id([m], lifted=False, fx=False)
    _, a1 = split_sheet_range(m["data_range"])
    series: dict = {
        "id": sid,
        "sheet": m["sheet"],
        "data_range": format_data_range(m["sheet"], a1),
        "layout": m["layout"],
    }
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
    if ctx:
        series["series_context"] = ctx
    if m["notes"]:
        series["notes"] = m["notes"]

    audit = {
        "id": sid,
        "lifted": False,
        "reason": "passthrough",
        "n_members": 1,
        "member_ids": [m["id"]],
        "direction": m["direction"],
        "layout": m["layout"],
        "sheet": m["sheet"],
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
        "family": m["family"],
        "source": m["source"],
    }
    return series, audit, set(m["cells"]), set(m["cells"])


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
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s) and s.lower() not in {
        "true",
        "false",
        "null",
        "yes",
        "no",
        "on",
        "off",
        "y",
        "n",
    }:
        return s
    return json.dumps(s, ensure_ascii=False)


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
            else:
                lines.append(f"{sp}{k}:")
                for x in v:
                    if isinstance(x, dict):
                        first = True
                        for ik, iv in x.items():
                            prefix = "- " if first else "  "
                            first = False
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


def emit_dimension(dim: dict, indent: int) -> list[str]:
    sp = " " * indent
    lines = [f"{sp}- id: {yaml_scalar(dim['id'])}"]
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
                for dim in dims:
                    lines.extend(emit_dimension(dim, indent + 4))
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
    lines = ["concept_scheme:", f"  id: {cs.get('id')}", "  concepts:"]
    for c in cs["concepts"]:
        lines.append(f"  - id: {c['id']}")
        if "name" in c:
            lines.append(f"    name: {yaml_scalar(c['name'])}")
        if "dtype" in c:
            lines.append(f"    dtype: {c['dtype']}")
        if c.get("sdmx_concept"):
            lines.append(f"    sdmx_concept: {c['sdmx_concept']}")
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


def sheet_rank(sheet: str) -> int:
    return 0 if sheet == "PV_Base" else 1


def tagged(sheet: str, cells: set[tuple[int, int]]) -> set[tuple[str, int, int]]:
    return {(sheet, c, r) for c, r in cells}


def write_audit(
    original_members: list[dict],
    audits: list[dict],
    orig_cells: set[tuple[str, int, int]],
    rem_cells: set[tuple[str, int, int]],
    corrections: list[dict],
    n_original: int,
    n_remodeled: int,
) -> str:
    extras = rem_cells - orig_cells
    missing = orig_cells - rem_cells
    lifted = [a for a in audits if a["lifted"]]
    passthrough = [a for a in audits if not a["lifted"]]
    by_source: dict[str, int] = defaultdict(int)
    for m in original_members:
        by_source[m["source"]] += 1

    lines: list[str] = []
    lines.append("# PV_Base remodel audit")
    lines.append("")
    lines.append("Prototype reshape-to-keys pass for `PV_Base` and `PV_Base-add.cost.mkt`.")
    lines.append("Original catalogs: `internals-pv-base.bindings.yaml` (618),")
    lines.append("`constants.bindings.yaml` (84 PV_Base + 2 add.cost.mkt),")
    lines.append("`internals-graph-coverage.bindings.yaml` (74 PV_Base + 14 add.cost.mkt),")
    lines.append("`inputs.bindings.yaml` (1).")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Original series: **{n_original}**")
    for src, n in sorted(by_source.items()):
        lines.append(f"  - {src}: {n}")
    lines.append(f"- Remodeled series: **{n_remodeled}**")
    lines.append(f"- Lifted groups (one series each): **{len(lifted)}**")
    lines.append(f"- Passthrough series: **{len(passthrough)}**")
    copy_ids = [
        a
        for a in lifted
        if a["family"] == "authored"
        and a["TABLE"] in {"pv_base.discount_schedule", "pv_base.new_loan_output"}
        and a["n_members"] in {6, 28}
        and a["direction"] == "internal"
        and a.get("VARIANT") in {"discount", "output"}
        and a["INDICATOR"]
        not in {"Repayment schedule", "Schedule period", "Selected instrument", "Projection year"}
    ]
    if copy_ids:
        n_orig = sum(a["n_members"] for a in copy_ids)
        lines.append(
            f"- Headline unit-loan / new-loan output copies: "
            f"**{n_orig} → {len(copy_ids)}** "
            f"(9 discount + 7 output indicators; 28 instruments + 6 FX `*_fx`)"
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
    lines.append(
        "Extra cells are bbox fill on member rows: unit-loan and output rows have "
        "ragged right edges (long-maturity IDA windows vs shorter commercial rows). "
        "`exclude_rows` carves the inter-block separators; it cannot drop trailing "
        "blanks on a member row (`exclude_columns` would drop original cells of "
        "wider members)."
    )
    lines.append("")

    big = [a for a in lifted if a["extras"] >= 50]
    if big:
        lines.append("### Largest bounding-rectangle extras")
        lines.append("")
        lines.append("| id | members | orig cells | remodeled | extras | on member rows | hole rows |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for a in sorted(big, key=lambda x: -x["extras"]):
            lines.append(
                f"| `{a['id']}` | {a['n_members']} | {a['orig_cells']} | "
                f"{a['remodeled_cells']} | {a['extras']} | {a['triangle_extras']} | "
                f"{len(a['exclude_rows'])} |"
            )
        lines.append("")

    if corrections:
        lines.append("## TIME_PERIOD header_row unification")
        lines.append("")
        lines.append(
            "Output blocks copy projection years onto a per-instrument header row "
            "(IMF row 21, IDA regular row 63, …). Discount schedules already share "
            "row 7. Remodeled output series read years from the first block header "
            f"(PV_Base row {OUTPUT_HEADER_ROW['PV_Base']}; add.cost.mkt row "
            f"{OUTPUT_HEADER_ROW['PV_Base-add.cost.mkt']})."
        )
        lines.append("")
        lines.append("| id | original header_row | remodeled |")
        lines.append("|---|---|---:|")
        for c in corrections:
            lines.append(f"| `{c['id']}` | {c['original']} | {c['remodeled']} |")
        lines.append("")

    lines.append("## Lifted series (id → keys)")
    lines.append("")
    lines.append("| id | n | dir | layout | TABLE | INDICATOR | keys |")
    lines.append("|---|---:|---|---|---|---|---|")
    for a in sorted(lifted, key=lambda x: (sheet_rank(x["sheet"]), x["id"])):
        keys = ", ".join(a["key"]) if a["key"] else "—"
        lines.append(
            f"| `{a['id']}` | {a['n_members']} | {a['direction']} | {a['layout']} | "
            f"`{a['TABLE'] or ''}` | {a['INDICATOR'] or ''} | `{keys}` |"
        )
    lines.append("")

    lines.append("## Holder split")
    lines.append("")
    lines.append(
        "FX local bonds reuse the same `INSTRUMENT` string for non-residents and "
        "residents. A single `INSTRUMENT` value_map cannot name both rows without "
        "colliding, and filling a dummy `HOLDER` for IMF/IDA would invent a key. "
        "Those copies are a second series (`*_fx`) keyed by `INSTRUMENT` + `HOLDER`. "
        "Original holder strings are preserved (`non-residents` / `residents` on "
        "internals; `non_residents` / `residents` on opening-stock constants)."
    )
    lines.append("")

    lines.append("## Graph-coverage leftovers")
    lines.append("")
    lines.append(
        "Draft leftovers without `TABLE` were grouped by geometry, not by the "
        "instrument name that the extractor stuffed into `INDICATOR`:"
    )
    lines.append("")
    lines.append("- `pv_base_block_labels` — column B four-row `Grace …` labels (`row_label` on A).")
    lines.append("- `pv_base_block_index` — year-grid row three above each unit-loan `Debt stock`.")
    lines.append("- `pv_base_instrument_title` — column A IDA instrument titles.")
    lines.append("- `pv_base_add_cost_mkt_grace` / `_maturity` — column B scalars on the shock sheet.")
    lines.append("")

    if passthrough:
        lines.append("## Passthrough (not lifted)")
        lines.append("")
        lines.append("| id | orig id | dir | TABLE | INDICATOR | reason |")
        lines.append("|---|---|---|---|---|---|")
        for a in sorted(passthrough, key=lambda x: x["id"]):
            orig = a["member_ids"][0]
            lines.append(
                f"| `{a['id']}` | `{orig}` | {a['direction']} | "
                f"`{a['TABLE'] or ''}` | {a['INDICATOR'] or ''} | {a['reason']} |"
            )
        lines.append("")

    lines.append("## Rules")
    lines.append("")
    lines.append("- Do not merge `input` / `internal` / `constant` of the same concept (year-1 output Interest leaves stay `constant`; formula years stay `internal`).")
    lines.append("- Preserve original instrument strings, including `Commecial Bank`.")
    lines.append("- `schema_version: 1.13.0`; `value_map` may list disjoint row specs for FX `INSTRUMENT` bands.")
    lines.append("- `exclude_rows` uses RowSpec (`11` or `\"11:17\"`) for bbox holes between instrument blocks.")
    lines.append("- Ids match `^[a-z][a-z0-9_]*$`. One YAML entry per series.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    members, concept_scheme = load_series()
    annotate(members)
    print(f"Loaded {len(members)} PV_Base-related series")

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for m in members:
        groups[group_key(m)].append(m)

    used_ids: set[str] = set()
    series_out: list[dict] = []
    audits: list[dict] = []
    corrections: list[dict] = []
    rem_cells: set[tuple[str, int, int]] = set()
    orig_cells: set[tuple[str, int, int]] = set()
    all_orig: set[tuple[str, int, int]] = set()
    for m in members:
        all_orig |= tagged(m["sheet"], m["cells"])

    for _gkey, gmembers in sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
        for chunk in split_holder_groups(gmembers):
            lift, reason = should_lift(chunk)
            if lift:
                series, audit, rcells, ocells = lift_group(chunk, corrections)
                series["id"] = unique_id(series["id"], used_ids)
                audit["id"] = series["id"]
                series_out.append(series)
                audits.append(audit)
                rem_cells |= tagged(series["sheet"], rcells)
                orig_cells |= tagged(chunk[0]["sheet"], ocells)
                continue
            for m in chunk:
                series, audit, rcells, ocells = passthrough_series(m)
                audit["reason"] = reason
                series["id"] = unique_id(series["id"], used_ids)
                audit["id"] = series["id"]
                series_out.append(series)
                audits.append(audit)
                rem_cells |= tagged(m["sheet"], rcells)
                orig_cells |= tagged(m["sheet"], ocells)

    series_out.sort(key=lambda s: (sheet_rank(s["sheet"]), min_row_of_series(s), s["id"]))

    missing = all_orig - rem_cells
    if missing:
        sample = ", ".join(f"{sh}!{num_to_col(c)}{r}" for sh, c, r in sorted(missing)[:20])
        raise SystemExit(f"Original cells missing from remodeled: {len(missing)} e.g. {sample}")
    if orig_cells != all_orig:
        raise SystemExit("orig_cells tracking drifted from union of members")

    ids = [s["id"] for s in series_out]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"duplicate ids: {[i for i in ids if ids.count(i) > 1]}")
    for sid in ids:
        if not ID_RE.match(sid):
            raise SystemExit(f"bad id: {sid}")

    header = [f"schema_version: {SCHEMA_VERSION}", "workbook: workbook.xlsm"]
    header.extend(emit_concept_scheme(concept_scheme))
    header.append("series:")
    body: list[str] = []
    for s in series_out:
        body.extend(emit_series(s))
    text = "\n".join(header + body) + "\n"
    OUT_YAML.write_text(text)

    parsed = yaml.safe_load(text)
    assert str(parsed["schema_version"]) == SCHEMA_VERSION
    assert len(parsed["series"]) == len(series_out)
    assert [s["id"] for s in parsed["series"]] == ids

    audit_text = write_audit(
        members,
        audits,
        all_orig,
        rem_cells,
        corrections,
        n_original=len(members),
        n_remodeled=len(series_out),
    )
    OUT_AUDIT.write_text(audit_text)

    extras = rem_cells - all_orig
    print(f"Wrote {OUT_YAML} ({len(series_out)} series)")
    print(f"Wrote {OUT_AUDIT}")
    print(
        f"original cells={len(all_orig)} remodeled={len(rem_cells)} "
        f"extras={len(extras)} missing={len(missing)}"
    )
    print(
        "lifted:",
        sum(1 for a in audits if a["lifted"]),
        "passthrough:",
        sum(1 for a in audits if not a["lifted"]),
    )
    print("fx:", [a["id"] for a in audits if a["id"].endswith("_fx")])


if __name__ == "__main__":
    main()
