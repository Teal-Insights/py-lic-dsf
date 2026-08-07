# Macro-Debt_Data (`MacroDebtBook`)

Excel analogue: **`Macro-Debt_Data`** — macro denominators (GDP, FX, exports,
revenues), debt stocks in LCU/USD, GFN, fiscal balances, and the stitch of Ext
PPG PV/service into the macro identity.

## What you get

| Piece | Role |
|-------|------|
| `MacroDebtBook` | Macro engine; optional `external=` for PPG stitch |
| `load_macro_debt_inputs` | Input 3 / Macro blocks from the workbook |

Almost every downstream panel (baseline DSA, stress, realism) needs Macro.

## Load and compute

```python
from pathlib import Path

from lic_dsf.pv import (
    ExternalDebtBook,
    MacroDebtBook,
    PVPortfolio,
    load_external_debt_inputs,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
    load_macro_debt_inputs,
)

workbook = Path("data/lic-dsf-template-2025-08-12.xlsx")
ext = ExternalDebtBook(
    portfolio=PVPortfolio(
        instruments=tuple(load_instruments_from_workbook(
            workbook, include_zero_disbursement=True
        ))
        + tuple(load_lc_nr_instruments_from_workbook(
            workbook, include_zero_disbursement=True
        ))
    ),
    inputs=load_external_debt_inputs(workbook),
)
macro = MacroDebtBook(
    inputs=load_macro_debt_inputs(workbook),
    external=ext,
)

macro.gdp_usd()
macro.gdp_lcu()
macro.exports()
macro.external_gfn()
macro.public_gfn()
macro.total_public_debt()
macro.pv_external_lcu()
macro.summary()  # when available — see demo
```

Pass `external=` so PPG external stocks/PV/service align with Ext; without it,
Macro still loads macro inputs but Ext-dependent series are incomplete.

## Excel cues

| Series | Typical Macro role |
|--------|--------------------|
| GDP USD / LCU | Denominators for DSA ratios |
| Exports, revenues ± grants | External / public capacity |
| External / public GFN | Financing need (Baseline R41 / R47 area) |
| Public debt, PPG external LCU | Public DSA stocks |
| FX(pa) | USD ↔ LCU for public aggregates |
| `first_projection_year` | History vs projection split |

## Demo

[`demo/macro_debt.ipynb`](../demo/macro_debt.ipynb)

Next: [Baseline DSA](baseline-dsa.md).
