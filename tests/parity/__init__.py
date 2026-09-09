"""Golden-master parity helpers for Output-panel differential tests.

Not part of the installed library. Equality, probe catalogs, live-Excel
reading, JSON cases (``case_schema`` / ``mint`` / ``run_case``), and
side-by-side comparison live here. Output *tables* are public and live in
``lic_dsf.output``.
"""

from tests.parity.compare import (
    assert_all_passed,
    compare_probes,
    lookup_sut,
    write_parity_csv,
)
from tests.parity.equality import ABS_TOL, REL_TOL, abs_diff, close, error_class
from tests.parity.excel import (
    ExcelComCrashed,
    ExcelNotAvailable,
    excel_available,
    read_cached_output,
    read_live_output,
)
from tests.parity.probes import Probe, a1, as_year, probes_for_years, year_columns
from tests.parity.run_case import assert_case_passed, run_case

__all__ = [
    "ABS_TOL",
    "REL_TOL",
    "ExcelComCrashed",
    "ExcelNotAvailable",
    "Probe",
    "a1",
    "abs_diff",
    "as_year",
    "assert_all_passed",
    "assert_case_passed",
    "close",
    "compare_probes",
    "error_class",
    "excel_available",
    "lookup_sut",
    "probes_for_years",
    "read_cached_output",
    "read_live_output",
    "run_case",
    "write_parity_csv",
    "year_columns",
]
