"""Load ``MacroDebtInputs`` from the LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.pv.macro_debt.types import MacroDebtInputs

_INPUT1 = "Input 1 - Basics"
_INPUT3 = "Input 3 - Macro-Debt data(DMX)"
_INPUT5 = "Input 5 - Local-debt Financing"
_MACRO = "Macro-Debt_Data"

_INPUT1_FIRST_PROJ_CELL = (18, 3)  # C18
_MACRO_YEAR_ROW = 5
_MACRO_FIRST_YEAR_COL = 8  # H → 2011
_INPUT3_YEAR_ROW = 7
_INPUT3_FIRST_YEAR_COL = 11  # K → 2011
_INPUT5_YEAR_ROW = 5
_INPUT5_FIRST_YEAR_COL = 8  # H → first year (2023 in template)

# Input 3 rows mirrored by Macro pass-through / hist formulas.
_I3_GDP_USD = 12
_I3_GDP_CONSTANT = 13
_I3_FOREIGN_DEFLATOR = 18
_I3_FX_EOP = 19
_I3_FX_PA = 20
_I3_CA = 34
_I3_EXPORTS = 35
_I3_IMPORTS = 38
_I3_TRANSFERS_NET = 41
_I3_TRANSFERS_OFFICIAL = 42
_I3_FDI = 43
_I3_EXCEPTIONAL = 44
_I3_RESERVES = 46
_I3_REVENUES = 22
_I3_GRANTS = 23
_I3_PRIVATIZATION = 27
_I3_PRIMARY_EXP = 24
_I3_ASSETS = 25
_I3_CONTINGENT = 28
_I3_OTHER_FLOWS = 30
_I3_DEBT_RELIEF = 29
_I3_MLT_EXT = 51
_I3_MLT_EXT_ADD = 209
_I3_ST_EXT = 52
_I3_ST_EXT_ADD = 210
_I3_PRIVATE_MLT = 57
_I3_PRIVATE_ST = 58
_I3_DOM_MLT = 191
_I3_DOM_ST = 192
_I3_PPG_INTEREST = 53
_I3_PPG_INTEREST_ADD = 211
_I3_PRIVATE_INTEREST = 59
_I3_DOM_INTEREST = 193
_I3_PPG_AMORT = 54
_I3_PPG_AMORT_ADD = 212
_I3_PRIVATE_AMORT = 60
_I3_DOM_AMORT = 195
_I3_CONCESSIONAL = 32
_I3_FC_PUBLIC_DEBT = 214

# Input 5 projection rows Macro uses from first projection year.
_I5_PUBLIC_GFN = 56
_I5_DOM_MLT = 212
_I5_DOM_ST = 213
_I5_DOM_INTEREST_LCU = 214
_I5_DOM_PRINCIPAL_LCU = 215


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


def _year_columns(
    worksheet: Any, header_row: int, first_col: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    columns: list[int] = []
    years: list[int] = []
    col = first_col
    while True:
        year = _as_int(worksheet.cell(header_row, col).value)
        if year is None:
            break
        columns.append(col)
        years.append(year)
        col += 1
    if not columns:
        raise ValueError(
            f"{worksheet.title} has no year headers from column {first_col}"
        )
    return tuple(columns), tuple(years)


def _series_from_row(
    worksheet: Any,
    row: int,
    columns: tuple[int, ...],
    years: tuple[int, ...],
) -> pd.Series:
    values: dict[int, float] = {}
    for col, year in zip(columns, years, strict=True):
        number = _as_float(worksheet.cell(row, col).value)
        values[year] = 0.0 if number is None else number
    return pd.Series(values, dtype=float)


def _align(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).fillna(0.0).astype(float)


def _sum_rows(
    worksheet: Any,
    rows: tuple[int, ...],
    columns: tuple[int, ...],
    years: tuple[int, ...],
) -> pd.Series:
    total = pd.Series(0.0, index=list(years), dtype=float)
    for row in rows:
        total = total + _align(_series_from_row(worksheet, row, columns, years), years)
    return total


def load_macro_debt_inputs(workbook_path: str | Path) -> MacroDebtInputs:
    """Load Input 3 / Input 5 series for Macro-Debt_Data.

    Uses cached workbook values (``data_only=True``). Macro year headers are
    the canonical horizon; Input 3 / Input 5 series are reindexed onto them.
    """
    path = Path(workbook_path)
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        macro = workbook[_MACRO]
        input1 = workbook[_INPUT1]
        input3 = workbook[_INPUT3]
        input5 = workbook[_INPUT5]

        _macro_cols, years = _year_columns(
            macro, _MACRO_YEAR_ROW, _MACRO_FIRST_YEAR_COL
        )
        first_proj = _as_int(input1.cell(*_INPUT1_FIRST_PROJ_CELL).value)
        if first_proj is None:
            raise ValueError("Input 1 - Basics!C18 has no first projection year")

        i3_cols, i3_years = _year_columns(
            input3, _INPUT3_YEAR_ROW, _INPUT3_FIRST_YEAR_COL
        )
        i5_cols, i5_years = _year_columns(
            input5, _INPUT5_YEAR_ROW, _INPUT5_FIRST_YEAR_COL
        )

        def i3(row: int) -> pd.Series:
            return _align(_series_from_row(input3, row, i3_cols, i3_years), years)

        def i3_sum(*rows: int) -> pd.Series:
            return (
                _sum_rows(input3, rows, i3_cols, i3_years)
                .reindex(list(years))
                .fillna(0.0)
            )

        def i5(row: int) -> pd.Series:
            return _align(_series_from_row(input5, row, i5_cols, i5_years), years)

        return MacroDebtInputs(
            years=years,
            first_projection_year=first_proj,
            gdp_usd=i3(_I3_GDP_USD),
            gdp_constant=i3(_I3_GDP_CONSTANT),
            fx_eop=i3(_I3_FX_EOP),
            fx_pa=i3(_I3_FX_PA),
            foreign_gdp_deflator=i3(_I3_FOREIGN_DEFLATOR),
            fc_public_debt_usd=i3(_I3_FC_PUBLIC_DEBT),
            current_account=i3(_I3_CA),
            exports=i3(_I3_EXPORTS),
            imports=i3(_I3_IMPORTS),
            current_transfers_net=i3(_I3_TRANSFERS_NET),
            current_transfers_official=i3(_I3_TRANSFERS_OFFICIAL),
            fdi=i3(_I3_FDI),
            exceptional_financing=i3(_I3_EXCEPTIONAL),
            reserves_flow=i3(_I3_RESERVES),
            revenues_incl_grants=i3(_I3_REVENUES),
            grants=i3(_I3_GRANTS),
            privatization=i3(_I3_PRIVATIZATION),
            primary_expenditure=i3(_I3_PRIMARY_EXP),
            public_assets=i3(_I3_ASSETS),
            contingent_liabilities=i3(_I3_CONTINGENT),
            other_debt_creating_flows=i3(_I3_OTHER_FLOWS),
            debt_relief=i3(_I3_DEBT_RELIEF),
            mlt_external=i3_sum(_I3_MLT_EXT, _I3_MLT_EXT_ADD),
            short_term_external=i3_sum(_I3_ST_EXT, _I3_ST_EXT_ADD),
            private_mlt_external=i3(_I3_PRIVATE_MLT),
            private_st_external=i3(_I3_PRIVATE_ST),
            domestic_mlt=i3(_I3_DOM_MLT),
            domestic_st=i3(_I3_DOM_ST),
            ppg_interest=i3_sum(_I3_PPG_INTEREST, _I3_PPG_INTEREST_ADD),
            private_interest=i3(_I3_PRIVATE_INTEREST),
            domestic_interest=i3(_I3_DOM_INTEREST),
            ppg_amortization=i3_sum(_I3_PPG_AMORT, _I3_PPG_AMORT_ADD),
            private_amortization=i3(_I3_PRIVATE_AMORT),
            domestic_amortization=i3(_I3_DOM_AMORT),
            concessional_loans=i3(_I3_CONCESSIONAL),
            domestic_mlt_input5=i5(_I5_DOM_MLT),
            domestic_st_input5=i5(_I5_DOM_ST),
            domestic_interest_lcu_input5=i5(_I5_DOM_INTEREST_LCU),
            domestic_principal_lcu_input5=i5(_I5_DOM_PRINCIPAL_LCU),
            public_gfn_input5=i5(_I5_PUBLIC_GFN),
        )
    finally:
        workbook.close()
