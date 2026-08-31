# Phase 4 — ResidualFinancingEngine and split policies

**Status:** Not started  
**Depends on:** [Phase 3](phase-03-external-debt-dynamics.md) (external gaps)  
**Also depends on:** Phase 6 stub for public gap input (can use legacy
`public_residual_gap` initially)  
**Blocks:** Phases 5, 6, 7

## Goal

Unify ResFin PV scheduling and fixed-point convergence in one engine. Replace
duplicated loops in `scenario.py` and `public.py` with explicit split policies
(`Capped` vs `Absolute` for B2).

## Prerequisites

- `ExternalGapResult` from Phase 3
- Phase 0 ResFin probes (`PV Stress`, `PV_ResFin_pub`)
- Legacy reference: `lic_dsf.stress.residual_pv`

## Deliverables

| Item | Location |
|------|----------|
| `ResidualPolicy` protocol | `src/lic_dsf/stress_v2/resfin/policy.py` |
| `CappedResidualPolicy` | same |
| `AbsoluteResidualPolicy` | same |
| `ResidualFinancingEngine` | `src/lic_dsf/stress_v2/resfin/engine.py` |
| `ResidualFinancingResult` | same |
| Overlay types (keep) | Reuse `ResFinOverlay`, `PublicResFinOverlay`, etc. |
| Parity tests | `tests/test_stress_v2_resfin.py` |

## Class responsibilities

### `ResidualPolicy` (protocol)

**Method:**

```python
def split(
    public_gap: pd.Series,
    external_gap: pd.Series,
    params: ResidualFinancingParams,
    fx: pd.Series,
) -> ResidualFill
```

| Implementation | Used by | Excel behavior |
|----------------|---------|----------------|
| `CappedResidualPolicy` | B1, B3–B6 | Gap capped by available financing |
| `AbsoluteResidualPolicy` | B2 | Full PB shock gap; uses ext R86 when coupled |

Fix legacy bug: `_run_public_stress` always used `modality="capped"`.

### `ResidualFinancingEngine`

**Takes:**

- `ResidualFill` or gaps + policy
- `ResidualFinancingParams`
- `years`, `discount_rate`
- Mode: `external_dsa` (100% ext MLT) vs `public_dsa` (J-column shares)

**Methods:**

- `build_external_overlay(gap_usd) -> ResFinOverlay`
- `build_public_overlay(fill) -> PublicResFinOverlay`
- `solve_public_with_gfn_feedback(...)` — fixed-point: GFN → gap → fill →
  overlays → GFN service (port `_run_public_stress` loop)

### `ResidualFinancingResult`

**Fields:**

- `external: ResFinOverlay | None`
- `public: PublicResFinOverlay | None`
- `fill: ResidualFill | None`
- `converged: bool`
- `iterations: int`

## Port map from legacy

| Legacy | v2 |
|--------|-----|
| `external_dsa_residual_params` | Engine mode flag |
| `public_dsa_residual_params` | Engine mode flag |
| `resfin_instrument` | `build_external_overlay` |
| `resfin_overlay_series` | internal |
| `split_residual_financing` | `ResidualPolicy.split` |
| `build_public_resfin_overlay` | `build_public_overlay` |
| `dom_mlt_resfin_series`, `dom_st_resfin_series` | internal |
| `_converged_external_gap` interest loop | Coordinate with `ExternalDebtDynamics` |

## Implementation tasks

1. Move overlay dataclasses to `stress_v2/resfin/types.py` or re-export from
   `residual_pv.py` during migration.

2. Implement `CappedResidualPolicy` — port existing `split_residual_financing`
   capped branch.

3. Implement `AbsoluteResidualPolicy` — port absolute branch; wire
   `external_gap` from Phase 3 when `spec.couple_ext_r86`.

4. Implement `ResidualFinancingEngine.build_external_overlay` — port
   `resfin_instrument` + `resfin_overlay_series`.

5. Implement public GFN ↔ ResFin fixed-point (can call legacy
   `estimate_b1_public_gfn` until Phase 6).

6. Single convergence tolerance: document `tol=1e-6` LCU for public,
   `1e-9` USD interest for external.

## Differential testing

Phase 0 ResFin probes:

| Sheet | Scenario | Rows |
|-------|----------|------|
| `PV Stress` | B3 ext | PV, interest, amort |
| `PV_ResFin_pub` | B1 pub | E75 PV ext, E78/E91 dom, E98 ST |
| `PV_ResFin_pub` | B1 pub | Fill vs gap (existing `test_pv_resfin_pub_b1_fill_parity`) |

Tests:

- External overlay from B3 gap matches `PV Stress` rows
- Public B1 iterative fill matches `PV_ResFin_pub` disbursement split
- `split_residual_financing` capped vs absolute with synthetic gaps

**Tolerance:** `1e-6` on PV and flow series.

## Definition of done

- [ ] B3 external ResFin overlay probes green
- [ ] B1 public ResFin fill probes green (iterative GFN loop)
- [ ] `AbsoluteResidualPolicy` implemented and unit-tested
- [ ] Single `ResidualFinancingEngine` replaces duplicate fixed-point code paths
- [ ] Legacy `residual_pv.py` still importable from `lic_dsf.stress` until Phase 8

## Out of scope

- `MarketAccessAddon` (Phase 7)
- B6 add.int from `PV_Base-add.cost.mkt` (Phase 7)
- Full `PublicGFNIdentity` (Phase 6 — engine may call legacy GFN temporarily)

## Delete criteria

Delete duplicate loops in `scenario.py` / `public.py` when Phases 5–6 ratio
probes pass using v2 engine exclusively.
