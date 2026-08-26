"""Load ``DomesticDebtInputs`` from the LIC-DSF workbook."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.pv.domestic_debt.types import (
    DEFAULT_PEER_MEDIAN_DEBT_TO_GDP,
    DEFAULT_PEER_MEDIAN_DS_TO_REVENUES,
    DomesticDebtInputs,
)

if TYPE_CHECKING:
    from lic_dsf.dsa.baseline.external import BaselineExternalBook
    from lic_dsf.dsa.baseline.public import BaselinePublicBook
    from lic_dsf.pv.macro_debt.book import MacroDebtBook

_INPUT1 = "Input 1 - Basics"
_INPUT7 = "Input 7 - Residual Financing"
_MACRO = "Macro-Debt_Data"
_BASELINE_PUBLIC = "Baseline - public"
_BASELINE_EXTERNAL = "Baseline - external"
_DOM_DATA = "Dom_Debt_Data"

_DOM_YEAR_ROW = 7
_DOM_FIRST_YEAR_COL = 4  # column D = 2013 in template
_INPUT1_FIRST_PROJ_CELL = (18, 3)  # C18

_BASELINE_PUBLIC_YEAR_ROW = 7
_BASELINE_PUBLIC_FIRST_YEAR_COL = 4
_BASELINE_PUBLIC_DEBT_ROW = 12
_BASELINE_PUBLIC_PPG_EXT_ROW = 20
_BASELINE_PUBLIC_DS_REV_ROW = 45

_BASELINE_EXTERNAL_YEAR_ROW = 8
_BASELINE_EXTERNAL_FIRST_YEAR_COL = 3
_BASELINE_EXTERNAL_PPG_DS_ROW = 40

_MACRO_YEAR_ROW = 5
_MACRO_FIRST_YEAR_COL = 8  # column H = 2011 in template
_MACRO_REVENUES_ROW = 45
_MACRO_GRANTS_ROW = 46
_MACRO_DOMESTIC_DEBT_ROW = 14
_MACRO_DOMESTIC_INTEREST_ROW = 21
_MACRO_GDP_USD_ROW = 56
_MACRO_FX_PA_ROW = 60

# Input 7 display cells used by Dom_Debt_Indicators.
_I7_DOM_MLT_SHARE = (10, 8)  # H10 = Ext C127
_I7_DOM_ST_SHARE = (11, 8)  # H11 = Ext C128
_I7_MLT_INTEREST = (19, 8)  # H19
_I7_MLT_MATURITY = (20, 8)  # H20
_I7_MLT_GRACE = (21, 8)  # H21
_I7_ST_INTEREST = (23, 8)  # H23


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
        values[year] = float("nan") if number is None else number
    return pd.Series(values, dtype=float)


def _align_series(series: pd.Series, years: tuple[int, ...]) -> pd.Series:
    return series.reindex(list(years)).astype(float)


def _cell_float(worksheet: Any, row: int, col: int, default: float = 0.0) -> float:
    number = _as_float(worksheet.cell(row, col).value)
    return default if number is None else number


def load_domestic_debt_inputs(
    workbook_path: str | Path,
    *,
    macro_book: MacroDebtBook | None = None,
    baseline_public: BaselinePublicBook | None = None,
    baseline_external: BaselineExternalBook | None = None,
) -> DomesticDebtInputs:
    """Load Baseline/Macro/Input 7 series for Dom_Debt indicator math.

    Uses cached workbook values (``data_only=True``). Dom year headers are the
    canonical horizon; Baseline and Macro series are reindexed onto them.

    When ``macro_book`` is provided, Macro-sourced Dom fields come from
    ``macro_book.as_domestic_macro_fields()`` instead of the Macro sheet.
    When ``baseline_public`` / ``baseline_external`` are provided, Dom Baseline
    ratio fields come from those books instead of Baseline sheet VLOOKUPs.
    """
    path = Path(workbook_path)
    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        dom = workbook[_DOM_DATA]
        input1 = workbook[_INPUT1]
        input7 = workbook[_INPUT7]
        macro = workbook[_MACRO]
        baseline_public_ws = workbook[_BASELINE_PUBLIC]
        baseline_external_ws = workbook[_BASELINE_EXTERNAL]

        _dom_cols, years = _year_columns(dom, _DOM_YEAR_ROW, _DOM_FIRST_YEAR_COL)
        first_proj = _as_int(input1.cell(*_INPUT1_FIRST_PROJ_CELL).value)
        if first_proj is None:
            raise ValueError("Input 1 - Basics!C18 has no first projection year")

        if baseline_public is not None:
            public_debt = baseline_public.public_sector_debt_to_gdp()
            ppg_ext = baseline_public.ppg_external_debt_to_gdp()
            public_ds = baseline_public.debt_service_to_revenue_grants()
        else:
            bp_cols, bp_years = _year_columns(
                baseline_public_ws,
                _BASELINE_PUBLIC_YEAR_ROW,
                _BASELINE_PUBLIC_FIRST_YEAR_COL,
            )
            public_debt = _series_from_row(
                baseline_public_ws, _BASELINE_PUBLIC_DEBT_ROW, bp_cols, bp_years
            )
            ppg_ext = _series_from_row(
                baseline_public_ws, _BASELINE_PUBLIC_PPG_EXT_ROW, bp_cols, bp_years
            )
            public_ds = _series_from_row(
                baseline_public_ws, _BASELINE_PUBLIC_DS_REV_ROW, bp_cols, bp_years
            )

        if baseline_external is not None:
            ppg_ds = baseline_external.ppg_debt_service_to_revenue()
        else:
            be_cols, be_years = _year_columns(
                baseline_external_ws,
                _BASELINE_EXTERNAL_YEAR_ROW,
                _BASELINE_EXTERNAL_FIRST_YEAR_COL,
            )
            ppg_ds = _series_from_row(
                baseline_external_ws,
                _BASELINE_EXTERNAL_PPG_DS_ROW,
                be_cols,
                be_years,
            )

        if macro_book is not None:
            fields = macro_book.as_domestic_macro_fields()
            revenues = fields["revenues_incl_grants"]
            grants = fields["grants"]
            domestic_stock = fields["domestic_debt_stock"]
            domestic_interest = fields["domestic_interest_due"]
            gdp_usd = fields["gdp_usd"]
            fx_pa = fields["fx_pa"]
        else:
            macro_cols, macro_years = _year_columns(
                macro, _MACRO_YEAR_ROW, _MACRO_FIRST_YEAR_COL
            )
            revenues = _series_from_row(
                macro, _MACRO_REVENUES_ROW, macro_cols, macro_years
            )
            grants = _series_from_row(macro, _MACRO_GRANTS_ROW, macro_cols, macro_years)
            domestic_stock = _series_from_row(
                macro, _MACRO_DOMESTIC_DEBT_ROW, macro_cols, macro_years
            )
            domestic_interest = _series_from_row(
                macro, _MACRO_DOMESTIC_INTEREST_ROW, macro_cols, macro_years
            )
            gdp_usd = _series_from_row(
                macro, _MACRO_GDP_USD_ROW, macro_cols, macro_years
            )
            fx_pa = _series_from_row(macro, _MACRO_FX_PA_ROW, macro_cols, macro_years)

        zero = pd.Series(0.0, index=list(years), dtype=float)

        # Peer medians: prefer Dom_Debt_Data cached D14/D22 when present.
        peer_debt = _cell_float(
            dom, 14, _DOM_FIRST_YEAR_COL, DEFAULT_PEER_MEDIAN_DEBT_TO_GDP
        )
        peer_ds = _cell_float(
            dom, 22, _DOM_FIRST_YEAR_COL, DEFAULT_PEER_MEDIAN_DS_TO_REVENUES
        )

        return DomesticDebtInputs(
            years=years,
            first_projection_year=first_proj,
            public_sector_debt_pct_gdp=_align_series(public_debt, years),
            ppg_external_debt_pct_gdp=_align_series(ppg_ext, years),
            public_ds_to_revenue_grants=_align_series(public_ds, years),
            ppg_ds_to_revenue=_align_series(ppg_ds, years),
            revenues_incl_grants=_align_series(revenues, years),
            grants=_align_series(grants, years),
            domestic_debt_stock=_align_series(domestic_stock, years),
            domestic_interest_due=_align_series(domestic_interest, years),
            gdp_usd=_align_series(gdp_usd, years),
            fx_pa=_align_series(fx_pa, years),
            fx_denominated_domestic_stock=zero.copy(),
            fx_denominated_domestic_interest=zero.copy(),
            peer_median_debt_to_gdp=peer_debt,
            peer_median_ds_to_revenues=peer_ds,
            residual_domestic_mlt_share=_cell_float(input7, *_I7_DOM_MLT_SHARE),
            residual_domestic_st_share=_cell_float(input7, *_I7_DOM_ST_SHARE),
            domestic_mlt_avg_interest=_cell_float(input7, *_I7_MLT_INTEREST),
            domestic_mlt_avg_maturity=_cell_float(input7, *_I7_MLT_MATURITY),
            domestic_mlt_avg_grace=_cell_float(input7, *_I7_MLT_GRACE),
            domestic_st_avg_interest=_cell_float(input7, *_I7_ST_INTEREST),
        )
    finally:
        workbook.close()
