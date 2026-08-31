# Phase 1 — StressContext and ScenarioSpec

**Status:** Not started  
**Depends on:** [Phase 0](phase-00-test-harness.md)  
**Blocks:** Phases 2–8

## Goal

Introduce immutable run context and declarative scenario recipes. Replace
scattered `run_b*_external` / `run_b*_public` knowledge with a single registry
that encodes Excel semantics (policies, coupling, output bindings).

## Prerequisites

- Phase 0 acceptance criteria documented
- Familiarity with Input 6 / Input 7 loaders (`lic_dsf.load`)

## Deliverables

| Item | Location |
|------|----------|
| `StressContext` | `src/lic_dsf/stress_v2/context.py` |
| `ScenarioSpec` | `src/lic_dsf/stress_v2/spec.py` |
| `ScenarioRegistry` | `src/lic_dsf/stress_v2/spec.py` |
| `OutputBinding` | `src/lic_dsf/stress_v2/spec.py` |
| Unit tests (no numeric parity) | `tests/test_stress_v2_spec.py` |
| Empty `StressScenarioRunner` stub | `src/lic_dsf/stress_v2/runner.py` |

## Class responsibilities

### `StressContext`

**Takes:**

- `MacroDebtBook macro`
- `ExternalDebtBook external`
- `BaselineExternalBook ext_base`
- `BaselinePublicBook pub_base`
- `Input6StandardParams input6`
- `ResidualFinancingParams residual`
- Optional `TailoredParams tailored`
- Optional `market_access: bool` (from Input 1)

**Responsibilities:**

- Immutable anchor for one workbook evaluation
- Factory: `@classmethod from_workbook(path) -> StressContext` wrapping
  `load_core()` + Input 6/7/tailored loaders
- No shock or ratio computation

### `ScenarioSpec`

**Takes:**

- `StressScenarioId id` (reuse from `stress/types.py`)
- `ShockKind` enum: `HISTORICAL`, `GDP`, `PRIMARY_BALANCE`, `EXPORTS`,
  `OTHER_FLOWS`, `FX`, `COMBO`, `TAILORED_*`
- `ResidualPolicy` reference: `CappedPolicy` | `AbsolutePolicy`
- Flags:
  - `market_access: bool`
  - `couple_ext_r86: bool` — wire external gap into public split
  - `fx_revalue_portfolio: bool` — LC-NR reval on B5/B6
  - `ext_r86_zero: bool` — B1 GDP external (gap ~0)
- `OutputBinding` — which ratio book feeds Output 3-1 B2 rows

**Responsibilities:**

- Single source of truth for “what does this Excel B-sheet scenario mean?”
- Lookup: `ScenarioRegistry.get("B2_PrimaryBalance")`

### `OutputBinding`

**Fields:**

- `output_31_source: Literal["external", "public_external_methods"]`
- `output_32_source: Literal["public"]`

Documents the Excel Chart Data quirk: Output 3-1 B2 uses public book external
ratio methods, not `B2_PB_*_ext`.

## Scenario registry (checklist)

| ID | ShockKind | ResidualPolicy | market_access | couple_ext_r86 | ext_r86_zero | fx_revalue |
|----|-----------|----------------|---------------|----------------|--------------|------------|
| A1_Historical | HISTORICAL | Capped | false | false | false | false |
| B1_GDP | GDP | Capped | false | false | **true** | false |
| B2_PrimaryBalance | PRIMARY_BALANCE | **Absolute** | from Input 1 | **true** | false | false |
| B3_Exports | EXPORTS | Capped | false | false | false | false |
| B4_OtherFlows | OTHER_FLOWS | Capped | false | false | false | false |
| B5_FX | FX | Capped | false | false | false | **true** |
| B6_Combo | COMBO | Capped | false | false | false | **true** |
| A2_Custom | TAILORED | … | … | … | … | … |
| C1–C4 | TAILORED | … | … | … | … | … |

Fill tailored rows in Phase 8; stub entries here with `NotImplementedError`.

## Implementation tasks

1. Create `stress_v2/` package with `__init__.py` (minimal exports).

2. Implement `StressContext` + `from_workbook()`.

3. Implement `ScenarioSpec`, `ScenarioRegistry.STANDARD`, `ScenarioRegistry.TAILORED`.

4. Add `StressScenarioRunner.run(spec) -> NotImplementedError` stub.

5. Write registry tests:
   - Every `StressScenarioId` in `types.py` has a spec
   - B2 uses `AbsolutePolicy`
   - B1 external has `ext_r86_zero=True`
   - Output 3-1 B2 binding is `public_external_methods`

6. Do **not** wire into `lic_dsf.stress` yet.

## Differential testing

No numeric probes in this phase. Tests are structural only.

Optional: snapshot test that registry JSON/YAML serializes deterministically for
review in PRs.

## Definition of done

- [ ] `StressContext.from_workbook(WORKBOOK)` returns wired baseline books
- [ ] `ScenarioRegistry` covers all standard A/B scenario IDs
- [ ] B2 / B1 flags match Excel semantics documented in registry table
- [ ] `tests/test_stress_v2_spec.py` green
- [ ] No changes to legacy `lic_dsf.stress` behavior

## Migration note

Keep `Input6StandardParams`, `StressScenarioId`, `ThresholdRule` in
`stress/types.py`. Import into v2; do not duplicate.
