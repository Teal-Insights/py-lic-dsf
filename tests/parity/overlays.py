"""Apply Excel-native cell overlays to a workbook copy.

Overlays are the shared input language for mint (Excel) and Python load paths.

Python-side writes use a surgical XLSX/ZIP patch so cached ``data_only`` values
(needed by ``load_*``) are preserved. A full openpyxl/fastpyxl rewrite drops
those caches and breaks instrument year headers.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path
from xml.etree import ElementTree as ET

from tests.parity.case_schema import CellOverlay

_A1 = re.compile(r"^([A-Za-z]+)(\d+)$")
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = {
    "r": "http://schemas.openxmlformats.org/package/2006/relationships"
}
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def parse_a1(cell: str) -> tuple[int, int]:
    """Return 1-based ``(row, col)`` for an A1 address."""
    match = _A1.match(cell.strip())
    if not match:
        raise ValueError(f"invalid A1 cell address: {cell!r}")
    letters, digits = match.group(1), match.group(2)
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch.upper()) - 64)
    return int(digits), col


def materialize_workbook(
    workbook: str | Path,
    overlays: Sequence[CellOverlay] = (),
    *,
    dest: str | Path | None = None,
) -> Path:
    """Copy ``workbook`` and apply overlays; return the path used for loading.

    When ``overlays`` is empty and ``dest`` is None, returns the original path
    (no copy). Otherwise writes a workbook copy with surgical cell patches.
    """
    src = Path(workbook).resolve()
    if not overlays and dest is None:
        return src
    if dest is None:
        tmp = Path(tempfile.mkdtemp(prefix="lic-dsf-overlay-"))
        dest_path = tmp / src.name
    else:
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_path)
    if overlays:
        apply_overlays_inplace(dest_path, overlays)
    return dest_path


def _sheet_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    """Map sheet name → zip member path (e.g. ``xl/worksheets/sheet3.xml``)."""
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    sheets = {
        sheet.attrib["name"]: sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        for sheet in wb.findall("m:sheets/m:sheet", _NS)
    }
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("r:Relationship", _REL_NS)
    }
    out: dict[str, str] = {}
    for name, rid in sheets.items():
        target = rid_to_target[rid]
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        out[name] = target
    return out


def _cell_xml(ref: str, value: object) -> ET.Element:
    """Build a ``<c>`` element for ``ref`` with a scalar overlay value."""
    cell = ET.Element(f"{{{_NS_MAIN}}}c", {"r": ref})
    if isinstance(value, bool):
        cell.set("t", "b")
        v = ET.SubElement(cell, f"{{{_NS_MAIN}}}v")
        v.text = "1" if value else "0"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        v = ET.SubElement(cell, f"{{{_NS_MAIN}}}v")
        v.text = str(value)
    else:
        cell.set("t", "inlineStr")
        is_el = ET.SubElement(cell, f"{{{_NS_MAIN}}}is")
        t_el = ET.SubElement(is_el, f"{{{_NS_MAIN}}}t")
        t_el.text = str(value)
    return cell


def _freeze_shared_formula_slaves(root: ET.Element, ref: str) -> None:
    """If ``ref`` is a shared-formula master, freeze siblings to cached values.

    Excel stores one master ``<f t="shared" si="N">formula</f>`` and slave
    stubs ``<f t="shared" si="N"/>`` with empty text. Replacing the master with
    a constant leaves slaves as empty ``=`` formulas that excel-grapher cannot
    parse. Convert each other cell in the same ``si`` group to its cached
    ``<v>`` (or drop the formula) before the master is overwritten.
    """
    sheet_data = root.find("m:sheetData", _NS)
    if sheet_data is None:
        return
    master_f: ET.Element | None = None
    master_si: str | None = None
    for row_el in sheet_data.findall("m:row", _NS):
        for cell in row_el.findall("m:c", _NS):
            if cell.attrib.get("r") != ref:
                continue
            formula = cell.find("m:f", _NS)
            if formula is None:
                return
            if formula.attrib.get("t") != "shared":
                return
            # Master cells carry formula text and/or a ref= range attribute.
            if not (formula.text or formula.attrib.get("ref")):
                return
            master_f = formula
            master_si = formula.attrib.get("si")
            break
        if master_si is not None:
            break
    if master_si is None:
        return

    for row_el in sheet_data.findall("m:row", _NS):
        for cell in list(row_el.findall("m:c", _NS)):
            cell_ref = cell.attrib.get("r")
            if cell_ref == ref:
                continue
            formula = cell.find("m:f", _NS)
            if formula is None or formula.attrib.get("t") != "shared":
                continue
            if formula.attrib.get("si") != master_si:
                continue
            cached = cell.find("m:v", _NS)
            if cached is not None and cached.text not in (None, ""):
                text = cached.text.strip()
                try:
                    value: object = float(text) if ("." in text or "e" in text.lower()) else int(text)
                except ValueError:
                    value = text
                row_el.remove(cell)
                row_el.append(_cell_xml(cell_ref or ref, value))
            else:
                # No cache: drop the empty shared stub to avoid '=' parse errors.
                row_el.remove(formula)


def _set_cell(root: ET.Element, ref: str, value: object) -> None:
    """Insert or replace cell ``ref`` under ``sheetData``."""
    _freeze_shared_formula_slaves(root, ref)
    row_num = int(re.search(r"(\d+)$", ref).group(1))  # type: ignore[union-attr]
    sheet_data = root.find("m:sheetData", _NS)
    if sheet_data is None:
        raise ValueError("worksheet missing sheetData")
    row_el = None
    for candidate in sheet_data.findall("m:row", _NS):
        if candidate.attrib.get("r") == str(row_num):
            row_el = candidate
            break
    if row_el is None:
        row_el = ET.Element(f"{{{_NS_MAIN}}}row", {"r": str(row_num)})
        # Keep rows roughly ordered by r.
        inserted = False
        for i, candidate in enumerate(list(sheet_data)):
            if candidate.tag.endswith("row"):
                other = int(candidate.attrib.get("r", "0"))
                if other > row_num:
                    sheet_data.insert(i, row_el)
                    inserted = True
                    break
        if not inserted:
            sheet_data.append(row_el)
    for old in list(row_el.findall("m:c", _NS)):
        if old.attrib.get("r") == ref:
            row_el.remove(old)
    row_el.append(_cell_xml(ref, value))


def apply_overlays_inplace(workbook: str | Path, overlays: Sequence[CellOverlay]) -> None:
    """Write overlay values into ``workbook`` on disk without rewriting the book.

    Patches worksheet XML inside the XLSX/XLSM zip so formula cached values
    used by ``data_only`` loaders remain intact.
    """
    path = Path(workbook)
    with zipfile.ZipFile(path, "r") as zf:
        sheet_map = _sheet_targets(zf)
        by_sheet: dict[str, list[CellOverlay]] = {}
        for overlay in overlays:
            if overlay.sheet not in sheet_map:
                raise KeyError(
                    f"overlay sheet {overlay.sheet!r} not in workbook; "
                    "adapter gap — fix the case overlay, not the SUT"
                )
            by_sheet.setdefault(overlay.sheet, []).append(overlay)
        updates: dict[str, bytes] = {}
        for sheet_name, sheet_overlays in by_sheet.items():
            member = sheet_map[sheet_name]
            root = ET.fromstring(zf.read(member))
            for overlay in sheet_overlays:
                parse_a1(overlay.cell)  # validate
                _set_cell(root, overlay.cell.upper(), overlay.value)
            updates[member] = ET.tostring(
                root, encoding="utf-8", xml_declaration=True
            )
        other_members = {
            info.filename: zf.read(info.filename)
            for info in zf.infolist()
            if info.filename not in updates
        }

    tmp = path.with_suffix(path.suffix + ".overlay-tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, data in other_members.items():
            out.writestr(name, data)
        for name, data in updates.items():
            out.writestr(name, data)
    tmp.replace(path)
