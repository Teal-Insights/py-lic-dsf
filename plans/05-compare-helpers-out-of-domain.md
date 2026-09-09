# Plan: Move Excel↔Python `compare_*` helpers out of domain packages

**Goal:** Keep production packages free of ad-hoc Excel CSV comparison tooling; own that tooling next to tests / parity.

**Non-goals:** Replacing the JSON parity corpus ([`01-excel-parity-differential-testing.md`](01-excel-parity-differential-testing.md)). Changing SUT math. Deleting useful compare scripts before parity covers the same surfaces.

**Status:** Implemented.

**Depends on:** None (orthogonal to Plans 03–04). Safer after parity cases exist for the same Output sheets.

**Related:** [`tests/parity/`](../tests/parity/), `lic_dsf.*.compare*`.

---

## 1. Problem

Domain packages currently ship Excel-oracle helpers:

| Module | Surface |
|---|---|
| `lic_dsf.dsa.compare` | Output 1-1 / 1-2 CSV |
| `lic_dsf.realism.compare` (+ `compare_realism2/3/4`) | Output 4 / Realism |
| `lic_dsf.stress.compare` | Output 2 / 3 |
| `lic_dsf.rating.compare` | Output 5 / 6 / 7 |

Smells:

- Cross-package use of **private** helpers (`realism.compare._a1`, `_books`).
- Inflated import graph (`dsa → realism`, `rating → stress/load/output/…`) for **dev tooling**, not product math.
- Two oracle stories: legacy CSV compare vs JSON parity probes — easy to maintain the wrong one.

`dsa.compare` already notes: prefer `tests.parity.compare_probes`.

## 2. Design rule

```text
Domain package  → compute ratios / ratings / panels
tests.parity / tools  → Excel mint, probe compare, legacy CSV dumps
```

**Dependency direction:**

```text
lic_dsf.*  (no imports of compare helpers)
    ↑
tests.parity / optional lic_dsf._devtools.compare
```

Production code must not import compare modules.

## 3. Target layout

**Preferred:**

```text
tests/parity/excel_compare/   # or tests/compare/
  __init__.py
  cells.py          # _a1, _as_year, _year_int, workbook open helpers
  books.py          # _books fixture builder
  baseline.py       # was dsa.compare
  realism1.py … realism4.py
  stress.py
  rating.py
  csv.py            # write_comparison_csv
```

**Alternative:** `src/lic_dsf/_compare/` marked private, not exported from `lic_dsf.__init__`. Prefer tests tree if nothing in `src/` needs it at runtime.

Keep using JSON parity (`tests.parity.mint`, `compare_probes`) as the CI path; treat moved CSV helpers as **manual / legacy** until retired.

## 4. Phases

### Phase A — Inventory & classify

1. List every `compare*.py` and every importer (tests, `output.rating`, demos, parity catalogs).
2. Flag any **runtime** import from production (e.g. `output/rating.py` → `rating.compare`): those must be untangled first (inline needed SUT keys into `output`, or call rating math directly).
3. Map each compare surface → existing JSON parity catalog (or gap).

**Exit:** Table of modules → tests-only vs still production-coupled; parity coverage gaps listed.

### Phase B — Untangle production imports

1. Stop `lic_dsf.output` / other `src/` modules from importing `*.compare`.
2. Move any needed “cell key” constants into `output` or `rating` proper.

**Exit:** `rg 'lic_dsf\.(dsa|realism|stress|rating)\.compare' src/` empty of production use (only the compare modules themselves, until deleted).

### Phase C — Move helpers under tests

1. Move shared cell/book helpers to one place.
2. Move baseline / realism / stress / rating compare builders.
3. Update `tests/test_compare_*.py` imports.
4. Update any demo notebooks that call `write_*_comparison_csv`.

**Exit:** Domain packages no longer contain `compare*.py`.

### Phase D — Document & optionally retire

1. Docs: “Excel CSV compare lives under `tests/…`; CI uses JSON parity.”
2. For surfaces with full parity coverage, mark CSV compare deprecated; delete in a later cleanup PR.

## 5. Compatibility

| Old | New |
|---|---|
| `from lic_dsf.realism.compare import build_realism1_comparison` | `from tests.parity.excel_compare.realism1 import …` (tests only) |
| `from lic_dsf.dsa.compare import write_comparison_csv` | shared tests helper |

No public library API promise for compare helpers (alpha).

## 6. Test plan

```bash
uv run pytest tests/test_compare_realism1.py tests/test_compare_realism2.py \
  tests/test_compare_realism3.py tests/test_compare_realism4.py \
  tests/test_compare_outputs_5_7.py
uv run pytest tests/test_parity_cases.py
uv run pytest
```

## 7. Risks

| Risk | Mitigation |
|---|---|
| Breaking demos that import compare from `lic_dsf` | Grep demos; update or drop cells |
| Losing a surface not yet in parity | Phase A gap list; keep CSV helper until parity exists |
| Circular imports while moving | Move shared `_a1` first; then leaf builders |

## 8. PR split

1. **PR1** — Untangle production → compare imports
2. **PR2** — Move modules under `tests/…`; fix test imports
3. **PR3** — Doc note + deprecate/delete redundant CSV paths

## 9. Done when

- [x] No `compare*.py` under `src/lic_dsf/{dsa,realism,stress,rating}/`
- [x] No production `src/` import of compare helpers
- [x] Test compare suite + parity suite green
- [x] Docs state the dual-oracle story (parity primary)

**Landing notes:** Excel CSV builders live under `tests/parity/excel_compare/`. Rating panel SUT stores stay in `lic_dsf.rating.sut_outputs` (used by `lic_dsf.output.rating`).
