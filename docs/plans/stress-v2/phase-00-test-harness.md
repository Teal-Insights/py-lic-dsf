# Phase 0 — Test harness and acceptance criteria

**Status:** Not started  
**Depends on:** Nothing (start here)  
**Blocks:** All implementation phases

## Goal

Define what “correct” means before rewriting stress logic. Expand differential
testing from partial Output 3-x checks to a full pyramid: macro intermediates →
B-sheet gaps → ResFin schedules → B-sheet ratios → Output 3-1 / 3-2.

## Prerequisites

- Bundled workbook: `data/lic-dsf-template-2025-08-12.xlsx`
- Existing parity tools: `tests/parity/probes.py`, `compare.py`, `equality.py`
- Existing Output 3-x catalogs: `tests/parity/catalogs/output_3.py`

## Deliverables

| Item | Location | Purpose |
|------|----------|---------|
| B-sheet external probe catalog | `tests/parity/catalogs/bsheet_external.py` | Ratio + gap rows on `B*_ext` sheets |
| B-sheet public probe catalog | `tests/parity/catalogs/bsheet_public.py` | Ratio + GFN rows on `B*_pub` sheets |
| ResFin probe catalog | `tests/parity/catalogs/resfin.py` | `PV Stress`, `PV_ResFin_pub` rows |
| Parametrized layer tests | `tests/test_stress_v2_parity.py` | One test module per catalog (initially xfail) |
| Coverage report script | `scripts/stress_parity_report.py` | Pass / fail / missing_sut summary |
| Feature flag | `conftest.py` or env `LIC_DSF_STRESS_V2` | Run v2 SUT alongside legacy during migration |

## Probe catalog design

### External B-sheet (`bsheet_external.py`)

Per scenario (`B1_GDP_ext`, `B3_Exports_ext`, `B5_depreciation_ext`, …):

| Row | Metric | Priority |
|-----|--------|----------|
| 46 | GDP USD | Phase 2 |
| 50 | Real GDP growth | Phase 2 |
| 19 | Exports / GDP | Phase 2–3 |
| 86 | Residual gross borrowing (R86) | Phase 3 |
| 35 | PV PPG / GDP | Phase 5 |
| 36 | PV PPG / exports | Phase 5 |
| 39 | PPG DS / exports | Phase 5 |
| 40 | PPG DS / revenue | Phase 5 |

Use the same year-row / first-col conventions as `test_stress_dsa.py`
(`_sheet_cached` pattern). Map `sut_key` to `(scenario_id, sheet_row, year)`.

### Public B-sheet (`bsheet_public.py`)

Per scenario (`B1_GDP_pub`, `B2_PB_*_pub`, …):

| Row | Metric | Priority |
|-----|--------|----------|
| 41 | GDP LCU | Phase 2 |
| 42 | Real GDP growth | Phase 2 |
| 90 | Public GFN | Phase 6 |
| 13 | PV public / GDP | Phase 6 |
| 43 | PV public / revenue | Phase 6 |
| Debt service rows | DS / revenue | Phase 6 |

### ResFin (`resfin.py`)

| Sheet | Rows | Priority |
|-------|------|----------|
| `PV Stress` | External MLT PV, interest, amort | Phase 4 |
| `PV_ResFin_pub` | Three-way fill, dom MLT/ST, ext overlay | Phase 4 |
| `PV_ResFin-add.int.cost - mkt` | Market add.int (B2/B6) | Phase 7 |

## Implementation tasks

1. **Inventory B-sheet rows** — scan template sheets; confirm row numbers match
   `_sheet_cached` / `_sheet_row` helpers in existing tests.

2. **Create probe builders** — mirror `output_31_probes()` API:
   ```python
   def bsheet_external_probes(workbook, scenario_id: str) -> tuple[Probe, ...]: ...
   ```

3. **Add `stress_parity_report.py`** — argparse script:
   - `--layer output31|output32|bsheet_ext|bsheet_pub|resfin`
   - `--sut legacy|v2`
   - Print: total probes, passed, failed, missing_sut, max abs_diff by scenario

4. **Wire initial tests as xfail** — mark all v2 tests `@pytest.mark.xfail`
   until each phase turns them green; remove xfail per phase.

5. **Document tolerance policy** — default `1e-6`; any exception (e.g. B2 2026
   PV today at `1e-3`) must be listed as a **known gap** with a probe name and
   target phase to fix.

6. **Add CI job step** (optional) — run coverage report on PRs; fail if
   `missing_sut > 0` for Output 3-x once v2 SUT exists.

## Differential testing workflow (reference)

For each probe:

```python
excel = read_cached_output(WORKBOOK, probes)
sut = build_v2_sut(...)  # layer-specific
report = compare_probes(excel, sut)
assert report["missing_sut"].sum() == 0
assert_all_passed(report)
```

Use `read_cached_output` (fastpyxl) in CI. Reserve `@pytest.mark.live_excel` for
`.xlsm` recalc sanity checks.

## Definition of done

- [ ] Probe catalogs exist for external B-sheets (B1, B3, B5 minimum), public
      B1, and ResFin B1 fill.
- [ ] `scripts/stress_parity_report.py` runs and reports legacy baseline
      pass rates (establishes current gap baseline).
- [ ] `tests/test_stress_v2_parity.py` exists with parametrized catalog tests.
- [ ] Known gaps documented in this file or a `KNOWN_GAPS.md` appendix:
      - B2 Output 3-1 2026 PV ~1e-3 drift
      - Tailored external not in full Output 3-1 bundle
      - B6 add.int loaded from workbook when path passed
- [ ] Phase 1 can start without ambiguity about acceptance criteria.

## Out of scope

- Implementing any v2 stress logic (Phases 1+).
- Changing `ABS_TOL` or `close()` semantics.
