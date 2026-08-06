# Ext_Debt_Data as a `lic_dsf.pv` extension

Design for the LIC-DSF **Ext_Debt_Data** sheet on top of
`PresentValueInstrument` / `PVPortfolio`.

**v1 status:** `ExternalDebtInputs`, `load_external_debt_inputs`,
`existing_mlt_pv` / `existing_mlt_nominal`, Input 5 locally-issued USD series,
and `ExternalDebtBook` headlines are implemented under
`lic_dsf.pv.external_debt` (Python API says **existing**; Excel labels the same
block “old MLT”).

Sheet purpose (from Ext_Debt itself): **calculate the PV of public (PPG)
external debt**. Aggregation is only part of that job.

---

## Ownership (three layers)

Ext_Debt logic does **not** belong on `PresentValueInstrument`. That class is
one loan template. New-debt aggregation also does **not** belong on Ext_Debt
itself — a portfolio owns the instruments, runs their calculations, and
exposes aggregates. Ext_Debt only *consumes* those aggregates plus existing-debt /
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
  ├─ existing MLT service + NPV  (Excel: “old”)
  ├─ arrears / ST / SDR
  ├─ residual financing params  # Input 7 defaults + overrides
  └─ total_pv_of_debt / public DS / PPG check
```

| Class | Owns | Does not own |
|-------|------|----------------|
| `PresentValueInstrument` | One instrument’s terms, disbursements, schedules | Other instruments, totals, existing debt, LC+FX |
| `LocalCurrencyNonResidentInstrument` | LC-NR vintages + FX(pa)/FX(eop) → USD Output | USD PV_Base path, existing debt |
| `PVPortfolio` | The instrument set; cached Output panels; new-debt sums / metric panels | Creditor taxonomy, existing-debt NPV, ST/SDR, DSA headlines |
| `ExternalDebtBook` | Existing + new + ST/SDR consolidation for PPG external PV | Per-instrument amortization math |

---

## What you already have vs next

```text
done
────
PresentValueInstrument.internal() / .external()
LocalCurrencyNonResidentInstrument.external()
load_instruments_from_workbook(...)
load_lc_nr_instruments_from_workbook(...)
PVPortfolio(...)
ExternalDebtBook(portfolio=..., inputs=...)
load_external_debt_inputs(...)
existing_mlt_pv / existing_mlt_nominal

done (params only)
──────────────────
ResidualFinancingParams / calculate_residual_defaults / resolve_residual_params
book.residual_defaults() / book.residual_params(overrides)

later
─────
grant element of new disbursements; stress DSA that *consumes* residual params
Dom_Debt_Data (full domestic DSA sheet)
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
    existing_debt.py          # existing MLT service + NPV (Excel: “old”)
    workbook.py               # load_external_debt_inputs
    types.py                  # ExternalDebtInputs
    residual.py               # Input 7 shares/terms defaults + overrides
```

Public import surface:

```python
from lic_dsf.pv import (
    PresentValueInstrument,
    PVPortfolio,
    load_instruments_from_workbook,
    ExternalDebtBook,
    ExternalDebtInputs,
    load_external_debt_inputs,
    ResidualFinancingParams,
    ResidualFinancingOverrides,
    calculate_residual_defaults,
    resolve_residual_params,
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
| Existing MLT debt service | `Input 3` / DMX | Principal + interest by creditor, by year (Excel: “old”) |
| Existing discount rates | `Input 4` col E (per instrument) | For `NPV` of remaining existing service |
| Arrears stock | Input 3 | Nominal arrears |
| ST external | Input 3 | Short-term PPG external |
| SDR PV / service | `Input 8 - SDR` | Net use of SDRs |
| Macro PPG / MLT stock | `Macro-Debt_Data` | Seed + PPG check |
| Locally-issued stock / service / ST | Input 5 ÷ FX(eop)/FX(pa) | Existing local PV, public DS, total ST |

In code, prefer typed bags of DataFrames over a live workbook handle:

```python
@dataclass(slots=True)
class ExternalDebtInputs:
    years: tuple[int, ...]
    existing_debt_service: pd.DataFrame     # creditor × year (P+I)
    existing_principal: pd.Series           # aggregate principal
    existing_discount_rates: dict[str, float]
    arrears: pd.Series
    short_term_external: pd.Series
    sdr_pv: pd.Series
    sdr_interest: pd.Series
    macro_ppg_external: pd.Series
    macro_mlt_external: pd.Series
    fx_eop: pd.Series
    fx_pa: pd.Series
    locally_issued_debt_stock: pd.Series
    locally_issued_principal: pd.Series
    locally_issued_interest: pd.Series
    locally_issued_st: pd.Series
    locally_issued_st_principal: pd.Series
    locally_issued_st_interest: pd.Series
    domestic_mlt_disbursements_usd: pd.Series
    domestic_st_disbursements_usd: pd.Series
    short_term_interest_rate: float
```

New MLT instruments live on **`PVPortfolio`**, not duplicated on
`ExternalDebtInputs`. Loader: `load_external_debt_inputs(workbook)`.

### 2. Creditor grouping (later, on `ExternalDebtBook`)

Ext_Debt rolls instruments through groups (Multilaterals, Bilaterals, …).
That taxonomy is sheet-specific and does **not** live on `PVPortfolio`. When
needed, `ExternalDebtBook` can own a caller-supplied name→group map.

---

## `ExternalDebtBook` API

Delegates all **new MLT** panels to `PVPortfolio`. Implements existing-debt NPV
and headline mixes only.

```python
@dataclass(slots=True)
class ExternalDebtBook:
    portfolio: PVPortfolio
    inputs: ExternalDebtInputs

    def new_debt_service(self) -> pd.DataFrame: ...
    def new_mlt_pv(self) -> pd.Series: ...          # Ext R279
    def new_mlt_nominal(self) -> pd.Series: ...     # Ext R329
    def existing_mlt_pv(self) -> pd.DataFrame: ...  # Ext R242 (“old”)
    def existing_mlt_nominal(self) -> pd.Series: ...  # Ext R67
    def total_pv_of_debt(self) -> pd.Series: ...    # R391
    def total_public_debt_service(self) -> pd.DataFrame: ...  # R394–396
    def nominal_ppg_check(self) -> pd.Series: ...   # R393
    def summary(self) -> pd.DataFrame: ...
```

Also on the book: `residual_defaults()` / `residual_params(overrides)` (Input 7
assumption bag). Later: `grant_element_new_disbursements` and stress execution.

Usage sketch:

```python
instruments = load_instruments_from_workbook(WORKBOOK, include_zero_disbursement=True)
lc_nr = load_lc_nr_instruments_from_workbook(WORKBOOK)
portfolio = PVPortfolio(tuple(instruments) + tuple(lc_nr))
inputs = load_external_debt_inputs(WORKBOOK)
book = ExternalDebtBook(portfolio=portfolio, inputs=inputs)

portfolio.aggregate_external().iloc[:, :8]   # new debt only
book.summary().iloc[:, :8]                   # Ext_Debt headlines
book.total_pv_of_debt()
book.existing_mlt_pv().loc["Total"]
book.residual_defaults()                     # Ext C126–C128 / C131–C133
book.residual_params(ResidualFinancingOverrides(avg_interest_rate=6.0))
```

---

## Calculation map (what to implement where)

| Ext_Debt section | Build with | Notes |
|------------------|------------|-------|
| 1. Existing MLT debt service | `existing_debt.py` / loader | Mostly ingest + split; little PV math |
| Evolution / checks | `existing_mlt_nominal` | Stock walk: opening − principal (− local adj) |
| 2. Arrears | input series | Pass-through; PV of arrears often = stock |
| 3. New disbursements | `PVPortfolio` / Input 4 | Already on instruments |
| Shares of marginal debt | `residual.py` | Decade avg of Ext R126–R128 → Input 7 |
| Residual financing terms | `residual.py` | Decade avg of Ext R131–R133 (+ ROUNDDOWN) |
| New debt: Interest / Amort | **`PVPortfolio`** | Sum / group Output Interest & Amortization |
| PV of existing MLT | `existing_mlt_pv` | `excel_npv(discount_i, service_i[t+1:])` + local stock |
| PV of new MLT | **`PVPortfolio`** | Sum Output `PV of debt` |
| Nominal new MLT | **`PVPortfolio`** | Sum Output stock |
| ST + SDR | inputs | Pass-through |
| **Total PV of debt** | `ExternalDebtBook` | Sum of the PV pieces |
| Locally-issued service / ST | Input 5 → inputs | LC→USD; folded into public DS + R386 |
| **Total public debt service** | `ExternalDebtBook` | Existing + local + new + ST (+ SDR interest) |
| Nominal PPG check | `ExternalDebtBook` | Macro − new − existing MLT − ST − arrears |
| Grant element new | later | From new PV vs disbursements |

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
PV of existing MLT debt
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
| 2 | `load_instruments_from_workbook` | done |
| 3 | **`PVPortfolio`** | done |
| 4 | Eurobond / portfolio new-MLT panels | done |
| 5 | `excel_npv` + `existing_mlt_pv()` | done |
| 6 | `ExternalDebtBook` wired to `PVPortfolio` | done |
| 7 | `total_pv_of_debt` / public DS / PPG check | done |
| 8 | `load_external_debt_inputs` + parity vs F242 / F279 / F391 / F393 | done |
| 9 | Input 5 locally-issued service / ST on the book | done |
| 10 | `residual_financing` params (defaults + overrides) | done |
| 11 | grant element of new disbursements | later |
| 12 | `Dom_Debt_Data` | later |

Skip for now: IMF special schedules, cost-shock PV sheets, ResFin PV, full
stress cones — those feed *variants* of new debt into the same book API.
---

## What *not* to put where

- On `PresentValueInstrument`: no other instruments, no group totals, no existing debt.
- On `PVPortfolio`: no existing-debt NPV, no ST/SDR mix, no PPG check — only new-loan
  instrument ownership and aggregates.
- On `ExternalDebtBook`: no per-instrument schedule math — call `portfolio.*`
  for new MLT; implement existing NPV + headline mixes only.
- Chart Data ratings / DSA ratios → consumers of `total_pv_of_debt()`, later.

---

## Parity targets (when you implement)

| Check | Excel anchor |
|-------|----------------|
| New interest / amort totals | `Ext_Debt_Data!F142` / `F192` |
| PV of new MLT | `F279` |
| Nominal new MLT | `F329` |
| PV of existing MLT (Excel “old”) | `F242` |
| Total PV of debt | `F391` |
| Total public debt service | `F394` |
| PPG check | `F393` |
| Residual shares (decade avg) | `C126` / `C127` / `C128` |
| Residual terms (decade avg / ROUNDDOWN) | `C131` / `C132` / `C133` |

Use Eurobond-heavy years for new-debt panels; existing-debt NPV parity needs the
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
                                     ├─ existing_mlt_pv()
                                     ├─ ST / SDR / arrears
                                     └─ total_pv_of_debt / public DS / PPG check
                                               │
                                               ▼
                                     Baseline / stress DSA, Macro-Debt, Input 5
```

**Next:** grant element of new disbursements; stress DSA that consumes residual
params; then `Dom_Debt_Data` if needed.
