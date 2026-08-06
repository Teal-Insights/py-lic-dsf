# Ext_Debt_Data as a `lic_dsf.pv` extension

Design sketch for implementing the LIC-DSF **Ext_Debt_Data** sheet on top of
`PresentValueInstrument` / `PVPortfolio`. Not implemented yet — this is the
target shape.

Sheet purpose (from Ext_Debt itself): **calculate the PV of public (PPG)
external debt**. Aggregation is only part of that job.

---

## Ownership (three layers)

Ext_Debt logic does **not** belong on `PresentValueInstrument`. That class is
one loan template. New-debt aggregation also does **not** belong on Ext_Debt
itself — a portfolio owns the instruments, runs their calculations, and
exposes aggregates. Ext_Debt only *consumes* those aggregates plus old-debt /
macro inputs.

```text
PresentValueInstrument          # one new loan (PV_Base template)
  ├─ internal() → unit-loan DataFrame
  └─ external() → Output DataFrame
         ▲
         │ owns & calls
         │
PVPortfolio                     # set of instruments → new-debt aggregates
  ├─ instruments: tuple[PresentValueInstrument, ...]
  ├─ external(name)             # cached Output panel
  ├─ aggregate_external()       # sum Output rows across instruments
  ├─ interest() / amortization() / pv() / stock()
  └─ new_debt_service()         # Interest + Amort (+ total)
         ▲
         │ reads aggregates only
         │
ExternalDebtBook                # Ext_Debt_Data sheet
  ├─ portfolio: PVPortfolio     # new MLT side
  ├─ old MLT service + NPV
  ├─ arrears / ST / SDR
  ├─ residual financing terms
  └─ total_pv_of_debt / public DS / PPG check
```

| Class | Owns | Does not own |
|-------|------|----------------|
| `PresentValueInstrument` | One instrument’s terms, disbursements, schedules | Other instruments, totals, old debt, LC+FX |
| `LocalCurrencyNonResidentInstrument` | LC-NR vintages + FX(pa)/FX(eop) → USD Output | USD PV_Base path, old debt |
| `PVPortfolio` | The instrument set; cached Output panels; new-debt sums / metric panels | Creditor taxonomy, old-debt NPV, ST/SDR, DSA headlines |
| `ExternalDebtBook` | Old + new + ST/SDR consolidation for PPG external PV | Per-instrument amortization math |

---

## What you already have vs next

```text
today
─────
PresentValueInstrument.internal() / .external()
LocalCurrencyNonResidentInstrument.external()   # PV_LC_NR1/2/3 sibling
load_instruments_from_workbook(...)
load_lc_nr_instruments_from_workbook(...)
PVPortfolio(...)

next (Ext_Debt sheet)
────────────────────
ExternalDebtBook(portfolio=..., inputs=...)
```

LC-NR is a **sibling** of `PresentValueInstrument`, not an LC flag on that class:
cohort schedules in LC plus FX(pa)/FX(eop) conversion. Both expose USD
`Interest` / `Amortization` / `PV of debt` / stock rows so `PVPortfolio` can mix them.

---

## Module layout (target)

```text
src/lic_dsf/pv/
  __init__.py                 # re-exports
  instrument.py               # PresentValueInstrument (move from __init__)
  portfolio.py                # PVPortfolio
  workbook.py                 # load_instruments_from_workbook
  external_debt/
    __init__.py
    book.py                   # ExternalDebtBook
    old_debt.py               # existing MLT service + NPV
    residual.py               # avg rate / grace / maturity for stress
    aggregates.py             # Total PV, public DS, PPG check, grant element
    types.py                  # CreditorGroup, series tables
```

Public import surface:

```python
from lic_dsf.pv import (
    PresentValueInstrument,
    PVPortfolio,
    load_instruments_from_workbook,
    ExternalDebtBook,
)
```

---

## `PVPortfolio` API (build this before Ext_Debt)

```python
@dataclass(slots=True)
class PVPortfolio:
    """Owns PresentValueInstrument instances and their Output projections."""

    instruments: tuple[PresentValueInstrument, ...]

    def get(self, name: str) -> PresentValueInstrument: ...

    def external(self, name: str) -> pd.DataFrame:
        """One instrument Output panel (cached)."""

    def aggregate_external(self) -> pd.DataFrame:
        """Sum of Output rows across all instruments."""

    def interest(self) -> pd.DataFrame: ...
    def amortization(self) -> pd.DataFrame: ...
    def pv(self) -> pd.DataFrame: ...
    def stock(self) -> pd.DataFrame: ...

    def new_debt_service(self) -> pd.DataFrame:
        """Interest + Amortization portfolio totals and their sum."""
```

Usage:

```python
instruments = load_instruments_from_workbook(WORKBOOK)
portfolio = PVPortfolio(instruments)
portfolio.aggregate_external().iloc[:, :8]
portfolio.interest().loc["Eurobond"]
portfolio.new_debt_service().loc["Total new debt service"]
```

Creditor-group roll-ups (Multilaterals / Bilaterals / …) belong on
`ExternalDebtBook` later, not on `PVPortfolio`.

---

## Domain objects

### 1. Inputs Ext_Debt needs (beyond new-loan PVs)

| Block | Source in workbook | Role in Python |
|-------|--------------------|----------------|
| New MLT Output | `PV_Base` / `PVPortfolio` | Interest, amort, PV, stock by instrument |
| New LC-NR / FX local | `PV_LC_NR*`, resident FX bonds | Same four metrics for local-issue lines |
| New disbursements | `Input 4` | Already on each instrument |
| Old MLT debt service | `Input 3` / DMX | Principal + interest by creditor, by year |
| Old discount rates | `Input 4` col E (per instrument) | For `NPV` of remaining old service |
| Arrears stock | Input 3 / Macro-Debt | Nominal arrears |
| ST external | Input 3 | Short-term PPG external |
| SDR PV / service | `Input 8 - SDR` | Net use of SDRs |
| Macro PPG stock | `Macro-Debt_Data` | Evolution / PPG check |

In code, prefer typed bags of DataFrames over a live workbook handle:

```python
@dataclass(slots=True)
class ExternalDebtInputs:
    years: tuple[int, ...]
    # old MLT debt service: rows = creditor, columns = years; or principal/interest split
    old_debt_service: pd.DataFrame          # total service by creditor × year
    old_principal: pd.DataFrame | None
    old_interest: pd.DataFrame | None
    old_discount_rates: dict[str, float]    # Input 4!E* per creditor
    arrears: pd.Series                      # year → stock
    short_term_external: pd.Series          # year → nominal (=PV)
    sdr_pv: pd.Series
    sdr_interest: pd.Series | None
    macro_ppg_external: pd.Series           # Macro-Debt MLT PPG path
    # optional extra new-debt panels (LC-NR, resident FX) not in PVPortfolio yet
    extra_new_external: dict[str, pd.DataFrame]
```

New MLT instruments live on **`PVPortfolio`**, not duplicated on
`ExternalDebtInputs`. Loader later: `load_external_debt_inputs(workbook)`.

### 2. Creditor grouping (later, on `ExternalDebtBook`)

Ext_Debt rolls instruments through groups (Multilaterals, Bilaterals, …).
That taxonomy is sheet-specific and does **not** live on `PVPortfolio`. When
needed, `ExternalDebtBook` can own a caller-supplied name→group map.

---

## `ExternalDebtBook` API

Delegates all **new MLT** panels to `PVPortfolio`. Implements old-debt NPV and
headline mixes only.

```python
@dataclass(slots=True)
class ExternalDebtBook:
    portfolio: PVPortfolio
    inputs: ExternalDebtInputs

    def new_debt_service(self) -> pd.DataFrame:
        """Delegate to portfolio.new_debt_service() (+ LC-NR extras if any)."""

    def new_mlt_pv(self) -> pd.Series:
        """Ext_Debt R279 — from portfolio.pv() total."""

    def new_mlt_nominal(self) -> pd.Series:
        """Ext_Debt R329 — from portfolio.stock() total."""

    def old_mlt_pv(self) -> pd.DataFrame:
        """Ext_Debt R242 block — NPV of remaining old service per creditor,
        then group + total. Sheet-local Excel NPV, not PV_Base.
        """

    def residual_financing_terms(self) -> pd.DataFrame:
        """Avg interest / grace / maturity (and rounded) for stress residual
        financing — Ext_Debt R130–136.
        """

    def total_pv_of_debt(self) -> pd.Series:
        """R391 = old MLT PV + arrears PV + new MLT PV + ST + SDR PV."""

    def total_public_debt_service(self) -> pd.DataFrame:
        """R394–396: total, of which principal, of which interest."""

    def nominal_ppg_check(self) -> pd.Series:
        """R393 consistency vs Macro-Debt PPG stock."""

    def grant_element_new_disbursements(self) -> pd.Series:
        """R408-style % grant element on new flows."""

    def summary(self) -> pd.DataFrame:
        """One Ext_Debt-shaped headline table (totals only)."""

    def to_frames(self) -> dict[str, pd.DataFrame]:
        """Named panels for notebook / parity dumps."""
```

Usage sketch:

```python
instruments = load_instruments_from_workbook(WORKBOOK, include_zero_disbursement=True)
portfolio = PVPortfolio(instruments)
inputs = load_external_debt_inputs(WORKBOOK)
book = ExternalDebtBook(portfolio=portfolio, inputs=inputs)

portfolio.aggregate_external().iloc[:, :8]   # new debt only
book.summary().iloc[:, :8]                   # full Ext_Debt headlines
book.total_pv_of_debt()
book.old_mlt_pv().loc["Total"]
```

---

## Calculation map (what to implement where)

| Ext_Debt section | Build with | Notes |
|------------------|------------|-------|
| 1. Old MLT debt service | `old_debt.py` | Mostly ingest + split; little PV math |
| Evolution / checks | `old_debt.py` | Stock walk: opening − principal (− local adj) |
| 2. Arrears | input series | Pass-through; PV of arrears often = stock |
| 3. New disbursements | `PVPortfolio` / Input 4 | Already on instruments |
| Shares of marginal debt | `residual.py` | Composition of new financing |
| Residual financing terms | `residual.py` | Weighted averages for stress |
| New debt: Interest / Amort | **`PVPortfolio`** | Sum / group Output Interest & Amortization |
| PV of old MLT | `old_debt.py` | `excel_npv(discount_i, service_i[t+1:])` per creditor |
| PV of new MLT | **`PVPortfolio`** | Sum Output `PV of debt` |
| Nominal new MLT | **`PVPortfolio`** | Sum Output stock |
| ST + SDR | inputs | Pass-through |
| **Total PV of debt** | `aggregates.py` | Sum of the PV pieces |
| **Total public debt service** | `aggregates.py` | Old + new + ST (+ SDR interest) |
| Nominal PPG check | `aggregates.py` | Macro − new nominal − old bits − ST − arrears |
| Grant element new | `aggregates.py` | From new PV vs disbursements |

Excel NPV convention already lives in `PresentValueInstrument` as
`_excel_npv` — **export it** (e.g. `excel_npv`) so old-debt NPV shares one
definition with the unit loan.

---

## DataFrame conventions (match current module)

- Columns = calendar years (`2024…`).
- Rows = metric labels close to sheet language.
- Prefer returning **DataFrame / Series**, not new result dataclasses
  (same pattern as `internal()` / `external()`).
- Group subtotals as extra rows (`Multilaterals`, `Commercial`, …) when the
  panel is creditor-level; headline methods return year Series only.

Example `PVPortfolio.new_debt_service()` shape:

```text
                         2024  2025  …  2084
Interest                  …     …
  Multilaterals           …
  …
Amortization              …
Total new debt service    …     …          # = Interest + Amortization
```

Example `ExternalDebtBook.summary()` shape:

```text
                         2024  2025  …
PV of old MLT debt
PV of existing arrears
PV of new MLT debt
Total ST external debt
PV of net use of SDRs
Total PV of debt
Nominal value of new MLT
Nominal PPG debt check
Total public debt service
  of which: principal
  of which: interest
```

---

## Build order (extend the notebook workflow)

| Step | Deliverable | Depends on |
|-----:|-------------|------------|
| 1 | `PresentValueInstrument` DataFrames | done |
| 2 | `load_instruments_from_workbook` | Input 4 + PV_Base / Input 3 disbursements |
| 3 | **`PVPortfolio`** (own instruments, `aggregate_external`, group metrics) | 2 |
| 4 | Eurobond (etc.) parity on Output + portfolio totals vs Ext_Debt new rows | 2–3 |
| 5 | `excel_npv` public + `old_mlt_pv()` | old service + discounts |
| 6 | `ExternalDebtBook` wired to `PVPortfolio` | 3 |
| 7 | `total_pv_of_debt` / public DS / PPG check | 5–6 + ST/SDR/arrears inputs |
| 8 | `residual_financing_terms` | disbursement weights + Input 4 terms |
| 9 | `load_external_debt_inputs` + full-sheet parity | Ext_Debt R391 / R394 |

Skip for v1 (same as PV notebook “later”): IMF special schedules, cost-shock
PV sheets, ResFin PV, full stress cones — those feed *variants* of new debt
into the same book API.

---

## What *not* to put where

- On `PresentValueInstrument`: no other instruments, no group totals, no old debt.
- On `PVPortfolio`: no old-debt NPV, no ST/SDR mix, no PPG check — only new-loan
  instrument ownership and aggregates.
- On `ExternalDebtBook`: no per-instrument schedule math — call `portfolio.*`
  for new MLT; implement old NPV + headline mixes only.
- Chart Data ratings / DSA ratios → consumers of `total_pv_of_debt()`, later.

---

## Parity targets (when you implement)

| Check | Excel anchor |
|-------|----------------|
| New interest / amort totals | `Ext_Debt_Data!F142` / `F192` |
| PV of new MLT | `F279` |
| Nominal new MLT | `F329` |
| PV of old MLT | `F242` |
| Total PV of debt | `F391` |
| Total public debt service | `F394` |
| PPG check | `F393` |

Use Eurobond-heavy years for new-debt panels; old-debt NPV parity needs the
Input 3 service streams even when many PV_Base instruments are zero.

---

## One-page mental model

```text
  Input 4 + disbursements
            │
            ▼
  PresentValueInstrument × N     (pure: one loan each)
            │
            ▼
       PVPortfolio               (owns instruments → new-debt aggregates)
            │
            ├──────────────────────────────┐
            ▼                              ▼
  (notebook / parity)              ExternalDebtBook
  aggregate_external()               │
                                     ├─ portfolio.new_*  (delegate)
                                     ├─ old_mlt_pv()
                                     ├─ ST / SDR / arrears
                                     └─ total_pv_of_debt / public DS / PPG check
                                               │
                                               ▼
                                     Baseline / stress DSA, Macro-Debt, Input 5
```

**Next concrete class to build:** `PVPortfolio` — owns the instruments, runs
their calculations, and produces the aggregate information Ext_Debt (and the
notebook) will read.
