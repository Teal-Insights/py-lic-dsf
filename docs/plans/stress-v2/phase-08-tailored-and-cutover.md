# Phase 8 — Tailored scenarios, facade cutover, and legacy removal

**Status:** Not started  
**Depends on:** [Phase 7](phase-07-coupling-and-market-access.md)  
**Blocks:** Nothing (final phase)

## Goal

Wire tailored A2/C* scenarios, swap the public `lic_dsf.stress` API to delegate
to v2, achieve full Output 3-1 / 3-2 catalog parity, and delete legacy stress
implementation code.

## Prerequisites

- Standard A/B scenarios green through Phase 7
- Phase 0 full catalog tests ready (currently xfail / partial)
- Legacy reference: `lic_dsf.stress.tailored`, `CachedStressExternalBook`

## Deliverables

| Item | Location |
|------|----------|
| Tailored shock adapters | `src/lic_dsf/stress_v2/tailored/` |
| `StressSuite.run_all(ctx)` | `src/lic_dsf/stress_v2/suite.py` |
| Facade in `lic_dsf.stress` | `src/lic_dsf/stress/__init__.py` + thin wrappers |
| Full catalog tests | `tests/test_stress_v2_full_catalog.py` |
| Removed legacy modules | Delete after green CI |

## Tailored scenario integration

Port `stress/tailored.py` into v2 with `ScenarioSpec` entries:

| ID | Excel source | Notes |
|----|--------------|-------|
| A2_Custom | Customized Scenario sheets | External + public paths |
| C1_CombinedCL | `C1_Combined CL` | CL flow injection |
| C2_NaturalDisaster | Input 6 tailored | Skip when Excel `n.a.` |
| C3_Commodity | Commodity price params | Export scaling |
| C4_Market | `market_cost_bps` | FX + financing cost |

Each tailored adapter:

1. Mutates `MacroDebtInputs` or flow series
2. Delegates to `CoupledScenarioRunner` or external/public runner
3. Respects Chart Data `IF(I17=1, …, n.a.)` off switches

Wire **tailored external** into Output 3-1 bundle (currently missing from
`test_stress_output_tables._bundle`).

## Facade cutover strategy

### Step 1 — Delegate behind stable API

```python
# lic_dsf/stress/__init__.py
def run_b1_gdp_external(macro, external, input6, residual, **kw):
    from lic_dsf.stress_v2.facade import run_scenario
    return run_scenario("B1_GDP", ...)
```

Keep return types compatible: either retain `StressExternalBook` as a thin
wrapper over `StressExternalRatios` or deprecate with matching protocol.

### Step 2 — Update output layer

`output_31_table` / `output_32_table` call v2 `StressSuite` when building SUT.

### Step 3 — Remove feature flag

Delete `LIC_DSF_STRESS_V2`; v2 is the only path.

### Step 4 — Delete legacy files

| File | Condition |
|------|-----------|
| `stress/scenario.py` | Full Output 3-1 external probes green |
| `stress/public.py` | Full Output 3-2 probes green |
| `stress/bound.py` | Moved to v2 Phase 3 |
| `stress/shocks.py` | Moved to v2 Phase 2 |
| `stress/residual_pv.py` | Moved to v2 Phase 4 |
| `stress/tailored.py` | Moved to v2 tailored |
| `stress/workbook.py` | `CachedStressExternalBook` deleted |
| `stress/compare.py` | Update to import v2 SUT builder |

Keep:

- `stress/types.py` (or move to `stress_v2/types.py` and re-export)
- Thin facade modules if needed for import stability

## Full catalog acceptance tests

```python
def test_output_31_full_catalog_v2():
    sut = build_output31_from_v2_suite(WORKBOOK)
    probes = output_31_probes(WORKBOOK)
    excel = read_cached_output(WORKBOOK, probes)
    excel = excel[excel["excel_value"].map(lambda v: isinstance(v, (int, float)))]
    report = compare_probes(excel, sut)
    assert report["missing_sut"].sum() == 0
    assert_all_passed(report)


def test_output_32_full_catalog_v2():
    ...
```

Optional live Excel smoke:

- `@pytest.mark.live_excel` on full catalog or representative subset

## Documentation updates

- Update `docs/08-stress-dsa.qmd` with v2 architecture
- Update `docs/01-excel-map.qmd` package roles
- Archive or remove `docs/plans/stress-v2/` phase status headers → **Complete**
- Update demos: `demo/stress_dsa.ipynb`, `demo/output_2_1_3_1.ipynb`

## Implementation tasks

1. Port tailored runners to v2; complete `ScenarioRegistry.TAILORED`.

2. Implement `StressSuite.run_all` returning results for Output 3-1/3-2 tables.

3. Add `test_stress_v2_full_catalog.py` — the program completion proof.

4. Switch `lic_dsf.stress` exports to v2 facade.

5. Migrate `tests/test_stress_dsa.py`, `test_stress_output_tables.py`,
   `test_residual_financing_applied.py` to v2 or merge into v2 parity module.

6. Delete legacy implementation files; keep git history.

7. Run `scripts/stress_parity_report.py --sut v2` — expect 100% pass, 0
   missing_sut.

## Definition of done (program complete)

- [ ] `test_output_31_full_catalog_v2` passes at `1e-6`
- [ ] `test_output_32_full_catalog_v2` passes at `1e-6`
- [ ] All B-sheet and ResFin layer probes pass
- [ ] `CachedStressExternalBook` and `load_cached_external_stress` removed
- [ ] No `workbook_path` required for any standard runner
- [ ] `lic_dsf.stress` public API unchanged for downstream imports
- [ ] CI green without `@pytest.mark.xfail` on v2 tests
- [ ] `stress_parity_report.py` documents zero failures

## Rollback plan

Keep legacy code on a git tag `pre-stress-v2-cutover` before deletion. Facade
can temporarily re-import legacy if a regression is found post-merge.

## Post-cutover cleanup (optional)

- Rename `stress_v2` → `stress` internal package layout
- Consolidate ratio helpers with `lic_dsf.dsa`
- Add mypy strict on `stress_v2/`
