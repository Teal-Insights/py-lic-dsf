# Plan: Shared public automatic debt-dynamics helper

**Goal:** Stop `lic_dsf.dsa` from importing `lic_dsf.realism` for shared debt-dynamics math used by both Baseline Output 1-2 and Realism 1.

**Non-goals:** Changing the dynamics formulas. Merging all of Realism 1 into DSA. Moving forecast-error / vintage rebase logic out of realism.

**Status:** Planning.

**Depends on:** None. Small; can ship before or after Plans 03–04. If Plan 04 lands first, place the helper under `books` or `dsa` accordingly (see §3).

**Related:** [`src/lic_dsf/realism/forecast_error.py`](../src/lic_dsf/realism/forecast_error.py) (`public_automatic_debt_dynamics`); [`src/lic_dsf/dsa/baseline/public.py`](../src/lic_dsf/dsa/baseline/public.py).

---

## 1. Problem

`BaselinePublicBook` (Output 1-2 automatic debt dynamics rows) does:

```python
from lic_dsf.realism.forecast_error import public_automatic_debt_dynamics
```

That creates **`dsa → realism`** for a function that is not “realism-specific”: it is the shared public debt-creating-flow / automatic-dynamics decomposition Excel uses in both Baseline and Realism 1.

Realism still owns vintage rebase, forecast-error panels, and imported-data catalogs — those stay.

## 2. Design rule

```text
Shared identity math used by baseline + realism  → neutral home
Realism-only forecast / vintage tools            → lic_dsf.realism
Baseline ratio books                             → lic_dsf.dsa
```

**Dependency direction after:**

```text
(shared helper module)
    ↑
dsa.baseline.public
realism.forecast_error / compare (until Plan 05)
```

No `dsa → realism` import for this symbol.

## 3. Target location (pick one)

| Option | Path | When to prefer |
|---|---|---|
| **A (recommended now)** | `lic_dsf.dsa.dynamics` or `lic_dsf.dsa.public_dynamics` | Smallest move; realism imports from dsa |
| **B** | `lic_dsf.books.macro.dynamics` | After Plan 04 if the inputs are purely Macro series |
| **C** | `lic_dsf.common.debt_dynamics` | Only if more shared kernels appear |

Start with **A** unless Plan 04 already created `books` and the function’s inputs are clearly Macro-book-native.

Keep the function name `public_automatic_debt_dynamics` to avoid churn.

## 4. Phases

### Phase A — Characterize the function

1. Read `public_automatic_debt_dynamics` signature and call sites (baseline public, realism compare, realism `__init__` export).
2. Confirm it has **no** dependency on Realism types (`ImportedDataCatalog`, vintage modes, multiplier grids).
3. List any sibling helpers in `forecast_error.py` that are truly shared vs realism-only (`gdp_rebase_scale` stays in realism).

**Exit:** Move-vs-stay list for symbols in `forecast_error.py`.

### Phase B — Move + re-export

1. Move `public_automatic_debt_dynamics` (and any tiny private helpers it needs) to the chosen module.
2. `realism.forecast_error` re-exports it for one release (or immediately updates internal callers).
3. `BaselinePublicBook` imports from the new home (no realism import).
4. Keep `lic_dsf.realism` public export if demos import it from realism — re-export from realism `__init__` → new home.

**Exit:** `rg 'from lic_dsf.realism' src/lic_dsf/dsa` empty (for this concern); tests green.

### Phase C — Docs / exports cleanup

1. Note in Realism / Baseline docs that automatic dynamics is shared DSA (or books) math.
2. Drop duplicate definitions; single source of truth.

## 5. Compatibility

| Old | New |
|---|---|
| `from lic_dsf.realism import public_automatic_debt_dynamics` | Still works via re-export **or** `from lic_dsf.dsa import …` |
| Baseline internal import | New home only |

## 6. Test plan

```bash
uv run pytest tests/test_output_tables.py tests/test_compare_realism1.py
uv run pytest -k 'baseline or realism1 or automatic or debt_dynamic'
uv run pytest
```

Parity: Output 1-2 and Realism 1 / Output 4-1 cases that touch automatic dynamics rows.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Moving too much of `forecast_error.py` | Only move the shared function + its private callees |
| Creating `realism → dsa` if that feels wrong | Acceptable: realism already conceptually sits on baseline series; or use Option B under books |
| Name confusion with Realism 1 panel | Docs one-liner: shared kernel, two presentations |

## 8. PR split

1. **Single PR** is enough: move + retarget + re-export + tests.

## 9. Done when

- [ ] `public_automatic_debt_dynamics` has one definition outside `realism`-only ownership
- [ ] `dsa.baseline.public` does not import `lic_dsf.realism`
- [ ] Realism 1 and Output 1-2 tests / parity still match
