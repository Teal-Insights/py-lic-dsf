# Phase 7 — Coupling, market access, and FX revaluation

**Status:** Complete  
**Depends on:** [Phase 5](phase-05-external-ratios-and-runner.md), [Phase 6](phase-06-public-gfn-and-ratios.md)  
**Blocks:** Phase 8

## Goal

Close the remaining divergence gaps: public↔external ResFin coupling (R86 into
public split), B2 market-access add.int, B6 combo add.int computed in Python,
and LC-NR FX portfolio revaluation on B5/B6.

## Prerequisites

- External and public runners from Phases 5–6
- Phase 0 ResFin + Output 3-1 B2 / B6 probes
- Legacy partial implementations in `public.py`, unused `rebuild_external_with_fx`

## Deliverables

| Item | Location |
|------|----------|
| `ExternalPortfolioAdjuster` | `src/lic_dsf/stress/external_portfolio.py` |
| `MarketAccessAddon` | `src/lic_dsf/stress/market_access.py` |
| `ComboMarketCost` | `src/lic_dsf/stress/market_access.py` |
| Coupled runner orchestration | `src/lic_dsf/stress/runner/coupled.py` |
| Parity tests | `tests/test_stress_v2_coupling.py` |

## Class responsibilities

### `ExternalPortfolioAdjuster`

**Takes:**

- `ExternalDebtBook external`
- Shocked `fx_pa`, `fx_eop` from `ShockedMacroPath`

**Returns:** New `ExternalDebtBook` with LC-NR instruments revalued.

Port `rebuild_external_with_fx` from `stress/scenario.py`. Invoke when
`ScenarioSpec.fx_revalue_portfolio` is true (B5, B6).

### `MarketAccessAddon`

**Takes:**

- `StressContext`
- `ShockedMacroPath`
- `PublicResFinOverlay` (market vs non-market blocks)
- PB deviation in shock window

**Responsibilities:**

- Port `_market_add_int_rates`, `_market_add_int_interest_lcu`
- Build add.int stock/amortization matching `PV_ResFin-add.int.cost - mkt`
- Dual-block semantics: PV uses market gap overlay; DS may use non-market
  (`resfin_external_ds` pattern from legacy `StressPublicBook`)

**Methods:**

- `additional_interest_lcu() -> pd.Series`
- `adjust_public_ratios(ratios: StressPublicRatios) -> StressPublicRatios`

### `ComboMarketCost`

**Takes:** B6 combo context, PB deviations, ResFin fill in shock window.

**Responsibilities:**

- Replace `load_combo_additional_borrowing_interest(workbook_path)` with Python
  computation from `PV_Base-add.cost.mkt` logic
- Feed `additional_borrowing_interest` into `ExternalDebtDynamics`

### Coupled orchestration

When `ScenarioSpec.couple_ext_r86`:

1. Run external dynamics → `external_gap`
2. Pass `external_gap` into `AbsoluteResidualPolicy.split` for public ResFin
3. Run public GFN ↔ ResFin loop with coupled fill

Single entry: `CoupledScenarioRunner.run(ctx, spec) -> StressScenarioResult`
with both `external_ratios` and `public_ratios`.

## Known gaps this phase fixes

| Gap | Fix |
|-----|-----|
| `ext_r86` API always zero | Wire Phase 3 gap into Phase 4 `AbsoluteResidualPolicy` (B2 gap is zero by construction) |
| B2 split always `capped` | Use `AbsoluteResidualPolicy` per spec |
| B2 Output 3-1 2026 PV ~1e-3 drift | Market add.int + dual-block; PV catalog now 1e-6 |
| B6 without `workbook_path` | `ComboMarketCost` in Python |
| LC-NR not revalued on B5/B6 | `ExternalPortfolioAdjuster` |
| `domestic_borrowing_cost_bps` unused | Apply if Excel B2 dom cost rows require it |

## Implementation tasks

1. Implement `ExternalPortfolioAdjuster`; integrate into external runner for
   B5/B6. ✅

2. Implement `MarketAccessAddon`; gate on `spec.market_access` and Input 1. ✅

3. Implement `ComboMarketCost`; remove workbook-path dependency from B6 external
   runner. ✅

4. Implement `CoupledScenarioRunner` for B2 (and any scenario with
   `couple_ext_r86`). ✅

5. Tighten fixed-point tolerances; verify 2026 B2 PV at `1e-6`. ✅

6. Run full Output 3-1 B2 probe catalog (all 4 indicators × 11 years). ✅ PV;
   DS shock-window only (later years still drift — KNOWN_GAPS).

## Differential testing

| Target | Probes |
|--------|--------|
| B2 Output 3-1 | All `output_31_probes` with B2 label (PV full; DS shock window) |
| B2 Output 3-2 | B2 public rows |
| B6 external | Combo add.int vs workbook loader; Output 3-1 smoke |
| B5 external | LC-NR PV change vs unrevalued legacy |
| `PV_ResFin-add.int.cost - mkt` | Interest rows in shock window |
| Coupling | Absolute policy + wired external gap on B2 result |

Migrate and tighten:

- `test_output_31_cached_b2_matches_excel` — remove `1e-3` relaxation on 2026 ✅

**Tolerance:** `1e-6` everywhere unless Excel iteration limit is proven
impossible (must document with cell-level evidence).

## Definition of done

- [x] Output 3-1 B2 full PV catalog at `1e-6`
- [x] B6 passes without reading `PV_Base-add.cost.mkt` from workbook
- [x] B5/B6 external ratios reflect LC-NR FX revaluation
- [x] B2 uses `AbsoluteResidualPolicy` with coupled R86 wiring (value is zero for PB shock)
- [x] No `workbook_path` argument on standard v2 runners

## Out of scope

- Tailored C* scenarios (Phase 8)
- Legacy code deletion (Phase 8)

## Delete criteria

Remove `load_combo_additional_borrowing_interest` from production **v2** runner
path; keep loader only for parity debugging. Legacy `run_b6_combo_external`
still accepts `workbook_path` until Phase 8 cutover.
