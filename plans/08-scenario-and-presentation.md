# Plan: Scenario split and presentation ownership (`output_map`, rating panels)

**Goal:** Separate the two unrelated “scenario” products, and move Excel-geometry / panel assembly to `lic_dsf.output` (and keep rating math in `rating`).

**Non-goals:** Changing probability coefficients, Chart Data breach logic, or Output 3 numbers. Large stress runner refactors (Plan 07).

**Status:** Planning.

**Depends on:** None strictly. `output_map` move pairs well after Plan 07 Phase A (so stress is not mid-ResFin churn). Scenario rename can ship anytime.

**Related:** [`docs/11-scenario.qmd`](../docs/11-scenario.qmd), [`docs/10-risk-rating.qmd`](../docs/10-risk-rating.qmd), [`src/lic_dsf/stress/output_map.py`](../src/lic_dsf/stress/output_map.py), [`src/lic_dsf/rating/summary.py`](../src/lic_dsf/rating/summary.py).

---

## 1. Problem

### 1a. `lic_dsf.scenario` is two Excel products

| Module | Excel | Job |
|---|---|---|
| `scenario.customized` | Customized Scenario – public/external | Path deltas / levels → Chart Data |
| `scenario.probability` | Probability approach / Output 6 | Probit / Φ / distress covariates |

They share a package name and almost nothing else. Stress tailored A2 also imports `CustomizedScenarioSpec`, which makes “scenario” sound like stress.

### 1b. Presentation lives in compute packages

| Today | Better owner |
|---|---|
| `stress.output_map` (Output 3-1 / 3-2 MultiIndex geometry) | `lic_dsf.output.stress` |
| `rating.summary.risk_summary_panel` (Output 7-shaped frame) | Already partly mirrored in `output.rating`; consolidate |

`output` is supposed to own Output-sheet DataFrames; compute packages should expose typed results, not Excel row layouts.

## 2. Design rule

```text
Customized path specs     → lic_dsf.scenario.customized (or lic_dsf.customized)
Probability / Output 6 math → lic_dsf.scenario.probability (or lic_dsf.probability)
Excel geometry / panels   → lic_dsf.output
Mechanical rating logic   → lic_dsf.rating (no DataFrame layout required)
```

## 3. Target layout

### Scenario clarity (pick one approach)

**Option A — Keep package, split docs + exports (minimal):**

```text
lic_dsf/scenario/
  customized.py
  probability.py
  __init__.py   # explicit two sections; no fake unity
```

**Option B — Two top-level packages (clearer long-term):**

```text
lic_dsf/customized/
lic_dsf/probability/
```

with deprecated re-exports from `lic_dsf.scenario`.

Recommend **A now**, **B only if** probability grows (new covariates / models from the LIC-DSF review).

### Presentation moves

```text
lic_dsf/output/stress.py   # absorb output_map builders (output_31_table already here)
lic_dsf/output/rating.py   # single home for output_7_table / risk_summary_panel
```

`stress.output_map` becomes a thin re-export or disappears.  
`rating.risk_summary_panel` re-exports from `output` or becomes a one-line wrapper.

## 4. Phases

### Phase A — Scenario packaging / docs

1. Rewrite `scenario/__init__.py` and `docs/11-scenario.qmd` to present **two** tools.
2. Excel-map row: split Customized vs Probability.
3. No import path breaks required for Option A.

**Exit:** Docs no longer imply one “scenario engine.”

### Phase B — Move `output_map` → `output`

1. Move geometry tables / label maps from `stress.output_map` into `output/stress.py` (or `output/geometry_stress.py`).
2. Update `output` `__init__` exports; `stress.suite` imports from `output`.
3. Fix tests (`test_stress_tailored`, parity catalogs) that import `output_map`.
4. Delete or shim `stress.output_map`.

**Exit:** Stress package does not define Output 3 Excel geometry.

### Phase C — Rating panel consolidation

1. Inventory `risk_summary_panel` vs `output_7_table` / `output.rating`.
2. One canonical Output 7 builder in `output`; rating keeps `RiskRatingSummary` + `compute_mechanical_ratings`.
3. Update demos (`output_7`, `risk_rating`) and docs 10.

**Exit:** Panel assembly not required to import rating for DataFrame shape (rating → output is OK; output should not need rating.compare — Plan 05).

### Phase D — Optional package rename (B)

Only if desired: introduce `lic_dsf.probability` / `lic_dsf.customized`, re-export from `scenario`, then delete `scenario` later.

## 5. Compatibility

| Old | New |
|---|---|
| `from lic_dsf.scenario import CustomizedScenarioSpec` | unchanged (Option A) |
| `from lic_dsf.stress.output_map import EXT_INDICATORS` | `from lic_dsf.output.stress import …` |
| `from lic_dsf.rating import risk_summary_panel` | still works via re-export **or** `lic_dsf.output` |

## 6. Test plan

```bash
uv run pytest tests/test_scenario.py tests/test_rating.py
uv run pytest tests/test_stress_output_tables.py tests/test_stress_tailored.py
uv run pytest tests/test_parity_cases.py -k 'output_3 or output_6 or output_7'
uv run pytest
```

## 7. Risks

| Risk | Mitigation |
|---|---|
| Circular `stress ↔ output` | `output` imports stress **result types** only; stress runners return results; geometry applied in `output` or suite calls `output` |
| Breaking demos | Update notebooks in same PR as moves |
| Over-splitting scenario too early | Stick to Option A unless probability scope expands |

## 8. PR split

1. **PR1** — Scenario docs / `__init__` clarity (Option A)
2. **PR2** — Move `output_map` into `output`
3. **PR3** — Consolidate Output 7 panel ownership
4. **PR4** (optional) — Top-level `probability` / `customized` packages

## 9. Done when

- [ ] Docs treat Customized and Probability as separate tools
- [ ] Output 3 geometry owned by `lic_dsf.output`
- [ ] Output 7 panel has a single canonical builder under `output` (rating may re-export)
- [ ] Scenario / stress output / rating tests + relevant parity green
