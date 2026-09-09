"""Map case ``probes.catalog`` names to probe lists and Python SUT builders."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from tests.parity.case_schema import CaseProbes, CaseSpec
from tests.parity.probes import Probe

Sut = pd.DataFrame | Mapping[Hashable, object]
ProbeBuilder = Callable[[Path, CaseProbes], tuple[Probe, ...]]
SutBuilder = Callable[[Path, CaseProbes], Sut]


def _filter_probes(probes: tuple[Probe, ...], spec: CaseProbes) -> tuple[Probe, ...]:
    out = probes
    if spec.years is not None:
        years = set(spec.years)
        out = tuple(p for p in out if p.year is None or p.year in years)
    if spec.rows is not None:
        rows = set(spec.rows)
        out = tuple(p for p in out if p.row in rows)
    return out


def _output_11_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.output_1 import output_11_probes

    return _filter_probes(output_11_probes(workbook), spec)


def _output_12_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.output_1 import output_12_probes

    return _filter_probes(output_12_probes(workbook), spec)


def _output_31_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.output_3 import output_31_probes

    return _filter_probes(output_31_probes(workbook), spec)


def _output_32_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.output_3 import output_32_probes

    return _filter_probes(output_32_probes(workbook), spec)


def _bsheet_ext_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.bsheet_external import (
        EXTERNAL_SHEETS,
        bsheet_external_probes,
    )

    if spec.scenario_id is not None:
        return _filter_probes(bsheet_external_probes(workbook, spec.scenario_id), spec)
    probes: list[Probe] = []
    for scenario_id in EXTERNAL_SHEETS:
        probes.extend(bsheet_external_probes(workbook, scenario_id))
    return _filter_probes(tuple(probes), spec)


def _bsheet_pub_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.bsheet_public import PUBLIC_SHEETS, bsheet_public_probes

    if spec.scenario_id is not None:
        return _filter_probes(bsheet_public_probes(workbook, spec.scenario_id), spec)
    probes: list[Probe] = []
    for scenario_id in PUBLIC_SHEETS:
        probes.extend(bsheet_public_probes(workbook, scenario_id))
    return _filter_probes(tuple(probes), spec)


def _resfin_probes(workbook: Path, spec: CaseProbes) -> tuple[Probe, ...]:
    from tests.parity.catalogs.resfin import resfin_probes

    return _filter_probes(resfin_probes(workbook), spec)


def _baseline_output_11(workbook: Path, _spec: CaseProbes) -> Sut:
    from lic_dsf.load import load_core
    from lic_dsf.output import output_11_table

    _macro, _ext, ext_base, _pub = load_core(workbook)
    return output_11_table(ext_base)


def _baseline_output_12(workbook: Path, _spec: CaseProbes) -> Sut:
    from lic_dsf.load import load_core
    from lic_dsf.output import output_12_table

    _macro, _ext, _ext_base, pub_base = load_core(workbook)
    return output_12_table(pub_base)


def _stress_layer(layer: str) -> SutBuilder:
    def build(workbook: Path, _spec: CaseProbes) -> Sut:
        from tests.parity.stress_sut import build_sut

        return build_sut(layer, workbook)  # type: ignore[arg-type]

    return build


_REGISTRY: dict[str, tuple[ProbeBuilder, SutBuilder]] = {
    "output_11": (_output_11_probes, _baseline_output_11),
    "output_12": (_output_12_probes, _baseline_output_12),
    "output_31": (_output_31_probes, _stress_layer("output31")),
    "output_32": (_output_32_probes, _stress_layer("output32")),
    "bsheet_ext": (_bsheet_ext_probes, _stress_layer("bsheet_ext")),
    "bsheet_pub": (_bsheet_pub_probes, _stress_layer("bsheet_pub")),
    "resfin": (_resfin_probes, _stress_layer("resfin")),
}


def known_catalogs() -> tuple[str, ...]:
    """Return registered catalog names."""
    return tuple(sorted(_REGISTRY))


def resolve_probes(case: CaseSpec, workbook: Path) -> tuple[Probe, ...]:
    """Build filtered probes for ``case`` against ``workbook``."""
    try:
        probe_builder, _ = _REGISTRY[case.probes.catalog]
    except KeyError as exc:
        raise KeyError(
            f"unknown probes.catalog {case.probes.catalog!r}; "
            f"known: {known_catalogs()}"
        ) from exc
    return probe_builder(workbook, case.probes)


def resolve_sut(case: CaseSpec, workbook: Path) -> Sut:
    """Build the Python SUT for ``case`` from ``workbook``."""
    try:
        _, sut_builder = _REGISTRY[case.probes.catalog]
    except KeyError as exc:
        raise KeyError(
            f"unknown probes.catalog {case.probes.catalog!r}; "
            f"known: {known_catalogs()}"
        ) from exc
    return sut_builder(workbook, case.probes)


def catalog_help() -> dict[str, Any]:
    """Short descriptions for CLI help."""
    return {
        "output_11": "Output 1-1 Excel-geometry table",
        "output_12": "Output 1-2 Excel-geometry table",
        "output_31": "Output 3-1 stress-external table",
        "output_32": "Output 3-2 stress-public table",
        "bsheet_ext": "External B-sheet metric cells",
        "bsheet_pub": "Public B-sheet metric cells",
        "resfin": "Residual financing probe cells",
    }
