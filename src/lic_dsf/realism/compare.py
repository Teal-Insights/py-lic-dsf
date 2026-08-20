"""Excel vs Python comparison for Realism 1 (Forecast Error)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastpyxl import load_workbook

from lic_dsf.dsa import load_core
from lic_dsf.realism.forecast_error import (
    GdpRebaseMode,
    debt_creating_flow_panel,
    debt_stock_from_ratio,
    forecast_error,
    gdp_rebase_scale,
    other_identified_flows_to_gdp,
    public_automatic_debt_dynamics,
    rebase_ratio_to_outturn_gdp,
    total_external_to_gdp,
)
from lic_dsf.realism.imported import ImportedDataCatalog, load_imported_data
from lic_dsf.realism.panels import forecast_error_panel

REALISM1_SHEET = "Realism 1 - Forecast Error"
_YEAR_HEADER_ROW = 11
_FIRST_YEAR_COL = 8

_DOMAIN_HEADERS = {
    "external debt": "External",
    "public debt": "Public",
}
_BLOCK_HEADERS = {
    "current vintage": "Current vintage",
    "5 years ago": "5 years ago",
    "5 years ago (re-based)": "5 years ago (re-based)",
    "last vintage": "Last vintage",
    "last vintage (re-based)": "Last vintage (re-based)",
}


def _norm_header(value: object) -> str:
    return str(value or "").strip().lower()


def _a1(row: int, col: int) -> str:
    letters = ""
    n = col
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row}"


def _year_int(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value))


def _as_year(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    year = int(value)
    if 1990 <= year <= 2100:
        return year
    return None


def _year_cols(ws) -> dict[int, int]:
    cols: dict[int, int] = {}
    for col in range(_FIRST_YEAR_COL, (ws.max_column or _FIRST_YEAR_COL) + 1):
        year = _as_year(ws.cell(_YEAR_HEADER_ROW, col).value)
        if year is not None:
            cols[year] = col
    return cols


def _read_realism1_rows(path: Path) -> pd.DataFrame:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[REALISM1_SHEET]
        year_cols = _year_cols(ws)
        domain = "External"
        block = "Current vintage"
        records: list[dict[object, object]] = []
        for row in range(1, (ws.max_row or 0) + 1):
            c2 = ws.cell(row, 2).value
            c3 = ws.cell(row, 3).value
            c5 = ws.cell(row, 5).value
            c7 = ws.cell(row, 7).value
            header = _norm_header(c2)
            if header in _DOMAIN_HEADERS:
                domain = _DOMAIN_HEADERS[header]
                continue
            if header in _BLOCK_HEADERS:
                block = _BLOCK_HEADERS[header]
                continue
            if isinstance(c7, str) and c7.strip() == "Nominal debt (in local currency)":
                block = "Chart (level)"
                continue
            if (
                isinstance(c7, str)
                and c7.strip()
                and not isinstance(c3, str)
                and block != "Chart (level)"
            ):
                block = "Chart"
            section = f"{domain} / {block}"
            series_code = c3 if isinstance(c3, str) else ""
            label = ""
            if isinstance(c5, str) and c5.strip():
                label = c5.strip()
            elif isinstance(c7, str) and c7.strip():
                label = c7.strip()
            elif isinstance(c2, str) and c2.strip():
                label = c2.strip()
            match_key = series_code or label
            for year, col in year_cols.items():
                raw = ws.cell(row, col).value
                if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                    continue
                records.append(
                    {
                        "sheet": REALISM1_SHEET,
                        "cell": _a1(row, col),
                        "row": row,
                        "col": col,
                        "year": year,
                        "section": section,
                        "series_code": series_code,
                        "label": label,
                        "match_key": match_key,
                        "excel_value": float(raw),
                    }
                )
        return pd.DataFrame.from_records(records)
    finally:
        wb.close()


@lru_cache(maxsize=4)
def _books(path: str):
    return load_core(path)


def _series_map(catalog: ImportedDataCatalog, vintage: str) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for item in catalog.series.values():
        if str(item.vintage_year) == vintage:
            out[item.series_code] = item.values.astype(float)
    return out


def _billion(series: pd.Series) -> pd.Series:
    return series.astype(float) / 1000.0


def _growth(series: pd.Series) -> pd.Series:
    return series.astype(float).pct_change()


def _change(series: pd.Series) -> pd.Series:
    return series.astype(float).diff()


def _index_growth_pct(level: pd.Series) -> pd.Series:
    lvl = level.astype(float)
    return (100.0 * (lvl / lvl.shift(1).replace(0.0, pd.NA) - 1.0)).astype(float)


def _rebase_block(
    prior: dict[str, pd.Series],
    old_gdp: pd.Series,
    new_gdp: pd.Series,
    *,
    mode: GdpRebaseMode = "constant",
    first_projection_year: int | None = None,
) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    r = gdp_rebase_scale(
        old_gdp,
        new_gdp,
        mode=mode,
        first_projection_year=first_projection_year,
    )
    out["r: ratio of Old GDP / New GDP"] = r
    for code, values in prior.items():
        if code in {"NGDPD", "NGDP"}:
            out[code] = values.astype(float) / r.replace(0.0, pd.NA)
        else:
            out[code] = rebase_ratio_to_outturn_gdp(
                old_gdp,
                new_gdp,
                values,
                mode=mode,
                first_projection_year=first_projection_year,
            )
    return out


def _put(
    store: dict[tuple[str, str], pd.Series],
    section: str,
    key: str,
    series: pd.Series,
) -> None:
    store[(section, key)] = pd.to_numeric(series, errors="coerce")


def compute_realism1_outputs(path: str | Path) -> dict[tuple[str, str], pd.Series]:
    """Compute Realism 1 series keyed by `(section, series_code_or_label)`."""
    path = Path(path)
    macro, _external, _ext_base, pub_base = _books(str(path))
    imported = load_imported_data(path)
    current_v = str(imported.current_vintage_year)
    prior_v = "2019"
    for item in imported.series.values():
        vint = str(item.vintage_year)
        if vint != current_v:
            prior_v = vint
            break

    ngdpd = _billion(macro.gdp_usd())
    ngdp = _billion(macro.gdp_lcu())
    first_proj = int(macro.inputs.first_projection_year)
    d_ppg = pub_base.ppg_external_debt_to_gdp()
    d_gdp = total_external_to_gdp(d_ppg, macro.private_external(), macro.gdp_usd())
    du = pub_base.public_sector_debt_to_gdp()
    pb = pub_base.primary_deficit_to_gdp()
    d_ppg_usd = d_ppg / 100.0 * ngdpd
    d_gdp_usd = d_gdp / 100.0 * ngdpd
    du_lcu = du / 100.0 * ngdp

    store: dict[tuple[str, str], pd.Series] = {}
    _put(store, "External / Current vintage", "NGDPD", ngdpd)
    _put(store, "External / Current vintage", "D_GDP", d_gdp)
    _put(store, "External / Current vintage", "D_PPG_GDP", d_ppg)
    _put(store, "External / Current vintage", "D_LCH_GDP", _change(d_gdp))
    _put(
        store,
        "External / Current vintage",
        "External debt o/w public and publicly guaranteed (in percent of GDP)",
        d_ppg,
    )
    _put(
        store,
        "External / Current vintage",
        "External debt (in billions of US dollars)",
        d_gdp_usd,
    )
    _put(
        store,
        "External / Current vintage",
        "PPG External debt (in billions of US dollars)",
        d_ppg_usd,
    )
    _put(
        store,
        "External / Current vintage",
        "g: Nominal GDP growth (USD)",
        _growth(ngdpd),
    )
    _put(store, "External / Chart", "Current DSA", d_ppg)
    _put(store, "External / Chart (level)", "Current DSA", d_gdp_usd)

    _put(store, "Public / Current vintage", "NGDP", ngdp)
    _put(store, "Public / Current vintage", "DU_GDP", du)
    _put(store, "Public / Current vintage", "PB_GDP", pb)
    _put(store, "Public / Current vintage", "DU_LCH_GDP", _change(du))
    _put(
        store,
        "Public / Current vintage",
        "Public sector debt (in billions of local currency)",
        du_lcu,
    )
    _put(store, "Public / Current vintage", "g: Nominal GDP growth (LC)", _growth(ngdp))
    _put(store, "Public / Chart", "Current DSA", du)

    prior_ext = _series_map(imported, prior_v)
    last_ext = _series_map(imported, current_v)
    for code, series in prior_ext.items():
        _put(store, "External / 5 years ago", code, series)
        _put(store, "Public / 5 years ago", code, series)
    for code, series in last_ext.items():
        _put(store, "External / Last vintage", code, series)
        _put(store, "Public / Last vintage", code, series)

    r_key = "r: ratio of Old GDP / New GDP"
    if "NGDPD" in prior_ext:
        rebased_5y = _rebase_block(prior_ext, prior_ext["NGDPD"], ngdpd)
        if r_key in rebased_5y:
            _put(store, "External / 5 years ago", r_key, rebased_5y[r_key])
        for key, series in rebased_5y.items():
            _put(store, "External / 5 years ago (re-based)", key, series)
        if "D_PPG_GDP" in rebased_5y:
            _put(store, "External / Chart", "DSA-2019", rebased_5y["D_PPG_GDP"])
            dsa2019_usd = debt_stock_from_ratio(
                prior_ext.get("D_GDP", prior_ext["D_PPG_GDP"]),
                prior_ext["NGDPD"],
            )
            _put(
                store,
                "External / 5 years ago",
                "External debt (in billions of US dollars)",
                dsa2019_usd,
            )
            _put(store, "External / Chart (level)", "DSA-2019", dsa2019_usd)
            err = forecast_error(rebased_5y["D_PPG_GDP"], d_ppg)
            _put(store, "External / Chart", "Forecast error (prior − current)", err)
            panel = forecast_error_panel(d_ppg, rebased_5y["D_PPG_GDP"], err)
            for label, row in panel.iterrows():
                _put(store, "Python panel / Forecast error", str(label), row)
    if "NGDPD" in last_ext:
        rebased_last = _rebase_block(
            last_ext,
            last_ext["NGDPD"],
            ngdpd,
            mode="last_vintage",
            first_projection_year=first_proj,
        )
        if r_key in rebased_last:
            _put(store, "External / Last vintage", r_key, rebased_last[r_key])
        for key, series in rebased_last.items():
            _put(store, "External / Last vintage (re-based)", key, series)
        if "D_PPG_GDP" in rebased_last:
            _put(store, "External / Chart", "Previous DSA", rebased_last["D_PPG_GDP"])
            prev_usd = debt_stock_from_ratio(last_ext["D_PPG_GDP"], last_ext["NGDPD"])
            _put(
                store,
                "External / Last vintage",
                "PPG External debt (in billions of US dollars)",
                prev_usd,
            )
            _put(
                store,
                "External / Last vintage (re-based)",
                "PPG External debt (in billions of US dollars)",
                prev_usd,
            )
            _put(store, "External / Chart (level)", "Previous DSA", prev_usd)

    if "NGDP" in prior_ext:
        rebased_pub_5y = _rebase_block(prior_ext, prior_ext["NGDP"], ngdp)
        if r_key in rebased_pub_5y:
            _put(store, "Public / 5 years ago", r_key, rebased_pub_5y[r_key])
        for key, series in rebased_pub_5y.items():
            _put(store, "Public / 5 years ago (re-based)", key, series)
        if "DU_GDP" in rebased_pub_5y:
            _put(store, "Public / Chart", "DSA-2019", rebased_pub_5y["DU_GDP"])
            flows = debt_creating_flow_panel(
                rebased_pub_5y["DU_GDP"].diff(),
                rebased_pub_5y.get("PB_GDP", pd.Series(dtype=float)),
                rebased_pub_5y.get("DU_OF_GDP", pd.Series(dtype=float)),
                real_interest=rebased_pub_5y.get("DUCIR_GDP"),
                real_gdp_growth=rebased_pub_5y.get("DUCGDPR_GDP"),
                real_exchange_rate=rebased_pub_5y.get("DUCER_GDP"),
            )
            _put(
                store,
                "Public / 5 years ago (re-based)",
                "Residual",
                flows.loc["Residual / GDP"],
            )
    if "NGDP" in last_ext:
        rebased_pub_last = _rebase_block(
            last_ext,
            last_ext["NGDP"],
            ngdp,
            mode="last_vintage",
            first_projection_year=first_proj,
        )
        if r_key in rebased_pub_last:
            _put(store, "Public / Last vintage", r_key, rebased_pub_last[r_key])
        for key, series in rebased_pub_last.items():
            _put(store, "Public / Last vintage (re-based)", key, series)
        if "DU_GDP" in rebased_pub_last:
            _put(store, "Public / Chart", "Previous DSA", rebased_pub_last["DU_GDP"])

    fc_usd = macro.fc_public_debt_usd()
    gdp_lcu = macro.gdp_lcu()
    fc_to_gdp = (
        100.0
        * fc_usd.astype(float).reindex(du.index)
        * macro.fx_eop().reindex(du.index)
        / gdp_lcu.reindex(du.index).replace(0.0, pd.NA)
    )
    us_defl = macro.foreign_gdp_deflator()
    if us_defl.empty:
        us_defl = pd.Series(0.0, index=du.index, dtype=float)
    lcu_defl = gdp_lcu / macro.gdp_constant().replace(0.0, pd.NA)
    i_pub = (
        100.0
        * macro.interest_expenditure().reindex(du.index)
        / macro.total_public_debt().shift(1).reindex(du.index).replace(0.0, pd.NA)
    )
    i_ext = (
        100.0
        * macro.ppg_interest().reindex(du.index)
        / macro.ppg_external().shift(1).reindex(du.index).replace(0.0, pd.NA)
    )
    i_dom = (
        100.0
        * macro.domestic_interest().reindex(du.index)
        / macro.domestic_debt().shift(1).reindex(du.index).replace(0.0, pd.NA)
        * macro.fx_pa().reindex(du.index)
    )
    auto = public_automatic_debt_dynamics(
        public_debt_to_gdp=du,
        fc_debt_to_gdp=fc_to_gdp,
        real_gdp_growth=macro.real_gdp_growth(),
        gdp_deflator_growth=_index_growth_pct(lcu_defl),
        us_deflator_growth=_index_growth_pct(us_defl),
        fx_eop=macro.fx_eop(),
        interest_rate_external=i_ext,
        interest_rate_domestic=i_dom,
        public_interest_rate=i_pub,
    )
    du_of = other_identified_flows_to_gdp(
        macro.inputs.contingent_liabilities,
        macro.inputs.other_debt_creating_flows,
        macro.inputs.privatization,
        macro.inputs.debt_relief,
        gdp_lcu,
    )
    _put(store, "Public / Current vintage", "DUCIR_GDP", auto.loc["DUCIR_GDP"])
    _put(store, "Public / Current vintage", "DUCGDPR_GDP", auto.loc["DUCGDPR_GDP"])
    _put(store, "Public / Current vintage", "DUCER_GDP", auto.loc["DUCER_GDP"])
    _put(store, "Public / Current vintage", "DU_OF_GDP", du_of)
    flows_current = debt_creating_flow_panel(
        _change(du),
        pb,
        du_of,
        real_interest=auto.loc["DUCIR_GDP"],
        real_gdp_growth=auto.loc["DUCGDPR_GDP"],
        real_exchange_rate=auto.loc["DUCER_GDP"],
    )
    _put(
        store,
        "Public / Current vintage",
        "Residual",
        flows_current.loc["Residual / GDP"],
    )
    return store


def build_realism1_comparison(path: str | Path) -> pd.DataFrame:
    """Build a side-by-side Excel vs Python table for Realism 1 cells."""
    path = Path(path)
    excel = _read_realism1_rows(path)
    computed = compute_realism1_outputs(path)
    computed_values: list[float | None] = []
    for section, match_key, year in zip(
        excel["section"].tolist(),
        excel["match_key"].tolist(),
        excel["year"].tolist(),
        strict=True,
    ):
        series = computed.get((str(section), str(match_key)))
        value: float | None = None
        year_i = _year_int(year)
        if series is not None and year_i in series.index:
            raw = series.loc[year_i]
            if pd.notna(raw):
                value = float(raw)
        computed_values.append(value)
    excel = excel.copy()
    excel["computed_value"] = computed_values
    excel["abs_diff"] = (excel["excel_value"] - excel["computed_value"]).abs()
    extra_rows: list[dict[object, object]] = []
    excel_keys = set(
        zip(excel["section"], excel["match_key"], excel["year"], strict=True)
    )
    for (section, key), series in computed.items():
        if not section.startswith("Python panel"):
            continue
        for year_key, value in series.dropna().items():
            year_i = _year_int(year_key)
            if (section, key, year_i) in excel_keys:
                continue
            extra_rows.append(
                {
                    "sheet": REALISM1_SHEET,
                    "cell": "",
                    "row": pd.NA,
                    "col": pd.NA,
                    "year": year_i,
                    "section": section,
                    "series_code": "",
                    "label": key,
                    "match_key": key,
                    "excel_value": pd.NA,
                    "computed_value": float(value),
                    "abs_diff": pd.NA,
                }
            )
    if extra_rows:
        excel = pd.concat([excel, pd.DataFrame(extra_rows)], ignore_index=True)
    return excel.sort_values(
        ["row", "col", "section", "year"], na_position="last"
    ).reset_index(drop=True)


def write_realism1_comparison_csv(
    workbook: str | Path,
    output: str | Path,
) -> Path:
    """Write the Realism 1 comparison table to `output` and return that path."""
    output = Path(output)
    frame = build_realism1_comparison(workbook)
    cols = [
        "sheet",
        "cell",
        "row",
        "col",
        "year",
        "section",
        "series_code",
        "label",
        "excel_value",
        "computed_value",
        "abs_diff",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, cols].to_csv(output, index=False)
    return output
