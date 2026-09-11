"""End-to-end orchestration: LIC-DSF workbook → Output panel DataFrames.

Separates calculation wiring from spreadsheet I/O (see ``lic_dsf.export``).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from lic_dsf.load import (
    load_capital_assumptions,
    load_ci_summary,
    load_core,
    load_distress_covariates,
    load_imported_data,
    load_input1_market,
    load_input6_standard,
    load_input7_residual_params,
    load_invest_growth_series,
)
from lic_dsf.output import (
    external_dsa_panel,
    fiscal_adjustment_panel,
    fiscal_multiplier_panel,
    forecast_error_panel,
    invest_growth_panel,
    output_31_table,
    output_32_table,
    probability_panel,
    public_dsa_panel,
    risk_summary_panel,
)
from lic_dsf.rating import (
    ChartDataRegistry,
    MarketFinancingInputs,
    RiskRatingSummary,
    assess_market_financing,
    compute_mechanical_ratings,
    market_panel,
    moderate_panel,
    most_extreme_shock_id,
)
from lic_dsf.realism import rebase_ratio_to_outturn_gdp
from lic_dsf.scenario import (
    CustomizedScenarioSpec,
    ProbabilityAssumptions,
    register_custom_path,
)
from lic_dsf.stress import (
    run_a1_historical_external,
    run_standard_external_stress,
    run_standard_public_stress,
)

# Canonical sheet titles written by ``compute_outputs`` / ``export.to_workbook``.
SHEET_1_1 = "Output 1-1 External DSA"
SHEET_1_2 = "Output 1-2 Public DSA"
SHEET_3_1 = "Output 3-1 Stress-external"
SHEET_3_2 = "Output 3-2 Stress-public"
SHEET_4_1 = "Output 4-1 Forecast Error"
SHEET_4_2_FISCAL_ADJ = "Output 4-2 Fiscal adjustment"
SHEET_4_2_MULTIPLIER = "Output 4-2 Fiscal multiplier"
SHEET_4_2_INVEST = "Output 4-2 Invest-growth"
SHEET_5_1 = "Output 5-1 Moderate"
SHEET_5_2 = "Output 5-2 Market"
SHEET_6 = "Output 6 Probability"
SHEET_7 = "Output 7 Risk rating"
SHEET_SUMMARY = "Output - Summary"
SHEET_DATABASE = "Output Database"

OUTPUT_SHEET_ORDER: tuple[str, ...] = (
    SHEET_1_1,
    SHEET_1_2,
    SHEET_3_1,
    SHEET_3_2,
    SHEET_4_1,
    SHEET_4_2_FISCAL_ADJ,
    SHEET_4_2_MULTIPLIER,
    SHEET_4_2_INVEST,
    SHEET_5_1,
    SHEET_5_2,
    SHEET_6,
    SHEET_7,
    SHEET_SUMMARY,
    SHEET_DATABASE,
)

_STRESS_SHEETS = frozenset({SHEET_3_1, SHEET_3_2})
_REALISM_SHEETS = frozenset(
    {SHEET_4_1, SHEET_4_2_FISCAL_ADJ, SHEET_4_2_MULTIPLIER, SHEET_4_2_INVEST}
)
_RATING_SHEETS = frozenset({SHEET_5_1, SHEET_5_2, SHEET_6, SHEET_7})
_ENGINE_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class OutputBook:
    """Computed Output panels ready for export or inspection.

    Attributes:
        sheets: Ordered mapping of sheet title → panel DataFrame.
        meta: Country / vintage / engine metadata.
    """

    sheets: Mapping[str, pd.DataFrame]
    meta: Mapping[str, Any]


def _wants(include: frozenset[str] | None, *names: str) -> bool:
    if include is None:
        return True
    return any(name in include for name in names)


def _db_rows(code: str, series: pd.Series, years: list[int], country_code: int) -> pd.DataFrame:
    values = series.reindex(years).dropna()
    return pd.DataFrame(
        {
            "Indicator": code,
            "Country.IMF Country Code": country_code,
            "Year": values.index.astype(int),
            "Value": values.to_numpy(dtype=float),
        }
    )


def compute_outputs(
    path: str | Path,
    *,
    include: Collection[str] | None = None,
) -> OutputBook:
    """Load a LIC-DSF workbook and assemble Output 1–7 panel DataFrames.

    Args:
        path: Path to a filled LIC-DSF ``.xlsx`` / ``.xlsm``.
        include: Optional subset of sheet titles from ``OUTPUT_SHEET_ORDER``.
            When set, only those sheets are computed (skips unused runners).

    Returns:
        ``OutputBook`` with panel frames and metadata.
    """
    workbook = Path(path)
    wanted = frozenset(include) if include is not None else None
    if wanted is not None:
        if not wanted:
            raise ValueError("include must contain at least one known sheet title")
        unknown = wanted - frozenset(OUTPUT_SHEET_ORDER)
        if unknown:
            raise ValueError(f"Unknown output sheet(s): {sorted(unknown)}")

    need_stress = _wants(wanted, *_STRESS_SHEETS, *_RATING_SHEETS, SHEET_SUMMARY)
    need_realism = _wants(wanted, *_REALISM_SHEETS)
    need_rating = _wants(wanted, *_RATING_SHEETS, SHEET_SUMMARY)

    macro, external, ext_base, pub_base = load_core(workbook)
    first_proj = int(macro.inputs.first_projection_year)
    proj_years = list(range(first_proj, first_proj + 11))

    ci = load_ci_summary(workbook) if (
        need_rating or _wants(wanted, SHEET_3_1, SHEET_3_2, SHEET_SUMMARY, SHEET_DATABASE)
    ) else None

    sheets: dict[str, pd.DataFrame] = {}

    if _wants(wanted, SHEET_1_1):
        sheets[SHEET_1_1] = external_dsa_panel(ext_base)
    if _wants(wanted, SHEET_1_2):
        sheets[SHEET_1_2] = public_dsa_panel(pub_base)

    external_stress: dict[str, Any] = {}
    public_stress: dict[str, Any] = {}
    historical = None
    residual = None
    input6 = None

    if need_stress or need_rating:
        input6 = load_input6_standard(workbook)
        residual = load_input7_residual_params(workbook)
        external_stress = run_standard_external_stress(
            macro, external, input6, residual
        )
        public_stress = run_standard_public_stress(
            macro, external, input6, residual
        )
        if need_rating or _wants(wanted, SHEET_3_1, SHEET_6):
            historical = run_a1_historical_external(macro, external, residual)

    if _wants(wanted, SHEET_3_1):
        assert ci is not None
        sheets[SHEET_3_1] = output_31_table(
            ext_base,
            historical=historical,
            external_stress=external_stress,
            public_stress=public_stress,
            thresholds=ci.thresholds.as_dict(),
        )
    if _wants(wanted, SHEET_3_2):
        assert ci is not None
        sheets[SHEET_3_2] = output_32_table(
            pub_base,
            public_stress=public_stress,
            public_threshold=ci.thresholds.public_pv_debt_to_gdp,
        )

    if need_realism:
        if _wants(wanted, SHEET_4_1):
            imported = load_imported_data(workbook)
            prior_ppg = imported.get("D_PPG_GDP", 2019) or imported.get(
                "D_PPG_GDP", "2019"
            )
            current_ext_debt = pub_base.ppg_external_debt_to_gdp()
            if prior_ppg is not None:
                prior_gdp = imported.get("NGDPD", prior_ppg.vintage_year)
                curr_gdp = imported.get("NGDPD", imported.current_vintage_year)
                if prior_gdp is not None and curr_gdp is not None:
                    rebased_prior = rebase_ratio_to_outturn_gdp(
                        prior_gdp.values, curr_gdp.values, prior_ppg.values
                    )
                else:
                    rebased_prior = prior_ppg.values
                overlap = sorted(
                    set(rebased_prior.dropna().index)
                    & set(current_ext_debt.dropna().index)
                )
                sheets[SHEET_4_1] = forecast_error_panel(
                    current_ext_debt.reindex(overlap),
                    rebased_prior.reindex(overlap),
                )
            else:
                sheets[SHEET_4_1] = pd.DataFrame(
                    {"note": ["No D_PPG_GDP vintage in Imported data"]}
                )

        if _wants(wanted, SHEET_4_2_FISCAL_ADJ):
            sheets[SHEET_4_2_FISCAL_ADJ] = fiscal_adjustment_panel(
                pub_base.primary_deficit_to_gdp(), first_proj
            )

        if _wants(wanted, SHEET_4_2_MULTIPLIER):
            pb_pct = 100.0 * macro.primary_balance() / macro.gdp_lcu()
            sheets[SHEET_4_2_MULTIPLIER] = fiscal_multiplier_panel(
                pb_pct, macro.real_gdp_growth(), first_proj
            )

        if _wants(wanted, SHEET_4_2_INVEST):
            ig_curr = load_invest_growth_series(workbook)
            cap = load_capital_assumptions(workbook)
            sheets[SHEET_4_2_INVEST] = invest_growth_panel(
                ig_curr, macro.real_gdp_growth().reindex(ig_curr.index), cap
            )

    mechanical = None
    out_5_1: pd.DataFrame | None = None

    if need_rating:
        assert ci is not None
        registry = ChartDataRegistry()
        registry.register_series(
            "pv_debt_to_gdp",
            "baseline",
            ext_base.pv_ppg_external_to_gdp().reindex(proj_years),
            is_baseline=True,
        )
        registry.register_series(
            "pv_debt_to_exports",
            "baseline",
            ext_base.pv_ppg_external_to_exports().reindex(proj_years),
            is_baseline=True,
        )
        registry.register_series(
            "debt_service_to_exports",
            "baseline",
            ext_base.ppg_debt_service_to_exports().reindex(proj_years),
            is_baseline=True,
        )
        registry.register_series(
            "debt_service_to_revenue",
            "baseline",
            ext_base.ppg_debt_service_to_revenue().reindex(proj_years),
            is_baseline=True,
        )
        registry.register_series(
            "public_pv_debt_to_gdp",
            "baseline",
            pub_base.pv_public_debt_to_gdp().reindex(proj_years),
            is_baseline=True,
        )
        for sid, book in external_stress.items():
            registry.register_series(
                "pv_debt_to_gdp",
                sid,
                book.pv_ppg_external_to_gdp().reindex(proj_years),
                is_shock=True,
            )
            registry.register_series(
                "pv_debt_to_exports",
                sid,
                book.pv_ppg_external_to_exports().reindex(proj_years),
                is_shock=True,
            )
            registry.register_series(
                "debt_service_to_exports",
                sid,
                book.ppg_debt_service_to_exports().reindex(proj_years),
                is_shock=True,
            )
            registry.register_series(
                "debt_service_to_revenue",
                sid,
                book.ppg_debt_service_to_revenue().reindex(proj_years),
                is_shock=True,
            )
        if "B1_GDP" in public_stress:
            registry.register_series(
                "public_pv_debt_to_gdp",
                "B1_GDP",
                public_stress["B1_GDP"].pv_public_debt_to_gdp().reindex(proj_years),
                is_shock=True,
            )
        register_custom_path(
            registry,
            indicator="pv_debt_to_gdp",
            values=ext_base.pv_ppg_external_to_gdp().reindex(proj_years),
            spec=CustomizedScenarioSpec(name="Customized", short_name="custom"),
        )
        mechanical = compute_mechanical_ratings(
            registry, ci.thresholds, years=proj_years
        )

        if _wants(wanted, SHEET_5_1):
            out_5_1 = moderate_panel(
                mechanical_external=mechanical.external,
                baseline_pv_gdp=ext_base.pv_ppg_external_to_gdp(),
                threshold_pv_gdp=ci.thresholds.pv_debt_to_gdp,
                rating_years=proj_years,
            )
            sheets[SHEET_5_1] = out_5_1

        if _wants(wanted, SHEET_5_2):
            market_access, embi_spread = load_input1_market(workbook)
            gfn = pub_base.public_gfn_to_gdp().reindex(
                list(range(first_proj, first_proj + 3))
            )
            market = assess_market_financing(
                MarketFinancingInputs(
                    market_access=market_access,
                    gfn_to_gdp=gfn,
                    embi_spread=embi_spread,
                )
            )
            sheets[SHEET_5_2] = market_panel(market)

        if _wants(wanted, SHEET_6):
            assert historical is not None
            mx_sid = most_extreme_shock_id(
                {
                    sid: book.pv_ppg_external_to_gdp()
                    for sid, book in external_stress.items()
                },
                ci.thresholds.pv_debt_to_gdp,
                proj_years,
            )
            sheets[SHEET_6] = probability_panel(
                {
                    "baseline": ext_base.pv_ppg_external_to_gdp().reindex(proj_years),
                    "historical": historical.pv_ppg_external_to_gdp().reindex(
                        proj_years
                    ),
                    "mx_shock": external_stress[mx_sid]
                    .pv_ppg_external_to_gdp()
                    .reindex(proj_years),
                },
                ci.thresholds.pv_debt_to_gdp,
                indicator="pv_debt_to_gdp",
                assumptions=ProbabilityAssumptions(bandwidth=0.1),
                covariates=load_distress_covariates(workbook),
            )

        if _wants(wanted, SHEET_7):
            if out_5_1 is None:
                out_5_1 = moderate_panel(
                    mechanical_external=mechanical.external,
                    baseline_pv_gdp=ext_base.pv_ppg_external_to_gdp(),
                    threshold_pv_gdp=ci.thresholds.pv_debt_to_gdp,
                    rating_years=proj_years,
                )
            summary = RiskRatingSummary(
                mechanical=mechanical,
                thresholds=ci.thresholds,
                dcc=ci.dcc,
                ci_score=ci.ci_score,
                moderate_granularity=str(
                    out_5_1.loc["Space to absorb shock", "Output 5-1"]
                ),
            )
            sheets[SHEET_7] = risk_summary_panel(summary)

    if _wants(wanted, SHEET_SUMMARY):
        assert ci is not None and mechanical is not None
        sheets[SHEET_SUMMARY] = pd.Series(
            {
                "Country": ci.country,
                "IFS Code": ci.country_code,
                "First Year of Projection": first_proj,
                "Composite Indicator": ci.ci_score,
                "Debt Carrying Capacity": ci.dcc.value,
                "Mechanical external": mechanical.external.label,
                "Mechanical fiscal": mechanical.fiscal.label,
                "Mechanical overall": mechanical.overall.label,
                **{f"Threshold {k}": v for k, v in ci.thresholds.as_dict().items()},
            },
            name="Output Summary",
        ).to_frame()

    if _wants(wanted, SHEET_DATABASE):
        assert ci is not None
        sheets[SHEET_DATABASE] = pd.concat(
            [
                _db_rows(
                    "DPPVNPV_GDP",
                    ext_base.pv_ppg_external_to_gdp(),
                    proj_years,
                    ci.country_code,
                ),
                _db_rows(
                    "DPPVNPV_BX",
                    ext_base.pv_ppg_external_to_exports(),
                    proj_years,
                    ci.country_code,
                ),
                _db_rows(
                    "TDS_BX",
                    ext_base.ppg_debt_service_to_exports(),
                    proj_years,
                    ci.country_code,
                ),
                _db_rows(
                    "TDS_REV",
                    ext_base.ppg_debt_service_to_revenue(),
                    proj_years,
                    ci.country_code,
                ),
                _db_rows(
                    "DU_NPV_GDP",
                    pub_base.pv_public_debt_to_gdp(),
                    proj_years,
                    ci.country_code,
                ),
                _db_rows(
                    "DU_GDP",
                    pub_base.public_sector_debt_to_gdp(),
                    proj_years,
                    ci.country_code,
                ),
            ],
            ignore_index=True,
        )

    ordered = {name: sheets[name] for name in OUTPUT_SHEET_ORDER if name in sheets}
    meta: dict[str, Any] = {
        "workbook": str(workbook.resolve()),
        "workbook_stem": workbook.stem,
        "first_projection_year": first_proj,
        "engine_version": _ENGINE_VERSION,
    }
    if ci is not None:
        meta["country"] = ci.country
        meta["country_code"] = ci.country_code
        meta["ci_score"] = ci.ci_score
        meta["dcc"] = ci.dcc.value

    return OutputBook(sheets=ordered, meta=meta)
