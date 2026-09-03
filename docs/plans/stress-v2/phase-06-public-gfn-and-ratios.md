# Phase 6 — PublicGFNIdentity and StressPublicRatios

**Status:** Complete  
**Depends on:** [Phase 2](phase-02-shocked-macro-path.md), [Phase 4](phase-04-residual-financing-engine.md)  
**Blocks:** Phase 7, Phase 8

## Goal

Implement the public stress leg: GFN identity, three-way ResFin integration,
public sustainability ratios, and **external-ratio methods for Output 3-1 B2**.

## Prerequisites

- `ShockedMacroPath`, `ResidualFinancingEngine`
- Phase 0 public B-sheet probes (R90, R13, R41)
- Legacy reference: `lic_dsf.stress.public`

## Deliverables

| Item | Location |
|------|----------|
| `PublicGFNIdentity` | `src/lic_dsf/stress/public_gfn.py` |
| `StressPublicRatios` | `src/lic_dsf/stress/ratios/public.py` |
| `PublicScenarioRunner` | `src/lic_dsf/stress/runner/public.py` |
| Parity tests | `tests/test_stress_v2_public_ratios.py` |

## Class responsibilities

### `PublicGFNIdentity`

**Methods:**

- `gdp_lcu() -> pd.Series` — B1 R41
- `primary_deficit_lcu() -> pd.Series` — R88
- `compute_gfn(resfin) -> pd.Series` — R90
- `compute_gap(...) -> pd.Series` — R67

Does not build ResFin instruments (Phase 4 engine).

### `StressPublicRatios`

Public Output 3-2 methods + Output 3-1 B2 external-ratio methods. Delegates
ratio math to legacy `StressPublicBook` during strangler migration.

### `PublicScenarioRunner`

Macro shock → `PublicGFNIdentity` ↔ `ResidualFinancingEngine` (with
`ScenarioSpec.residual_policy`, Absolute for B2) → `StressPublicRatios`.

External R86 coupling into the public split remains Phase 7 (zero R86 for now).

## Implementation tasks

1. [x] `PublicGFNIdentity`
2. [x] `StressPublicRatios` (+ B2 external methods)
3. [x] Wire engine fixed-point through `PublicGFNIdentity`
4. [x] `PublicScenarioRunner` + `StressSuite.run_public_standard`
5. [x] `build_output32_table` + Output 3-1 B2 via public results
6. [x] Flag-delegate `run_b1_gdp_public` when `LIC_DSF_STRESS_V2` + workbook

## Differential testing

- B1 R41/R90 vs Excel; R13/R95/R93 legacy-lock (KNOWN_GAPS)
- Output 3-2 Baseline vs Excel; A1/B1 legacy-lock
- Output 3-1 B2 PV 2024–2025 vs Excel at `1e-6`

## Definition of done

- [x] B1 public B-sheet GFN R90 + GDP R41 green vs Excel
- [x] Output 3-2 Baseline green; A1/B1 match legacy
- [x] Output 3-1 B2 PV 2024–2025 at `1e-6`
- [x] `PublicGFNIdentity` separated from ratio projection
- [x] Legacy `run_b1_gdp_public` can delegate to v2 behind flag

## Out of scope

- Full B2 market access add.int timing (Phase 7 refinements)
- `ext_r86` coupling into split (Phase 7)
- Tailored public A2/C* (Phase 8)

## Delete criteria

Remove `StressPublicBook` and public runners from `stress/public.py` when
Output 3-2 standard scenarios pass via v2 only.
