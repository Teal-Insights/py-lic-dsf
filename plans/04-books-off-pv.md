# Plan: Carve Ext / Dom / Macro books out of `pv`

**Goal:** Leave `lic_dsf.pv` as the present-value *instrument* layer; give Ext / Dom / Macro books a home whose name matches the Excel sheet family.

**Non-goals:** Changing Macro/Ext/Dom math. Moving ResFin (see [`03-resfin-off-pv.md`](03-resfin-off-pv.md)). Moving baseline ratios (`dsa`) or Output panels (`output`).

**Status:** Implemented (Phases A–D).

**Depends on:** Prefer completing Plan 03 (ResFin off `pv`) first so ResidualFinancing* is not dragged into the books package by mistake. Can start inventory in parallel.

**Related:** [`docs/01-excel-map.qmd`](../docs/01-excel-map.qmd), [`docs/04-ext-debt-module-design.qmd`](../docs/04-ext-debt-module-design.qmd), [`docs/05-dom-debt-indicators.qmd`](../docs/05-dom-debt-indicators.qmd), [`docs/06-macro-debt-bridge.qmd`](../docs/06-macro-debt-bridge.qmd).

---

## 1. Problem

`lic_dsf.pv` currently means three different things:

| Subtree today | Excel analogue | Is it PV math? |
|---|---|---|
| `instrument`, `portfolio`, `lc_nr`, `mathutil` | `PV_Base` / `PV_LC_NR*` | Yes |
| `external_debt` | `Ext_Debt_Data` | Mostly stocks / service / grant element |
| `domestic_debt` | `Dom_Debt_*` | Indicators / peer medians |
| `macro_debt` | `Macro-Debt_Data` | Macro identities + debt stitch |

Callers think “import from `pv`” whenever they need a Macro book. That hides the real dependency (books → instruments) and makes Plan 03-style splits harder to see.

## 2. Design rule

```text
Loan template / unit PV / portfolio aggregation  → lic_dsf.pv (or rename to instruments)
Sheet engines Ext / Dom / Macro                → lic_dsf.books
```

**Dependency direction:**

```text
pv (PresentValueInstrument, PVPortfolio, LC-NR, excel_npv)
 ↑
books (ExternalDebtBook, DomesticDebtBook, MacroDebtBook + inputs/types)
 ↑
dsa / realism / stress / resfin / load / rating / output
```

## 3. Target layout

```text
src/lic_dsf/books/
  __init__.py
  external/          # move from pv/external_debt/ (minus residual → resfin)
  domestic/          # move from pv/domestic_debt/
  macro/             # move from pv/macro_debt/
```

Keep under `pv`:

```text
src/lic_dsf/pv/
  instrument.py
  portfolio.py
  lc_nr.py
  mathutil.py
  __init__.py        # instruments only
```

**Naming:** Prefer `lic_dsf.books` over renaming the whole library. Optional later alias `lic_dsf.instruments` for `pv` if the name still confuses; not required in this plan.

## 4. Phases

### Phase A — Inventory

1. List public exports from `lic_dsf.pv` that are books vs instruments.
2. Confirm ResFin symbols are already gone from `pv` (Plan 03) or excluded from the move set.
3. Grep call sites: `ExternalDebtBook`, `MacroDebtBook`, `DomesticDebtBook`, `MacroDebtInputs`, …

**Exit:** Move checklist of modules + import rewrite map.

### Phase B — Add `lic_dsf.books` by move

1. `git mv` `external_debt` / `domestic_debt` / `macro_debt` trees under `books/` (adjust package names).
2. Fix internal imports (`pv.macro_debt` → `books.macro`, etc.).
3. Re-export from `lic_dsf.books`.
4. Temporary re-exports on `lic_dsf.pv` for books (compat).

**Exit:** Full test suite green; no formula edits.

### Phase C — Retarget callers

Update in waves:

1. `lic_dsf.load`, `dsa`, `stress`, `resfin`, `realism`, `rating`, `output`, `scenario`
2. Tests and demos
3. Docs (`01-excel-map`, getting-started, Ext/Dom/Macro guides, README package table)

### Phase D — Strip `pv` surface

1. Remove book exports from `lic_dsf.pv.__init__` (optional deprecated shim one release).
2. Update package-role table: `pv` = instruments only; `books` = Ext/Dom/Macro.

## 5. Compatibility

| Old | New |
|---|---|
| `from lic_dsf.pv import MacroDebtBook` | `from lic_dsf.books import MacroDebtBook` |
| `from lic_dsf.books.external…` | `from lic_dsf.books.external…` |
| `from lic_dsf.pv import PresentValueInstrument` | unchanged |

## 6. Test plan

```bash
uv run pytest tests/test_pv.py tests/test_ext_panels.py tests/test_macro_debt.py
uv run pytest tests/test_dom_debt.py  # if present
uv run pytest
```

## 7. Risks

| Risk | Mitigation |
|---|---|
| Mixing ResFin move with books move | Finish Plan 03 first, or exclude residual modules explicitly |
| Mass import churn | Compat re-exports on `pv` for one PR cycle |
| Docs / demos lag | Phase C checklist + grep `lic_dsf.pv` for book names |

## 8. PR split

1. **PR1** — Create `books`, re-export from `pv`
2. **PR2** — Retarget internal callers + docs
3. **PR3** — Drop book exports from `pv`

## 9. Done when

- [x] Ext/Dom/Macro live under `lic_dsf.books`
- [x] `lic_dsf.pv` exports only instrument/portfolio/LC-NR/math helpers (plus optional shim)
- [x] Docs package table updated
- [x] Full pytest green; no intentional math drift
