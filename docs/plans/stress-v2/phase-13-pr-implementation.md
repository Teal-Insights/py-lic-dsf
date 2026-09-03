# Phase 13 — PR implementation plan (C1 / C3 / C4)

**Parent:** [phase-13-tailored-c-excel-parity.md](phase-13-tailored-c-excel-parity.md)  
**Status:** In progress — Track A: C1/C3/C4 O31 improved; C3 O31 green 2024–2034; C1 O32 green; C3 O32 green 2024–2026; C4 O32 overlay  
**Depends on:** Phase 11 wiring, Phase 12 standard public green  
**Blocks:** Full-catalog C* rows in Output 3-1 / 3-2 Excel-green subsets

## Goal

Ship **focused PRs** that close tailored C1 / C3 / C4 on:

1. **Output 3-1** (finish Phase 11 tails)
2. **Output 3-2** (public tailored — new)

Use the same ladder as Phase 9–12:

```
identity / gap → ResFin → B-sheet ratios → Output 3-x unlock
```

## W0 baseline (2026-09-02)

### Output 3-1 — `stress_phase11_localize.py --years 2024-2028`

| Scenario | Fails | Max abs | First-suspect bucket |
|----------|-------|---------|----------------------|
| C1_CombinedCL | 14/20 | 6.11 ppt @ 2028 | CL / ResFin decay after shock year |
| C3_Commodity | 14/20 | 4.47 ppt @ 2027 | Export fade + GDP ε (PV/exports) |
| C4_Market | 15/20 | 4.47 ppt @ 2025 | Maturity/grace shorten + FX |

Phase 11 anchors still hold: all 2024 rows; C3 R36 @ 2025 @ `1e-6`; C1 R35 @
2025 within `1e-2`.

### Output 3-2 — last full v2 report (post Phase 12)

| Scenario | Pass / 63 | Max abs | Note |
|----------|-----------|---------|------|
| C1 | ~4 | ~3.7 | Public tailored mostly red |
| C3 | ~3 | ~270 | Exports-denominated blow-up |
| C4 | ~3 | ~54 | FX / market path |

### Sheet inventory (must confirm in PR-0)

| Id | Candidate sheets |
|----|------------------|
| C1 | `C1_Combined CL` |
| C3 | `C3_Commodity prices_ext`, `C3_commodity_prices_pub` |
| C4 | `C4_Market_financing` |

## PR rules (all PRs)

1. **One scenario family per PR** when possible (C4 maturity ≠ C1 CL).
2. **Do not** regress Phase 11 anchors or Phase 12 B1–B6 / Baseline Output 3-x.
3. **No per-probe tolerance exceptions** — global `1e-6` or document in
   [`KNOWN_GAPS.md`](KNOWN_GAPS.md).
4. Prefer **intermediate-first**: B-sheet R19/R35/R36/R39/R40 (ext) or
   R41/R90/R13/R95/R93 (pub) before Output unlock.
5. **Do not invent** `*_pub` sheet names — if Excel has no public B-sheet,
   use the Phase 12 PR-4 pattern (baseline public + external ResFin overlay)
   only after proving Excel Chart Data formulas do that.
6. C2 Natural disaster stays out of scope unless Input 6 is On.

## Architecture surfaces

| Layer | Files |
|-------|-------|
| Tailored params | `load/tailored.py`, `stress/tailored.py` (`TailoredParams`) |
| Macro shocks | `stress/tailored/__init__.py`, `stress/shocks.py`, `stress/tailored.py` |
| C1 CL gap | `stress/bound.py` (`external_cl_gap_usd`), `external_dynamics.py` |
| C4 market add.int | `stress/market_access.py` (`MarketFinancingCost`) |
| C4 maturity/grace | **new** — Input 6 rows ~54–56 → ResFin / commercial terms |
| External runner | `stress/runner/external.py` |
| Public runner | `stress/runner/public.py` (+ coupled if C1 needs R86) |
| Public GFN / ratios | `public_gfn.py`, `stress/public.py`, `ratios/public.py` |
| Suite / Output map | `suite.py`, `output_map.py` |
| Tests | `tests/test_stress_v2_tailored_external.py`, `test_stress_v2_full_catalog.py` |
| Localize | `scripts/stress_phase11_localize.py` → extend or add `stress_phase13_localize.py` |

## Diagnostic commands

```bash
# Output 3-1 C* (2024–2028)
PYTHONPATH=src:. .venv/bin/python scripts/stress_phase11_localize.py

# Full coverage report
time uv run python scripts/stress_parity_report.py --layer output31 --sut v2
time uv run python scripts/stress_parity_report.py --layer output32 --sut v2

# Phase 11 regression
PYTHONPATH=src:. .venv/bin/pytest tests/test_stress_v2_tailored_external.py -q

# Standard public must stay green
PYTHONPATH=src:. .venv/bin/pytest \
  tests/test_stress_v2_full_catalog.py::test_output_32_excel_green_subset \
  tests/test_stress_v2_full_catalog.py::test_output_31_excel_green_subset -q
```

### Classification matrices

**External (Output 3-1 / `*_ext`)**

| R19 exports/GDP | R86/gap | R35 PV/GDP | R36 PV/X | Next |
|-----------------|---------|------------|----------|------|
| fail | — | — | — | Fix macro export / commodity scale |
| pass | fail | — | — | Fix CL gap or residual borrowing |
| pass | pass | fail | — | Fix ResFin PV / FX / maturity |
| pass | pass | pass | fail | Fix exports denominator or DS |
| all pass | | | | Unlock Output 3-1 for that id |

**Public (Output 3-2 / `*_pub`)**

| R41 | R90 | R13 | Next |
|-----|-----|-----|------|
| fail | — | — | LCU GDP / shock passthrough |
| pass | fail | — | GFN / CL / market add.int |
| pass | pass | fail | Debt dynamics / PV overlay |
| all pass | | | Unlock Output 3-2 (or overlay path) |

---

## Track A — Output 3-1 (finish Phase 11)

### PR-0 — Hygiene & localization harness

**Effort:** 0.5 d  
**Acceptance:** Better diagnostics; no formula changes required

#### Tasks

- [ ] Extend localize script to print **indicator** (not only scenario label),
      year, excel/py/diff for Output 3-1.
- [ ] Add optional `--bsheet` mode: probe `C3_Commodity prices_ext` /
      `C4_Market_financing` / `C1_Combined CL` rows R19, R35, R36, R39, R40,
      residual gap (confirm row numbers per sheet).
- [ ] Register C* sheets in `bsheet_external.py` (and public catalog when
      confirmed) **without** asserting green yet.
- [ ] Document sheet role table in parent Phase 13 doc (ext vs pub vs dual).
- [ ] Snapshot fail counts into Phase 13 parent (refresh W0 table).

#### Tests

- [ ] Existing `test_stress_v2_tailored_external.py` still passes.
- [ ] New catalog probes load without KeyError.

---

### PR-1 — C4_Market: maturity / grace shortening

**Effort:** 1–2 d  
**Maps to:** Phase 11 remaining item #1  
**Status:** Done — C4 Output 3-1 green 2024–2034 @ `1e-6`. Excel `PV Stress`
R150/R164 copy residual stock (5% USD discount unused); `rate1` is K41
disbursement-weighted commercial + 400 bps. Keep `fx_revalue_portfolio=False`.

#### Investigation

1. Read Input 6 tailored market block (cost bps row 52; FX dep; **rows 54–56**
   maturity/grace shortening — confirm exact cells in template).
2. Diff Excel `C4_Market_financing` commercial / ResFin terms vs Python
   `MarketFinancingCost` + residual instrument grace/maturity.
3. Confirm FX path: C4 uses `MarketFinancingShock` + optional portfolio reval
   (currently `fx_revalue_portfolio=False` — do **not** flip without workbook
   recalc; see KNOWN_GAPS LC-NR).

#### Tasks

- [ ] Load maturity/grace shorten parameters into `TailoredParams`.
- [ ] Apply shorten to C4 ResFin / commercial borrowing schedule (Excel
      semantics — year window, which instruments).
- [ ] Re-localize R35/R36/R39/R40 and Output 3-1 C4 for 2024–2028.
- [ ] Keep C4 400 bps × 3y add.int behavior unchanged except where Excel ties
      them to shortened terms.

#### Tests to pass

- [x] C4 Output 3-1 all indicators 2024–2034 (`test_c4_output31_excel_green`).
- [x] Phase 11 C4 2024 + early-horizon guard still pass.
- [x] B5/B6 Output 3-1 green subset unchanged.

---

### PR-2 — C3_Commodity: export fade + GDP ε polish

**Effort:** 1–2 d  
**Maps to:** Phase 11 remaining item #3  
**Symptom:** PV-to-exports drifts ~3–4.5 ppt from 2025; R36 @ 2025 is green  
**Status:** Done — C3 O31 green 2024–2034 @ `1e-6`. Root causes: (1) post-shock R18 must copy baseline % (C3), not B3's `R18×GDP_b/GDP_s`; (2) after `commodity_close_years`, exports grow from last faded level at baseline export growth (Excel R111 2031+).

#### Investigation

1. Re-diff Excel `C3_Commodity prices_ext` R19 (exports/GDP) vs Python for
   2025–2028 (fade after `commodity_close_years`).
2. Check whether GDP ε / CA / revenue side effects match B3 path for **all**
   fade years (not only shock window).
3. Separate denominator (exports) failures from numerator (PV) failures.

#### Tasks

- [x] Align fade timing / scale path in `apply_commodity_price_shock` with
      Excel C3 formulas (incl. post-close export growth).
- [x] Align post-shock R18 in `external_residual_borrowing` for
      `exports_shocked_in_levels` (C3) — not B3 side effects.
- [x] Localize R19 → R36 → Output 3-1 C3.

#### Tests to pass

- [x] Keep `test_c3_commodity_pv_to_exports_2025` green.
- [x] C3 Output 3-1 all indicators 2024–2034 @ `1e-6` (`test_c3_output31_excel_green`).
- [x] B3 Output 3-1 / 3-2 regression green (shared export side effects).

---

### PR-3 — C1_CombinedCL: later-year PV / CL persistence

**Effort:** 1–2 d  
**Maps to:** Phase 11 remaining item #2  
**Symptom:** Shock year (~2025) ≈ Excel; 2026–2028 PV drifts up to ~6 ppt

#### Investigation

1. Diff `external_cl_gap_usd` and ResFin PV stock path vs Excel C1 sheet for
   years **after** the one-off CL year.
2. Check whether Excel keeps CL in the identity / other flows beyond t+1.
3. Compare residual gap R86 (or sheet residual row) year-by-year.
4. Confirm 40.7% external PPG share still correct for this template.

#### Tasks

- [ ] Fix CL persistence / ResFin amort / interest feedback so later-year PV
      matches Excel.
- [ ] Localize gap → R35 → Output 3-1 C1 for 2024–2028.
- [ ] Tighten `test_c1_cl_external_resfin_2025` from `1e-2` → `1e-6` if R35
      closes.

#### Tests to pass

- [ ] C1 Output 3-1 PV indicators 2024–2028 @ `1e-6` (or sized residual).
- [ ] Phase 11 early-horizon max-diff guard (tighten from 7.0 toward 1.0 as
      PRs land).

---

### PR-4 — Unlock Output 3-1 C* green subset

**Effort:** 0.5 d  
**Depends on:** PR-1–PR-3 materially green

#### Tasks

- [ ] Add C1/C3/C4 labels to `_OUTPUT31_EXCEL_GREEN` (PV indicators; DS only
      if green).
- [ ] Promote `test_tailored_output31_early_horizon_improved` from soft max-
      abs guard to `assert_all_passed` for agreed years.
- [ ] Update Phase 11 status → **Complete**; shrink KNOWN_GAPS O31 C* rows.
- [ ] Record before/after pass counts from `stress_parity_report.py --layer
      output31`.

#### Tests to pass

- [ ] `test_output_31_excel_green_subset` includes C* and passes.
- [ ] Full-catalog `missing_sut == 0` unchanged.

---

## Track B — Output 3-2 (public tailored)

### PR-5 — C3 public Output 3-2

**Effort:** 1–2 d  
**Depends on:** PR-2 (trusted commodity macro)  
**Sheet:** `C3_commodity_prices_pub` exists  
**Status:** Done for 2024–2026 @ `1e-6`; ~0.001 ppt PV 2027+ (ResFin ST tail)

#### Route

Full public stress on `C3_commodity_prices_pub` (not B3-style overlay).

```
R41 (AA69 R54) → R88 (R20 B1 GDP denom) → R90 → R13 / R95 / R97 → Output 3-2
```

#### Tasks

- [x] Diff `C3_commodity_prices_pub` R41/R90/R13 vs Python public runner.
- [x] Fix public GDP / GFN / PV path for commodity (R54 + R20/R18 quirks).
- [x] Wire debt-dynamics R11/R80 through `StressPublicBook` C3 metadata.
- [ ] Graduate C3 into full `_OUTPUT32_EXCEL_GREEN` when 2027+ @ `1e-6`.

#### Tests to pass

- [x] Focused C3 Output 3-2 2024–2026 @ `1e-6`.
- [x] B3/B4 Output 3-2 regression green (`test_stress_v2_public_ratios`).

---

### PR-6 — C4 public Output 3-2

**Effort:** 1–2 d  
**Depends on:** PR-1 (C4 terms trusted)
**Status:** Done — C4 Output 3-2 overlay green 2024–2034 @ `1e-6`. Residual was
PV Stress stock = face (not discounted); closed with O31 C4 identity.

#### Investigation

1. Confirm whether a dedicated `*_pub` sheet exists; if only
   `C4_Market_financing`, classify as ext-only vs dual.
2. Expect FX passthrough + market financing add.int on the public side
   (B5/B2 lessons).
3. Watch for double-counting C4 `MarketFinancingCost` vs B2-style
   `_market_add_int_*`.

#### Tasks

- [x] Wire public (or overlay) path for C4 Output 3-2.
- [x] Localize pub intermediates if present; else Output-only diffs.
- [x] Graduate C4 Output 3-2 green subset (`test_c4_output32_excel_green`).

#### Tests to pass

- [x] C4 Output 3-2 @ `1e-6` for 2024–2034.
- [x] B5/B6 Output 3-2 regression green.

---

### PR-7 — C1 public Output 3-2

**Effort:** 1–2 d  
**Depends on:** PR-3 (CL gap trusted)  
**Status:** Done — root cause was flat 10% CL; Excel AA60 = Input 2 F25 ≈ 9.375%

#### Investigation

1. Map `C1_Combined CL` formulas for public PV/DS.
2. Likely needs CL in GFN **and** external gap coupling (closer to B2 coupled
   than to B3 overlay).
3. One-off CL year vs persistence must match PR-3 semantics.
4. **Landed:** Chart Data O32 ← `C1_Combined CL` R13; CL size = Input 2 F25
   (not Input 6). Loader sets `TailoredParams.cl_shock_pct_gdp` from F25.

#### Tasks

- [x] Implement coupled/public path for C1 Output 3-2.
- [x] Localize R41/R90/R13 if pub rows exist.
- [x] Graduate C1 Output 3-2 green subset.

#### Tests to pass

- [x] C1 Output 3-2 @ `1e-6` for agreed years.
- [x] B2 Output 3-2 regression green (shared market/coupling surfaces).

---

### PR-8 — Graduate Track B + close phase

**Effort:** 0.5 d

#### Tasks

- [ ] `_OUTPUT32_EXCEL_GREEN` includes C1/C3/C4 labels.
- [ ] Update [`KNOWN_GAPS.md`](KNOWN_GAPS.md): remove or shrink C* O31/O32 rows.
- [ ] Mark Phase 13 + Phase 11 complete in [`README.md`](README.md).
- [ ] Record Output 3-2 before/after pass counts in parent Phase 13 doc.
- [ ] Optional: C2 stub note if still `n.a.`.

#### Phase definition of done

- [ ] Output 3-1 and 3-2 C1/C3/C4 Excel-green for agreed horizon @ `1e-6`.
- [ ] Phase 11/12 regression suites green.
- [ ] `missing_sut == 0` on full catalogs.
- [ ] No unexplained C* rows left in KNOWN_GAPS (or residuals sized).

---

## Suggested merge order

```
PR-0 (hygiene / localize)
  → PR-1 (C4 O31 maturity)     ┐
  → PR-2 (C3 O31 fade)         ├─ can parallel after PR-0 if careful
  → PR-3 (C1 O31 persistence)  ┘
  → PR-4 (unlock O31 C*)
  → PR-5 (C3 O32)
  → PR-6 (C4 O32)
  → PR-7 (C1 O32)
  → PR-8 (docs + graduate)
```

| PR | Effort | Impact |
|----|--------|--------|
| PR-0 | 0.5 d | Diagnostics |
| PR-1 | 1–2 d | C4 Output 3-1 |
| PR-2 | 1–2 d | C3 Output 3-1 |
| PR-3 | 1–2 d | C1 Output 3-1 |
| PR-4 | 0.5 d | Unlock O31 C* |
| PR-5 | 1–2 d | C3 Output 3-2 |
| PR-6 | 1–2 d | C4 Output 3-2 |
| PR-7 | 1–2 d | C1 Output 3-2 |
| PR-8 | 0.5 d | Docs / green subset |

**Total:** ~8–14 days.

## What not to do

- Unlock Output 3-2 C* before Track A identity is trusted for that shock.
- Flip `fx_revalue_portfolio=True` for C4 without a workbook recalc plan.
- Edit `bound.external_residual_borrowing` “for quick O32 wins” on standard B*.
- Add per-year fudge factors.
- Invent `C1_*_pub` / `C4_*_pub` names that are not in the workbook.
- Bundle C1+C3+C4 formula fixes in one PR.

## Coordination

```
Phase 11 leftovers (O31)          Phase 13 Track B (O32)
stress/tailored.py, bound.py      public_gfn.py, public.py, suite
market_access.py                  output_map.py (overlay if needed)
         │                                    │
         └──────── merge at suite / KNOWN_GAPS / full_catalog ────────┘
```

Low conflict with Phase 12 leftovers (A2) if A2 stays on `custom_spec` only.
