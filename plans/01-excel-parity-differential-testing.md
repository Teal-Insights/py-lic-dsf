# Plan: Excel parity differential testing (JSON cases)

**Goal:** Strengthen the claim that `lic_dsf` is nearly identical mathematically to the official LIC-DSF spreadsheet.

**Non-goals:** Parameter sensitivity / ranking (see [`02-output-parameter-sensitivity.md`](02-output-parameter-sensitivity.md)). Python-only snapshot tests that are not Excel-minted.

**Status:** Implemented through Phase C + grapher mint path. Corpus under `data/parity/cases/`; mint via `python -m tests.parity.mint --source cached|grapher|live`.

---

## 1. Problem

Today parity rests on:

- Live Excel on Windows (`LIC_DSF_EXCEL=1` + `xlwings`) reading probe cells.
- Probe catalogs under `tests/parity/catalogs/` and equality in `tests/parity/equality.py`.
- Excel-geometry SUT tables in `lic_dsf.output` / stress builders in `tests/parity/stress_sut.py`.

Gaps for a stronger identity claim:

- Default CI is Excel-free; live parity is hard to run and hard to grow as a corpus.
- Cases are mostly the bundled template defaults, not a library of deliberate input overlays.
- Expected values are not always checked in as reviewable artifacts tied to a named case.

## 2. Approach

Treat **Excel as the only oracle**. Use JSON as a portable case format:

```text
input case JSON  →  Excel adapter (mint)  →  output golden JSON
input case JSON  →  Python adapter (SUT)  →  compare vs golden (reuse close / probes)
```

- Goldens are produced only by the Excel path (or a documented refresh job that drives Excel).
- CI compares Python to committed goldens; it does not invent goldens from Python.
- Comparison reuses `tests.parity.equality.close` and probe/`sut_key` conventions — never raw float `==`.

## 3. Case schema (draft)

Each case is a directory or paired files, e.g. `data/parity/cases/<case_id>/`:

| File | Role |
|---|---|
| `case.json` | Metadata + logical inputs |
| `expected.json` | Excel-minted probe values (golden) |
| optional `workbook.xlsx` | Case-local copy or pointer to template + patch list |

### `case.json` (conceptual)

```json
{
  "id": "template-baseline-output11",
  "workbook": "data/lic-dsf-template-2025-08-12.xlsx",
  "description": "Default template, Output 1-1 sustainability rows",
  "inputs": {
    "overlays": []
  },
  "probes": {
    "catalog": "output_11",
    "years": [2024, 2025, 2026]
  },
  "oracle": {
    "minted_at": null,
    "template_sha": null,
    "excel_build": null
  }
}
```

**Input rule:** Prefer Excel-native overlays (sheet + A1/cell + value). Python applies the same logical change via workbook rewrite or an equivalent typed mapping — not a Python-only object dump that Excel cannot faithfully receive.

### `expected.json` (conceptual)

One record per probe (aligned with `compare_probes` columns):

```json
{
  "probes": [
    {
      "sheet": "Output 1-1 - External DSA",
      "cell": "N30",
      "row": 30,
      "year": 2024,
      "label": "PV of PPG external debt / GDP",
      "sut_key": 30,
      "excel_value": 12.345678
    }
  ]
}
```

Sparse probes first; full Excel-geometry table dumps only where catalogs already demand dense coverage.

## 4. Adapters

### Excel mint (Windows + `excel` extra)

1. Open base workbook (copy under temp).
2. Apply `inputs.overlays` cell writes.
3. Force calculate; read probe cells (extend `tests.parity.excel.read_live_output`).
4. Write `expected.json` + stamp `oracle` metadata (template hash, timestamp).
5. Never call Python SUT builders in this path.

### Python SUT

1. Materialize the same workbook state (apply overlays, then `load_*`, or load a case-local xlsx).
2. Build the relevant books / stress suite / output table.
3. Project to the same probe keys as `expected.json`.
4. `compare_probes` + `assert_all_passed` (or JSON-native wrapper that shares `close`).

## 5. Phased delivery

### Phase A — Harness skeleton

- Define `case.json` / `expected.json` schema (validate with a small pydantic/dataclass or jsonschema).
- Case loader + Python runner that consumes one catalog and the bundled template (no overlays yet).
- Pytest plugin or parametrize over `data/parity/cases/*/case.json`.
- Document mint command: e.g. `uv run python -m tests.parity.mint --case <id>` (Windows-only).

**Exit:** One baseline Output 1-1 case runs on CI against a committed golden; mint path documented.

### Phase B — Corpus from existing catalogs

Migrate / wrap existing catalogs without rewriting math:

| Wave | Catalogs / surfaces |
|---|---|
| B1 | `output_11`, `output_12` |
| B2 | `output_31`, `output_32`, B-sheet external/public |
| B3 | `resfin`, stress SUT layers |
| B4 | Realism / Output 4-x, rating Output 5/7 |

Each wave: mint goldens on Excel, commit, gate in CI.

**Exit:** Template-default coverage matches or exceeds current live-Excel probe breadth, CI-enforced.

### Phase C — Input overlays

- Add cell-overlay vocabulary (and optional named presets: “higher FX shock”, “market access on”).
- Mint goldens for a small set of non-default scenarios (still Excel-authored).
- Fail loud when overlay mapping is missing on the Python side (adapter gap ≠ math gap).

**Exit:** ≥ N non-default cases (choose N when implementing; start with 5–10) covering stress + one tailored path.

### Phase D — Reporting for the identity claim

- Aggregate pass rate by sheet / section / year.
- Optional CSV/HTML diff (extend `write_parity_csv`).
- Short doc section (or README note) describing corpus size, mint policy, and tolerances (`ABS_TOL` / `REL_TOL`).

**Exit:** A reproducible statement: “On M probes across K cases, Python matches Excel under the published equality rule.”

## 6. Equality and failure policy

- Reuse `ABS_TOL = 1e-6`, `REL_TOL = 1e-12`, blank / `n.a.` / `#ERROR!` handling from `tests.parity.equality`.
- Missing `sut_key` ⇒ fail (same as `assert_all_passed`).
- Golden refresh: only via Excel mint; PR review must show mint provenance in `oracle` metadata.
- Template bump: remint all cases that pin that workbook hash.

## 7. Layout (proposed)

```text
data/parity/cases/
  <case_id>/
    case.json
    expected.json
tests/parity/
  case_schema.py      # load / validate
  mint.py             # Excel → expected.json
  run_case.py         # Python → compare
  ...existing...
tests/test_parity_cases.py
```

Keep mint/run helpers in `tests/parity/` (not installed), consistent with current design.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Overlay applied differently in Excel vs Python | Excel-native cells as source of truth; shared patch applicator writing xlsx both sides |
| Goldens regenerated from Python by mistake | Mint CLI refuses SUT path; CI check that `oracle.minted_at` present |
| Corpus rot on template upgrade | Pin `template_sha`; remint checklist in Phase D docs |
| Scope explosion (whole workbook dumps) | Probe catalogs only; inventory tool already classifies numeric vs exclude |

## 9. Success metrics

- CI runs the full committed case corpus on Linux without Excel.
- Live Excel path exists solely to mint/refresh goldens and spot-check.
- Documented probe count and pass rate for the identity claim.
- New Output surfaces add a catalog + cases, not one-off notebooks.

## 10. Dependencies / prerequisites

- Existing `tests/parity/*` and `lic_dsf.output` Excel-geometry tables.
- Windows machine + Excel for minting (`uv sync --extra excel`).
- Bundled template provenance (`data/PROVENANCE.md`, `NOTICE.md`).

## 11. Out of scope for this plan

- Sobol / tornado / OAT sweeps (Plan 02).
- Public API that accepts arbitrary JSON as a product feature (harness-only unless later promoted).
- Claiming bit-identity with Excel beyond the published `close` rule.
