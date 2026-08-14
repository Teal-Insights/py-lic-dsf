"""Load ``PresentValueInstrument`` rows from the LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastpyxl import load_workbook

if TYPE_CHECKING:
    from lic_dsf.pv import PresentValueInstrument
    from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument

# Input 4 rows that back PV_Base's 34 instrument tables (see docs/pv-base-tables.md).
_PV_BASE_INPUT4_ROWS: tuple[int, ...] = (
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,  # Multilaterals
    21,
    22,
    23,  # Other Multilaterals
    26,
    27,
    28,
    29,
    30,  # Paris Club / ECA
    32,
    33,
    34,
    35,
    36,  # Non-Paris Club
    38,
    39,
    40,
    41,
    42,  # Commercial
    54,
    55,
    56,  # FX local bonds, non-residents
    59,
    60,
    61,  # FX local bonds, residents
)

_INPUT4_SHEET = "Input 4 - External Financing"
_YEAR_HEADER_ROW = 6
_FIRST_DISBURSEMENT_COL = 12  # column L
_NAME_COL = 2
_DISCOUNT_COL = 5
_INTEREST_COL = 6
_GRACE_COL = 7
_MATURITY_COL = 8


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def _year_columns(worksheet: Any) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return (column_indices, calendar_years) for the disbursement block."""
    columns: list[int] = []
    years: list[int] = []
    col = _FIRST_DISBURSEMENT_COL
    while True:
        raw = worksheet.cell(_YEAR_HEADER_ROW, col).value
        year = _as_int(raw)
        if year is None:
            break
        columns.append(col)
        years.append(year)
        col += 1
    if not columns:
        raise ValueError(
            f"{_INPUT4_SHEET} has no year headers from column "
            f"{_FIRST_DISBURSEMENT_COL}"
        )
    return tuple(columns), tuple(years)


def _instrument_name(base_name: str, row: int) -> str:
    """Disambiguate duplicate FX bond labels (NR vs resident holders)."""
    if row in (59, 60, 61):
        return f"{base_name} (residents)"
    if row in (54, 55, 56):
        return f"{base_name} (non-residents)"
    return base_name


def _read_disbursements(
    worksheet: Any, row: int, columns: tuple[int, ...]
) -> tuple[float, ...]:
    values: list[float] = []
    for col in columns:
        raw = worksheet.cell(row, col).value
        number = _as_float(raw)
        values.append(0.0 if number is None else number)
    return tuple(values)


def load_instruments_from_workbook(
    workbook_path: str | Path,
    *,
    include_zero_disbursement: bool = True,
    sheet_name: str = _INPUT4_SHEET,
) -> list[PresentValueInstrument]:
    """Load PV_Base-backed instruments from Input 4 terms + disbursements.

    Reads discount / interest / grace / maturity and the projection-year
    disbursement row for each PV_Base Input 4 line. Rows with incomplete terms
    (e.g. empty PC2–PC5 grace/maturity in the template) are skipped because
    ``PresentValueInstrument`` requires ``maturity > grace``.

    Args:
        workbook_path: Path to the LIC-DSF ``.xlsx`` workbook.
        include_zero_disbursement: When False, drop instruments whose
            disbursement series sums to zero.
        sheet_name: External financing sheet (default Input 4).

    Returns:
        ``PresentValueInstrument`` instances in PV_Base / Input 4 order.
    """
    # Local import avoids a package cycle with ``lic_dsf_pv.__init__``.
    from lic_dsf.pv import PresentValueInstrument

    path = Path(workbook_path)
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        worksheet = workbook[sheet_name]
        columns, years = _year_columns(worksheet)
        instruments: list[PresentValueInstrument] = []

        for row in _PV_BASE_INPUT4_ROWS:
            raw_name = worksheet.cell(row, _NAME_COL).value
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue

            discount = _as_float(worksheet.cell(row, _DISCOUNT_COL).value)
            interest = _as_float(worksheet.cell(row, _INTEREST_COL).value)
            grace = _as_int(worksheet.cell(row, _GRACE_COL).value)
            maturity = _as_int(worksheet.cell(row, _MATURITY_COL).value)
            if (
                discount is None
                or interest is None
                or grace is None
                or maturity is None
                or maturity <= grace
            ):
                continue

            disbursements = _read_disbursements(worksheet, row, columns)
            if not include_zero_disbursement and sum(disbursements) == 0.0:
                continue

            instruments.append(
                PresentValueInstrument(
                    name=_instrument_name(raw_name.strip(), row),
                    grace=grace,
                    maturity=maturity,
                    interest_rate=interest,
                    discount_rate=discount,
                    disbursements=disbursements,
                    years=years,
                )
            )
    finally:
        workbook.close()

    return instruments


# LC-NR tenor specs: (name_row, terms_row, rate_row, disbursement_row)
_LC_NR_TENORS: tuple[tuple[int, int, int, int], ...] = (
    (31, 16, 31, 104),  # Bonds (1 to 3 years)-LC → PV_LC_NR1
    (32, 17, 32, 105),  # Bonds (4 to 7 years)-LC → PV_LC_NR2
    (33, 18, 33, 106),  # Bonds (beyond 7 years)-LC → PV_LC_NR3
)

_INPUT5_SHEET = "Input 5 - Local-debt Financing"
_MACRO_DEBT_SHEET = "Macro-Debt_Data"
_INPUT1_SHEET = "Input 1 - Basics"
_INPUT5_YEAR_ROW = 5
_INPUT5_FIRST_YEAR_COL = 9  # column I
_MACRO_FX_PA_ROW = 60
_MACRO_FX_EOP_ROW = 59
_MACRO_YEAR_2024_COL = 21  # column U
_INPUT1_DISCOUNT_CELL = (25, 3)  # C25


def load_lc_nr_instruments_from_workbook(
    workbook_path: str | Path,
    *,
    include_zero_disbursement: bool = True,
) -> list[LocalCurrencyNonResidentInstrument]:
    """Load the three PV_LC_NR tenors from Input 5 + Macro-Debt FX.

    Disbursements are the Input 5 local-currency financing rows (which Ext_Debt
    converts to USD and PV_LC_NR converts back via FX(pa)). FX(pa)/FX(eop) come
    from ``Macro-Debt_Data`` rows 60/59 starting at the 2024 column; the
    instrument then extends past Macro with the last FX growth factor so late
    vintages can run off (matching ``PV_LC_NR*``). Discount rate comes from
    ``Input 1 - Basics``!C25.

    Args:
        workbook_path: Path to the LIC-DSF ``.xlsx`` workbook.
        include_zero_disbursement: When False, drop tenors with zero LC flows.

    Returns:
        Up to three ``LocalCurrencyNonResidentInstrument`` instances.
    """
    from lic_dsf.pv.lc_nr import LocalCurrencyNonResidentInstrument

    path = Path(workbook_path)
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        input5 = workbook[_INPUT5_SHEET]
        macro = workbook[_MACRO_DEBT_SHEET]
        input1 = workbook[_INPUT1_SHEET]

        year_cols: list[int] = []
        years: list[int] = []
        col = _INPUT5_FIRST_YEAR_COL
        while True:
            raw = input5.cell(_INPUT5_YEAR_ROW, col).value
            year = _as_int(raw)
            if year is None:
                break
            year_cols.append(col)
            years.append(year)
            col += 1
        if not year_cols:
            raise ValueError(
                f"{_INPUT5_SHEET} has no year headers from column "
                f"{_INPUT5_FIRST_YEAR_COL}"
            )

        fx_pa: list[float] = []
        fx_eop: list[float] = []
        for offset, _year in enumerate(years):
            macro_col = _MACRO_YEAR_2024_COL + offset
            pa = _as_float(macro.cell(_MACRO_FX_PA_ROW, macro_col).value)
            eop = _as_float(macro.cell(_MACRO_FX_EOP_ROW, macro_col).value)
            if pa is None or eop is None or pa == 0.0 or eop == 0.0:
                # Truncate to years with FX coverage.
                year_cols = year_cols[:offset]
                years = years[:offset]
                break
            fx_pa.append(pa)
            fx_eop.append(eop)

        discount = _as_float(
            input1.cell(_INPUT1_DISCOUNT_CELL[0], _INPUT1_DISCOUNT_CELL[1]).value
        )
        if discount is None:
            raise ValueError("Input 1 - Basics!C25 discount rate is missing")

        instruments: list[LocalCurrencyNonResidentInstrument] = []
        for name_row, terms_row, rate_row, disb_row in _LC_NR_TENORS:
            raw_name = input5.cell(name_row, 1).value
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            grace = _as_int(input5.cell(terms_row, 3).value)
            maturity = _as_int(input5.cell(terms_row, 4).value)
            if grace is None or maturity is None or maturity <= grace:
                continue

            rates: list[float] = []
            disbursements: list[float] = []
            for year_col in year_cols:
                rate = _as_float(input5.cell(rate_row, year_col).value)
                disb = _as_float(input5.cell(disb_row, year_col).value)
                rates.append(0.0 if rate is None else rate)
                disbursements.append(0.0 if disb is None else disb)

            if not include_zero_disbursement and sum(disbursements) == 0.0:
                continue

            instruments.append(
                LocalCurrencyNonResidentInstrument(
                    name=raw_name.strip(),
                    grace=grace,
                    maturity=maturity,
                    discount_rate=discount,
                    interest_rates=rates,
                    disbursements_lc=disbursements,
                    fx_pa=fx_pa[: len(year_cols)],
                    fx_eop=fx_eop[: len(year_cols)],
                    years=tuple(years),
                )
            )
    finally:
        workbook.close()

    return instruments
