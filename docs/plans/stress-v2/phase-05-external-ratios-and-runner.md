# Phase 5 — StressExternalRatios and external runner

**Status:** Not started  
**Depends on:** [Phase 3](phase-03-external-debt-dynamics.md), [Phase 4](phase-04-residual-financing-engine.md)  
**Blocks:** Phase 7 (partial), Phase 8

## Goal

Thin ratio projection layer for **external** stress scenarios plus a runner
that composes macro path → external dynamics → ResFin → ratios. Match B-sheet
rows 35/36/39/40 and Output 3-1 for external scenarios.

## Prerequisites

- `ShockedMacroPath`, `ExternalGapResult`, `ResidualFinancingResult`
- Phase 0 B-sheet ratio probes and `output_31_probes`
- Legacy reference: `StressExternalBook` in `stress/scenario.py`

## Deliverables

| Item | Location |
|------|----------|
| `StressExternalRatios` | `src/lic_dsf/stress_v2/ratios/external.py` |
| `ExternalScenarioRunner` | `src/lic_dsf/stress_v2/runner/external.py` |
| `StressScenarioResult.external` | `src/lic_dsf/stress_v2/result.py` |
| `to_output31_rows()` helper | `src/lic_dsf/stress_v2/output_map.py` |
| Parity tests | `tests/test_stress_v2_external_ratios.py` |

## Class responsibilities

### `StressExternalRatios`

**Takes:**

- `ShockedMacroPath path`
- `ExternalDebtBook external`
- `ResidualFinancingResult.external` (ResFin overlay)
- `ExternalDebtDynamics` (for `exports_to_gdp`)

**Methods** (mirror `BaselineExternalBook` / `StressExternalBook`):

- `pv_ppg_usd() -> pd.Series`
- `pv_ppg_external_to_gdp() -> pd.Series` — B-sheet R35
- `pv_ppg_external_to_exports() -> pd.Series` — R36
- `ppg_debt_service_to_exports() -> pd.Series` — R39
- `ppg_debt_service_to_revenue() -> pd.Series` — R40

**Responsibilities:**

- Numerators: baseline `external.total_pv_of_debt()` + ResFin PV; baseline service
  + ResFin service
- Denominators: shocked macro from `ShockedMacroPath`
- Clamp negative ratios at 0 where Excel does

No scenario running logic inside this class.

### `ExternalScenarioRunner`

**Takes:** `StressContext`, `ScenarioSpec`

**Pipeline:**

1. `MacroShock.apply` → `ShockedMacroPath`
2. If `spec.ext_r86_zero`: zero gap; else `ExternalDebtDynamics.compute_gap_converged`
3. `ResidualFinancingEngine.build_external_overlay` (external DSA mode)
4. `StressExternalRatios(...)` → return in `StressScenarioResult`

### `StressScenarioResult`

Add fields: `scenario_id`, `external_ratios`, optional debug trace
(gap, iterations).

## Port map from legacy

| Legacy | v2 |
|--------|-----|
| `StressExternalBook` | `StressExternalRatios` |
| `run_b*_external` | `ExternalScenarioRunner.run` |
| `run_standard_external_stress` | `StressSuite.run_external_standard` |
| `run_a1_historical_external` | Registry entry + runner |
| `_build_book`, `_zero_overlay` | Runner internals |

## Output 3-1 mapping

Build SUT table keys matching `output_31_probes`:

```python
(indicator, scenario_label) -> pd.Series[years]
```

Scenario labels from `_EXT_SCENARIO_LABELS` in `output/stress.py`.

**Exclude B2 from external runner** — Output 3-1 B2 comes from public book
(Phase 6); document in `OutputBinding`.

## Implementation tasks

1. Port ratio methods from `StressExternalBook` verbatim first.

2. Implement `ExternalScenarioRunner` using v2 components only.

3. Implement `StressSuite.run_external_standard(ctx) -> dict[id, Result]`.

4. Add `build_output31_external_sut(results, ext_base, ...)`.

5. Wire `LIC_DSF_STRESS_V2=1` to use v2 SUT in Phase 0 report script.

6. Parametrize B-sheet ratio probes for B1, B3, B4, B5, B6, A1.

## Differential testing

### Layer 1 — B-sheet ratios

| Scenario | Rows 35/36/39/40 |
|----------|------------------|
| B1_GDP | Denominator-only move |
| B3_Exports | ResFin + exports |
| B5_FX | FX + ResFin |
| B6_Combo | Partial (add.int Phase 7) |
| A1_Historical | Historical path |

### Layer 2 — Output 3-1

Filter `output_31_probes` to scenarios: Baseline, A1, B1, B3–B6, C1 (when
tailored wired), **excluding B2**.

```python
def test_output_31_external_scenarios_v2():
    sut = build_output31_from_v2(...)
    probes = [p for p in output_31_probes(WORKBOOK) if p.sut_key[1] != "B2. Primary balance"]
    ...
    assert_all_passed(compare_probes(excel, sut))
```

**Tolerance:** `1e-6`.

## Definition of done

- [ ] B-sheet ratio probes green for B1, B3, B5, A1
- [ ] Output 3-1 probes green for same scenarios (all 4 indicators × 11 years)
- [ ] B6 passes except add.int rows deferred to Phase 7 (document if partial)
- [ ] `StressExternalRatios` has no shock or gap logic
- [ ] Legacy `run_standard_external_stress` can delegate to v2 behind flag

## Out of scope

- Public ratios (Phase 6)
- B2 Output 3-1 rows (Phase 6–7)
- Tailored external C* (Phase 8)
- `CachedStressExternalBook` (delete at Phase 8)

## Delete criteria

Remove `StressExternalBook` and external runners from `stress/scenario.py` when
full external Output 3-1 probes (excl. B2, tailored) pass without legacy fallback.
