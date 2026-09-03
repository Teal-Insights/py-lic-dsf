# Phase 9 — External Excel parity (B3 / B5 / B6)

**Status:** Complete  
**Depends on:** [Phase 3](phase-03-external-debt-dynamics.md)–[Phase 5](phase-05-external-ratios-and-runner.md), [Phase 7](phase-07-coupling-and-market-access.md), [Phase 8](phase-08-tailored-and-cutover.md)  
**Blocks:** Full Output 3-1 Excel green for B3/B5/B6  
**Parallel:** [Phase 10](phase-10-public-excel-parity.md) (public / Output 3-2 — different files)

## Goal

Close Excel drifts for external stress scenarios in causal order:

**W0 localize → W1 B3 R86 → W2 B5 R87 identity → W3 LC-NR reval → W4 B6 integrate.**

Accept only when **B-sheet intermediate rows** (R86/R87) match Excel before ratios
(R35/R36) and Output 3-1. Do not tune `StressExternalRatios` to absorb residual
error.

## What shipped

### W0 — Localization

First-failing matrix (pre-fix):

| scenario | first failing row | first failing year | notes |
|----------|-------------------|--------------------|-------|
| B3_Exports | R86 | 2025 | ~37 USD; Excel-gap → ResFin green |
| B5_FX | R87 | 2025 | ~1097 USD; reval-invariant |
| B6_Combo | R35 | 2024 | gap was green; R35 from LC-NR reval |

Helper: `scripts/stress_phase9_localize.py`.

### W1 / W2 — Residual identity (`bound.external_residual_borrowing`)

Shock-window **R21/R24** used baseline GDP as denominator; Excel B1/B3/B5 use
**shocked GDP** (same as R20). That single fix closed B3 R86 and B5 R87.

B6 combo sheet uniquely divides R21/R24 by **baseline GDP** when FX + export
shocks co-occur — matched with an explicit combo special case.

### W3 — LC-NR reval

Cached B5/B6 R35 matches the **unrevalued** book. Default
`fx_revalue_portfolio=False` for B5/B6/C4. `ExternalPortfolioAdjuster` remains
opt-in (force `True` on the spec) for post-recalc workbooks.

### W4 — B6

With identity special case + reval off: B6 R86/R35/R36/DS Excel-green; Output 3-1
B3/B5/B6 unlocked.

### Catalog

B5 residual probe row corrected to **R87** (`EXTERNAL_RESIDUAL_ROW` in
`tests/parity/catalogs/bsheet_external.py`).

## Deliverables

| Item | Location |
|------|----------|
| R21/R24 GDP denom fix + B6 combo case | `src/lic_dsf/stress/bound.py` |
| `fx_revalue_portfolio=False` for B5/B6/C4 | `src/lic_dsf/stress/spec.py` |
| B5 R87 catalog override | `tests/parity/catalogs/bsheet_external.py` |
| Localization script | `scripts/stress_phase9_localize.py` |
| Graduated Excel tests | `test_stress_v2_external_dynamics.py`, `external_ratios.py`, `full_catalog.py` |
| Docs | [`KNOWN_GAPS.md`](KNOWN_GAPS.md) |

## Definition of done

- [x] B3 R86/R89 and R35/R36 Excel-green at `1e-6`
- [x] B5 R87 and R35/R36 Excel-green at `1e-6` (reval off)
- [x] B6 R86 and R35/R36 Excel-green at `1e-6`
- [x] Output 3-1 B3/B5/B6 in Excel-green subset
- [x] Excel-gap → ResFin regression still passes
- [x] KNOWN_GAPS updated (public gaps → Phase 10; LC-NR reval noted)

## Remaining (not this phase)

- Public Output 3-2 / B1 R13–R95 — [Phase 10](phase-10-public-excel-parity.md)
- B2 later-year DS
- Re-enable LC-NR reval after Excel workbook recalc if the live template
  revalues LC-NR into R35
