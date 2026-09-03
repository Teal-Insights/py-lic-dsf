# Phase 10 — Public Excel parity (Output 3-2 / B1)

**Status:** Complete  
**Depends on:** [Phase 6](phase-06-public-gfn-and-ratios.md), [Phase 8](phase-08-tailored-and-cutover.md)  
**Blocks:** Full Output 3-2 Excel green for A1/B1 (and same-root scenarios)  
**Parallel:** [Phase 9](phase-09-external-excel-parity.md) (external B3/B5/B6 — different files)

## Goal

Close public Excel drifts using the same intermediate-first discipline as
Phase 9:

**W5.0 localize → W5.1 GFN / residual identity → W5.2 ResFin + ratios →
(optional) W5.3 catalog cleanup.**

Target probes: **B1 R13 / R95 / R93** and **Output 3-2** (A1/B1). Accept on
B-sheet rows before Output 3-2 cells.

## Prerequisites

- Probes: `tests/parity/catalogs/bsheet_public.py`; Output 3-2 catalog
- Code:
  - `stress/public_gfn.py` (`PublicGFNIdentity`)
  - `stress/public.py` (`estimate_b1_public_gfn`)
  - `stress/residual_pv.public_residual_gap`
  - `StressPublicRatios`, `PublicScenarioRunner`
- Existing: R41/R90 Excel-green; Excel-gap injection tests
  (`test_b1_public_gfn_matches_excel_r90_given_excel_gap`,
  `test_pv_resfin_pub_b1_fill_parity_with_excel_gap`,
  `test_run_b1_gdp_public_with_excel_gap`)
- R13/R95/R93 and Output 3-2 A1/B1 legacy-locked — see
  [`KNOWN_GAPS.md`](KNOWN_GAPS.md)
- Phase 7 coupling: Absolute policy / ext R86 into public split — verify B2
  PV not regressed; B1 may not need R86

## Out of scope

- B3/B5/B6 external identity / LC-NR (`bound.py`, `external_portfolio.py`) —
  [Phase 9](phase-09-external-excel-parity.md)
- B2 later-year DS (optional follow-on; not required to close this phase)
- Facade / suite / tailored wiring (already complete)

## Deliverables

| Item | Location |
|------|----------|
| Public localization harness | `tests/parity/` and/or `scripts/` (mirror Phase 9 W0) |
| GFN / residual identity fix | `public_gfn.py` and/or legacy helpers it wraps |
| Public ResFin / ratio fix (only if identity clean) | `resfin/`, `ratios/public.py` |
| Graduated parity tests | `tests/test_stress_v2_public_ratios.py` (+ residual applied tests) |
| Docs | [`KNOWN_GAPS.md`](KNOWN_GAPS.md) public rows |

## Pipeline (reminder)

```
MacroShock (GDP / …)
  → PublicGFNIdentity (R41, R90, gap)
  → ResidualFinancingEngine ↔ GFN fixed point
  → StressPublicRatios → Output 3-2 (PV / DS)
```

---

## W5.0 — Localization

**Goal:** Name the first failing public row/year. No formula edits.

### Tasks

1. [x] For Baseline / A1 / B1 (extend if needed): Excel vs Python for
   **R41, R90, residual/gap, R13, R95, R93**, then Output 3-2 PV/DS cells,
   years 2024–2028+.
2. [x] Inject **Excel public gap** into ResFin (existing Excel-gap tests).
   Classify: GFN identity vs ResFin vs ratio math.
3. [x] Note year-1 pass vs later-year fail (KNOWN_GAPS: after year-1).

### Definition of done

- [x] First failing public row/year documented
- [x] Clear bucket: GFN / residual / PV stock / DS

### W5.0 results

| Scenario | First fail | Bucket |
|----------|------------|--------|
| B1 | R13 @ 2025 (~0.43 ppt) | Debt-dynamics R11 / R80 (gap+ResFin already green) |
| A1 | R41 hist LCU GDP, R17 hist PD, R86 coupling, modality-1 split | Public hist path + capped ResFin |

### Exit gate

Do not start W5.1 until W5.0 names the first failing row for B1. **Met.**

---

## W5.1 — Public GFN / residual identity

**Primary surface:** `PublicGFNIdentity` + `estimate_b1_public_gfn` /
`public_residual_gap`

### Tasks

1. [x] Fix whatever W5.0 names (stock evolution, interest, FX on public PPG,
   etc.).
2. [x] Lock **R13 / residual gap** vs Excel before unlocking ratios.
3. [x] Keep R90/R41 green.

### Definition of done

- [x] B1 R13 (and gap row if probed) Excel-green for agreed years
- [x] Excel-gap injection tests still pass

### PR rule

No edits to `external_residual_borrowing` or `ExternalPortfolioAdjuster`.

---

## W5.2 — Public ResFin feedback + ratios

### Tasks

1. [x] If identity matches but R95/R93 fail → ResFin interest loop / fill /
   PV overlay.
2. [x] Unlock `StressPublicRatios` Output 3-2 probes from legacy-lock → Excel
   `1e-6`.
3. [x] Confirm Output 3-1 B2 PV remains green (shared public runner).

### Definition of done

- [x] B1 R95/R93 Excel-green (or residual documented)
- [x] Output 3-2 A1/B1 Excel-green for agreed horizon
- [x] KNOWN_GAPS public rows closed or updated
- [x] B2 Output 3-1 PV regression green

---

## W5.3 — Catalog / suite cleanup (optional)

### Tasks

1. [x] Expand year coverage if the early window is green but 2027+ still
   drifts (same bug vs separate — do not invent per-year fudge).
2. [x] Optional: B2 later-year DS (KNOWN_GAPS separate line) as a follow-on,
   not required to close this phase.

### Definition of done

- [x] Agreed year horizon documented and tested (full projection horizon)
- [x] Optional B2 DS left in KNOWN_GAPS with size

---

## Suggested order and sizing

| Stream | Effort (rough) | Parallel with Phase 9? |
|--------|----------------|------------------------|
| W5.0 | 0.5–1 d | Yes, immediately |
| W5.1 | 2–4 d | Yes (different files) |
| W5.2 | 1–2 d | Yes |
| W5.3 | 0.5 d | After W5.2 |

## Phase definition of done

- [x] Public B-sheet R13/R95/R93 and Output 3-2 A1/B1 vs Excel at global tol
      for agreed years
- [x] External B3/B5/B6 work not required
- [x] KNOWN_GAPS updated
- [x] Full-catalog `missing_sut == 0` unchanged

## Coordination with Phase 9

```
Phase 9 (W0→W4)              Phase 10 (W5)
bound.py / external_portfolio  public_gfn / public ratios
     │                              │
     └────── merge only at ─────────┘
           Output suite / KNOWN_GAPS
           (no shared formula PRs)
```

- **Merge conflict risk:** low if Phase 9 owns `bound.py` +
  `external_portfolio.py` and Phase 10 owns `public_gfn.py` + public ratios.
- **Shared:** `KNOWN_GAPS.md`, Output catalogs, `ResidualFinancingEngine` —
  prefer separate PRs for external vs public overlay test changes.

## What not to do

- Bundle external identity fixes into this phase
- Unlock Output 3-2 before B-sheet R13 / gap are green
- Per-year tolerance exceptions without listing in KNOWN_GAPS
