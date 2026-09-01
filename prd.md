# In-Memory Workbook Data Model

**Status:** Design spec (not yet implemented)

**Goal:** Represent an Excel workbook as a typed object graph in memory, with cell-level provenance, so interned formula shapes can be emitted as reusable Python helpers and checked against Excel as a golden master.

This document is the data-model contract. An implementation may choose supporting libraries (pydantic for validation is recommended) as long as the types, invariants, and APIs below are preserved.

**Target.** This is the object model an [excel-grapher](https://github.com/Teal-Insights/excel-grapher) codegen rewrite should emit. Today’s exporter generates a Records API of free functions (`set_*`, `compute_*`, `xl_cell`). That is not the public surface here. The rewrite still interns parameterizable formula ASTs and emits reusable helpers; what changes is the *caller*: generated `ExcelTable` subclasses with `@excel_property` methods that dispatch to those helpers. Do not treat “one unique property body per A1 cell” as the codegen unit, and do not emit `compute_*` as the typed API.

---

## 1. Purpose

The IMF LIC-DSF workbook is a large spreadsheet: sheets hold tables, some cells are user inputs, and most others are formulas that read other cells. The Python model must reproduce that data flow, not a simplified substitute.

Constraints:

1. **Traceability.** Every modeled value maps to a sheet, column, and row (or to an absolute cell on a sparse sheet).

2. **Fidelity.** Hardcoded Excel values are stored on records. Formula cells are `@excel_property` methods that *dispatch* to interned helpers. Helpers *are* the emitted interned shape; they are not a unique handwritten AST per address.

3. **Addressability.** Callers can resolve Excel-style addresses and ranges (`'Input 1 - Basics'!C19`, `PV_Base!D9:BD9`) to records and attributes. Resolution is a router onto the same helper as the typed property, not a second formula implementation.

4. **Ephemerality.** The object graph lives for the lifetime of a `Workbook` instance. There is no durable store. Persistence, if ever needed, is a serializer on top of this model, not part of it.

5. **Fail closed.** Missing workbook context, missing records, unknown addresses, overlapping table claims, circular formula evaluation, and formula cells with neither a helper nor an explicit `xl_cell` fallback are errors. They are not silent `None`.

Non-goals:

- A general spreadsheet *product* (no calc-chain interpreter, no re-parsing A1 text at evaluation time when a shape or helper covers the cell). Generated helpers may call excel-grapher `xl_*` primitives (`xl_sum`, `xl_if`, …). That is compiled formula semantics, not an engine that interprets the workbook.

- Reading the `.xlsm` file from inside formula properties or helpers.

- A durable store or query language. The graph exists only for the lifetime of a `Workbook`.

- One unique Python method body per formula cell. Reuse is interned at the shape, then (when bindings lift keys) at the helper.

- Today’s excel-grapher Records export (`compute_*`, `set_*`, package-level `list_computes`). The public API is `Workbook` + table records + properties.

---

## 2. Conceptual model

Six nested concepts:

| Concept | Excel analogue | Python analogue |
|---|---|---|
| **Workbook** | The `.xlsm` file | In-memory identity map and evaluation context |
| **Table** | A rectangular (or sparse) region on a sheet | A class: `ExcelTable` subclass |
| **Record** | One row, one column, or one singleton | An instance of that class, keyed by `record_index` |
| **Cell** | One address | A hardcoded attribute or a formula property on that instance |
| **Formula shape** | Autofill / copy-paste of the same AST with moving refs | Interned skeleton: address leaves punched into typed holes; instances share a `shape_key` |
| **Helper** | Shared formula (Excel) or one named internals function | One Python function for that shape, optionally parameterized by binding keys |

A sheet may contain several tables. A table never spans sheets. Records of a table do not overlap: each `(table class, record_index)` pair is unique inside a workbook.

**Geometry vs formula reuse are different layers.**

- Tables, records, `data_range`, and `value_map` are *provenance*: which keys map to which cells, so `resolve` and golden-master address checks work.
- Formula evaluation is *interned*: many cells share one shape. Codegen emits one helper; each `@excel_property` call site passes parameters. Binding `key:` lists (and cluster-refactor sweep keys) are those parameters. `record_index` is how a geometric record maps onto keys, not the helper’s public signature.

Table classes are generated from a dependence graph of the workbook. That graph is a codegen input. It is not loaded into the running `Workbook` (section 12). Formula *bodies* are not “each edge baked into a unique property.” They come from interned shapes (section 6.4). Thin `@excel_property` methods map the current record’s keys into a helper call.

Cross-sheet formulas do not open Excel. Mechanical shape helpers may still take resolved A1 holes (`xl_cell` / `xl_eval`). Key-lifted internals helpers query other helpers or modeled series by key, not by string-address lookups for cells that already have a table class.

```
Workbook
  └── table class  →  { record_index → instance }
                         instance.attr  ↔  hardcoded cell
                         instance.prop() → helper(keys)  ↔  formula cell

  └── interned helpers
        _shape_N(ctx, p0, …)          # mechanical: address holes
        named_hot(ctx, time_period=)  # key-lifted: binding dims
```

---

## 3. Provenance metadata

### 3.1 `ColumnMeta`

Used when the table is a regular grid `column_header` or `row_header`). The metadata names the **field dimension**; the record supplies the **record dimension**.

```python

@dataclass(frozen=True)

class ColumnMeta:

    letter: str          # Excel column letter, e.g. "B", "AA"

    number: int          # 1-based Excel row number

    display_name: str    # Human-readable label

    header_cell: str     # Header address, e.g. "B6"

    internal: bool = False

```

Interpretation of `letter` and `number` depends on table format (section 4).

`internal=True` marks a storage attribute that is not part of the public cell mapping (used for MIXED columns, section 6). Internal attributes are omitted from public dumps and from address lookup.

### 3.2 `CellMeta`

Used when the table is sparse `cell` format). Each attribute maps to an absolute address on the sheet.

```python

@dataclass(frozen=True)

class CellMeta:

    address: str         # e.g. "E16", stored uppercase

    display_name: str

    header_cell: str

    internal: bool = False

```

### 3.3 Attaching metadata

**Hardcoded cells** are declared as annotated attributes:

```python

from typing import Annotated

country: Annotated[

    str,

    ColumnMeta(letter="C", number=7, display_name="Country", header_cell="B7"),

] = ""

```

**Formula cells** are methods decorated so the same metadata can be recovered by introspection:

```python

@property

@excel_property(letter="C", number=8, display_name="Country code", header_cell="B8")

def country_code(self) -> str:

    return country_code_hot(self.workbook)

```

Sparse sheets use `@excel_cell_property(address="B3", display_name="Title", header_cell="B3")`.

The decorator must wrap the function so that evaluating the property cannot perform Excel I/O (open a workbook, read a path, call openpyxl). Formula code sees only Python objects. The body is a helper call (section 6.4), not the interned AST.

### 3.4 Enforcement at class definition

When an `ExcelTable` subclass is created, the implementation must:

- Require every public data attribute (except `record_index`) to be `Annotated[..., ColumnMeta]` or `Annotated[..., CellMeta]`, matching `__table_format__`.

- Reject duplicate field-dimension coordinates on the same class:

  - `column_header`: unique `letter` across attributes and properties

  - `row_header`: unique `number`

  - `cell`: unique `address`

- Reject `ColumnMeta` on a `cell` table and `CellMeta` on a grid table.

- Register the class in the sheet registry if `__sheet_name__` is set (section 8).

Failure is a `TypeError` or `ValueError` at import time, not at first use.

---

## 4. Table layouts

Every table class sets:

```python

class Input1Basics(ExcelTable):

    __sheet_name__ = "Input 1 - Basics"   # exact Excel tab name

    __table_format__ = "row_header"       # column_header | row_header | cell

    __record_range__ = (3, 3)             # inclusive (min, max) record_index

    # alternatively: __record_list__ = [3, 7, 12]

```

Exactly one of `__record_range__` or `__record_list__` is required for loading. `__sheet_name__` is required.

### 4.1 `column_header` (rows are records)

Classic list: headers across a row, one record per following row.

- Field dimension = column `ColumnMeta.letter`)

- Record dimension = row `record_index` is the Excel row number)

- Cell for attribute `metric` on the record at row 10: `{letter}{record_index}` → `B10`

### 4.2 `row_header` (columns are records)

Wide / time-series / form layout: labels down a column, one record per following column.

- Field dimension = row `ColumnMeta.number`)

- Record dimension = column `record_index` is the 1-based column number: A=1, B=2, …)

- Cell for attribute `imf_base` (row 9) on column D `record_index=4`): `{column_letter(record_index)}{number}` → `D9`

- Constructors may accept `record_index="D"` and must normalize to `4`

### 4.3 `cell` (sparse singleton)

Scattered cells that do not form a grid. The table has exactly one record, `record_index=1`. Each attribute’s address is `CellMeta.address` with no transform.

`__record_range__` is `(1, 1)`.

---

## 5. Record identity

`record_index: int` is the identity of a record. It is not an autoincrement surrogate. It **is** the Excel row number, column number, or `1` for a singleton.

Inside one `Workbook`, identity is `(type(record), record.record_index)`. Adding a second instance with the same pair is an error.

Record-identity helpers (not formula helpers — those are section 6.4):

- `record_index_as_letter` → column letter (meaningful for `row_header`)

- `get_cell_address(field_name) -> str` → e.g. `"C19"`

- `get_all_cell_addresses() -> dict[str, str]`

Logical ↔ physical conversion:

| Format | Field + record → address | Address → field + record |

|---|---|---|

| `column_header` | `letter + str(record_index)` | letter → field, row → `record_index` |

| `row_header` | `column_letter(record_index) + str(number)` | row → field, column number → `record_index` |

| `cell` | `CellMeta.address` | address → field, `record_index=1` |

---

## 6. Hardcoded attributes, formula properties, MIXED columns

### 6.1 Hardcoded

A cell whose Excel content is a literal (number, text, blank, boolean) is an attribute on the record. The loader writes the coerced value. Formula properties read these attributes; they never re-read the file.

Blank Excel cells become `None` for `Optional` types. They do not omit the record.

### 6.2 Formula

A cell whose Excel content starts with `=` is a `@property` with `@excel_property` / `@excel_cell_property`. The method is thin: it maps this record’s identity onto helper parameters and calls the interned helper (section 6.4). It does not duplicate the AST, and it is not a package-level `compute_*` function.

```python
@property
@excel_property(letter="D", number=9, display_name="IMF - Base", header_cell="C9")
def imf_base(self) -> float | None:
    return pv_base_imf_base(self.workbook, time_period=self.year)
```

Within a `Workbook` epoch, both the public property and the helper are memoized (section 12). The memo is observably equivalent to recomputing from current state. Any write to a mapped hardcoded attribute starts a new epoch and drops both memos.

### 6.3 MIXED columns

Some columns contain literals in some rows and formulas in others. Model them as:

1. An **internal** storage attribute `value_raw`) with `ColumnMeta(..., internal=True)` on the same coordinates as the public cell.

2. A public property on those coordinates.

Loader behavior for the internal attribute:

- Literal cell → store the coerced value

- Formula cell → leave the attribute unset `None`)

Property behavior:

- If `value_raw` is not `None`, return it (this row is a literal).

- Otherwise call the same interned helper the formula years use, parameterized by this record’s keys (not a second copy of the AST).

Do not expose `value_raw` in public dumps or address lookup. The public name is the property.

Schema 1.13.0 bindings are **series-level** (one direction per series), not MIXED-per-cell. A catalog that splits a MIXED Excel column into a `constant` / `input` year-1 series and an `internal` formula series still shares one public property in this model: literals from the leaf series, formulas from the helper. Do not merge those directions in the binding catalog; merge at the typed property.

### 6.4 Interned formula shapes and reusable helpers

excel-grapher does not emit one unique function body per formula cell. It interns *shapes* and codegen emits *helpers*. This model must consume that, not fight it.

#### 6.4.1 Interning

Each formula node’s source of truth is `formula_ast`. A **shape** is that AST with cell / range / whole-column / whole-row leaves punched into typed holes (`AddressHoleNode`). Formulas that differ only in those addresses share a `shape_key` and skeleton; each instance carries its own parameter tuple.

The `formula_shapes` overlay is optional for *correctness* (missing shapes fall back to the per-node AST) and required for *reuse*. Warm it for codegen and evaluation. Compression, formula rewrite, and graph load drop the overlay; callers rewarm.

#### 6.4.2 Two helper layers

| Layer | Emitted as | Parameters | When |
|---|---|---|---|
| **Mechanical shape helper** | `_shape_N(ctx, p0, p1, …)` in generated internals | Resolved A1 addresses for the holes | Overlay is warm and the shape is used at least twice |
| **Key-lifted internals helper** | Named function, e.g. `scenario_primary_expenditure_pct_gdp_hot(ctx, time_period=…)` | Binding dimension ids (sweep keys) | Cluster refactor succeeded for that cluster |

Cell / property wrappers stay thin. Arithmetic and `xl_*` calls live in the helper.

Mechanical helpers are the interned AST. Key-lifted helpers are the same interned AST after address holes have been rewritten as reads of modeled series by key. Prefer key-lifted helpers on the public typed surface. Mechanical `_shape_N` plus `xl_cell` is the fallback when a cluster cannot be lifted.

#### 6.4.3 Cluster refactor contracts

The cluster-refactor step (excel-grapher / extraction pipeline `src/refactor_contracts.py`) selects one of two contracts from each cluster’s shape:

| Contract | Applies when | Helper signature |
|---|---|---|
| **A — member sweep** | Every formula operand is derivable from the member cells’ own sweep keys, including constant lags/offsets like `t − 1` (default; always true under `variation_mode: dominant_key_only`) | Parameters are exactly the varying member sweep keys. Lags stay in the helper body. Do not invent counterpart parameters. |
| **B — dimension aware** | Some operands route through counterpart dimension ids that share a *concept* with a member key (e.g. `REF_AREA` vs `COUNTERPART_REF_AREA`) | Parameters and `member_keys` are keyed by effective dimension **id**, so two parameters may share one concept. Do not collapse distinct ids onto a single concept parameter. |

If an operand position cannot be routed this way (for example three independently varying `REF_AREA` roles with only two declared dimension ids), skip the cluster as `operand_level_variation_unsupported`. To make it refactorable, declare one counterpart dimension (distinct `id`, shared `concept`) per independently varying operand role on the internal series that binds the member cells.

`variation_mode` only controls whether such clusters are formed: `dominant_key_only` splits them during clustering; `independent` keeps them together for Contract B.

Helper parameter names follow effective dimension ids (`time_period`, `instrument`, `issuance_year`), not Excel row numbers.

#### 6.4.4 Binding attachment

Series bindings remain a *codegen input*: they triangulate formula cells as `{address, key, record}` so intern and cluster refactor can parameterize helpers. `internal: {}` series do that for non-public formula nodes.

They do **not** define the public Python API. Today’s exporter turns an `output` series into `compute_*` (optionally via `output.compute.helper`) and an `input` series into `set_*`. The OOP rewrite instead:

- Emits an `ExcelTable` subclass (or property on an existing one) for the bound region.
- Generates an `@excel_property` that calls the interned helper with the record’s keys.
- Uses `xl_cell` only inside helpers (or as a last-resort fallback) for leaves the helper does not cover.

`resolve("'Sheet'!E27")` and `record.interest` must be the same implementation: the property, which calls the helper. Do not generate a parallel `compute_*` beside the property.

`output.compute.helper` in schema 1.13.0 is how the *current* exporter wires a helper to a Records function. Treat it as provenance of helper name and `dims`, not as a requirement to emit `compute_*`.

#### 6.4.5 Fallback (fail closed)

Leaves (or operand positions) **without** helper coverage still use `xl_cell(ctx, address)` in generated code. That is an explicit, auditable fallback, not a silent skip.

- Partial helper coverage: helper for covered leaves, `xl_cell` for the rest.
- No interned shape and no helper: per-node AST codegen, still not a handwritten unique property.
- A property that claims to be modeled but has no helper, no `xl_cell` path, and no mapped upstream: `UnmodeledDependencyError` with the Excel address. Never `return None`.

Do not add an address fallback inside a property that already has a table class for that cell.

#### 6.4.6 Key lift vs copy explosion

Interning a shape is not the same as lifting keys.

- **Shape interned, keys not lifted.** Thirty-four pasted PV_Base unit-loan blocks share one skeleton. Mechanical codegen can still emit one `_shape_N`. Cluster refactor without `INSTRUMENT` in `key:` can still emit thirty-four named helpers that are copies of each other, each closed over a different row.
- **Keys lifted.** One helper, parameters `(instrument, time_period, …)`. Call sites are the pasted copies.

The same applies to Baseline DSA pasted onto `B1_GDP_ext`, `B3_Exports_ext`, …: they share shapes; `SCENARIO` in `key:` is what makes one helper. Geometry (`value_map`, `row_label`, `exclude_rows`) stays provenance.

Bindings that keep `key: [TIME_PERIOD]` while the workbook repeats the same shape across instruments or scenarios are helper-unaware catalogs. Reshape-to-keys is what makes interned helpers *one* function instead of N.

#### 6.4.7 What wrappers must not do

Formula properties:

- Must not copy-paste the helper body.
- Must not call `Workbook.resolve` / `lookup_named` to reach a cell that already has a table class or a helper.
- Must not open files or import openpyxl.
- Must not implement their own cache (`functools.cached_property`, instance dict, module globals). Helper memo lives on the workbook (section 12).
- Must not exist alongside a generated `compute_*` for the same cells.

---

## 7. `Workbook` — the in-memory store

`Workbook` is the sole evaluation context. It is constructed explicitly (tests and loaders create one; there is no process-global default).

### 7.1 Contents

- Identity map: `dict[type[ExcelTable], dict[int, ExcelTable]]`

- Evaluation stack for circular-reference detection (section 11)

- Epoch counter, formula-property memo, and helper memo (section 12)

- Optional named-range map: `dict[str, str]` from name → full address `'Input 1 - Basics'!$C$19`)

### 7.2 Record API

```python

class Workbook:

    def add(self, record: ExcelTable) -> None:

        """Attach record to this workbook. Sets record.workbook.

        Raises DuplicateRecordError if (type, record_index) is occupied."""

    def get(self, table: type[T], record_index: int) -> T:

        """Return the record. Raises RecordNotFound if absent.

        Accepts a column letter string for row_header tables."""

    def all(self, table: type[T]) -> list[T]:

        """All records of this table, sorted by record_index."""

    def range(self, table: type[T], start: int, end: int) -> list[T]:

        """Records with start <= record_index <= end, sorted.

        Missing indices inside the span are errors (fail closed):

        the caller asked for a contiguous Excel region that is not fully loaded."""

```

There is no “get or None” on the hot path. Formula code that needs a peer record which must exist (same table, declared `__record_range__`) calls `get` and lets absence raise.

If Excel itself treats a lookup as optional (the formula uses `IFERROR` / missing keys in a search range), the helper may catch `RecordNotFound` or use a dedicated `find` that returns `None` **only** when that matches Excel’s documented empty-on-miss behavior. Such uses must be called out on the helper. Default is `get`.

### 7.3 Attachment

`Workbook.add` sets `record.workbook` to this workbook (weak reference is allowed). Accessing `record.workbook` when unattached raises `DetachedRecordError`. Formula properties and helpers must not proceed without a workbook.

Records do not look up siblings by searching a global registry of instances. Wrappers call interned helpers; mechanical helpers that still need a peer record use `self.workbook.get(...)`.

Mapped hardcoded attributes (including MIXED internal `*_raw` fields) are written only through `ExcelTable.__setattr__` (or an equivalent interceptor). That path is what bumps the epoch. Bypassing it `object.__setattr__`, direct `__dict__` writes) is undefined and forbidden in model and test code.

### 7.4 Address API

```python

def resolve(self, full_address: str) -> Any:

    """Evaluate "'Sheet'!C19" or "Sheet!C19" to the Python value.

    Raises UnmappedAddressError if no table claims the cell.

    Raises RecordNotFound if the table is registered but the record is not loaded."""

def resolve_range(self, full_range: str) -> list[Any]:

    """Evaluate a contiguous range to a list of values, record-major order."""

def lookup_named(self, name: str) -> Any:

    """Resolve a workbook named range through resolve()."""

```

Address resolution algorithm:

1. Parse sheet name and cell (or range).

2. List table classes registered to that sheet.

3. Find the unique class for which `cls.contains_address(cell)` is true.

4. If zero matches → `UnmappedAddressError`.

5. If two or more matches → `OverlappingTableError` (also checked at registration; still fail if it happens).

6. Convert the cell to `(record_index, field_name)` and `get` that record; return `getattr(record, field_name)`.

That `getattr` is the public property, which dispatches to the interned helper. `resolve` is not a parallel A1 evaluator.

`contains_address` is true when the field dimension matches a public (non-internal) attribute or property **and** the record dimension lies in `__record_range__` / `__record_list__`.

Formula implementations **must not** call `resolve` / `lookup_named` to reach values that already have a table class. They query that class or call the interned helper by key. Address APIs exist for tests, named ranges at the workbook boundary, and tooling.

### 7.5 Isolation

Two `Workbook` instances do not share records or memos. Scenario tests that mutate inputs clone or rebuild a workbook; they do not mutate a shared global graph. Mutating a hardcoded attribute on a shared workbook is allowed only when every later read is supposed to see that write (the epoch flush in section 12 makes that true for the memo; it does not isolate two tests that share the same instance).

---

## 8. Sheet registry

A global registry maps Excel sheet name → list of table classes:

```python

def get_tables_for_sheet(sheet_name: str) -> list[type[ExcelTable]]: ...

def all_table_classes() -> dict[str, list[type[ExcelTable]]]: ...

```

Registration happens at class definition when `__sheet_name__` is set. Importing the model package must import every table module so registration is complete.

At registration, if two tables on the same sheet have overlapping address sets, raise `OverlappingTableError`. Overlap is defined by `contains_address`: any cell claimed by both classes.

---

## 9. Loading from Excel

Loading is a workbook-construction step. It is the only place model code may read `.xlsx.xlsm` files.

```python

@classmethod

def load_from_excel(cls, path: Path, workbook: Workbook, *, replace: bool = False) -> int:

    ...

```

```python

def load_tables(path: Path, workbook: Workbook, tables: Sequence[type[ExcelTable]] | None = None) -> dict[str, int]:

    """Load the given classes, or all registered classes if tables is None."""

```

Rules:

1. Open the file twice: once for formulas `data_only=False`) and once for cached values `data_only=True`).

2. Iterate `record_index` values from `__record_range__` or `__record_list__`.

3. For each **non-internal, non-property** attribute, read the physical cell:

   - If the formula workbook shows a string starting with `=`, do not store a value `None`).

   - Otherwise store the value-workbook cell, coerced to the annotation (section 9.1).

4. For internal MIXED storage attributes, apply the same rule (formula → `None`, literal → coerced value).

5. Construct the instance, `workbook.add(record)`.

6. If `replace=True`, drop existing records of this class first.

Loaders never evaluate Python formula properties or interned helpers. They never write formula results into attributes.

`load_tables(..., tables=None)` skipping a class on error is forbidden. A load either completes or raises. Callers who want a subset pass that subset explicitly.

### 9.1 Coercion

| Annotation | Excel value | Result |

|---|---|---|

| `int` | number or numeric string | `int` |

| `float` | number or numeric string | `float` |

| `str` | anything | `str` |

| `bool` | Excel boolean | `bool` |

| `Optional[T]` | blank / `None` | `None` |

| `Optional[T]` | unparsable placeholder `"n.a."`, `"N/A"`, `"#N/A"`) | `None` |

| non-optional `T` | blank or unparsable | `CoercionError` |

Fail closed on required fields: do not silently store the raw string when the type is `int` or `float`.

---

## 10. Formula evaluation rules

1. A property wrapper maps this record to helper parameters (binding keys). The helper may read hardcoded attributes, call other helpers, and read properties on records obtained via `self.workbook.get` / `range` / `all` (mechanical path) or via keyed series readers (lifted path).

2. A property or helper may not open files, import openpyxl, or call `Workbook.resolve` to reach a cell that belongs to a known table.

3. Same-sheet, same-column references (`=C402` from row 497) are either `self.workbook.get(type(self), 402).<attr>` (mechanical) or the same helper at the lagged key (lifted Contract A: `t − 1` stays in the helper body).

4. Cross-sheet references (`='Input 1 - Basics'!C19`) are `self.workbook.get(Input1Basics, 3).scale` or a keyed reader for that series — not an A1 string inside a property that already has a mapping.

5. If the upstream cell is not yet modeled as a public attribute, property, helper, or explicit `xl_cell` fallback, the evaluation is unfinished: raise `UnmodeledDependencyError` with the Excel address. Do not return `None` and do not read Excel.

6. Excel error sentinels (`#DIV/0!`, `#REF!`, `#VALUE!`) are not stored as success values. If Python hits the same condition, raise a typed error or use `Optional` only when Excel would display blank rather than an error. Do not coerce Excel error strings into `0`.

7. Property results and helper results are read through the workbook memo (section 12). Properties and helpers must not implement their own cache (`functools.cached_property`, instance dict, module globals). Generated wrappers contain no cache logic.

8. Two call sites that share a helper and the same parameter tuple must share one memo entry. Interning without key lift can still share a mechanical `_shape_N`. Thirty-four named copies of the same internals helper (one per pasted instrument or DSA sheet) are a catalog that has not lifted the varying keys, not a second evaluation strategy.

Language- and flag-dependent formulas (e.g. English vs French labels) branch on the modeled language record, then read the corresponding modeled column. They do not hard-code sheet letters beyond the metadata already on those attributes.

---

## 11. Circular evaluation

`Workbook` keeps a thread-local (or instance-local) stack of frames currently being evaluated. A frame is either:

- a public property: `(table class, record_index, field_name)`, or
- a helper: `(helper identity, parameter tuple)`.

On entry, push. If the same frame is already on the stack more than `MAX_CELL_VISITS` times (default 50), raise `CircularReferenceError` with the stack rendered as full addresses and helper signatures (`'PV_Base'!D10` → `pv_base_imf_base(instrument='IMF', time_period=2025)` → …).

On exit, pop. This is independent of Python’s recursion limit; the error must fire first.

A value is stored in the formula memo or helper memo only after the call returns normally. An evaluation that raises (including `CircularReferenceError`) does not write a memo entry.

---

## 12. Caching (MVP: epoch flush)

Two problems are easy to conflate:

- **Intra-evaluation memo.** While computing one output, do not recompute cell D because both B and C read it (diamonds, and year-*t* walking year-*t−1*). The same applies to helpers: `accum(ctx, time_period=50)` then `accum(ctx, time_period=51)` must not walk 50 years twice (excel-grapher `xl_memoize` / `helper_cache`).

- **Incremental invalidation.** After a write, recompute only the cone of dependents.

MVP does **epoch flush**, which solves the first fully and the second only at workbook granularity: any mapped write drops every memoized formula value *and* every helper memo. That is intentional.

### 12.1 The dependence graph is not a runtime object

OOP table classes and interned helpers are generated from a dependence graph of the Excel workbook. Codegen:

1. Interns formula shapes (shared skeletons, per-instance address holes).
2. Emits mechanical `_shape_N` helpers when a shape is used more than once.
3. Cluster-refactors profitable clusters into key-lifted internals helpers.
4. Emits thin `@excel_property` methods that call those helpers. Does not emit `compute_*` / `set_*`.

The running `Workbook` does **not** store that graph. Edge count is high; keeping adjacency lists (especially reverse edges for dirty-bit flood) is expensive relative to storing computed values. Do not hang per-cell dep sets or reader sets on records. Do not re-parse A1 or walk the graph at evaluation time when a helper covers the cell.

A later increment may bake compact static dep tuples onto generated helpers if profiling warrants finer invalidation. That is not MVP, and it must not be approximated by building a graph at runtime from tracing.

Out of scope for MVP (do not implement):

- Lazy validation with per-cell version clocks

- Eager dirty propagation along reverse edges

- Early cutoff (skip dependents when a recomputed value is unchanged)

- Invalidation from Excel’s calc chain

- A second, handwritten formula body beside the interned helper

### 12.2 Policy

`Workbook` holds:

- `epoch: int` — starts at `1` after construction. Loaders do not evaluate formulas; they leave `epoch` at `1` and the memos empty.

- `memo: dict[tuple[type[ExcelTable], int, str], Any]` — key is `(table class, record_index, field_name)` for public formula properties (including MIXED public names).

- `helper_memo: dict[tuple[object, tuple], Any]` — key is `(helper identity, bound parameter tuple)`, equivalent to excel-grapher `EvalContext.helper_cache` / `xl_memoize`. Two wrappers that call the same helper with the same keys share this entry.

The property-memo check lives in `@excel_property` / `@excel_cell_property` (or one `Workbook` helper they call). The helper-memo check lives in the helper decorator (`xl_memoize` or a workbook equivalent). Generated wrappers and helper *bodies* do not contain cache logic.

**Read (formula property):**

1. If `key in memo`, return the stored value. Do not re-enter the property body.

2. Push the circular-evaluation stack (section 11).

3. Run the property body (typically one helper call).

4. On success: store the return value, pop, return. `None` is a legitimate cached value (blank / optional).

5. On exception: do not store, pop, re-raise.

**Read (helper):**

1. If `(helper, params) in helper_memo`, return the stored value.

2. Push the helper frame; run the body; store on success; never store exceptions.

A property memo hit must not skip helper-memo population in a way that makes a later direct helper call recompute. Implementation may populate helper_memo from the property path, or always enter the helper (which then hits helper_memo). Observable result is the same.

**Read (hardcoded attribute):** return the stored attribute. These are not memoized; they are the source of truth.

**Write (mapped hardcoded attribute, including MIXED `*_raw`):**

1. `epoch += 1`

2. `memo.clear()`

3. `helper_memo.clear()`

4. Store the new value

The write path is `ExcelTable.__setattr__` (section 7.3). Writes to `record_index` after `Workbook.add` are an error. Writes to unmapped names (private Python methods, not interned formula helpers) do not bump the epoch.

**Structural changes:** `add` of a record, or dropping records `replace=True` load, explicit remove), after any formula has been evaluated in this workbook, also bumps the epoch and clears the memo. During initial `load_tables`, records are added with no formula evaluation; do not flush per row.

### 12.3 Invariants

- Memo hits (property and helper) are observably equal to a full recompute from current hardcoded attributes.

- Two `Workbook` instances never share a memo or helper_memo.

- Memo identity includes the workbook. Instance-level caches (`functools.cached_property`, putting values on `self._cache`) are forbidden: they survive epoch flush and leak across tests.

- Exceptions are never memoized. In particular, do not cache `UnmodeledDependencyError` or `CircularReferenceError`.

- Do not store a memo entry until the property or helper returns; a partial cycle must not become a “value.”

- Fail closed: a stale hit is a spec bug. Golden-master mismatches are treated as cache bugs until proven otherwise.

- Helper memo keys include every parameter that can change the result. Omitting `instrument` while evaluating two pasted copies is a spec bug, not an optimization.

### 12.4 Required tests (Workbook / ExcelTable, not full sheets)

- Read a formula twice with no writes: the second call does not re-enter the body (spy / call counter on a tiny fake table) and returns the same object/value.

- Two `@excel_property` methods that call the same helper with the same keys: the helper body runs once.

- A helper that recurses on `time_period − 1`: evaluating year 50 then year 51 enters the body once more, not fifty times.

- Write a hardcoded input the formula reads, then read again: the new result reflects the write (`epoch` increased; both memos missed).

- A property or helper that raises is retried on the next access (not stuck on a cached error).

- Two workbooks loaded the same way do not share memo state; mutating one does not change the other.

### 12.5 Scenarios

Perturbing inputs (section 15.3) is: mutate hardcoded attributes, then read outputs. Epoch flush makes that correct. Isolating tests still requires separate `Workbook` instances when they must not see each other’s writes.

---

## 13. Dependency tracing

Opt-in tracing records which cells were read while computing a value.

```python

with workbook.trace() as accesses:

    result = record.some_output

# accesses: list[CellAccess(model, field, address, is_property, value)]

```

Implementation: `ExcelTable.__getattribute__` (or equivalent) notifies the active tracer when the name is a mapped attribute or property. Interned formula helpers notify on entry (helper identity + params + result). Private Python names that are not formula helpers are ignored.

Tracing does not change results. It is off unless `trace()` is entered.

---

## 14. Errors

All errors are exceptions. Do not return `None` as a stand-in for “could not evaluate.”

| Error | When |

|---|---|

| `TypeError` / `ValueError` | Class metadata invalid (missing `ColumnMeta`, duplicate letters, wrong meta type) |

| `OverlappingTableError` | Two tables claim the same cell |

| `DuplicateRecordError` | `add` of an occupied `(class, record_index)` |

| `DetachedRecordError` | Formula or lookup on a record not attached to a workbook |

| `RecordNotFound` | `get` / `range` asked for an index that is not loaded |

| `UnmappedAddressError` | `resolve` address not claimed by any table |

| `UnmodeledDependencyError` | Formula needs a cell with no public mapping, helper, or `xl_cell` fallback |

| `CircularReferenceError` | Evaluation stack exceeded |

| `CoercionError` | Loader cannot convert a required cell |

| `ExcelIOForbiddenError` | Formula property or helper attempted to read a workbook file |

`None` is a valid **cell value** (blank input, optional metric). It is not a valid stand-in for a missing record or a missing mapping.

---

## 15. Testing contract

Tests treat Excel as the golden master.

### 15.1 Structural

For every registered table class:

- Expand all cell addresses implied by metadata × declared record indices.

- In the workbook with formulas visible `data_only=False`):

  - Public attributes (non-internal) point at non-formula cells.

  - Public `@excel_property` / `@excel_cell_property` names point at formula cells.

  - Formula properties with interned coverage call the documented helper (name and dims from the interned shape / cluster refactor, not from a `compute_*` binding). Two cells that share a `shape_key` must not ship two independent bodies.

- MIXED public properties are exempt from the “must be formula” check; their internal storage attributes must cover the column, and tests for those properties must cover both a literal row and a formula row. The formula row must use the interned helper.

- `record_index` is the only *record* identity key. Helper identity is `(helper, parameter tuple)` and is not a substitute for record identity.

Mismatches fail the test. There is no warning-only mode.

### 15.2 Golden master (values)

Load a `Workbook` from the golden workbook. For sampled addresses:

```text

python_value = workbook.resolve("'Sheet'!A1")

excel_value  = openpyxl_data_only["Sheet"]["A1"].value

assert python_value == excel_value   # with documented numeric tolerance

```

Prefer resolving through the typed record (`workbook.get(Cls, idx).prop`) for model tests; use `resolve` for address-driven harnesses. Both paths must hit the same helper (spy the helper, not only the property).

### 15.3 Scenarios

To test a formula under perturbed inputs:

1. Load a workbook.

2. Mutate hardcoded attributes on the relevant records (not formula properties). This increments `workbook.epoch` and clears the formula memo.

3. Read the output property.

4. Compare to Excel outputs obtained by writing the same input cells and recalculating the workbook (cached per scenario is allowed).

Do not inject formula results by assigning to properties. Do not patch address helpers to return Excel values inside the model under test. Do not bypass interned helpers by evaluating A1 in the test harness when the property is supposed to be helper-backed.

### 15.4 Isolation

Each test (or test module) owns a `Workbook`. Tests that mutate records do not share that instance with tests that expect baseline values.

---

## 16. Illustrative tables

These examples are normative for shape, not for LIC-DSF content.

### 16.1 Form sheet `row_header`, one column of values)

```python

class Input1Basics(ExcelTable):

    __sheet_name__ = "Input 1 - Basics"

    __table_format__ = "row_header"

    __record_range__ = (3, 3)  # column C only

    country: Annotated[

        str,

        ColumnMeta(letter="C", number=7, display_name="Country", header_cell="B7"),

    ] = ""

    @property

    @excel_property(letter="C", number=8, display_name="Country code", header_cell="B8")

    def country_code(self) -> str:

        return country_code_hot(self.workbook)

```

`workbook.get(Input1Basics, 3).country` is cell C7. `record_index` may be constructed as `3` or `"C"`. `country_code` is a helper call, not a unique AST for C8.

### 16.2 Time series `row_header`, many year-columns)

```python

class PVBase(ExcelTable):

    __sheet_name__ = "PV_Base"

    __table_format__ = "row_header"

    __record_range__ = (4, 56)  # D through BD

    year: Annotated[

        int | None,

        ColumnMeta(letter="D", number=7, display_name="Year", header_cell="D7"),

    ] = None

    @property

    @excel_property(letter="D", number=9, display_name="IMF - Base", header_cell="C9")

    def imf_base(self) -> float | None:

        return pv_base_imf_base(self.workbook, time_period=self.year)

```

Column E (`record_index=5`) of `imf_base` is E9. Every year-column of this field calls the same helper; `year` (the `TIME_PERIOD` key) is the parameter. Other instruments that share this shape call the same helper with a different `instrument` key once that dimension is lifted — they do not each get a copy of the body.

### 16.3 List table `column_header`)

```python

class Data(ExcelTable):

    __sheet_name__ = "Data"

    __table_format__ = "column_header"

    __record_range__ = (2, 57)

    year: Annotated[

        int,

        ColumnMeta(letter="D", number=1, display_name="Year", header_cell="D1"),

    ] = 0

```

Row 10 is `record_index=10`; `year` is D10.

### 16.4 Sparse dashboard `cell`)

```python

class OutputCharts(ExcelTable):

    __sheet_name__ = "Output 2-2 Stress_Charts_Pub"

    __table_format__ = "cell"

    __record_range__ = (1, 1)

    @property

    @excel_cell_property(address="B3", display_name="Title", header_cell="B3")

    def title(self) -> str:

        return output_charts_title(self.workbook)

```

`workbook.get(OutputCharts, 1).title` is B3.

---

## 17. Suggested module boundaries

Names are suggestions; the types and invariants are not.

| Module | Responsibility |

|---|---|

| `models.meta` | `ColumnMeta`, `CellMeta`, `@excel_property`, `@excel_cell_property` |

| `models.table` | `ExcelTable` base: identity, address math, metadata enforcement, `__setattr__` epoch bump, `__getattribute__` tracing hook |

| `models.workbook` | `Workbook`, registry, address parse/resolve, circular stack, epoch + property memo + helper memo, `trace()` |

| `models.helpers` | Interned mechanical `_shape_N` helpers and key-lifted internals helpers; `xl_memoize` (or workbook equivalent) |

| `models.loading` | `load_from_excel`, `load_tables`, coercion |

| `models.errors` | The exception types in section 14 |

| `models.<sheet>` | One module per Excel sheet; one or more `ExcelTable` subclasses; property wrappers only |

| `models.__init__` | Import every sheet module so the registry is populated |

Sheet modules import helper **functions** and peer table **classes**. They call helpers (and, on the mechanical path, `self.workbook.get`). They do not import loaders. They do not contain interned AST bodies.

---

## 18. Implementation notes for agents

This spec is the target for an excel-grapher codegen rewrite. Do not implement it by wrapping today’s `generate_modules()` Records export.

- Implement the base (`meta`, `table`, `workbook`, `helpers`, `loading`, errors) under tests first, using a tiny fake sheet, before extracting real LIC-DSF sheets.

- Implement epoch-flush memo on that fake sheet (section 12.4) before any real formula batch — including helper_memo sharing across two wrappers.

- Codegen order for a real sheet:

  1. Extract / warm the dependence graph and intern formula shapes.
  2. Emit mechanical `_shape_N` helpers for shapes used more than once; per-node AST only when a shape is unique or the overlay is cold.
  3. Bind internals (`internal: {}`) so cluster refactor can see keys. Prefer reshape-to-keys (`INSTRUMENT`, `HOLDER`, `SCENARIO`, `ISSUANCE_YEAR`, …) before refactor so one helper covers pasted copies.
  4. Cluster-refactor under Contract A or B; skip `operand_level_variation_unsupported` rather than inventing counterpart dims.
  5. For formula cells with helper coverage, generate `@excel_property` methods that call the helper with the record’s keys. Uncovered leaves stay `xl_cell` inside the helper (or raise `UnmodeledDependencyError` if the property claims to be modeled). Do not emit `compute_*`.
  6. Stubs that are not yet generated raise `UnmodeledDependencyError` or `NotImplementedError` (not `return None`).

- Outer loop for layout still applies: inspect layout → classify literal vs formula vs MIXED → declare class metadata and attributes. Do not hand-write a unique property body per cell.

- Inner loop: implement or regenerate helpers in small batches against Excel values. Mock or load only the upstream series those helpers read.

- When a formula references a cell with no table yet, stop and scaffold that table (or an `internal` / `constant` series); do not add an address fallback for a cell that should have a class.

- Numeric comparisons use a documented absolute/relative tolerance; strings and booleans compare exactly.

- Do not add a “get or default” helper unless a specific Excel formula’s miss behavior is documented on that property.

- Do not add per-cell dependence lists or reverse edges to the runtime model.

- Do not treat N identical generated helpers (one per pasted instrument or DSA sheet) as done interned design. That is a catalog that has not lifted the varying keys.