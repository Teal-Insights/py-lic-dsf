# Phase 6 — PublicGFNIdentity and StressPublicRatios

**Status:** Not started  
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
| `PublicGFNIdentity` | `src/lic_dsf/stress_v2/public_gfn.py` |
| `StressPublicRatios` | `src/lic_dsf/stress_v2/ratios/public.py` |
| `PublicScenarioRunner` | `src/lic_dsf/stress_v2/runner/public.py` |
| Parity tests | `tests/test_stress_v2_public_ratios.py` |

## Class responsibilities

### `PublicGFNIdentity`

**Takes:**

- `StressContext`
- `ShockedMacroPath`
- Optional `ResidualFinancingResult.public` (for iteration)
- `inflation_elasticity` from Input 6
- Optional precomputed `gdp_lcu: pd.Series`

**Methods:**

- `gdp_lcu() -> pd.Series` — B1 R41 LCU compounding (port `_b1_public_gdp_lcu`)
- `primary_deficit_lcu() -> pd.Series` — R88
- `compute_gfn(resfin: PublicResFinOverlay | None) -> pd.Series` — R90 (port
  `estimate_b1_public_gfn`)
- `compute_gap(baseline_gfn, stressed_gfn) -> pd.Series` — R67 public residual

**Responsibilities:**

- Excel public GFN block only
- Knows revenue scales with shocked GDP (B1) vs expenditure from shocked inputs (B2)
- Does not build ResFin instruments (delegates to Phase 4 engine)

### `StressPublicRatios`

**Takes:**

- `ShockedMacroPath` / `PublicGFNIdentity` for denominators
- `StressContext.pub_base` for baseline revenue scaling
- `ResidualFinancingResult.public`

**Public methods:**

- `pv_public_debt_to_gdp()`
- `pv_public_debt_to_revenue_grants()`
- `debt_service_to_revenue_grants()`
- `debt_service_to_gdp()` (optional; not all Output 3-2 probes)

**External-facing methods** (for Output 3-1 B2):

- `pv_ppg_external_to_gdp()`
- `pv_ppg_external_to_exports()`
- `ppg_debt_service_to_exports()`
- `ppg_debt_service_to_revenue()`

Port from legacy `StressPublicBook` — these use public ResFin blocks and
market-access dual overlays when enabled.

### `PublicScenarioRunner`

**Pipeline:**

1. Macro shock → `ShockedMacroPath`
2. Loop: `PublicGFNIdentity.compute_gfn` ↔ `ResidualFinancingEngine.solve_public`
3. Apply `ScenarioSpec.residual_policy` (Absolute for B2)
4. `StressPublicRatios` → `StressScenarioResult.public_ratios`

## Port map from legacy

| Legacy | v2 |
|--------|-----|
| `_b1_public_gdp_lcu` | `PublicGFNIdentity.gdp_lcu` |
| `estimate_b1_public_gfn` | `PublicGFNIdentity.compute_gfn` |
| `public_residual_gap` | `PublicGFNIdentity.compute_gap` |
| `_b1_primary_deficit_lcu` | internal |
| `StressPublicBook` | `StressPublicRatios` |
| `run_b*_public` | `PublicScenarioRunner.run` |
| `run_standard_public_stress` | `StressSuite.run_public_standard` |

## Implementation tasks

1. Port `PublicGFNIdentity` from `public.py` helper functions.

2. Port `StressPublicRatios` ratio methods; keep baseline rev/GDP scaling for B1.

3. Wire public ResFin fixed-point through `ResidualFinancingEngine` (Phase 4).

4. Implement `PublicScenarioRunner` for B1 first, then B2–B6.

5. Implement `build_output32_sut` and Output 3-1 B2 rows via
   `StressPublicRatios` external methods + `OutputBinding`.

6. Add `StressSuite.run_public_standard(ctx, market_access)`.

## Differential testing

### Layer 1 — Public B-sheet

| Sheet | Rows | Scenario |
|-------|------|----------|
| `B1_GDP_pub` | 41, 90, 13 | B1 |
| `B1_GDP_pub` | 43 | PV/revenue |
| `B2_PB_mkt_pub` / `B2_PB_non_mkt_pub` | 13, 90 | B2 (Phase 7 for full) |

Existing tests to migrate:

- `test_pv_resfin_pub_b1_fill_parity_with_excel_gap`
- `test_b1_public_gfn` patterns in `test_residual_financing_applied.py`

### Layer 2 — Output 3-2

Full `output_32_probes` for:

- Baseline, A1, B1 (minimum)
- Expand to B2–B6, A2, C1 as runners complete

### Layer 3 — Output 3-1 B2

Probes with `sut_key[1] == "B2. Primary balance"` — currently relaxed to `1e-3`
on 2026 PV; target `1e-6` by Phase 7.

**Tolerance:** `1e-6` for B1; document B2 gaps until Phase 7.

## Definition of done

- [ ] B1 public B-sheet probes green (GFN R90, PV/GDP R13, GDP R41)
- [ ] Output 3-2 probes green for Baseline + A1 + B1 (all 3 indicators)
- [ ] Output 3-1 B2 PV probes green for 2024–2025 at `1e-6`
- [ ] `PublicGFNIdentity` separated from ratio projection
- [ ] Legacy `run_b1_gdp_public` delegating to v2 behind flag

## Out of scope

- Full B2 market access add.int (Phase 7)
- `ext_r86` coupling into split (Phase 7)
- Tailored public A2/C* (Phase 8)

## Delete criteria

Remove `StressPublicBook` and public runners from `stress/public.py` when
Output 3-2 standard scenarios pass via v2 only.
