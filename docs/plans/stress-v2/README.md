# Stress module rewrite — phase plans

Strangler migration from the current `lic_dsf.stress` package to a layered
architecture (`stress`) driven by differential testing against the bundled
LIC-DSF workbook.

## Principles

- **Do not delete** the current stress module until the new path passes the full
  probe catalog.
- **Baseline is trusted** — `load_core()`, `BaselineExternalBook`, and
  `BaselinePublicBook` are inputs, not rewritten.
- **Test bottom-up** — macro path → gaps → ResFin → B-sheet ratios → Output 3-x.
- **Completeness** — `missing_sut == 0` and all probes pass at `1e-6` tolerance.

## Target architecture

```
StressContext → MacroShock → ShockedMacroPath
                          → ExternalDebtDynamics ─┐
                          → PublicGFNIdentity ────┼→ ResidualFinancingEngine
                                                  └→ Stress*Ratios → StressScenarioResult
```

New code lives in `src/lic_dsf/stress/` during migration. Public API in
`lic_dsf.stress` delegates to v2 at cutover.

## Phases

| Phase | Document | Summary |
|-------|----------|---------|
| 0 | [phase-00-test-harness.md](phase-00-test-harness.md) | Probe catalogs, coverage report, acceptance criteria |
| 1 | [phase-01-context-and-spec.md](phase-01-context-and-spec.md) | `StressContext`, `ScenarioSpec`, registry |
| 2 | [phase-02-shocked-macro-path.md](phase-02-shocked-macro-path.md) | `MacroShock`, `ShockedMacroPath` |
| 3 | [phase-03-external-debt-dynamics.md](phase-03-external-debt-dynamics.md) | `ExternalDebtDynamics`, external R86 |
| 4 | [phase-04-residual-financing-engine.md](phase-04-residual-financing-engine.md) | `ResidualFinancingEngine`, split policies |
| 5 | [phase-05-external-ratios-and-runner.md](phase-05-external-ratios-and-runner.md) | `StressExternalRatios`, external runner |
| 6 | [phase-06-public-gfn-and-ratios.md](phase-06-public-gfn-and-ratios.md) | `PublicGFNIdentity`, `StressPublicRatios` |
| 7 | [phase-07-coupling-and-market-access.md](phase-07-coupling-and-market-access.md) | R86 coupling, market access, FX reval |
| 8 | [phase-08-tailored-and-cutover.md](phase-08-tailored-and-cutover.md) | Tailored scenarios, facade swap — **Complete** |
| 9 | [phase-09-external-excel-parity.md](phase-09-external-excel-parity.md) | B3/B5/B6 Excel parity (W0–W4) — **Complete** |
| 10 | [phase-10-public-excel-parity.md](phase-10-public-excel-parity.md) | Public / Output 3-2 Excel parity (W5) — **Complete** |
| 11 | [phase-11-tailored-external-excel-parity.md](phase-11-tailored-external-excel-parity.md) | Tailored external C1/C3/C4 Output 3-1 — **Complete (partial)** |
| 12 | [phase-12-public-stress-excel-parity.md](phase-12-public-stress-excel-parity.md) | Public Output 3-2 B2–B6 (+ A2) — **In progress** ([PR plan](phase-12-pr-implementation.md)) |
| 13 | [phase-13-tailored-c-excel-parity.md](phase-13-tailored-c-excel-parity.md) | C1/C3/C4 Output 3-1 finish + Output 3-2 — **In progress** ([PR plan](phase-13-pr-implementation.md)) |

Phases 9–11 are independent workstreams (different formula surfaces). Phase 12
covers shocked-macro public ratios. Phase 13 finishes tailored C* on both
Output 3-1 and 3-2. See each plan for PR ownership rules.

## Definition of done (program-wide)

1. Every numeric probe in `output_31_probes` and `output_32_probes` passes at
   `ABS_TOL = 1e-6` (`tests/parity/equality.py`).
2. B-sheet intermediate catalogs pass for all standard scenarios.
3. No production code reads stressed ratios from Excel B sheets
   (`CachedStressExternalBook`, workbook-path B6 add.int loaders removed).
4. `lic_dsf.stress.run_*` public API unchanged for downstream callers.

## Related docs

- [Stress DSA guide](../../08-stress-dsa.qmd)
- [Excel → Python map](../../01-excel-map.qmd)
- Parity harness: `tests/parity/`
- Existing output probes: `tests/parity/catalogs/output_3.py`
- Known gaps: [KNOWN_GAPS.md](KNOWN_GAPS.md)
