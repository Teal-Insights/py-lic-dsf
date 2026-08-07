"""Tests for ``lic_dsf.scenario`` (customized + probability)."""

from __future__ import annotations

import pandas as pd
import pytest

from lic_dsf.pv import MacroDebtInputs
from lic_dsf.rating import (
    ChartDataRegistry,
    RiskRating,
    compute_mechanical_ratings,
    thresholds_for,
)
from lic_dsf.scenario import (
    CustomizedScenarioSpec,
    ProbabilityAssumptions,
    apply_customized_deltas,
    borderline_bands,
    breach_probability,
    probability_panel,
    register_custom_path,
)


def _zero(years: tuple[int, ...]) -> pd.Series:
    return pd.Series(0.0, index=list(years), dtype=float)


def _macro_inputs() -> MacroDebtInputs:
    years = (2023, 2024, 2025)
    z = _zero(years)
    return MacroDebtInputs(
        years=years,
        first_projection_year=2024,
        gdp_usd=pd.Series({2023: 1000.0, 2024: 1100.0, 2025: 1200.0}),
        gdp_constant=pd.Series({2023: 900.0, 2024: 950.0, 2025: 1000.0}),
        fx_eop=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5}),
        fx_pa=pd.Series({2023: 2.0, 2024: 2.5, 2025: 2.5}),
        current_account=z.copy(),
        exports=pd.Series({2023: 400.0, 2024: 440.0, 2025: 480.0}),
        imports=z.copy(),
        current_transfers_net=z.copy(),
        current_transfers_official=z.copy(),
        fdi=z.copy(),
        exceptional_financing=z.copy(),
        reserves_flow=z.copy(),
        revenues_incl_grants=pd.Series({2023: 200.0, 2024: 220.0, 2025: 240.0}),
        grants=pd.Series({2023: 20.0, 2024: 22.0, 2025: 24.0}),
        privatization=z.copy(),
        primary_expenditure=pd.Series({2023: 150.0, 2024: 160.0, 2025: 170.0}),
        public_assets=z.copy(),
        contingent_liabilities=z.copy(),
        other_debt_creating_flows=z.copy(),
        debt_relief=z.copy(),
        mlt_external=pd.Series({2023: 500.0, 2024: 0.0, 2025: 0.0}),
        short_term_external=z.copy(),
        private_mlt_external=z.copy(),
        private_st_external=z.copy(),
        domestic_mlt=pd.Series({2023: 200.0, 2024: 0.0, 2025: 0.0}),
        domestic_st=pd.Series({2023: 20.0, 2024: 0.0, 2025: 0.0}),
        ppg_interest=z.copy(),
        private_interest=z.copy(),
        domestic_interest=z.copy(),
        ppg_amortization=z.copy(),
        private_amortization=z.copy(),
        domestic_amortization=z.copy(),
        concessional_loans=z.copy(),
        domestic_mlt_input5=z.copy(),
        domestic_st_input5=z.copy(),
        domestic_interest_lcu_input5=z.copy(),
        domestic_principal_lcu_input5=z.copy(),
        public_gfn_input5=z.copy(),
    )


def test_borderline_and_probability() -> None:
    lower, upper = borderline_bands(40.0, 0.1)
    assert lower == pytest.approx(36.0)
    assert upper == pytest.approx(44.0)
    assert breach_probability(40.0, 40.0) == pytest.approx(0.5)
    assert breach_probability(50.0, 40.0) > 0.5
    assert breach_probability(30.0, 40.0) < 0.5

    paths = {
        "baseline": pd.Series({2024: 42.0, 2025: 41.0, 2026: 39.0}),
        "mx_shock": pd.Series({2024: 42.0, 2025: 48.0, 2026: 50.0}),
    }
    panel = probability_panel(
        paths, 40.0, assumptions=ProbabilityAssumptions(bandwidth=0.1)
    )
    assert "baseline prob" in panel.index
    assert "lower_band" in panel.index


def test_customized_deltas_and_chart_registration() -> None:
    inputs = _macro_inputs()
    spec = CustomizedScenarioSpec(
        name="Alt fiscal",
        short_name="custom",
        primary_expenditure_delta_pct_gdp=pd.Series({2024: 2.0, 2025: 2.0}),
    )
    shocked = apply_customized_deltas(inputs, spec)
    gdp_lcu_2024 = 1100.0 * 2.5
    assert float(shocked.primary_expenditure.loc[2024]) == pytest.approx(
        160.0 + 0.02 * gdp_lcu_2024
    )

    registry = ChartDataRegistry()
    registry.register_series(
        "pv_debt_to_gdp",
        "baseline",
        pd.Series({2024: 35.0, 2025: 34.0}),
        is_baseline=True,
    )
    for ind in (
        "pv_debt_to_exports",
        "debt_service_to_exports",
        "debt_service_to_revenue",
        "public_pv_debt_to_gdp",
    ):
        registry.register_series(
            ind, "baseline", pd.Series({2024: 1.0, 2025: 1.0}), is_baseline=True
        )
    register_custom_path(
        registry,
        indicator="pv_debt_to_gdp",
        values=pd.Series({2024: 45.0, 2025: 46.0}),
        spec=spec,
    )
    result = compute_mechanical_ratings(registry, thresholds_for("Medium"))
    assert result.external_shock_breach is True
    assert result.external == RiskRating.MODERATE
