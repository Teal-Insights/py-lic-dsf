# Plan: Break ResFin off of `pv`

**Goal:** Make residual financing a first-class domain package that *uses* PV loan math, instead of living inside `lic_dsf.pv`.

**Non-goals:** Changing Excel parity math. Rewriting amortization. Inventing a second loan engine. Moving Macro’s baseline “Residual financing gap” row (that stays a Macro identity).

**Status:** Implemented (Phases A–D).

**Related:** Stress DSA docs ([`docs/08-stress-dsa.qmd`](../docs/08-stress-dsa.qmd)); current engine under [`src/lic_dsf/stress/resfin/`](../src/lic_dsf/stress/resfin/).

---

## 1. Problem

Excel already separates concerns:

| Sheet family | Job |
|---|---|
| `PV_Base` / Input 4 | Instrument template |
| `PV Stress` / `PV_ResFin_pub` | Residual loan + public three-way fill after a GFN gap |

Python has the same economic split but a muddy package boundary:

| Piece | Today | Smell |
|---|---|---|
| `PresentValueInstrument` | `lic_dsf.pv` | Correct home |
| `ResidualFinancingParams` / overrides / Ext averages | `lic_dsf.books.external.residual` | ResFin domain in PV |
| `resfin_instrument` / overlays / dom MLT–ST | `lic_dsf.stress.residual_pv` | Stress owns overlays |
| Fixed-point GFN + policy | `lic_dsf.stress.resfin` | Stress owns engine |
| Docs | `pv` “owns ResFin instrument math” | Out of date / wrong |

Also: `public_dsa_residual_params` exists in **both** `pv.external_debt.residual` and `stress.residual_pv`.

Callers (`load.input7`, stress facades, tests) import ResFin types from `pv`, which makes PV look like the residual-financing owner.

## 2. Design rule

```text
Same math primitive  → keep PresentValueInstrument in pv
Different economic job → ResFin owns gap → fill → overlay → fixed point
```

**Keep:** `resfin_instrument(...)` building a synthetic `"ResFin"` `PresentValueInstrument` (Excel’s PV Stress / ResFin loan).

**Move:** params, defaults, overlays, engine, and the public API for residual financing.

**Dependency direction (hard constraint):**

```text
pv  (instruments, Ext/Dom/Macro books)
 ↑
resfin  (params, defaults, overlays, engine)
 ↑
stress / load / tests / demos
```

Do **not** let `pv` import `resfin` at runtime (no cycles via `ExternalDebtBook.residual_defaults`).

## 3. Target layout

Prefer a **top-level** package (Excel analogy: ResFin is its own sheet family, not a sub-mode of Ext):

```text
src/lic_dsf/resfin/
  __init__.py          # public surface
  params.py            # ResidualFinancingParams, Overrides, resolve_*
  defaults.py          # calculate_residual_defaults(book)  [imports pv]
  overlay.py           # today’s stress/residual_pv.py
  policy.py            # Absolute / Capped (from stress/resfin/policy.py)
  engine.py            # ResidualFinancingEngine + Result
  types.py             # ResFinOverlay, ResidualFill, Dom*, PublicResFinOverlay
```

Then:

- `lic_dsf.stress.resfin` becomes a **thin re-export / compatibility shim** (or is deleted once call sites move).
- `lic_dsf.stress.residual_pv` deleted after move.
- `lic_dsf.books.external.residual` deleted after move (compat re-exports optional; see §5).

### Why not only nest under `stress.resfin`?

`load.input7` already needs `ResidualFinancingParams`. `load → stress` is the wrong story (“parsing Input 7 requires the stress package”). A sibling `resfin` package keeps loaders and stress both as clients.

### What stays in `pv`

| Keep | Why |
|---|---|
| `PresentValueInstrument`, `PVPortfolio`, LC-NR | Loan primitives |
| `ExternalDebtBook`, `MacroDebtBook`, Dom books | Baseline books |
| `MacroDebtBook.residual_financing_gap()` | Macro-Debt_Data row identity, not ResFin fill |

### What leaves `pv`

| Move | To |
|---|---|
| `ResidualFinancingParams`, `ResidualFinancingOverrides` | `resfin.params` |
| `calculate_residual_defaults`, `resolve_residual_params` | `resfin.defaults` / `resfin.params` |
| `external_dsa_residual_params`, `public_dsa_residual_params` | `resfin.params` (single copy) |
| `ExternalDebtBook.residual_defaults` / `resolve_residual` methods | **Delete**; call `resfin.calculate_residual_defaults(book)` |
| `stress.residual_pv` | `resfin.overlay` |
| `stress.resfin.engine` / `policy` / overlay types | `resfin.*` |

## 4. Phases

### Phase A — Inventory and freeze behavior

1. List every import of:
   - `lic_dsf.books.external.residual`
   - `ResidualFinancingParams` / `Overrides` from `lic_dsf.pv`
   - `stress.residual_pv` / `stress.resfin`
2. Note duplicate `public_dsa_residual_params` and pick one implementation.
3. Confirm parity cases that touch ResFin (`overlay-resfin-*` in [`data/parity/OUTPUT_3_INPUT_CATALOG.md`](../data/parity/OUTPUT_3_INPUT_CATALOG.md)) — these are the exit tests; math must not drift.

**Exit:** Written import map + “no math change” commitment.

### Phase B — Create `lic_dsf.resfin` by move (not rewrite)

1. Add `src/lic_dsf/resfin/` with modules above.
2. Move code with git-aware renames where practical; keep function bodies identical.
3. Wire `lic_dsf.resfin.__init__` public API:

```python
# conceptual
from lic_dsf.resfin import (
    ResidualFinancingParams,
    ResidualFinancingOverrides,
    calculate_residual_defaults,
    resolve_residual_params,
    external_dsa_residual_params,
    public_dsa_residual_params,
    ResidualFinancingEngine,
    ResidualFinancingResult,
    resfin_instrument,
    build_public_resfin_overlay,
    # ...
)
```

4. Point `stress.resfin` and (temporarily) `pv.external_debt.residual` at the new modules via re-exports.

**Exit:** `uv run pytest tests/test_residual_financing.py tests/test_stress_dsa.py` green; no intentional formula edits.

### Phase C — Retarget callers

Update imports in order (low risk → high visibility):

1. `lic_dsf.load.input7`
2. `lic_dsf.stress.*` (facade, runners, market_terms, external_dynamics, context, …)
3. `tests/test_residual_financing.py`, stress tests, parity presets if any
4. Demos / docs that import ResFin types from `pv`

Replace:

```python
book.residual_defaults()
book.resolve_residual(overrides)
```

with:

```python
from lic_dsf.resfin import calculate_residual_defaults, resolve_residual_params

calculate_residual_defaults(book)
resolve_residual_params(calculate_residual_defaults(book), overrides)
```

**Exit:** No production code imports ResFin symbols from `lic_dsf.pv` except optional shims.

### Phase D — Strip PV surface + docs

1. Remove ResFin exports from `lic_dsf.pv.__init__` and `lic_dsf.books.external.__init__`.
2. Delete `pv/external_debt/residual.py` once shims are gone.
3. Delete or shrink `stress/residual_pv.py`; keep `stress.resfin` as thin re-export **or** remove and import `lic_dsf.resfin` everywhere.
4. Fix docs:

| Doc | Change |
|---|---|
| [`docs/01-excel-map.qmd`](../docs/01-excel-map.qmd) | Input 7 → `lic_dsf.resfin`; package table: `pv` does **not** own ResFin |
| [`docs/08-stress-dsa.qmd`](../docs/08-stress-dsa.qmd) | Stress *uses* `resfin`; ResFin API lives in `lic_dsf.resfin` |
| README package table | Add `lic_dsf.resfin` row |

**Exit:** Grep shows no `pv.external_debt.residual`; docs match layout.

### Phase E — Compat window (optional)

If external consumers might import from `pv`:

- Keep deprecated re-exports on `lic_dsf.pv` for one release with `DeprecationWarning`.
- Remove in the following release.

Internal-only alpha: skip and delete in Phase D.

## 5. Compatibility matrix

| Old import | New import |
|---|---|
| `from lic_dsf.pv import ResidualFinancingParams` | `from lic_dsf.resfin import ResidualFinancingParams` |
| `from lic_dsf.books.external.residual import …` | `from lic_dsf.resfin import …` |
| `from lic_dsf.stress.residual_pv import resfin_instrument` | `from lic_dsf.resfin import resfin_instrument` |
| `from lic_dsf.stress.resfin import ResidualFinancingEngine` | `from lic_dsf.resfin import ResidualFinancingEngine` (stress shim OK) |
| `book.residual_defaults()` | `calculate_residual_defaults(book)` |

## 6. Test plan

Run after each phase (minimum):

```bash
uv run pytest tests/test_residual_financing.py tests/test_stress_dsa.py
uv run pytest tests/test_parity_cases.py -k resfin
uv run pytest tests/test_stress_output_tables.py  # if present / Output 3 ResFin-sensitive
```

Broader gate before declaring done:

```bash
uv run pytest
```

Parity overlays that must still pass (catalog R1–R7): share / ST share / interest / maturity / discount / grace / domestic MLT rate.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Accidental math drift while moving | Move-only commits; no formula edits in the same PR |
| `pv` ↔ `resfin` import cycle via book methods | Delete book methods; free functions take `ExternalDebtBook` |
| `load → stress` if nested only under stress | Prefer top-level `lic_dsf.resfin` |
| Stale docs / demos | Phase D checklist; grep for `ResidualFinancing` under `docs/` and `demo/` |
| Duplicate `public_dsa_residual_params` | Delete one copy in Phase B |

## 8. Suggested PR split

1. **PR1 — Add `lic_dsf.resfin`, re-export from old homes** (Phase B; behavior-identical).
2. **PR2 — Retarget internal callers** (Phase C).
3. **PR3 — Remove PV / stress duplicates + docs** (Phase D; optional deprecations).

Do not mix formula/parity fixes into these PRs.

## 9. Done when

- [x] `ResidualFinancingParams` and ResFin engine live under `lic_dsf.resfin`
- [x] `lic_dsf.pv` no longer exports ResFin types (except optional deprecated shim)
- [x] ResFin still builds overlays via `PresentValueInstrument`
- [x] `MacroDebtBook.residual_financing_gap` unchanged in `pv`
- [x] Docs / README package table updated
- [x] ResFin-related unit + parity tests green
