"""Compare Excel probe values to an Excel-shaped SUT table."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from pathlib import Path

import pandas as pd

from tests.parity.equality import abs_diff, close
from tests.parity.probes import Probe

_CSV_COLS = (
    "sheet",
    "cell",
    "row",
    "col",
    "year",
    "section",
    "label",
    "sut_key",
    "excel_value",
    "computed_value",
    "abs_diff",
    "passed",
    "missing_sut",
)


def lookup_sut(sut: pd.DataFrame | Mapping[Hashable, object], key: Hashable, year: int | None) -> object:
    """Pull one value from an Excel-shaped table or cell-keyed mapping."""
    if isinstance(sut, Mapping):
        value = sut.get(key)
        if isinstance(value, pd.Series) and year is not None and year in value.index:
            return value.loc[year]
        return value
    if key not in sut.index:
        return None
    row = sut.loc[key]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    if year is not None and year in row.index:
        return row.loc[year]
    if isinstance(row, pd.Series) and len(row) == 1:
        return row.iloc[0]
    return row


def compare_probes(
    excel: pd.DataFrame,
    sut: pd.DataFrame | Mapping[Hashable, object],
    probes: Sequence[Probe] | None = None,
) -> pd.DataFrame:
    """Attach SUT values and pass/fail flags to an Excel probe frame.

    A catalog row whose ``sut_key`` is missing from the SUT is recorded as
    ``missing_sut=True`` and ``passed=False``.

    Args:
        excel: Frame from ``read_live_output`` / ``read_cached_output``.
        sut: Excel-shaped table (index = probe ``sut_key``) or cell map.
        probes: Optional probe list used when ``excel`` has no ``sut_key``.

    Returns:
        One row per comparison with ``passed`` / ``missing_sut``.
    """
    frame = excel.copy()
    if "sut_key" not in frame.columns:
        if probes is None:
            raise ValueError("excel frame missing sut_key and no probes given")
        frame["sut_key"] = [p.sut_key for p in probes]
    computed: list[object] = []
    diffs: list[float | None] = []
    passed: list[bool] = []
    missing: list[bool] = []
    for key, year, excel_value in zip(
        frame["sut_key"].tolist(),
        frame["year"].tolist() if "year" in frame.columns else [None] * len(frame),
        frame["excel_value"].tolist(),
        strict=True,
    ):
        if isinstance(sut, pd.DataFrame):
            absent = key not in sut.index
        else:
            absent = key not in sut
        if absent:
            computed.append(pd.NA)
            diffs.append(None)
            passed.append(False)
            missing.append(True)
            continue
        year_i = None if year is None or (isinstance(year, float) and pd.isna(year)) else int(year)
        value = lookup_sut(sut, key, year_i)
        computed.append(value if value is not None else pd.NA)
        diffs.append(abs_diff(excel_value, value))
        passed.append(close(excel_value, value))
        missing.append(False)
    frame["computed_value"] = computed
    frame["abs_diff"] = diffs
    frame["passed"] = passed
    frame["missing_sut"] = missing
    return frame.reset_index(drop=True)


def write_parity_csv(frame: pd.DataFrame, output: str | Path) -> Path:
    """Write comparison columns to ``output``."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [c for c in _CSV_COLS if c in frame.columns]
    frame.loc[:, cols].to_csv(path, index=False)
    return path


def assert_all_passed(frame: pd.DataFrame) -> None:
    """Raise ``AssertionError`` if any comparison failed or SUT key is missing."""
    missing = frame[frame["missing_sut"]] if "missing_sut" in frame.columns else frame.iloc[0:0]
    failed = frame[~frame["passed"]] if "passed" in frame.columns else frame
    if len(missing):
        keys = missing["sut_key"].tolist()[:8]
        raise AssertionError(f"{len(missing)} probes missing from SUT, e.g. {keys}")
    if len(failed):
        sample = failed.head(5)
        raise AssertionError(f"{len(failed)} parity failures, e.g.\n{sample}")
