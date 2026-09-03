# Phase 5 — StressExternalRatios and external runner

**Status:** Complete  
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
| `StressExternalRatios` | `src/lic_dsf/stress/ratios/external.py` |
| `ExternalScenarioRunner` | `src/lic_dsf/stress/runner/external.py` |
| `StressScenarioResult` | `src/lic_dsf/stress/result.py` |
| `to_output31_rows()` / table builder | `src/lic_dsf/stress/output_map.py` |
| Parity tests | `tests/test_stress_v2_external_ratios.py` |

## Class responsibilities

### `StressExternalRatios`

**Takes:**

- `ShockedMacroPath path`
- `ExternalDebtBook external`
- `ResFinOverlay` (from Phase 4)
- Optional `additional_borrowing_interest` (B6 — Phase 7)

**Methods** (mirror `BaselineExternalBook` / `StressExternalBook`):

- `pv_ppg_usd() -> pd.Series`
- `pv_ppg_external_to_gdp() -> pd.Series` — B-sheet R35
- `pv_ppg_external_to_exports() -> pd.Series` — R36
- `ppg_debt_service_to_exports() -> pd.Series` — R39
- `ppg_debt_service_to_revenue() -> pd.Series` — R40

No scenario running logic inside this class.

### `ExternalScenarioRunner`

**Pipeline:**

1. `MacroShock.apply` → `ShockedMacroPath`
2. `ExternalDebtDynamics.compute_gap_converged` (honours `ext_r86_zero`)
3. `ResidualFinancingEngine.build_external_overlay`
4. Optional public GFN ResFin for B1/B2 (Phase 4 continuity)
5. `StressExternalRatios(...)` → `StressScenarioResult`

`StressScenarioRunner` is an alias of `ExternalScenarioRunner`.

### `StressSuite.run_external_standard`

Runs all `ScenarioRegistry.STANDARD` entries with
`output_31_source == "external"` (skips B2).

## Port map from legacy

| Legacy | v2 |
|--------|-----|
| `StressExternalBook` | `StressExternalRatios` |
| `run_b*_external` | `ExternalScenarioRunner.run` |
| `run_standard_external_stress` | `StressSuite.run_external_standard` (+ flag delegate) |
| `run_a1_historical_external` | Registry + runner |

## Output 3-1 mapping

`build_output31_external_table` builds MultiIndex keys matching
`output_31_probes`. B2 excluded (`OUTPUT31_EXTERNAL_EXCLUDE`).

## Implementation tasks

1. [x] Port ratio methods from `StressExternalBook`
2. [x] `ExternalScenarioRunner` using v2 components
3. [x] `StressSuite.run_external_standard`
4. [x] `build_output31_external_table` / `to_output31_rows`
5. [x] Wire v2 SUT for `bsheet_ext` + `output31` in Phase 0 report
6. [x] Expand B-sheet catalog (A1, B1, B3–B6)
7. [x] Flag-delegate `run_standard_external_stress` when
   `LIC_DSF_STRESS_V2` + `workbook_path`

## Differential testing

- B-sheet R35/36/39/40: Excel for A1/B1; legacy-lock for B3/B5 (KNOWN_GAPS)
- Output 3-1: Excel for Baseline/A1/B1/B4; legacy-lock for B3/B5/B6
- B6 add.int still Phase 7

**Tolerance:** `1e-6` vs Excel; `1e-9` vs legacy lock.

## Definition of done

- [x] B-sheet ratio probes green for B1, A1 (Excel); B3/B5 (legacy lock)
- [x] Output 3-1 probes green for Baseline/A1/B1/B4 (Excel); B3/B5/B6 (legacy)
- [x] B6 without add.int matches legacy; Excel add.int deferred to Phase 7
- [x] `StressExternalRatios` has no shock or gap logic
- [x] Legacy `run_standard_external_stress` can delegate to v2 behind flag

## Out of scope

- Public ratios (Phase 6)
- B2 Output 3-1 rows (Phase 6–7)
- Tailored external C* (Phase 8)
- `CachedStressExternalBook` (delete at Phase 8)
- B6 market add.int (Phase 7)

## Delete criteria

Remove `StressExternalBook` and external runners from `stress/scenario.py` when
full external Output 3-1 probes (excl. B2, tailored) pass without legacy fallback.
