# Ext_Debt_Data (`ExternalDebtBook`)

Excel analogue: **`Ext_Debt_Data`** — existing PPG external MLT, new portfolio
MLT, ST / locally issued / SDR pieces, creditor groups, grant element, and
PPG PV headlines (e.g. Ext R391).

## What you get

| Piece | Role |
|-------|------|
| `ExternalDebtBook` | Sheet engine: `portfolio` + `ExternalDebtInputs` |
| `load_external_debt_inputs` | Existing debt / Ext input blocks from the workbook |
| `PVPortfolio` | New MLT schedules ([pv-instruments.md](pv-instruments.md)) |
| `load_input7_residual_params` | Input 7 residual-financing terms (used heavily in stress) |

Creditor grouping, grant element, debt evolution, and memorandum panels are
methods / helpers on or under this book — not on `PVPortfolio`.

## Load and compute

```python
from pathlib import Path

from lic_dsf.pv import (
    ExternalDebtBook,
    PVPortfolio,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)

workbook = Path("data/lic-dsf-template-2025-08-12.xlsx")
portfolio = PVPortfolio(
    instruments=tuple(load_instruments_from_workbook(
        workbook, include_zero_disbursement=True
    ))
    + tuple(load_lc_nr_instruments_from_workbook(
        workbook, include_zero_disbursement=True
    ))
)
ext = ExternalDebtBook(
    portfolio=portfolio,
    inputs=load_external_debt_inputs(workbook),
)

ext.total_pv_of_debt()          # Ext R391-style PPG PV
ext.new_mlt_pv()                # new portfolio only
ext.existing_mlt_pv()           # existing by creditor + Total
ext.new_disbursements_by_creditor()
ext.debt_evolution()
ext.summary()                   # compact headline table when available
```

## Excel cues

| Concept | Typical Ext cue |
|---------|-----------------|
| Total PPG external PV | R391 |
| New MLT PV / stock | R279 / R329 |
| Existing MLT PV | R242 block |
| Debt service aggregates | R394–396 |
| Residual financing terms | Input 7 (via `load_input7_residual_params`) |

## Architecture (brief)

```text
PVPortfolio (new loans)
        +
ExternalDebtInputs (existing, ST, SDR, FX, …)
        ↓
ExternalDebtBook  →  MacroDebtBook / Baseline DSA
```

## Demo

[`demo/ext_debt.ipynb`](../demo/ext_debt.ipynb)

Next: [Macro-Debt_Data](macro-debt-bridge.md) or [Baseline DSA](baseline-dsa.md).
