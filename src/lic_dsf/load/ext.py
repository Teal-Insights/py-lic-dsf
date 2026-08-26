"""Load ``ExternalDebtInputs`` from the LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.pv.external_debt.fxutil import lc_to_usd, sum_rows_lc
from lic_dsf.pv.external_debt.types import ExternalDebtInputs

_INPUT1 = "Input 1 - Basics"
_INPUT3 = "Input 3 - Macro-Debt data(DMX)"
_INPUT4 = "Input 4 - External Financing"
_INPUT5 = "Input 5 - Local-debt Financing"
_INPUT8 = "Input 8 - SDR"
_MACRO = "Macro-Debt_Data"
_EXT = "Ext_Debt_Data"
_LOOKUP = "lookup"
_INPUT1_CONCESSIONALITY_CELL = (15, 3)  # C15

# (Input 4 terms row, Input 3 existing-service row)
_EXISTING_CREDITOR_ROWS: tuple[tuple[int, int], ...] = (
    (10, 65),
    (11, 66),
    (12, 67),
    (13, 68),
    (18, 69),
    (19, 70),
    (21, 72),
    (22, 73),
    (23, 74),
    (26, 77),
    (27, 78),
    (28, 79),
    (29, 80),
    (30, 81),
    (32, 83),
    (33, 84),
    (34, 85),
    (35, 86),
    (36, 87),
    (38, 89),
    (39, 90),
    (40, 91),
    (41, 92),
    (42, 93),
)

_INPUT3_FIRST_YEAR_COL = 23  # column W → first Ext year (2023 in template)
_INPUT3_YEAR_ROW = 7
_INPUT3_PRINCIPAL_ROW = 95
_INPUT3_ARREARS_ROW = 55
_INPUT3_ST_ROW = 52
_INPUT4_NAME_COL = 2
_INPUT4_DISCOUNT_COL = 5
_INPUT4_ST_RATE_CELL = (45, 6)  # F45
_INPUT5_YEAR_ROW = 5
_INPUT5_FIRST_YEAR_COL = 8  # column H
# Residency-based Input 5 rows (Ext C120 == lookup!X4).
_I5_STOCK_RES = (166, 167)
_I5_PRINCIPAL_RES = (156, 157)
_I5_INTEREST_RES = (147, 148)
_I5_ST_RES = (191, 193)
_I5_ST_PRINCIPAL_RES = (191, 193)
_I5_ST_INTEREST_RES = (180, 182)
# Aggregate (non-residency) fallbacks.
_I5_STOCK_AGG = (163,)
_I5_PRINCIPAL_AGG = (153,)
_I5_SERVICE_AGG = (145, 153)
_I5_ST_AGG = (188,)
_I5_ST_PRINCIPAL_AGG = (188,)
_I5_ST_INTEREST_AGG = (177,)
_I5_DOM_MLT_DISB = 123
_I5_DOM_ST_DISB = 122
# Input 4 F/G/H terms Ext uses for LC-NR residual SUMPRODUCT (R131–R133).
_INPUT4_LC_NR_RESIDUAL_TERM_ROWS: tuple[int, ...] = (49, 50, 51)
# Input 4 rows in Ext R408 GE numerator (always). Skips IDA NEW 14–17.
_INPUT4_GE_CORE_ROWS: tuple[int, ...] = (
    10,
    11,
    12,
    13,
    18,
    19,
    21,
    22,
    23,
    26,
    27,
    28,
    29,
    30,
    32,
    33,
    34,
    35,
    36,
    38,
    39,
    40,
    41,
    42,
)
_INPUT4_GE_LC_NR_ROWS: tuple[int, ...] = (49, 50, 51)
_INPUT4_GE_FX_NR_ROWS: tuple[int, ...] = (54, 55, 56)
_INPUT4_GE_FX_RES_ROWS: tuple[int, ...] = (59, 60, 61)
_MACRO_PPG_ROW = 8
_MACRO_MLT_ROW = 9
_MACRO_FX_EOP_ROW = 59
_MACRO_FX_PA_ROW = 60
_MACRO_YEAR_2023_COL = 20  # column T
_INPUT8_YEAR_ROW = 9
_INPUT8_FIRST_YEAR_COL = 3  # column C = first projection year
_INPUT8_PV_ROW = 24
_INPUT8_INTEREST_ROW = 17
_EXT_RESIDENCY_CELL = (120, 3)  # C120
_LOOKUP_RESIDENCY_CELL = (4, 24)  # X4
_EXT_R399_ROW = 399
_EXT_YEAR_ROW = 1
_EXT_FIRST_YEAR_COL = 5


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


def _align_series(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).fillna(0.0).astype(float)


def _sum_input5_rows(
    input5: Any,
    rows: tuple[int, ...],
    columns: tuple[int, ...],
    years: tuple[int, ...],
) -> pd.Series:
    return sum_rows_lc([_series_from_row(input5, row, columns, years) for row in rows])


def load_external_debt_inputs(
    workbook_path: str | Path,
) -> ExternalDebtInputs:
    """Load existing-debt schedules and Ext headline inputs from the template.

    Reads Input 3 service / principal / arrears / ST, Input 4 discount rates and
    ST interest rate, Input 5 locally-issued stock / service / ST /
    disbursements (LC→USD via Macro FX), Input 8 SDR PV and interest, and
    Macro-Debt PPG / MLT stocks plus FX(eop)/FX(pa).
    """
    path = Path(workbook_path)
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        input3 = workbook[_INPUT3]
        input4 = workbook[_INPUT4]
        input5 = workbook[_INPUT5]
        input8 = workbook[_INPUT8]
        macro = workbook[_MACRO]
        ext = workbook[_EXT]
        lookup = workbook[_LOOKUP]

        i3_cols, years = _year_columns(input3, _INPUT3_YEAR_ROW, _INPUT3_FIRST_YEAR_COL)

        service_rows: dict[str, pd.Series] = {}
        discounts: dict[str, float] = {}
        for input4_row, input3_row in _EXISTING_CREDITOR_ROWS:
            raw_name = input4.cell(input4_row, _INPUT4_NAME_COL).value
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            name = raw_name.strip()
            discount = _as_float(input4.cell(input4_row, _INPUT4_DISCOUNT_COL).value)
            if discount is None:
                continue
            service_rows[name] = _series_from_row(input3, input3_row, i3_cols, years)
            discounts[name] = discount

        if not service_rows:
            raise ValueError("no existing-debt creditors found in Input 3 / 4")

        existing_debt_service = pd.DataFrame(service_rows).T
        existing_debt_service = existing_debt_service.reindex(columns=list(years))

        existing_principal = _series_from_row(
            input3, _INPUT3_PRINCIPAL_ROW, i3_cols, years
        )
        arrears = _series_from_row(input3, _INPUT3_ARREARS_ROW, i3_cols, years)
        short_term = _series_from_row(input3, _INPUT3_ST_ROW, i3_cols, years)

        st_rate = _as_float(
            input4.cell(_INPUT4_ST_RATE_CELL[0], _INPUT4_ST_RATE_CELL[1]).value
        )
        if st_rate is None:
            st_rate = 0.0

        macro_cols = tuple(
            _MACRO_YEAR_2023_COL + offset for offset in range(len(years))
        )
        macro_ppg = _series_from_row(macro, _MACRO_PPG_ROW, macro_cols, years)
        macro_mlt = _series_from_row(macro, _MACRO_MLT_ROW, macro_cols, years)
        fx_eop = _align_series(
            _series_from_row(macro, _MACRO_FX_EOP_ROW, macro_cols, years), years
        )
        fx_pa = _align_series(
            _series_from_row(macro, _MACRO_FX_PA_ROW, macro_cols, years), years
        )

        i5_cols, i5_years = _year_columns(
            input5, _INPUT5_YEAR_ROW, _INPUT5_FIRST_YEAR_COL
        )
        residency_based = (
            ext.cell(_EXT_RESIDENCY_CELL[0], _EXT_RESIDENCY_CELL[1]).value
            == lookup.cell(_LOOKUP_RESIDENCY_CELL[0], _LOOKUP_RESIDENCY_CELL[1]).value
        )

        if residency_based:
            stock_lc = _sum_input5_rows(input5, _I5_STOCK_RES, i5_cols, i5_years)
            principal_lc = _sum_input5_rows(
                input5, _I5_PRINCIPAL_RES, i5_cols, i5_years
            )
            interest_lc = _sum_input5_rows(input5, _I5_INTEREST_RES, i5_cols, i5_years)
            st_lc = _sum_input5_rows(input5, _I5_ST_RES, i5_cols, i5_years)
            st_prin_lc = _sum_input5_rows(
                input5, _I5_ST_PRINCIPAL_RES, i5_cols, i5_years
            )
            st_int_lc = _sum_input5_rows(input5, _I5_ST_INTEREST_RES, i5_cols, i5_years)
        else:
            stock_lc = _sum_input5_rows(input5, _I5_STOCK_AGG, i5_cols, i5_years)
            principal_lc = _sum_input5_rows(
                input5, _I5_PRINCIPAL_AGG, i5_cols, i5_years
            )
            service_lc = _sum_input5_rows(input5, _I5_SERVICE_AGG, i5_cols, i5_years)
            interest_lc = service_lc.sub(principal_lc, fill_value=0.0)
            st_lc = _sum_input5_rows(input5, _I5_ST_AGG, i5_cols, i5_years)
            st_prin_lc = _sum_input5_rows(
                input5, _I5_ST_PRINCIPAL_AGG, i5_cols, i5_years
            )
            st_int_lc = _sum_input5_rows(input5, _I5_ST_INTEREST_AGG, i5_cols, i5_years)

        local_stock = _align_series(lc_to_usd(stock_lc, fx_eop), years)
        local_principal = _align_series(lc_to_usd(principal_lc, fx_pa), years)
        local_interest = _align_series(lc_to_usd(interest_lc, fx_pa), years)
        local_st = _align_series(lc_to_usd(st_lc, fx_eop), years)
        # Ext ST principal/interest use same-year FX(pa) on the ST LC stock rows
        # for most projection columns (template local ST is often zero).
        local_st_principal = _align_series(lc_to_usd(st_prin_lc, fx_pa), years)
        local_st_interest = _align_series(lc_to_usd(st_int_lc, fx_pa), years)

        dom_mlt = _align_series(
            lc_to_usd(
                _series_from_row(input5, _I5_DOM_MLT_DISB, i5_cols, i5_years),
                fx_pa,
            ),
            years,
        )
        dom_st = _align_series(
            lc_to_usd(
                _series_from_row(input5, _I5_DOM_ST_DISB, i5_cols, i5_years),
                fx_pa,
            ),
            years,
        )

        i8_cols, i8_years = _year_columns(
            input8, _INPUT8_YEAR_ROW, _INPUT8_FIRST_YEAR_COL
        )
        sdr_pv = _align_series(
            _series_from_row(input8, _INPUT8_PV_ROW, i8_cols, i8_years), years
        )
        prior_pv = _as_float(input8.cell(_INPUT8_PV_ROW, 2).value)
        if prior_pv is not None and years:
            sdr_pv.loc[years[0]] = prior_pv
        sdr_interest = _align_series(
            _series_from_row(input8, _INPUT8_INTEREST_ROW, i8_cols, i8_years),
            years,
        )
        prior_interest = _as_float(input8.cell(_INPUT8_INTEREST_ROW, 2).value)
        if prior_interest is not None and years:
            sdr_interest.loc[years[0]] = prior_interest

        residual_interest_rates: dict[str, float] = {}
        for row in _INPUT4_LC_NR_RESIDUAL_TERM_ROWS:
            raw_name = input4.cell(row, _INPUT4_NAME_COL).value
            rate = _as_float(input4.cell(row, 6).value)
            if isinstance(raw_name, str) and raw_name.strip() and rate is not None:
                residual_interest_rates[raw_name.strip()] = rate

        # Match Ext R408 residency branch for which local/FX bands enter GE.
        ge_rows = list(_INPUT4_GE_CORE_ROWS) + list(_INPUT4_GE_FX_NR_ROWS)
        if residency_based:
            ge_rows.extend(_INPUT4_GE_LC_NR_ROWS)
        else:
            ge_rows.extend(_INPUT4_GE_FX_RES_ROWS)
        grant_element_weight_names: set[str] = set()
        for row in ge_rows:
            raw_name = input4.cell(row, _INPUT4_NAME_COL).value
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            base = raw_name.strip()
            if row in _INPUT4_GE_FX_NR_ROWS:
                grant_element_weight_names.add(f"{base} (non-residents)")
            elif row in _INPUT4_GE_FX_RES_ROWS:
                grant_element_weight_names.add(f"{base} (residents)")
            else:
                grant_element_weight_names.add(base)

        # Ext R399: FX-denominated debt outstanding (used as Macro R83 in projection)
        ext_year_cols, ext_years = _year_columns(
            ext, _EXT_YEAR_ROW, _EXT_FIRST_YEAR_COL
        )
        fx_denom = _align_series(
            _series_from_row(ext, _EXT_R399_ROW, ext_year_cols, ext_years), years
        )

        input1 = workbook[_INPUT1]
        concessionality = _as_float(
            input1.cell(*_INPUT1_CONCESSIONALITY_CELL).value
        )
        if concessionality is None:
            concessionality = 0.35

        return ExternalDebtInputs(
            years=years,
            existing_debt_service=existing_debt_service.fillna(0.0),
            existing_principal=_align_series(existing_principal, years),
            existing_discount_rates=discounts,
            arrears=_align_series(arrears, years),
            short_term_external=_align_series(short_term, years),
            sdr_pv=sdr_pv,
            sdr_interest=sdr_interest,
            macro_ppg_external=_align_series(macro_ppg, years),
            macro_mlt_external=_align_series(macro_mlt, years),
            fx_eop=fx_eop,
            fx_pa=fx_pa,
            locally_issued_debt_stock=local_stock,
            locally_issued_principal=local_principal,
            locally_issued_interest=local_interest,
            locally_issued_st=local_st,
            locally_issued_st_principal=local_st_principal,
            locally_issued_st_interest=local_st_interest,
            domestic_mlt_disbursements_usd=dom_mlt,
            domestic_st_disbursements_usd=dom_st,
            short_term_interest_rate=float(st_rate),
            residual_interest_rates=residual_interest_rates,
            grant_element_weight_names=frozenset(grant_element_weight_names),
            fx_denominated_outstanding=fx_denom,
            concessionality_threshold=float(concessionality),
        )
    finally:
        workbook.close()
