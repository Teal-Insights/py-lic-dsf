# Phase 12 — Public stress Output 3-2 (B2–B6 + A2)

**Status:** In progress (W0 complete; PR plan ready)  
**Depends on:** [Phase 6](phase-06-public-gfn-and-ratios.md),
[Phase 10](phase-10-public-excel-parity.md)  
**Blocks:** Full Output 3-2 Excel green for standard public shocks  
**Parallel:** [Phase 11](README.md) (tailored external C1/C3/C4 — different files)  
**Implementation:** [phase-12-pr-implementation.md](phase-12-pr-implementation.md)

## Goal

Close public ratios when macro is shocked — the reason B3/B5/B6 are green on
Output 3-1 but red on Output 3-2.

Same intermediate-first discipline as Phase 9/10:

**W0 localize → W1 GFN / residual identity → W2 ResFin + ratios → W3 B2 / A2
→ unlock Output 3-2 Excel-green subset.**

Target probes: public B-sheet **R41 / R90 / R13 / R95 / R93**, then
**Output 3-2**. Accept on B-sheet rows before Output 3-2 cells.

## Why separate from Phase 11

Output 3-2 is `PublicGFNIdentity` + public ResFin + `StressPublicRatios`, not
external `bound.py`. Phase 11 owns tailored external C*.

## Out of scope

- Tailored public C1/C3/C4 — [Phase 13](phase-13-tailored-c-excel-parity.md)
- External B3/B5/B6 identity (`bound.py`, `ExternalPortfolioAdjuster`)

## Deliverables

| Item | Location |
|------|----------|
| Public B-sheet catalog B2–B6 (+ A1 if present) | `tests/parity/catalogs/bsheet_public.py` |
| Localization harness | `scripts/stress_phase12_localize.py` |
| GFN / FX / other-flows identity fix | `stress/public.py`, `public_gfn.py` |
| Graduated parity tests | `tests/test_stress_v2_public_ratios.py` |
| Output 3-2 Excel-green subset | `tests/test_stress_v2_full_catalog.py` |
| Docs | [`KNOWN_GAPS.md`](KNOWN_GAPS.md), [README](README.md) |

## Pipeline (reminder)

```
MacroShock (GDP / PB / exports / other / FX / combo)
  → PublicGFNIdentity (R41, R90, gap)
  → ResidualFinancingEngine ↔ GFN fixed point
  → StressPublicRatios → Output 3-2 (PV / DS)
```

B1 already green — use as control. Inject Excel public gap to classify GFN vs
ResFin vs ratio math when a scenario's identity is the first fail.

## Suggested order

**B3 → B5 → B6 → B4 → B2 → A2**

Simplest macro shocks first. B2 last (coupled + Absolute policy + market
access). A2 is a separate public `custom_spec` path.

---

## W0 — Localization

**Goal:** Name the first failing public row/year per scenario. No formula edits.

### Tasks

1. [x] Expand `PUBLIC_SHEETS` to B3 / B4 / B5 / B6 (B2/A1 names still candidate-only in the localizer).
2. [x] For B3 / B5 / B6 / B4 / B2 / A2: Excel vs Python for **R41, R90, R13,
   R95, R93**, years 2024–2028 first.
3. [x] Classify: GDP LCU vs GFN identity vs debt-dynamics / FX vs ResFin vs
   ratio math.
4. [x] Keep B1 as a regression control.

### W0 results

| Scenario | B-sheet | First fail | Bucket |
|----------|---------|------------|--------|
| A1, B1 | yes | — | Control |
| B5_FX | `B5_depreciation_pub` | R13 @ 2025; R41 +1,717 LCU | LCU GDP / FX passthrough |
| B6_Combo | `B6_combo_mkt_pub` | R13 @ 2025; R41 −3,939 LCU | Combo LCU deflator |
| B2_PrimaryBalance | `B2_PB_mkt_pub` | R13 @ 2026 (~2 ppt) | Coupled / market access |
| B3_Exports | none | Output 3-2 only | Macro → public |
| B4_OtherFlows | none | Output 3-2 only | Macro → public |

See [phase-12-pr-implementation.md](phase-12-pr-implementation.md) for PR breakdown.

### Definition of done

- [x] First failing public row/year documented per scenario
- [x] Clear bucket per scenario

---

## W1 — Public GFN / residual identity (B3 / B5 / B6 / B4)

**Primary surface:** `PublicGFNIdentity` + `estimate_b1_public_gfn` /
`_b1_public_gdp_lcu` / `_b1_other_identified_flows_lcu` /
`StressPublicBook._debt_dynamics_debt_to_gdp`

Likely surfaces (from Phase 10 leftovers):

- B5/B6: debt-dynamics and R82/R91 still use **baseline** `fx_eop` in places
- B5/B6: public R41 LCU compounding may omit FX passthrough
- B4/B6: other identified flows pinned to baseline rather than shocked Macro
- B3: export→GDP interaction (if Input 6 interactions on) must reach R41/R88

### PR rule

No edits to `external_residual_borrowing` or `ExternalPortfolioAdjuster`.

### Definition of done

- [ ] B3/B5/B6/B4 R41 and R90 Excel-green for agreed years
- [ ] B1 Excel-gap injection tests still pass

---

## W2 — Public ResFin feedback + ratios

If identity matches but R13/R95/R93 fail → ResFin interest loop / PV overlay /
revenue-to-GDP (R18).

Unlock Output 3-2 B3–B6 from coverage-only → Excel `1e-6`.

### Definition of done

- [ ] B3–B6 R13/R95/R93 Excel-green (or residual documented)
- [ ] Output 3-2 B3–B6 Excel-green for agreed horizon
- [ ] Output 3-1 B3–B6 / B2 PV regression green

---

## W3 — B2 + A2

B2: Absolute policy, `couple_ext_r86`, market-access add.int. A2: public
`custom_spec` path.

### Definition of done

- [x] Output 3-2 B2 Excel-green for agreed years (PV at minimum)
- [x] Output 3-2 A2 Excel-green when the public customized sheet is on
  (`test_a2_output32_excel_green`; R121 prior+R15 at first projection year)
- [x] Output 3-1 B2 DS 2024–2034 (`test_b2_output31_ds_excel_green`;
  non-mkt GFN keeps domestic add.int)

---

## Phase definition of done

- [ ] Output 3-2 Excel-green for Baseline/A1/B1 **plus** B3–B6 (and A2 if in
      scope) at global tol for agreed years
- [ ] Public B-sheet R41/R90/R13/R95/R93 for those scenarios at `1e-6`
- [ ] KNOWN_GAPS updated (tailored public C* remain if not closed)
- [ ] Full-catalog `missing_sut == 0` unchanged
