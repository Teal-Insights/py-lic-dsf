# Phase 12 — PR implementation plan (B3–B6 Output 3-2)

**Parent:** [phase-12-public-stress-excel-parity.md](phase-12-public-stress-excel-parity.md)  
**Status:** Ready to execute (W0 complete)  
**Depends on:** [Phase 10](phase-10-public-excel-parity.md) (B1/A1 public green)  
**Blocks:** `test_output_32_excel_green_subset`, `test_output_32_standard_public`

## Goal

Ship **seven focused PRs** that close public stress Output 3-2 for standard
scenarios B3–B6, using the same intermediate-first ladder as Phase 9/10:

```
R41 (gdp_lcu) → R90 (public_gfn) → R13 / R95 / R93 → Output 3-2
```

Do **not** unlock Output 3-2 cells until the public B-sheet row above them is
green (where a B-sheet exists).

## W0 baseline (2026-09-01)

Localization: `PYTHONPATH=src:. .venv/bin/python scripts/stress_phase12_localize.py --years 2024-2028`

| Scenario | B-sheet | First fail @ 2025 | Bucket |
|----------|---------|-------------------|--------|
| A1, B1 | yes | — | Control (ALL PASS) |
| B5_FX | `B5_depreciation_pub` | R13 (−1.8 ppt); R41 +1,717 LCU | LCU GDP / FX passthrough |
| B6_Combo | `B6_combo_mkt_pub` | R13 (+7.0 ppt); R41 −3,939 LCU | Combo LCU deflator + identity |
| B2_PrimaryBalance | `B2_PB_mkt_pub` | R13 @ 2026 (−2.1 ppt) | Coupled ResFin / market access |
| B3_Exports | **none** | Output 3-2 only | Macro → public path |
| B4_OtherFlows | **none** | Output 3-2 only | Macro → public path |

Workbook pub sheets that exist: `B1_GDP_pub`, `B2_PB_mkt_pub`,
`B5_depreciation_pub`, `B6_combo_mkt_pub`. There is **no**
`B3_Exports_pub` or `B4_other flows_pub` in the bundled template.

Current full-catalog Output 3-2 (v2): **269/777** pass. B3/B5/B6: **3/63**
each (2024 anchor only).

## PR rules (all PRs)

1. **One scenario family per PR** when possible (B5 identity, B6 identity, …).
2. **No edits** to `bound.external_residual_borrowing` or
   `ExternalPortfolioAdjuster` (Phase 9/11).
3. **No per-probe tolerance exceptions** — use global `1e-6` or document in
   [`KNOWN_GAPS.md`](KNOWN_GAPS.md).
4. **Regression controls:** B1/A1 public B-sheet + Excel-gap injection tests
   must stay green after every PR.
5. **External Output 3-1** B3/B5/B6 green subset must not regress.

## Architecture surfaces

| Layer | Files |
|-------|-------|
| LCU GDP (R41) | `stress/public.py` — `_b1_public_gdp_lcu`, `_shocked_real_and_lcu_deflator`, `_extra_fx_depreciation_ppt` |
| GFN (R90) | `estimate_b1_public_gfn`, `_b1_primary_deficit_lcu`, `_b1_other_identified_flows_lcu` |
| Identity wrapper | `stress/public_gfn.py` — `PublicGFNIdentity` |
| Debt dynamics (R11 → R13) | `StressPublicBook._debt_dynamics_debt_to_gdp`, `pv_public_debt_to_gdp` |
| Ratios facade | `stress/ratios/public.py` — `StressPublicRatios` |
| Runner wiring | `stress/runner/public.py`, `stress/runner/coupled.py` (B2) |
| Macro shocks | `stress/shocks.py` — `apply_fx_depreciation_shock`, `apply_combo_shock`, `apply_exports_shock` |

**Structural fix (do in PR-3):** `StressPublicRatios.gdp_lcu()` reads from
`PublicGFNIdentity`, but `pv_public_debt_to_gdp()` uses `StressPublicBook` with
a separate `_gdp_lcu_cache`. Pass precomputed GDP into the book so R13 uses the
same R41 as localization.

## Diagnostic commands

```bash
# Re-run W0 after each PR
PYTHONPATH=src:. .venv/bin/python scripts/stress_phase12_localize.py --years 2024-2028

# Per-scenario B-sheet gate
PYTHONPATH=src:. .venv/bin/pytest \
  'tests/test_stress_v2_public_ratios.py::test_public_bsheet_matches_excel[B5_FX]' -q

# Output 3-2 gate (all standard public shocks)
PYTHONPATH=src:. .venv/bin/pytest \
  tests/test_stress_v2_public_ratios.py::test_output_32_standard_public -q

# Full-catalog subset
PYTHONPATH=src:. .venv/bin/pytest \
  tests/test_stress_v2_full_catalog.py::test_output_32_excel_green_subset -q

# Sanity (should not move missing_sut)
PYTHONPATH=src:. .venv/bin/pytest \
  tests/test_stress_v2_full_catalog.py::test_output_32_full_catalog_no_missing_sut -q
```

### Classification matrix

| R41 | R90 | R13 | Next action |
|-----|-----|-----|-------------|
| fail | — | — | Fix LCU GDP compounding |
| pass | fail | — | Fix GFN identity (primary, DS, other flows, ResFin) |
| pass | pass | fail | Fix debt dynamics R11 or PV overlay (W2) |
| pass | pass | pass | Graduate tests for that scenario |

---

## PR-0 — Catalog & harness hygiene

**Effort:** ~0.5 day  
**Blocks:** accurate probes for PR-1+

### Problem

- `PUBLIC_SHEETS["B6_Combo"]` is `B6_Combo_mkt_pub` but the workbook sheet is
  `B6_combo_mkt_pub` (localizer resolves via candidate list; catalog is wrong).
- `test_public_bsheet_matches_excel` parametrizes B3/B4 against sheets that do
  not exist in the template.
- Localizer requires `PYTHONPATH=src:.` (document in script docstring).

### Tasks

- [ ] Set `PUBLIC_SHEETS["B6_Combo"]` → `"B6_combo_mkt_pub"` in
      `tests/parity/catalogs/bsheet_public.py`.
- [ ] Remove `B3_Exports` and `B4_OtherFlows` from `_PHASE12_BSHEET` in
      `tests/test_stress_v2_public_ratios.py`, or mark skipped with reason
      “no pub B-sheet in template”.
- [ ] Add `R42` / `R54` (real GDP %, LCU deflator %) to
      `scripts/stress_phase12_localize.py` optional `--intermediate` flag for
      B5/B6 debugging.
- [ ] Update W0 checkboxes in
      [phase-12-public-stress-excel-parity.md](phase-12-public-stress-excel-parity.md)
      with the table above.

### Tests

- [ ] `stress_phase12_localize.py` runs without sheet-resolution warnings for
      B5/B6.
- [ ] No false failures from reading `B3_Exports_pub`.

### Definition of done

- Catalog sheet names match workbook.
- B3/B4 acceptance path documented as Output 3-2 only.

---

## PR-1 — B5_FX: R41 LCU GDP

**Effort:** 1–2 days  
**Maps to:** Phase 12 W1 (B5 slice)  
**First symptom:** Python R41 **+1,717 LCU** @ 2025 → R13 **−1.81 ppt**

### Hypothesis

`_b1_public_gdp_lcu` FX passthrough via `_extra_fx_depreciation_ppt` does not
match Excel `B5_depreciation_pub` R42/R54 compounding. Macro
`apply_fx_depreciation_shock` already applies B5 E51
`(1 − passthrough) × dep` to the **USD deflator**; the public LCU path may
double-count or use the wrong sign/year.

### Investigation

1. Read Excel `B5_depreciation_pub` rows **41, 42, 54** for 2024–2028.
2. Compare to Python `_shocked_real_and_lcu_deflator(..., fx_passthrough=...)`.
3. Confirm shock year = **second projection year** (matches macro FX shock).
4. Compare `_extra_fx_depreciation_ppt` @ 2025 to baseline vs shocked FX YoY.

### Implementation (likely)

- [ ] Align LCU deflator in `_shocked_real_and_lcu_deflator` with Excel B5 E51
      (may differ from generic `passthrough × extra FX depreciation`).
- [ ] Ensure `PublicScenarioRunner` passes `fx_passthrough` only when
      `interactions_on` and shock ∈ `{FX, COMBO}` (already wired — verify).
- [ ] Add pinpoint test:
      `test_b5_public_gdp_lcu_matches_excel_r41` (years 2024–2028).

### Excel-gap test (classify GFN vs GDP)

- [ ] Clone `test_b1_public_gfn_matches_excel_r90_given_excel_gap` for B5:
      inject `PV_ResFin_pub` R67 from Excel → if R41 still fails, pure GDP bug;
      if R41 passes but R90 fails, GFN components.

### Tests to pass

- [ ] `stress_phase12_localize.py` — B5: R41 + R90 green 2024–2028.
- [ ] `test_public_bsheet_matches_excel[B5_FX]`.
- [ ] B1 Excel-gap tests unchanged.

### PR exit gate

Do not merge PR-2 until B5 R41 is green @ 2025.

---

## PR-2 — B6_Combo: R41 LCU GDP

**Effort:** 1–2 days  
**Maps to:** Phase 12 W1 (B6 slice)  
**First symptom:** Python R41 **−3,939 LCU** @ 2025 → R13 **+6.96 ppt**

### Hypothesis

Combo macro (`apply_combo_shock`) uses a **different** deflator rule than public
LCU compounding:

- Macro B6 E51: `deflator += passthrough × (baseline_nc_dep − combo_dep)` at
  shock year (half-size FX).
- Public path: `passthrough × full_extra_fx_depreciation_ppt` — not equivalent.

Combo also sets `gdp_elasticity=0` on export leg; public R41 must compound
**combo** `gdp_constant` growth, not B3-style export ε side effects.

### Investigation

1. Excel `B6_combo_mkt_pub` R41/R42/R54 vs Python intermediates.
2. Diff `depreciation_of_nc_pct` @ shock year vs `_extra_fx_depreciation_ppt`.
3. Verify half PB shock in `_b1_primary_deficit_lcu` via shocked
   `primary_expenditure`.

### Implementation (likely)

- [ ] Add **COMBO-aware** branch in `_shocked_real_and_lcu_deflator` or
      `_b1_public_gdp_lcu` mirroring `apply_combo_shock` E51 (use
      `combo_fx_depreciation_pct`, not full B5 dep).
- [ ] Do **not** copy PR-1 B5 formula verbatim.
- [ ] Add `test_b6_public_gdp_lcu_matches_excel_r41`.

### Tests to pass

- [ ] Localizer — B6: R41 + R90 green 2024–2028 (R90 may need ResFin re-run
      after R41 fix).
- [ ] `test_public_bsheet_matches_excel[B6_Combo]`.
- [ ] B5 regression from PR-1 green.

---

## PR-3 — B5/B6: R13 / R95 / R93 (debt dynamics + shared GDP)

**Effort:** 1–2 days  
**Maps to:** Phase 12 W2 (B5/B6 slice)  
**Prerequisite:** PR-1 and PR-2 (R41 + R90 green)

### Problem

Even with correct R41/R90, R13 can fail via:

- `StressPublicBook` using a **different** `gdp_lcu` than `PublicGFNIdentity`.
- Debt-dynamics R11 path (`_debt_dynamics_debt_to_gdp`) vs Excel R11.
- ResFin PV overlay (`_external_pv_lcu`) or R18 revenue identity.

### Tasks

- [x] Pass `gdp_lcu` from `PublicGFNIdentity` into `StressPublicBook` (new
      optional ctor arg or shared cache) so `pv_public_debt_to_gdp` uses the
      same R41 as probes.
- [x] Compare Python R11 vs Excel B5/B6 R11 for 2025–2028; fix FX terms in
      R23–R25 if needed (shocked `fx_eop` / `fx_pa` already wired — verify).
- [x] If R11 matches but R13 fails → debug `_external_pv_lcu` / ResFin fill.
- [x] If R95 fails with R13 green → `_revenue_to_gdp` (R18 grants hold).
- [x] Excel-gap ladder for B5/B6 (R67 → R11 → R13).

### Tests to pass

- [x] Localizer — B5/B6: all five rows (R41, R90, R13, R95, R93) green
      2024–2028.
- [x] `test_output_32_excel_green_subset` — B5 + B6 labels pass (B3/B4
      deferred to PR-4).
- [x] Output 3-1 B5/B6 external PV subset unchanged.

---

## PR-4 — B3_Exports & B4_OtherFlows (Output 3-2)

**Effort:** 1–2 days  
**Maps to:** Phase 12 W1/W2 (no pub B-sheet)  
**Acceptance:** `Output 3-2 Stress-public` cells only

### B3_Exports

Macro path already applies export shock + `_apply_export_shock_side_effects`
(GDP ε, CA, revenue hold). Public Output 3-2 does **not** re-run a public
stress path: Excel ``Baseline - public`` R91 adds external ResFin PV
(``B3_Exports_ext`` R89 × FX eop) onto baseline public PV.

- [x] Diff Output 3-2 **B3. Exports** vs `build_output32_table` 2024–2034.
- [x] Wire `to_output32_rows_external_resfin_overlay` (baseline + ext ResFin).
- [x] If ratio drift with GDP OK: `_revenue_to_gdp`, ResFin gap, debt dynamics.

### B4_OtherFlows

Same overlay pattern as B3 (`Baseline - public` R92 / R106 +
``B4_other flows_ext`` R89 / R98).

- [x] Verify shocked transfers/FDI drive **external** ResFin (not public R89).
- [x] Diff Output 3-2 **B4. Other flows** cells.

### Tasks

- [x] Add focused tests in `test_stress_v2_public_ratios.py`:
      `test_output_32_b3_b4_external_resfin_overlay` (2024–2034).
- [x] Do **not** add fake `B3_Exports_pub` catalog entries.

### Tests to pass

- [x] `test_output_32_standard_public` — B3 + B4 labels green.
- [x] `test_output_32_excel_green_subset` — B3 + B4 labels green.

---

## PR-5 — B2_PrimaryBalance (coupled + market access)

**Effort:** 1–2 days  
**Maps to:** Phase 12 W3  
**Symptom:** R41/R90 pass; R13 fails from **2026** (~2 ppt)

### Route

`PublicScenarioRunner` → `CoupledScenarioRunner` when `couple_ext_r86=True`.

### Investigation

1. External R86 gap feeds Absolute public split — verify Phase 3 gap magnitude.
2. `resfin_external_ds` overlay: market vs non-market PV blocks for DS (R93).
3. `_market_add_int_interest_lcu` in GFN during PB shock window (years 2–3).
4. Compare `B2_PB_mkt_pub` R13 @ 2026–2028 after B3–B6 green.

### Tasks

- [x] Fix B2 market-access add.int on public R91 (PV) and R86/R87 (interest)
      in `stress/public.py` (GFN already included add.int; R41/R90 were green).
- [x] Add `test_public_bsheet_matches_excel[B2_PrimaryBalance]` to CI gate
      (`_PHASE12_BSHEET` + `PUBLIC_SHEETS`).
- [x] Confirm Output 3-1 B2 PV early years still green
      (`test_output_31_b2_early_years`).

### Tests to pass

- [x] Localizer — B2: R13/R95/R93 green 2024–2028.
- [x] `test_output_32_standard_public` — B2 label green.
- [x] `test_output_32_excel_green_subset` — B2 label green.

---

## PR-6 — Graduate tests & close phase

**Effort:** ~0.5 day  
**Maps to:** Phase 12 definition of done

### Tasks

- [ ] Mark [phase-12-public-stress-excel-parity.md](phase-12-public-stress-excel-parity.md)
      **Complete**; check all W0–W3 boxes.
- [ ] Update [`KNOWN_GAPS.md`](KNOWN_GAPS.md): remove or shrink B3–B6 Output
      3-2 rows; leave tailored public C* for a later phase.
- [ ] Run `scripts/stress_parity_report.py --layer output32 --sut v2` and
      record before/after counts in phase-12 doc.
- [x] Verify `_OUTPUT32_EXCEL_GREEN` in `test_stress_v2_full_catalog.py` fully
      passes (B3–B6 + A2 custom).

### Phase definition of done

- [ ] `test_output_32_standard_public` green.
- [ ] `test_output_32_excel_green_subset` green.
- [ ] Public B-sheet probes green for B1, B5, B6, B2 (B3/B4 via Output 3-2).
- [ ] `test_output_32_full_catalog_no_missing_sut` unchanged.
- [ ] B1/A1 Excel-gap injection tests green.
- [ ] External Output 3-1 B3/B5/B6 green subset unchanged.

---

## Suggested merge order

```
PR-0 (hygiene)
  → PR-1 (B5 R41)
  → PR-2 (B6 R41)
  → PR-3 (B5/B6 ratios + shared GDP)
  → PR-4 (B3/B4 Output 3-2)     ┐
  → PR-5 (B2 coupled)            ├─ PR-4 and PR-5 can parallel after PR-3
  → PR-6 (docs + graduate)       ┘
```

| PR | Effort | Catalog impact (approx.) |
|----|--------|--------------------------|
| PR-0 | 0.5 d | — |
| PR-1 | 1–2 d | B5 partial |
| PR-2 | 1–2 d | B6 partial |
| PR-3 | 1–2 d | B5/B6 → 63/63 per scenario |
| PR-4 | 1–2 d | B3/B4 Output 3-2 (+~120 passes) |
| PR-5 | 1–2 d | B2 Output 3-2 |
| PR-6 | 0.5 d | Full subset green |

**Total:** ~6–10 days.

## What not to do

- Unlock `test_output_32_excel_green_subset` before B-sheet R13 is green (B5/B6).
- Bundle B5 and B6 identity fixes in one PR (different deflator rules).
- Touch `bound.py` / external portfolio for “quick wins” on Output 3-2.
- Add per-year fudge factors to pass probes.
- Invent `B3_Exports_pub` / `B4_other flows_pub` sheet names — they are not in
  the bundled workbook.

## Coordination

```
Phase 11 (tailored external C*)     Phase 12 (this plan)
stress/tailored.py, bound.py       stress/public.py, public_gfn.py
         │                                    │
         └──────── merge at suite / KNOWN_GAPS only ────────┘
```

Low merge-conflict risk if Phase 12 PRs stay in `stress/public.py` and
`stress/ratios/public.py`.
