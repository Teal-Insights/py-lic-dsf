# Plan: Split internal seams inside `stress`

**Goal:** Make `lic_dsf.stress` navigable by subdomain (shocks / runners / ratios) after ResFin is no longer nested inside it.

**Non-goals:** Changing stress formulas. Extracting ResFin (Plan 03). Full merge of stress ratios with `dsa` baseline books in one PR. Renaming every public `run_b1_*` facade.

**Status:** Planning.

**Depends on:** [`03-resfin-off-pv.md`](03-resfin-off-pv.md) (ResFin becomes `lic_dsf.resfin`; stress only *calls* it). Prefer after Plan 03 Phase D so `stress.residual_pv` / `stress.resfin` are shims or gone.

**Related:** [`docs/08-stress-dsa.qmd`](../docs/08-stress-dsa.qmd); current tree under [`src/lic_dsf/stress/`](../src/lic_dsf/stress/) (~10k lines).

---

## 1. Problem

`stress` is the largest package and mixes:

| Concern | Examples today |
|---|---|
| Shock construction | `macro_shocks`, `shocks/`, `tailored/`, `tailored_params`, `bound` |
| Residual financing | `resfin/`, `residual_pv` → should leave (Plan 03) |
| Orchestration | `runner/`, `facade`, `suite`, `scenario`, `public`, `context` |
| Ratio projection | `ratios/external`, `ratios/public`, `ratios/public_paths` |
| Presentation | `output_map` → Plan 08 |
| Spec / types | `spec`, `types`, `path`, `result` |

New contributors cannot tell where to put a B-sheet fix vs an Input 6 shock fix vs a ResFin fixed-point fix.

## 2. Design rule

```text
Input 6 / tailored → shocked Macro path     → stress.shocks
Shocked path + Ext + ResFin → ratios          → stress.ratios
Wire shocks → resfin → ratios → result        → stress.runners (facade/suite stay thin)
Excel Output 3 geometry                         → output (Plan 08)
Residual financing                              → lic_dsf.resfin (Plan 03)
```

**Dependency direction:**

```text
books / pv
    ↑
resfin
    ↑
stress.shocks → stress.runners → stress.ratios
    ↑
output / rating
```

## 3. Target layout

```text
src/lic_dsf/stress/
  __init__.py          # stable public facade (run_* re-exports)
  types.py             # Input6StandardParams, StressScenarioId, …
  spec.py
  path.py              # ShockedMacroPath
  result.py
  context.py
  shocks/
    __init__.py        # MacroShockFactory + tailored entrypoints
    macro.py           # today’s macro_shocks.py
    tailored.py        # tailored package + params
    bound.py
    market_access.py
    market_terms.py    # C4 term tweaks (uses resfin params)
  ratios/
    …                  # already exists; keep
  runners/
    …                  # today’s runner/ + slim facade/suite/scenario/public
```

Public API stability: keep `from lic_dsf.stress import run_b1_gdp_external, …` working via `__init__.py` re-exports.

## 4. Phases

### Phase A — Post-ResFin cleanup

1. Confirm ResFin imports come from `lic_dsf.resfin`.
2. Delete empty shims (`residual_pv`, nested `stress.resfin`) or leave one-line re-exports.
3. Draw current call graph: facade → runner → shocks / resfin / ratios.

**Exit:** Stress package no longer *owns* ResFin implementation.

### Phase B — Group shocks

1. Move `macro_shocks.py`, `bound.py`, market helpers, tailored modules under `stress/shocks/`.
2. Keep `MacroShockFactory` as the external entry.
3. Update runners only (no math changes).

**Exit:** All Input 6 / tailored shock construction imports live under `stress.shocks`.

### Phase C — Clarify runners vs legacy modules

1. Fold overlapping `scenario.py` / `public.py` orchestration into `runners/` where duplication is clear; or document “legacy facade wrappers” if too risky.
2. Ensure `suite.py` / `facade.py` remain thin: build context → run specs → return results.
3. Avoid renaming public `run_*` functions in this phase.

**Exit:** One documented orchestration path; fewer duplicate runner-shaped modules (or explicit deprecation comments).

### Phase D — Ratios hygiene (light)

1. Deduplicate `_pct` / `_align` / `_clamp` helpers shared with `dsa` only if trivial (optional shared `lic_dsf.dsa._series` or leave copies — do not force a big shared util PR).
2. Document: stress ratios = baseline Ext numerators + ResFin overlay over shocked denominators.

**Exit:** Short module docstring contract on `stress.ratios`.

### Phase E — Docs

Update `08-stress-dsa.qmd` and excel-map package roles: stress = shocks + runners + ratios; ResFin separate; Output 3 in `output`.

## 5. Compatibility

Preserve:

```python
from lic_dsf.stress import (
    run_standard_external_stress,
    run_b1_gdp_public,
    Input6StandardParams,
    …
)
```

Internal deep imports (`lic_dsf.stress.macro_shocks`) may break — grep and fix, or re-export for one release.

## 6. Test plan

```bash
uv run pytest tests/test_stress_dsa.py tests/test_stress_tailored.py
uv run pytest tests/test_stress_output_tables.py tests/test_stress_spec.py
uv run pytest tests/test_parity_cases.py -k 'output_3 or stress or resfin'
uv run pytest
```

## 7. Risks

| Risk | Mitigation |
|---|---|
| Drive-by refactors while moving | Move-only PRs; no formula edits |
| Facade / scenario / public duplication rabbit hole | Phase C: document first, merge only clear dupes |
| Coupling to Plan 08 output_map | Leave `output_map` in place until Plan 08; don’t block stress seams |

## 8. PR split

1. **PR1** — Post-ResFin delete/shim cleanup
2. **PR2** — `stress/shocks/` grouping
3. **PR3** — Runner consolidation (optional / smaller)
4. **PR4** — Docs

## 9. Done when

- [ ] ResFin implementation not under `stress/`
- [ ] Shock construction concentrated under `stress.shocks`
- [ ] Public `run_*` API unchanged
- [ ] Stress + Output 3 parity tests green
- [ ] Docs describe shocks / runners / ratios / resfin roles
