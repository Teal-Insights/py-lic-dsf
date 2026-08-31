# Phase 2 — MacroShock and ShockedMacroPath

**Status:** Not started  
**Depends on:** [Phase 1](phase-01-context-and-spec.md)  
**Blocks:** Phases 3–8

## Goal

Isolate Input 6 macro path shocks into a single layer. No ResFin, no ratios —
only shocked `MacroDebtInputs` and derived denominators (GDP, exports/GDP).

## Prerequisites

- `StressContext`, `ScenarioSpec` from Phase 1
- Phase 0 B-sheet macro probes (GDP, growth rows)

## Deliverables

| Item | Location |
|------|----------|
| `MacroShock` protocol | `src/lic_dsf/stress_v2/path.py` |
| Concrete shocks | `src/lic_dsf/stress_v2/shocks/` (or port `stress/shocks.py`) |
| `ShockedMacroPath` | `src/lic_dsf/stress_v2/path.py` |
| `ShockMetadata` | `src/lic_dsf/stress_v2/path.py` |
| Parity tests | `tests/test_stress_v2_macro_path.py` |

## Class responsibilities

### `MacroShock` (protocol)

**Method:** `apply(ctx: StressContext, spec: ScenarioSpec) -> ShockedMacroPath`

One implementation per `ShockKind`. Port logic from `lic_dsf.stress.shocks`
with minimal changes initially.

### `ShockedMacroPath`

**Takes:**

- `baseline: MacroDebtBook`
- `shocked: MacroDebtBook` (new inputs, same `external` reference until FX phase)
- `metadata: ShockMetadata` — shock years, fx_depreciation_pct, exports_shocked_in_levels

**Responsibilities:**

- Expose shocked series: `gdp_usd()`, `gdp_lcu()`, `exports()`, `revenues_excl_grants()`
- Expose `years`, `first_projection_year`
- **No** ResFin, **no** ratio methods

### `ShockMetadata`

Fields: `shock_window_years: tuple[int, int]`, `fx_depreciation_pct: float`,
`threshold_rule: ThresholdRule`, `interactions_on: bool`.

## Port map from legacy

| Legacy function | v2 home |
|-----------------|---------|
| `apply_real_gdp_shock` | `GdpShock` |
| `apply_primary_balance_shock` | `PrimaryBalanceShock` |
| `apply_exports_shock` | `ExportsShock` |
| `apply_other_flows_shock` | `OtherFlowsShock` |
| `apply_fx_depreciation_shock` | `FxShock` |
| `apply_combo_shock` | `ComboShock` |
| `apply_historical_averages_shock` | `HistoricalShock` |

Keep projection shock window: second and third projection years (Excel Input 6
bound-test window).

## Implementation tasks

1. Copy `shocks.py` into v2 (or re-export during migration); avoid redesign.

2. Implement `ShockedMacroPath` wrapper around two `MacroDebtBook` instances.

3. Implement `MacroShockFactory.from_spec(spec) -> MacroShock`.

4. Add `ShockedMacroPath.gdp_growth_pct()` helper for probe comparison.

5. Wire `StressScenarioRunner` to return `ShockedMacroPath` only (ratios still
   `NotImplementedError`).

## Differential testing

Use Phase 0 B-sheet macro probes:

| Sheet | Rows | Scenarios |
|-------|------|-----------|
| `B1_GDP_ext` | 46 (GDP), 50 (growth) | B1 |
| `B1_GDP_pub` | 41 (GDP LCU), 42 (growth) | B1 |
| `A1_historical_ext` | growth pins | A1 |
| `B3_Exports_ext` | export levels | B3 |
| `B5_depreciation_ext` | FX / deflator | B5 |

Parametrize:

```python
@pytest.mark.parametrize("scenario_id", ["B1_GDP", "A1_Historical", "B3_Exports", "B5_FX"])
def test_shocked_macro_matches_bsheet(scenario_id): ...
```

Compare v2 `ShockedMacroPath` series to cached Excel cells via
`read_cached_output` + `compare_probes`.

**Tolerance:** `1e-6` for growth and GDP levels.

## Definition of done

- [ ] All macro-path probes green for A1 + B1–B6 (standard shocks)
- [ ] Legacy `shocks.py` still passes existing `test_stress_dsa.py` tests
- [ ] `ShockedMacroPath` has no ResFin or ratio methods
- [ ] Shock window (proj years 2–3) verified against Excel for each scenario

## Out of scope

- `bsheet_exports_to_gdp` hybrid logic (Phase 3 — lives on external dynamics)
- B1 LCU GDP compounding for public (Phase 6 — public-specific)

## Delete criteria

When v2 macro shocks are green, legacy `stress/shocks.py` can remain as a
facade re-export until Phase 8; do not delete until full cutover.
