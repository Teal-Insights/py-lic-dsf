"""Phase 7 coupling, market access, FX revaluation, and combo add.int."""

from __future__ import annotations

import pytest

from lic_dsf.load.input6 import load_combo_additional_borrowing_interest
from lic_dsf.stress import (
    AbsoluteResidualPolicy,
    CoupledScenarioRunner,
    ExternalScenarioRunner,
    PublicScenarioRunner,
    ScenarioRegistry,
    StressContext,
)
from lic_dsf.stress.external_portfolio import ExternalPortfolioAdjuster
from lic_dsf.stress.market_access import ComboMarketCost, MarketAccessAddon
from lic_dsf.stress.output_map import EXT_SCENARIO_LABELS, to_output31_rows
from lic_dsf.stress.resfin import policy_from_spec
from lic_dsf.stress.shocks import MacroShockFactory
from tests.conftest import WORKBOOK_XLSX
from tests.parity import assert_all_passed, compare_probes, read_cached_output
from tests.parity.catalogs.output_3 import output_31_probes

WORKBOOK = WORKBOOK_XLSX


@pytest.fixture(scope="module")
def stress_context() -> StressContext:
    return StressContext.from_workbook(WORKBOOK)


def test_combo_market_cost_matches_workbook_loader(
    stress_context: StressContext,
) -> None:
    """B6 add.int is computed in Python (no production workbook read)."""
    spec = ScenarioRegistry.get("B6_Combo")
    path = MacroShockFactory.from_spec(spec).apply(stress_context, spec)
    computed = ComboMarketCost().compute(
        path.baseline, path.shocked, stress_context.external
    )
    loaded = load_combo_additional_borrowing_interest(WORKBOOK, path.years)
    for year in path.years:
        assert float(computed.loc[year]) == pytest.approx(
            float(loaded.loc[year]), abs=1e-9, rel=1e-12
        ), f"combo add.int {year}"


def test_external_portfolio_adjuster_revalues_fx(
    stress_context: StressContext,
) -> None:
    spec = ScenarioRegistry.get("B5_FX")
    path = MacroShockFactory.from_spec(spec).apply(stress_context, spec)
    adjusted = ExternalPortfolioAdjuster().adjust(stress_context.external, path)
    first = path.first_projection_year
    shock_year = first + 1
    assert float(adjusted.inputs.fx_pa.loc[shock_year]) == pytest.approx(
        float(path.shocked.fx_pa().loc[shock_year]), abs=1e-12
    )
    assert float(adjusted.inputs.fx_pa.loc[shock_year]) != pytest.approx(
        float(stress_context.external.inputs.fx_pa.loc[shock_year]), abs=1e-9
    )


def test_b6_runner_uses_python_add_int_without_workbook_path(
    stress_context: StressContext,
) -> None:
    result = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B6_Combo")
    )
    assert result.external_ratios is not None
    add_int = result.external_ratios.additional_borrowing_interest
    assert add_int is not None
    assert float(add_int.loc[2026]) == pytest.approx(11.94418990135332, abs=1e-9)


def test_b5_fx_revalue_changes_external_pv_vs_unadjusted(
    stress_context: StressContext,
) -> None:
    """LC-NR FX rebuild moves PPG PV when explicitly enabled (opt-in)."""
    from dataclasses import replace

    spec = replace(ScenarioRegistry.get("B5_FX"), fx_revalue_portfolio=True)
    result = ExternalScenarioRunner(context=stress_context).run(spec)
    assert result.external_ratios is not None
    unrevalued = ExternalScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B5_FX")
    )
    assert unrevalued.external_ratios is not None
    assert float(result.external_ratios.pv_ppg_external_to_gdp().loc[2025]) != (
        pytest.approx(
            float(unrevalued.external_ratios.pv_ppg_external_to_gdp().loc[2025]),
            abs=1e-6,
        )
    )


def test_coupled_b2_absolute_and_wires_external_gap(
    stress_context: StressContext,
) -> None:
    spec = ScenarioRegistry.get("B2_PrimaryBalance")
    assert isinstance(policy_from_spec(spec), AbsoluteResidualPolicy)
    assert spec.couple_ext_r86 is True
    result = CoupledScenarioRunner(context=stress_context).run(spec)
    assert result.public_ratios is not None
    assert result.external_ratios is not None
    assert result.resfin.fill is not None
    # B2 PB shock leaves external residual at zero (legacy + Excel agree).
    assert float(result.external_gap.gap.abs().sum()) == pytest.approx(0.0, abs=1e-12)
    assert float(result.resfin.fill.external_mlt_usd.loc[2025]) >= 0.0


def test_public_runner_delegates_b2_to_coupled(
    stress_context: StressContext,
) -> None:
    pub = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    )
    coupled = CoupledScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    )
    assert pub.external_ratios is not None
    assert float(pub.public_ratios.pv_ppg_external_to_gdp().loc[2025]) == pytest.approx(
        float(coupled.public_ratios.pv_ppg_external_to_gdp().loc[2025]),
        abs=1e-12,
    )


def test_market_access_addon_interest(
    stress_context: StressContext,
) -> None:
    result = CoupledScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    )
    assert result.resfin.public is not None
    addon = MarketAccessAddon.from_path(
        result.path,
        result.resfin.public,
        enabled=stress_context.market_access,
    )
    if stress_context.market_access:
        ext_rate, dom_rate = addon.rates()
        assert ext_rate > 0.0
        interest = addon.additional_interest_lcu()
        assert float(interest.abs().sum()) >= 0.0
        assert dom_rate >= 0.0
    else:
        assert addon.rates() == (0.0, 0.0)


def test_output_31_b2_full_catalog_pv_at_1e6(
    stress_context: StressContext,
) -> None:
    """Output 3-1 B2: all PV indicators × projection years at global tol."""
    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    )
    assert result.public_ratios is not None
    rows = to_output31_rows(
        result.public_ratios, scenario_id="B2_PrimaryBalance"
    )
    label = EXT_SCENARIO_LABELS["B2_PrimaryBalance"]
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.sut_key[0].startswith("PV of debt")
        and p.year is not None
        and 2024 <= int(p.year) <= 2034
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {k: v for k, v in rows.items() if k[0].startswith("PV of debt")}
    assert_all_passed(compare_probes(excel, sut))


def test_output_31_b2_ds_shock_window(
    stress_context: StressContext,
) -> None:
    """Debt-service Output 3-1 B2 matches Excel in the shock window."""
    result = PublicScenarioRunner(context=stress_context).run(
        ScenarioRegistry.get("B2_PrimaryBalance")
    )
    assert result.public_ratios is not None
    rows = to_output31_rows(
        result.public_ratios, scenario_id="B2_PrimaryBalance"
    )
    label = EXT_SCENARIO_LABELS["B2_PrimaryBalance"]
    probes = tuple(
        p
        for p in output_31_probes(WORKBOOK)
        if isinstance(p.sut_key, tuple)
        and p.sut_key[1] == label
        and p.sut_key[0].startswith("Debt service")
        and p.year in {2024, 2025, 2026}
    )
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    sut = {k: v for k, v in rows.items() if k[0].startswith("Debt service")}
    assert_all_passed(compare_probes(excel, sut))
