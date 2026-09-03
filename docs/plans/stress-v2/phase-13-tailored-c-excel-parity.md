# Phase 13 — Tailored C* Excel parity (C1 / C3 / C4)

**Status:** In progress (Track A mostly landed 2026-09-02; Track B next)  
**Depends on:** [Phase 11](phase-11-tailored-external-excel-parity.md) (partial),
[Phase 12](phase-12-public-stress-excel-parity.md) (standard public B2–B6 green)  
**Blocks:** Full Output 3-1 / 3-2 Excel green for tailored C scenarios  
**Implementation:** [phase-13-pr-implementation.md](phase-13-pr-implementation.md)

## Goal

Close the remaining tailored **C1 / C3 / C4** drifts on both surfaces:

1. **Output 3-1** — finish Phase 11 (later-year PV/DS @ `1e-6`)
2. **Output 3-2** — public tailored path (new; Phase 12 deferred this)

Same intermediate-first discipline as Phases 9–12:

```
macro / CL gap → B-sheet identity → ResFin → ratios → Output 3-x unlock
```

Do **not** unlock Output 3-x green-subset cells until the row above them is
green (or the scenario is documented as Output-only, like B3/B4).

## Why this phase

| Surface | Today (template workbook) | Owner so far |
|---------|---------------------------|--------------|
| Output 3-1 C* | 2024 green; 2025+ drifts ~0.5–6 ppt | Phase 11 (partial) |
| Output 3-2 C* | ~3–4 / 63 pass (2024 anchor only) | **None** (deferred) |
| C2 Natural disaster | Often `n.a.` in Input 6 | Out of scope unless On |

Phase 11 closed the hard wiring (commodity export scale, C4 400 bps add.int,
C1 CL → external PPG gap). What remains is **numeric close** of known tails,
then the **public** path for Output 3-2.

## Current baseline (2026-09-02)

### Output 3-1 progress (2026-09-02 after Track A)

| Scenario | Was (max abs) | Now (max abs) | Notes |
|----------|---------------|---------------|-------|
| C1 | ~6.1 ppt | ~1.1 ppt | Public three-way ResFin for O31 |
| C3 | ~4.5 ppt | ~0.9 ppt | Exports/GDP gap fade + GDP ppt |
| C4 | ~4.5 ppt | ~0 (2025); ~0.1–1.3 later | No FX-gap ResFin + baseline USD rev; O32 overlay |

Localization: `scripts/stress_phase13_localize.py`

### Output 3-2 (full catalog, pre–Phase 13)

From `stress_parity_report.py --layer output32 --sut v2` (after Phase 12 B2–B6):

| Scenario | Pass / n | Max abs |
|----------|----------|---------|
| C1 | ~4 / 63 | ~3.7 ppt |
| C3 | ~3 / 63 | ~270 ppt (exports-denominated) |
| C4 | ~3 / 63 | ~54 ppt |

Almost all failure mass is C*; standard A1/B1–B6 + Baseline are green.

### Workbook sheets (bundled template)

| Scenario | External-ish | Public-ish |
|----------|--------------|------------|
| C1 | `C1_Combined CL` | *(confirm in W0 — may be dual-use)* |
| C3 | `C3_Commodity prices_ext` | `C3_commodity_prices_pub` |
| C4 | `C4_Market_financing` | *(confirm in W0)* |
| C2 | `C2_Natural disaster` | — |

W0 must map which sheets are B-sheet intermediates vs chart-data only.

## Out of scope

- B2 Output 3-1 later-year DS (~0.01–0.26 ppt) — separate KNOWN_GAPS follow-on
- A2 Output 3-2 — finish under Phase 12 W3 / PR-6 if still open
- C2 Natural disaster — only if Input 6 flag is On for the template
- Re-opening `bound.external_residual_borrowing` for standard B3/B5/B6
- Per-probe tolerance exceptions without a KNOWN_GAPS row

## Pipeline reminder

```
TailoredParams (Input 6)
  → MacroShock (CL / commodity / market FX)
  → ExternalDebtDynamics (+ CL gap / C4 add.int)
  → ResidualFinancingEngine
  → StressExternalRatios → Output 3-1
  → PublicGFNIdentity ↔ public ResFin → StressPublicRatios → Output 3-2
```

C1 may need coupling (CL affects GFN and external gap). C3 is export-like
(B3 overlay lessons apply for Output 3-2). C4 is FX + market financing cost.

## Suggested order

```
Track A — Output 3-1 (finish Phase 11)
  A0 localize / catalogs
  A1 C4 maturity·grace
  A2 C3 fade / ε polish
  A3 C1 later-year PV
  A4 unlock O31 C* green subset

Track B — Output 3-2 (new)
  B0 public sheet map + R41/R90/R13 ladder
  B1 C3 public (has *_pub sheet)
  B2 C4 public
  B3 C1 public
  B4 unlock O32 C* green subset + docs
```

Track A before Track B for each scenario family when the public path reuses
the same macro/gap. C3 public can start once C3 O31 shock math is trusted.

## Definition of done

- [ ] Output 3-1 C1/C3/C4 Excel-green @ `1e-6` for 2024–2034 (or residual
      documented & sized in KNOWN_GAPS)
- [ ] Output 3-2 C1/C3/C4 Excel-green @ `1e-6` for agreed years
- [ ] Public / external B-sheet intermediates green where sheets exist
- [ ] `test_output_31_excel_green_subset` / `test_output_32_excel_green_subset`
      include C* labels
- [ ] Phase 11 regression anchors still pass (2024; C3 R36 @ 2025; C1 R35 @ 2025)
- [ ] Standard B1–B6 / Baseline Output 3-x unchanged
- [ ] [`KNOWN_GAPS.md`](KNOWN_GAPS.md) updated; Phase 11 marked complete

## Related

- Phase 11 leftovers: maturity shorten, CL persistence, commodity fade
- Phase 12 PR-4 lesson: some Output 3-2 rows are **baseline public + external
  ResFin overlay** (no `*_pub` sheet) — check C1/C4 before inventing sheets
- Localization: `scripts/stress_phase11_localize.py` (extend for B-sheets + O32)
- Tests: `tests/test_stress_v2_tailored_external.py`
