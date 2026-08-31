# Phase 3 — ExternalDebtDynamics

**Status:** Not started  
**Depends on:** [Phase 2](phase-02-shocked-macro-path.md)  
**Blocks:** Phases 4, 5, 7

## Goal

Encapsulate the Excel **external B-sheet debt identity** (R12–R30 → R86 residual
gross borrowing) as a stateful engine. This is the foundation for external
ResFin and external stress ratios.

## Prerequisites

- `ShockedMacroPath` from Phase 2
- Phase 0 external gap probes (R86, R89)
- Legacy reference: `lic_dsf.stress.bound`

## Deliverables

| Item | Location |
|------|----------|
| `ExternalDebtDynamics` | `src/lic_dsf/stress_v2/external_dynamics.py` |
| `ExternalGapResult` | `src/lic_dsf/stress_v2/external_dynamics.py` |
| `bsheet_exports_to_gdp` (moved) | same module or `src/lic_dsf/stress_v2/bsheet.py` |
| Parity tests | `tests/test_stress_v2_external_dynamics.py` |

## Class responsibilities

### `ExternalDebtDynamics`

**Takes:**

- `ShockedMacroPath path`
- `ExternalDebtBook external` (baseline portfolio; FX-adjusted in Phase 7)
- `BaselineExternalBook ext_base` (for hybrid exports/GDP)
- Optional `resfin_interest: pd.Series` (iteration feedback)
- Optional kwargs for B5/B6: `fx_depreciation_pct`, passthrough, elasticities,
  `additional_borrowing_interest`

**Methods:**

- `exports_to_gdp() -> pd.Series` — B-sheet R19 logic (port `bsheet_exports_to_gdp`)
- `compute_gap() -> ExternalGapResult` — R86 residual gross borrowing
- `compute_gap_converged(max_iter=25) -> ExternalGapResult` — iterate with
  ResFin interest feedback (port `_converged_external_gap`)

### `ExternalGapResult`

**Fields:**

- `gap: pd.Series` — R86 USD
- `resfin_interest: pd.Series` — converged interest used in loop
- `iterations: int`
- `residual_borrowing: pd.Series` — alias for gap (Excel R99 path)

## Port map from legacy

| Legacy | v2 |
|--------|-----|
| `external_residual_borrowing` | `ExternalDebtDynamics.compute_gap` |
| `bsheet_exports_to_gdp` | `ExternalDebtDynamics.exports_to_gdp` |
| `historical_identity_pins` | Used by A1 spec before dynamics |
| `_converged_external_gap` | `compute_gap_converged` |

## Scenario-specific behavior

| Scenario | Gap behavior |
|----------|--------------|
| B1 GDP | Gap ≈ 0 (document in spec `ext_r86_zero`); skip iteration |
| B3 Exports | Non-zero; converged loop |
| B4 Other flows | Non-zero; converged loop |
| B5 FX | Non-zero; NX year + FX passthrough kwargs |
| B6 Combo | Non-zero; half-size shocks + add.int (Phase 7) |
| A1 Historical | Historical CA/FDI pins + converged loop |

## Implementation tasks

1. Port `bound.py` into `ExternalDebtDynamics` class; keep formulas identical
   on first pass.

2. Inject `ShockedMacroPath` instead of separate baseline/shocked macro books.

3. Add factory: `ExternalDebtDynamics.from_context(ctx, path, spec)`.

4. Expose intermediate series for probes: R89, R87 where applicable.

5. Wire into `StressScenarioRunner` — returns `ExternalGapResult` alongside
   `ShockedMacroPath` (still no ratios).

## Differential testing

Phase 0 B-sheet external gap probes:

| Sheet | Rows | Notes |
|-------|------|-------|
| `B3_Exports_ext` | 86, 89 | Existing test: `test_b3_external_gap_r86_r89_parity` |
| `B5_depreciation_ext` | 87 | Existing test: `test_b5_fx_gap_r87_parity` |
| `B1_GDP_ext` | 86 | Expect ~0 |
| `B4_other flows_ext` | 86 | Non-zero |
| `A1_historical_ext` | 86 | With historical pins |

Also test `exports_to_gdp` vs B-sheet R19 for B1 and B3.

**Tolerance:** `1e-6` on gap series for projection years.

## Definition of done

- [ ] Gap probes green for B1 (zero), B3, B5 minimum
- [ ] `exports_to_gdp` matches B-sheet R19 for B1 and B3
- [ ] Converged loop terminates within 25 iterations for B3/B5
- [ ] Legacy `bound.py` tests still pass (or moved to v2 tests)
- [ ] No ResFin PV instrument built yet (Phase 4)

## Out of scope

- `resfin_instrument` / PV overlay (Phase 4)
- LC-NR FX portfolio rebuild (Phase 7)
- Stress external ratios (Phase 5)

## Delete criteria

Delete `stress/bound.py` when all gap + exports/GDP probes pass through v2 and
Phase 5 external ratios are green.
