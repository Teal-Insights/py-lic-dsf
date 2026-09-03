# Phase 4 — ResidualFinancingEngine and split policies

**Status:** Complete  
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
| `ResidualPolicy` protocol | `src/lic_dsf/stress/resfin/policy.py` |
| `CappedResidualPolicy` | same |
| `AbsoluteResidualPolicy` | same |
| `ResidualFinancingEngine` | `src/lic_dsf/stress/resfin/engine.py` |
| `ResidualFinancingResult` | same |
| Overlay types (keep) | Re-export from `residual_pv.py` via `resfin/types.py` |
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
`ScenarioSpec` for B2 selects `AbsoluteResidualPolicy` via
`ResidualPolicyKind.ABSOLUTE` (wired in the runner for B1/B2 public loops).

### `ResidualFinancingEngine`

**Takes:**

- `ResidualFill` or gaps + policy
- `ResidualFinancingParams`
- `years`, `discount_rate`
- Mode: `external_dsa` (100% ext MLT) vs `public_dsa` (J-column shares)

**Methods:**

- `build_external_overlay(gap_usd) -> ResFinOverlay`
- `build_public_overlay(fill, *, deflator) -> PublicResFinOverlay`
- `solve_public_with_gfn_feedback(...)` — fixed-point: GFN → gap → fill →
  overlays → GFN service (calls legacy `estimate_b1_public_gfn` until Phase 6)

### `ResidualFinancingResult`

**Fields:**

- `external: ResFinOverlay | None`
- `public: PublicResFinOverlay | None`
- `fill: ResidualFill | None`
- `converged: bool`
- `iterations: int`
- `public_gap: pd.Series | None` (R67)

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
| `_converged_external_gap` interest loop | `ExternalDebtDynamics` + engine |

## Implementation tasks

1. [x] Re-export overlay dataclasses from `stress/resfin/types.py`.

2. [x] Implement `CappedResidualPolicy` — wrap `split_residual_financing`
   capped branch.

3. [x] Implement `AbsoluteResidualPolicy` — absolute branch; B2
   `couple_ext_r86` passes Phase 3 gap into the public loop.

4. [x] Implement `ResidualFinancingEngine.build_external_overlay`.

5. [x] Public GFN ↔ ResFin fixed-point via legacy `estimate_b1_public_gfn`.

6. [x] Document tolerances: `PUBLIC_GAP_TOL=1e-6` LCU,
   `EXTERNAL_INTEREST_TOL=1e-9` USD.

## Differential testing

Phase 0 ResFin probes:

| Sheet | Scenario | Rows |
|-------|----------|------|
| `PV Stress` | B3 ext | R46/49/52/53 |
| `PV_ResFin_pub` | B1 pub | R67, E72/75/77/78, E85/90/91, E98/99 |

Tests:

- External overlay from Excel B3 gap matches `PV Stress` rows
- Converged B3 overlay matches legacy Python (Excel R86 still drifts — KNOWN_GAPS)
- Public B1 iterative fill matches `PV_ResFin_pub`
- Capped vs absolute synthetic splits

**Tolerance:** `1e-6` on PV and flow series.

## Definition of done

- [x] B3 external ResFin overlay probes green (Excel gap → overlay)
- [x] B1 public ResFin fill probes green (iterative GFN loop)
- [x] `AbsoluteResidualPolicy` implemented and unit-tested
- [x] Single `ResidualFinancingEngine` used by dynamics + runner
- [x] Legacy `residual_pv.py` still importable from `lic_dsf.stress` until Phase 8

## Out of scope

- `MarketAccessAddon` (Phase 7)
- B6 add.int from `PV_Base-add.cost.mkt` (Phase 7)
- Full `PublicGFNIdentity` (Phase 6 — engine may call legacy GFN temporarily)

## Delete criteria

Delete duplicate loops in `scenario.py` / `public.py` when Phases 5–6 ratio
probes pass using v2 engine exclusively.
