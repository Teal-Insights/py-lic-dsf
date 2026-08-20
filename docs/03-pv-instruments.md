# PV instruments (Input 4 / 5)

Excel analogues: hidden **`PV_Base`** tables (Input 4, USD) and **`PV_LC_NR1/2/3`**
(Input 5, local-currency non-resident bonds converted to USD).

## What you get

| Class | Role |
|-------|------|
| `PresentValueInstrument` | One Input 4 financing instrument → `internal()` / `external()` schedules |
| `LocalCurrencyNonResidentInstrument` | One Input 5 LC-NR bond → same canonical Output rows in USD |
| `PVPortfolio` | Named collection; per-loan panels + new-debt aggregates |
| `load_instruments_from_workbook` | Input 4 → list of `PresentValueInstrument` |
| `load_lc_nr_instruments_from_workbook` | Input 5 → list of LC-NR instruments |

`PVPortfolio` owns **new MLT only**. Existing debt, ST, SDR, and Ext headlines
live on [`ExternalDebtBook`](04-ext-debt-module-design.md).

## Load and inspect

```python
from pathlib import Path

from lic_dsf.pv import (
    PVPortfolio,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)

workbook = Path("data/lic-dsf-template-2025-08-12.xlsx")
instruments = load_instruments_from_workbook(workbook, include_zero_disbursement=True)
lc_nr = load_lc_nr_instruments_from_workbook(workbook, include_zero_disbursement=True)
portfolio = PVPortfolio(instruments=tuple(instruments) + tuple(lc_nr))

# One loan's Output-shaped panel
portfolio.external(portfolio.instruments[0].name)

# Per-instrument PV (rows = names, columns = years)
portfolio.pv()

# Portfolio totals: Interest / Amortization / Total new debt service
portfolio.new_debt_service()
```

Canonical external rows include gross new borrowing, stock, PV of debt,
interest, and amortization (see `PVPortfolio.aggregate_external()`).

## Excel cues

- Discount rate and year grid come from Input 1 / instrument tables (as loaded).
- LC-NR uses FX(pa) / FX(eop) paths from the workbook, matching `PV_LC_NR*`.
- Empty disbursement slots: pass `include_zero_disbursement=True` when you need
  Ext creditor-group row alignment.

## Demos

- [`demo/pv.ipynb`](../demo/pv.ipynb) — single USD instrument
- [`demo/lc_nr.ipynb`](../demo/lc_nr.ipynb) — LC-NR
- [`demo/portfolio.ipynb`](../demo/portfolio.ipynb) — combined portfolio

---

**Next:** [4. Ext debt](04-ext-debt-module-design.md)
