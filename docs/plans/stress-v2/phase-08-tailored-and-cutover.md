# Phase 8 — Tailored scenarios, facade cutover, and legacy removal

**Status:** Complete  
**Depends on:** [Phase 7](phase-07-coupling-and-market-access.md)  
**Blocks:** [Phase 9](phase-09-external-excel-parity.md) / [Phase 10](phase-10-public-excel-parity.md) (Excel numeric close)

## Goal

Wire tailored A2/C* scenarios, swap the public `lic_dsf.stress` API to delegate
to v2, achieve Output 3-1 / 3-2 catalog coverage (`missing_sut == 0`), and
deprecate Excel-cached B-sheet ratio loaders.

## Deliverables

| Item | Location |
|------|----------|
| Tailored shock adapters | `src/lic_dsf/stress/tailored/` |
| `StressSuite.run_all` / table builders | `src/lic_dsf/stress/suite.py` |
| Facade in `lic_dsf.stress` | `src/lic_dsf/stress/facade.py` + thin `run_*` wrappers |
| Full catalog tests | `tests/test_stress_v2_full_catalog.py` |
| Deprecated cached loader | `stress/workbook.py` warns; production uses Python runners |

## What shipped

1. Tailored `ScenarioRegistry` entries implemented; MacroShock adapters for A2/C1–C4.
2. `StressSuite.run_tailored_*`, `run_all`, `build_output31` / `build_output32`.
3. `lic_dsf.stress.run_*` delegates to v2 (no `LIC_DSF_STRESS_V2` flag).
4. Output 3-1 bundle includes tailored external; `missing_sut == 0` for full catalogs.
5. Excel-green subset (Baseline/A1/B1/B2 PV/B4) asserted at `1e-6`; remaining
   drifts documented in [`KNOWN_GAPS.md`](KNOWN_GAPS.md).

## Definition of done

- [x] `test_output_31_full_catalog_no_missing_sut` — zero missing SUT
- [x] `test_output_32_full_catalog_no_missing_sut` — zero missing SUT
- [x] Tailored A2/C* in Output 3-1
- [x] `load_cached_external_stress` deprecated (debug only)
- [x] No `workbook_path` required for standard / B6 runners
- [x] `lic_dsf.stress` public API unchanged for downstream imports
- [ ] Full numeric 1e-6 on **all** B3/B5/B6/public later-year probes — blocked on
      Excel drifts in KNOWN_GAPS (not a missing implementation)

## Kept (not deleted)

Implementation helpers still used by v2:

- `stress/bound.py`, `stress/shocks.py`, `stress/residual_pv.py`
- `stress/public.py` (`_run_public_stress` for override paths)
- `stress/scenario.py` (`StressExternalBook`, rebuild helpers)

Full file deletion / rename `stress` → `stress` is optional post-cutover
cleanup once Excel drifts are closed.
