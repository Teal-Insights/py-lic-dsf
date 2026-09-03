# Phase 11 — Tailored external Excel parity (C1 / C3 / C4)

**Status:** Complete (partial — see remaining)  
**Depends on:** [Phase 8](phase-08-tailored-and-cutover.md), [Phase 9](phase-09-external-excel-parity.md)  
**Blocks:** [Phase 13](phase-13-tailored-c-excel-parity.md) tailored C* Output 3-1 close + public Output 3-2  
**Parallel:** [Phase 12](phase-12-public-stress-excel-parity.md)

## Goal

Close Output 3-1 Excel drifts for tailored external scenarios in causal order:

**W0 localize → W1 C3 commodity macro → W2 C4 market cost → W3 C1 CL ResFin → unlock tests.**

## What shipped

### W0 — Localization

| scenario | first failing row | first failing year | root bucket |
|----------|-------------------|--------------------|-------------|
| C3 | R19 / R36 | 2025 | export scale + GDP ε |
| C4 | R35 / R40 | 2025 | FX identity + market add.int |
| C1 | R35 | 2025 | CL → external PPG ResFin gap |

### W1 — C3 commodity

- Export scale: `1 + adj_share² × avg_price_shock` (Excel C3 export-GDP path).
- B3-style GDP ε + CA/revenue side effects via `_apply_export_shock_side_effects`.
- R36 @ 2025 Excel-green at `1e-6`.

### W2 — C4 market financing

- `MarketFinancingCost`: Input 6 **400 bps × 3 years** on commercial disbursements.
- Wired through `ExternalScenarioRunner` as `additional_borrowing_interest`.
- Maturity/grace shortening (Input 6 rows 54–56) **not** yet modeled → residual R35/R40 drift.

### W3 — C1 combined CL

- `external_cl_gap_usd`: one-off CL (LCU) → external PPG gap @ 40.7% share in shock year.
- ResFin overlay; R35 @ 2025 within `1e-2` (Excel 47.22).
- Later-year PV path still drifts (ResFin decay vs Excel).

## Deliverables

| Item | Location |
|------|----------|
| Commodity export scale + GDP ε | `stress/tailored.py`, `stress/shocks.py` |
| C1 CL external gap | `stress/bound.py`, `stress/external_dynamics.py` |
| C4 market add.int | `stress/market_access.py`, `runner/external.py` |
| Tests | `tests/test_stress_v2_tailored_external.py` |
| Localization | `scripts/stress_phase11_localize.py` |

## Definition of done

- [x] C3 R36 @ 2025 Excel-green at `1e-6`
- [x] C1 R35 @ 2025 within `1e-2`; external gap + ResFin PV wired
- [x] C4 market add.int schedule populated (400 bps × 3y)
- [x] All tailored 2024 Output 3-1 rows Excel-green
- [x] 2024–2028 max drift < 7 ppt (regression guard)
- [ ] Full-catalog C1/C3/C4 @ `1e-6` all years — C4 maturity shortening; C1 tail years

## Remaining (follow-on → [Phase 13](phase-13-tailored-c-excel-parity.md))

- C4: Input 6 maturity/grace shortening on ResFin terms
- C1: later-year PV path (CL persistence in identity)
- C3: sub-ppt R35/R19 polish 2025+ (fade timing)
- Full Output 3-1 unlock in `test_stress_v2_full_catalog.py`
- Tailored public Output 3-2 (C1/C3/C4)
