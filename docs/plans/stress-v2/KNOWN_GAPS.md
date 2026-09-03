"""Known gaps for the stress-v2 rewrite (post Phase 8 cutover).

Tolerance policy is global: ``ABS_TOL = 1e-6`` or ``REL_TOL = 1e-12`` in
``tests/parity/equality.py``. Do not add per-probe exceptions without listing
them here.

Phase 8 cut over ``lic_dsf.stress.run_*`` to the v2 facade and wired tailored
A2/C* into Output 3-1. Phase 9 closed standard external Output 3-1 (B3/B5/B6).
Phase 10 closed public B1/A1 R13/R95/R93 and Output 3-2 Baseline/A1/B1.
Phase 11 closed tailored external C1/C3/C4 Output 3-1 for 2024 and materially
reduced 2025+ drift (C3 R36 @ 2025 green; C1 R35 @ 2025 ≈ Excel). Phase 13 PR-2
closed C3 Output 3-1 through 2034. Phase 12
covers public B2–B6 Output 3-2. Remaining drifts below are **not** missing SUT
rows.

| Gap | Probe / location | Current size | Notes |
|-----|------------------|--------------|-------|
| C1 Output 3-1 / 3-2 | Combined CL | green | Input 2 F25 CL% (Excel AA60); was flat 10% |
| C3 Output 3-1 | Commodity external | green 2024–2034 | Post-shock R18 = baseline % (not B3 USD scale); export tail grows at baseline R55 after close years |
| C3 Output 3-2 | Tailored public | green 2024–2026; ~0.001 ppt 2027+ | Pub R54 AA69 deflator + R20 B1 GDP denom + R18 AA66; ResFin ST tail |
| C4 Output 3-1 / 3-2 | Market financing | green 2024–2034 | PV Stress R150/R164 copy residual stock; keep `fx_revalue_portfolio=False` |
| B2 Output 3-1 DS | Debt-service / B2 | green 2024–2034 | Non-mkt GFN keeps domestic add.int (Excel B70:C70 = 0 ext rate) |
| A2 Output 3-2 | Public customized | green 2024–2034 | R121 uses prior+R15 at t0 (not Macro stock); Chart Data ← custom R123 |
| Add.int schedule layout | `PV_ResFin-add.int.cost - mkt` F–G | Incomplete catalog | Debug only |
| Public B-sheet row 43 | Plan draft vs template | Catalog uses R95 / R93 | Documented Phase 0 |
| `CachedStressExternalBook` | `load_cached_external_stress` | Deprecated debug dump | Not used in production SUT |
| LC-NR reval default | `fx_revalue_portfolio` | Off for B5/B6/C4 | Re-enable after workbook recalc |
"""
