# Plan: Output parameter sensitivity analysis

**Goal:** Learn which parameters final LIC-DSF outputs are increasingly sensitive (or insensitive) to.

**Non-goals:** Proving Excel↔Python mathematical identity (see [`01-excel-parity-differential-testing.md`](01-excel-parity-differential-testing.md)). Replacing Input 6 stress scenarios with a generic fuzzer.

**Status:** Planning — independent of the JSON parity corpus, but may reuse the same **input parameter vocabulary** once that exists.

---

## 1. Problem

Economists and implementers need a map of:

- Which inputs move headline outputs a lot vs barely at all.
- Where small input error (or Python/Excel disagreement) would change risk conclusions.
- Which regions of the input space deserve denser parity coverage.

The spreadsheet already encodes *standardized* shocks (Input 6, tailored stresses). That is scenario analysis, not a systematic local/global sensitivity study over a chosen parameter set.

## 2. Approach

Run **perturbation experiments** primarily on **Python**, using bases that Plan 01 (or current parity) has already cleared.

```text
parity-cleared baseline
    → choose output vector Y
    → choose parameter set Θ
    → apply design (OAT → Morris → optional Sobol)
    → rank / visualize sensitivity
    → optional Excel spot-check on extremes
```

Rationale: once Python matches Excel near a baseline, Python is a fast surrogate for ΔY/Δθ. Dual-running every sample through Excel is usually unnecessary and expensive.

**Hard rule:** Do not interpret sensitivity rankings on a baseline that fails parity in the same neighborhood — bugs look like “sensitivity.”

## 3. Define Y (outputs) and Θ (parameters)

### 3.1 Output vector Y (start small)

Prefer Excel-facing, decision-relevant series already exposed by `lic_dsf.output` / DSA panels:

| Priority | Outputs |
|---|---|
| P0 | Baseline external indicators (Output 1-1 style): PV/GDP, PV/X, PV/Rev, DS/X, DS/Rev |
| P0 | Baseline public indicators (Output 1-2): public PV/GDP, DS/(Rev+grants), GFN/GDP |
| P1 | Stress envelope (Output 3-1 / 3-2): baseline vs worst bound for key ratios |
| P2 | Mechanical rating / summary labels (Output 7) — discrete metric |
| P2 | Realism / forecast-error headlines if needed later |

Aggregate metrics for ranking (pick explicitly per study):

- Max abs change over projection horizon: \(\max_t |Y_t(\theta+\delta) - Y_t(\theta)|\)
- Change at a fixed horizon (e.g. last projection year)
- Threshold events (breach of CI bound, rating notch change)

### 3.2 Parameter set Θ

Group by Input surface (Excel-native ids help later dual-use with Plan 01 overlays):

| Group | Examples |
|---|---|
| Macro / debt stocks | GDP path, exports, primary balance, FX, existing debt stocks |
| Financing / ResFin | Residual financing mix, concessionality, market access flags |
| Stress knobs | Input 6 shock sizes, interaction elasticities, tailored disaster/commodity params |
| Rating / CI | CI covariates that move thresholds (if in scope) |
| Instrument terms | Grant element drivers, maturity, interest (sparse at first) |

Start with a **hand-picked Θ of ~15–40 continuous (or binary) params** tied to known Output movers; expand after OAT.

Normalize for ranking: report elasticities or %ΔY / %Δθ (or per-σ for Morris), not raw Δ with mixed units.

## 4. Experimental designs (phased)

### Phase A — One-at-a-time (OAT) / tornado

- Fix baseline θ₀ (template or a named case).
- For each θᵢ ∈ Θ, apply ±ε (relative or absolute policy per param).
- Record ΔY for each P0 output.
- Produce tornado charts / ranked tables.

**Exit:** First sensitivity report for baseline template; document ε policy per group.

### Phase B — Screening (Morris / elementary effects)

- When Θ grows or interactions matter (combo shocks, ResFin × FX).
- Modest sample count; identify params with high μ* / σ for follow-up.

**Exit:** Shortlist of “always move Y” vs “flat” params; drop flats from expensive designs.

### Phase C — Optional global (Sobol) on shortlist

- Only for 5–12 params that survive Morris.
- Estimate main-effect and total-order indices for 1–2 scalar Y summaries.

**Exit:** Interaction-aware ranking for the shortlist; stop if OAT+Morris already answers the product question.

### Phase D — Excel spot-checks

- For top-k sensitive directions and a few “surprising flats,” remint or live-compare Excel vs Python (Plan 01 mint or existing live probes).
- If dual-run disagrees, fix parity first; do not publish the sensitivity rank.

**Exit:** Confidence that the sensitivity map is about the DSF math, not a Python-only artifact.

## 5. Harness shape (proposed)

Keep sensitivity tooling under tests or a small analysis package — not required as public API initially:

```text
analysis/sensitivity/   # or tests/sensitivity/
  config.py             # Y definitions, Θ registry, ε policies
  perturb.py            # apply param → workbook overlay or in-memory inputs
  designs/
    oat.py
    morris.py           # optional later
  metrics.py            # Δ aggregators, discrete rating distance
  report.py             # CSV / markdown / plots
  baselines/            # pointers to parity-cleared cases
```

**Input application:** Prefer the same overlay vocabulary as Plan 01 (`sheet`, `cell`, `value`) so a sensitive direction can become a parity case. Until Plan 01 exists, allow direct mutation of loaded dataclasses / Input 6 structs with a registry that records the Excel cell when known.

Pipeline CLI (illustrative):

```bash
uv run python -m analysis.sensitivity.run --baseline template --design oat --out results/sens-oat/
```

## 6. Relationship to Plan 01

| Concern | Plan 01 | Plan 02 |
|---|---|---|
| Oracle | Excel-minted goldens | Python primary; Excel spot-check |
| Case role | Identity corpus | Baseline + perturbation grid |
| Shared asset | Input overlay schema | Same |
| Feedback | — | High-sensitivity params → add Plan 01 cases |

Independence: Plan 02 can start with programmatic perturbations on `load_*` results **before** JSON cases exist, but should gate publication of rankings on parity clearance for that baseline.

## 7. Reporting

Minimum deliverable per study:

1. Baseline id + template hash + parity status.
2. Θ list with units and ε policy.
3. Ranked table: param → metric(ΔY) for each Y in P0.
4. Tornado plot (optional but recommended).
5. Notes: discrete rating flips, params with near-zero effect, known Excel scenario analogues (e.g. “similar to B3 Exports”).

Store results under `data/sensitivity/` or `results/` (git policy TBD — large binaries/plots may be gitignored; keep CSV summaries).

## 8. Risks

| Risk | Mitigation |
|---|---|
| Ranking on buggy baseline | Require parity green near θ₀ |
| Unit-incomparable Δ | Normalize (elasticity / % / per-σ) |
| Confusing Input 6 scenarios with OAT | Document: standard stresses ≠ sensitivity design |
| Combinatorial explosion | OAT → Morris shortlist → optional Sobol |
| Discrete outputs | Separate metric (notch distance); don’t force Sobol on labels |

## 9. Success metrics

- Published OAT tornado for P0 outputs on the bundled template.
- Explicit list of low-sensitivity params (candidates for thinner parity probing).
- Explicit list of high-sensitivity params (candidates for denser Plan 01 cases and code review).
- At least one Excel spot-check on a top-ranked direction with documented agreement.

## 10. Dependencies / prerequisites

- Ability to rebuild baseline books from the template (`load_*`, DSA, stress runners).
- Output accessors already used in demos/tests (`output_*_table`, panels).
- Prefer Plan 01 Phase A overlays when available; not a hard blocker for Phase A OAT.

## 11. Out of scope for this plan

- Minting Excel goldens for every perturbation sample.
- Claiming policy recommendations from sensitivity ranks alone.
- Full instrument-by-instrument global SA across the entire PV portfolio.
