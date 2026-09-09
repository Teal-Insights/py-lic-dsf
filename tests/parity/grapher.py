"""excel-grapher FormulaEvaluator oracle for parity minting.

Faster/cheaper than live Excel COM. Goldens stamped ``excel_build: "grapher"``
are *proxy* oracles (Excel-semantics emulator), not Microsoft Excel itself.
Prefer ``--source live`` when strengthening the spreadsheet-identity claim,
especially for overlay cases where cached OFFSET/INDIRECT resolution may freeze
intermediate dependencies.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from tests.parity.case_schema import CellOverlay
from tests.parity.excel import _record
from tests.parity.overlays import materialize_workbook
from tests.parity.probes import Probe, a1

# LIC-DSF workbooks use a defined name ``n.a.`` → ``lookup!$AB$4`` (literal
# ``"n.a."``). excel-grapher's formula parser rejects bare defined names, so
# rewrite before parse. String literal matches the resolved cell value.
_NA_DEFINED_NAME = re.compile(r"(?<![\w'])n\.a\.(?![\w])")


class GrapherNotAvailable(RuntimeError):
    """Raised when excel-grapher (or a compatible fastpyxl) is missing."""


def grapher_available() -> bool:
    """Return True when ``excel-grapher`` imports and fastpyxl supports formula cache."""
    try:
        import inspect

        import excel_grapher  # noqa: F401
        import fastpyxl

        return "keep_formula_cache" in inspect.signature(fastpyxl.load_workbook).parameters
    except ImportError:
        return False


@contextmanager
def _rewrite_na_defined_name() -> Iterator[None]:
    """Expand workbook ``n.a.`` defined-name refs so grapher can parse formulas."""
    import excel_grapher.core.formula_ast as formula_ast
    import excel_grapher.evaluator.parser as evaluator_parser

    original_core = formula_ast.parse
    original_eval = evaluator_parser.parse

    def _patched_core(formula: str, *args, **kwargs):
        return original_core(
            _NA_DEFINED_NAME.sub('"n.a."', formula), *args, **kwargs
        )

    def _patched_eval(formula: str, *args, **kwargs):
        return original_eval(
            _NA_DEFINED_NAME.sub('"n.a."', formula), *args, **kwargs
        )

    formula_ast.parse = _patched_core  # type: ignore[assignment]
    evaluator_parser.parse = _patched_eval  # type: ignore[assignment]
    try:
        yield
    finally:
        formula_ast.parse = original_core  # type: ignore[assignment]
        evaluator_parser.parse = original_eval  # type: ignore[assignment]


def _probe_key(probe: Probe) -> str:
    from excel_grapher import format_key

    if probe.col is None:
        raise ValueError(f"probe {probe!r} missing col")
    cell = a1(probe.row, probe.col)
    # format_key wants A1 letters+row separately via (sheet, cell) overload
    return str(format_key(probe.sheet, cell))


def _coerce_value(value: object) -> object:
    """Normalize grapher FormulaValue to a JSON/parity-comparable scalar."""
    if value is None:
        return None
    try:
        from excel_grapher import XlError

        if isinstance(value, XlError):
            return str(value)
    except ImportError:
        pass
    if isinstance(value, (bool, int, float, str)):
        return value
    # CellValue / wrappers
    inner = getattr(value, "value", None)
    if inner is not None and inner is not value:
        return _coerce_value(inner)
    return value


def read_grapher_output(
    workbook: str | Path,
    probes: Sequence[Probe],
    overlays: Sequence[CellOverlay] = (),
    *,
    max_depth: int = 120,
) -> pd.DataFrame:
    """Evaluate ``probes`` with excel-grapher after optional overlays.

    Builds one dependency graph for all probe addresses (plus overlay cells),
    using ``use_cached_dynamic_refs=True`` so OFFSET/INDIRECT resolve from
    workbook caches. Overlays are applied via surgical XLSX patch before graph
    build so constants replace formulas at the patched cells.
    """
    if not grapher_available():
        raise GrapherNotAvailable(
            "excel-grapher mint requires the 'grapher' extra "
            "(excel-grapher + fastpyxl>=1.1 with keep_formula_cache)"
        )
    from excel_grapher import FormulaEvaluator, create_dependency_graph, format_key

    if not probes:
        return pd.DataFrame()

    path = materialize_workbook(workbook, overlays)
    targets: list[str] = []
    seen: set[str] = set()
    for probe in probes:
        key = _probe_key(probe)
        if key not in seen:
            targets.append(key)
            seen.add(key)
    for overlay in overlays:
        key = str(format_key(overlay.sheet, overlay.cell.upper()))
        if key not in seen:
            targets.append(key)
            seen.add(key)

    with _rewrite_na_defined_name():
        graph = create_dependency_graph(
            path,
            targets=targets,
            max_depth=max_depth,
            load_values=True,
            use_cached_dynamic_refs=True,
        )
        evaluator = FormulaEvaluator(graph)
        values = evaluator.evaluate(targets)
    if not isinstance(values, dict):
        values = {targets[0]: values}

    records: list[dict[object, object]] = []
    for probe in probes:
        key = _probe_key(probe)
        raw = values.get(key)
        records.append(_record(probe, _coerce_value(raw)))
    return pd.DataFrame.from_records(records)
