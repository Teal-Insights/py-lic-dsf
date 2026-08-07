# Dom_Debt indicators (`DomesticDebtBook`)

Excel analogues: **`Dom_Debt_Data`** / **`Dom_Debt_Indicators`** — domestic
public debt stocks, service, and presentation bands (including peer medians
where the template provides them).

## What you get

| Piece | Role |
|-------|------|
| `DomesticDebtBook` | Domestic debt engine from workbook inputs |
| `load_domestic_debt_inputs` | Dom sheet blocks → `DomesticDebtInputs` |

Public DSA and Macro already stitch domestic stocks into public ratios when
you build `MacroDebtBook` with Ext; use Dom when you need Dom-sheet indicators
or presentation panels directly.

## Load and compute

```python
from pathlib import Path

from lic_dsf.pv import DomesticDebtBook, load_domestic_debt_inputs

workbook = Path("data/lic-dsf-template-2025-08-12.xlsx")
dom = DomesticDebtBook(inputs=load_domestic_debt_inputs(workbook))

dom.domestic_debt_to_gdp()
dom.domestic_ds_to_revenues()
dom.peer_median_debt_to_gdp()
dom.peer_median_ds_to_revenues()
dom.indicator_charts()
dom.borrowing_assumptions()  # Input 7 domestic terms
dom.summary()
```

`load_domestic_debt_inputs` pulls Baseline public/external ratios, Macro
stocks/flows, and Input 7 domestic borrowing assumptions (see demo).

## Excel cues

Domestic series feed **Baseline – public** debt service and PV public debt
(Macro R82 domestic stock + external PV in LCU). Peer median bands appear on
Dom indicator rows (e.g. debt/GDP, DS/revenues).

## Demo

[`demo/dom_debt.ipynb`](../demo/dom_debt.ipynb)

Related: [macro-debt-bridge.md](macro-debt-bridge.md), [baseline-dsa.md](baseline-dsa.md).
