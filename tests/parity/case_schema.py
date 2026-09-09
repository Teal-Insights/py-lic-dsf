"""JSON case schema for Excel-oracle differential tests.

Cases live under ``data/parity/cases/<id>/`` with ``case.json`` + ``expected.json``.
Goldens are oracle-minted (``cached``, ``grapher``, or ``live``); never from the Python SUT.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_ROOT = REPO_ROOT / "data" / "parity" / "cases"

ExcelBuild = Literal["live", "cached", "grapher"]


@dataclass(frozen=True, slots=True)
class CellOverlay:
    """One Excel cell write applied before mint or Python load."""

    sheet: str
    cell: str
    value: Any


@dataclass(frozen=True, slots=True)
class CaseInputs:
    overlays: tuple[CellOverlay, ...] = ()
    presets: tuple[str, ...] = ()

    def resolved_overlays(self) -> tuple[CellOverlay, ...]:
        """Presets first, then explicit overlays (explicit wins on duplicates)."""
        from tests.parity.presets import expand_presets

        return expand_presets(self.presets) + self.overlays


@dataclass(frozen=True, slots=True)
class CaseProbes:
    """Which probe catalog (and optional filters) a case exercises."""

    catalog: str
    years: tuple[int, ...] | None = None
    rows: tuple[int, ...] | None = None
    scenario_id: str | None = None


@dataclass(frozen=True, slots=True)
class OracleMeta:
    minted_at: str | None = None
    template_sha: str | None = None
    excel_build: ExcelBuild | None = None


@dataclass(frozen=True, slots=True)
class CaseSpec:
    """Loaded ``case.json`` plus resolved paths."""

    id: str
    workbook: str
    description: str
    inputs: CaseInputs
    probes: CaseProbes
    oracle: OracleMeta
    case_dir: Path

    @property
    def case_path(self) -> Path:
        return self.case_dir / "case.json"

    @property
    def expected_path(self) -> Path:
        return self.case_dir / "expected.json"

    def workbook_path(self, repo_root: Path | None = None) -> Path:
        root = repo_root or REPO_ROOT
        path = Path(self.workbook)
        if not path.is_absolute():
            path = root / path
        return path.resolve()


@dataclass(frozen=True, slots=True)
class ExpectedProbe:
    sheet: str
    cell: str
    row: int
    col: int | None
    year: int | None
    section: str
    label: str
    sut_key: Any
    excel_value: Any


@dataclass(frozen=True, slots=True)
class ExpectedBundle:
    probes: tuple[ExpectedProbe, ...]
    oracle: OracleMeta = field(default_factory=OracleMeta)


def file_sha256(path: Path) -> str:
    """Return hex SHA-256 of ``path`` contents."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encode_sut_key(key: Any) -> Any:
    """JSON-safe ``sut_key`` (tuples → lists)."""
    if isinstance(key, tuple):
        return [encode_sut_key(part) for part in key]
    return key


def decode_sut_key(key: Any) -> Any:
    """Restore tuple ``sut_key`` values from JSON lists."""
    if isinstance(key, list):
        return tuple(decode_sut_key(part) for part in key)
    return key


def encode_excel_value(value: Any) -> Any:
    """JSON-safe Excel cell value (NaN / NA → null)."""
    import math

    import pandas as pd

    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and (math.isnan(value) or pd.isna(value)):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _require_mapping(data: Any, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError(f"{label} must be a JSON object")
    return data


def _parse_presets(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(p, str) and p for p in raw):
        raise TypeError("inputs.presets must be a string or list of non-empty strings")
    from tests.parity.presets import known_presets

    known = set(known_presets())
    for name in raw:
        if name not in known:
            raise KeyError(f"unknown overlay preset {name!r}; known: {sorted(known)}")
    return tuple(raw)


def _parse_overlays(raw: Any) -> tuple[CellOverlay, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise TypeError("inputs.overlays must be a list")
    overlays: list[CellOverlay] = []
    for i, item in enumerate(raw):
        item = _require_mapping(item, f"inputs.overlays[{i}]")
        sheet = item.get("sheet")
        cell = item.get("cell")
        if not isinstance(sheet, str) or not sheet:
            raise ValueError(f"inputs.overlays[{i}].sheet must be a non-empty string")
        if not isinstance(cell, str) or not cell:
            raise ValueError(f"inputs.overlays[{i}].cell must be a non-empty A1 string")
        if "value" not in item:
            raise ValueError(f"inputs.overlays[{i}] missing value")
        overlays.append(CellOverlay(sheet=sheet, cell=cell, value=item["value"]))
    return tuple(overlays)


def _parse_probes(raw: Any) -> CaseProbes:
    raw = _require_mapping(raw, "probes")
    catalog = raw.get("catalog")
    if not isinstance(catalog, str) or not catalog:
        raise ValueError("probes.catalog must be a non-empty string")
    years = raw.get("years")
    if years is not None:
        if not isinstance(years, list) or not all(isinstance(y, int) for y in years):
            raise ValueError("probes.years must be a list of ints")
        years_t = tuple(years)
    else:
        years_t = None
    rows = raw.get("rows")
    if rows is not None:
        if not isinstance(rows, list) or not all(isinstance(r, int) for r in rows):
            raise ValueError("probes.rows must be a list of ints")
        rows_t = tuple(rows)
    else:
        rows_t = None
    scenario_id = raw.get("scenario_id")
    if scenario_id is not None and not isinstance(scenario_id, str):
        raise ValueError("probes.scenario_id must be a string")
    return CaseProbes(
        catalog=catalog,
        years=years_t,
        rows=rows_t,
        scenario_id=scenario_id,
    )


def _parse_oracle(raw: Any) -> OracleMeta:
    if raw is None:
        return OracleMeta()
    raw = _require_mapping(raw, "oracle")
    build = raw.get("excel_build")
    if build is not None and build not in {"live", "cached", "grapher"}:
        raise ValueError("oracle.excel_build must be 'live', 'cached', or 'grapher'")
    return OracleMeta(
        minted_at=raw.get("minted_at"),
        template_sha=raw.get("template_sha"),
        excel_build=build,
    )


def load_case(case_dir: str | Path) -> CaseSpec:
    """Load and validate ``case.json`` from ``case_dir``."""
    directory = Path(case_dir)
    path = directory / "case.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    data = _require_mapping(json.loads(path.read_text(encoding="utf-8")), "case.json")
    case_id = data.get("id")
    workbook = data.get("workbook")
    description = data.get("description", "")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("case id must be a non-empty string")
    if not isinstance(workbook, str) or not workbook:
        raise ValueError("workbook must be a non-empty string")
    if not isinstance(description, str):
        raise TypeError("description must be a string")
    inputs_raw = data.get("inputs") or {}
    inputs_map = _require_mapping(inputs_raw, "inputs")
    inputs = CaseInputs(
        overlays=_parse_overlays(inputs_map.get("overlays")),
        presets=_parse_presets(inputs_map.get("presets")),
    )
    probes = _parse_probes(data.get("probes"))
    oracle = _parse_oracle(data.get("oracle"))
    return CaseSpec(
        id=case_id,
        workbook=workbook,
        description=description,
        inputs=inputs,
        probes=probes,
        oracle=oracle,
        case_dir=directory.resolve(),
    )


def load_expected(path: str | Path) -> ExpectedBundle:
    """Load ``expected.json`` probe goldens."""
    file_path = Path(path)
    data = _require_mapping(
        json.loads(file_path.read_text(encoding="utf-8")), "expected.json"
    )
    raw_probes = data.get("probes")
    if not isinstance(raw_probes, list):
        raise TypeError("expected.json probes must be a list")
    probes: list[ExpectedProbe] = []
    for i, item in enumerate(raw_probes):
        item = _require_mapping(item, f"probes[{i}]")
        probes.append(
            ExpectedProbe(
                sheet=str(item["sheet"]),
                cell=str(item.get("cell", "")),
                row=int(item["row"]),
                col=int(item["col"]) if item.get("col") is not None else None,
                year=int(item["year"]) if item.get("year") is not None else None,
                section=str(item.get("section", "")),
                label=str(item.get("label", "")),
                sut_key=decode_sut_key(item["sut_key"]),
                excel_value=item.get("excel_value"),
            )
        )
    return ExpectedBundle(probes=tuple(probes), oracle=_parse_oracle(data.get("oracle")))


def dump_expected(bundle: ExpectedBundle, path: str | Path) -> Path:
    """Write ``expected.json``."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "oracle": {
            "minted_at": bundle.oracle.minted_at,
            "template_sha": bundle.oracle.template_sha,
            "excel_build": bundle.oracle.excel_build,
        },
        "probes": [
            {
                "sheet": p.sheet,
                "cell": p.cell,
                "row": p.row,
                "col": p.col,
                "year": p.year,
                "section": p.section,
                "label": p.label,
                "sut_key": encode_sut_key(p.sut_key),
                "excel_value": encode_excel_value(p.excel_value),
            }
            for p in bundle.probes
        ],
    }
    file_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return file_path


def update_case_oracle(case: CaseSpec, oracle: OracleMeta) -> None:
    """Rewrite ``case.json`` oracle metadata after a successful mint."""
    data = json.loads(case.case_path.read_text(encoding="utf-8"))
    data["oracle"] = {
        "minted_at": oracle.minted_at,
        "template_sha": oracle.template_sha,
        "excel_build": oracle.excel_build,
    }
    case.case_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def iter_case_dirs(root: str | Path | None = None) -> Iterator[Path]:
    """Yield case directories that contain ``case.json``."""
    base = Path(root) if root is not None else CASES_ROOT
    if not base.is_dir():
        return
    for path in sorted(base.iterdir()):
        if path.is_dir() and (path / "case.json").is_file():
            yield path


def discover_cases(root: str | Path | None = None) -> tuple[CaseSpec, ...]:
    """Load every case under ``root`` (default ``data/parity/cases``)."""
    return tuple(load_case(path) for path in iter_case_dirs(root))
