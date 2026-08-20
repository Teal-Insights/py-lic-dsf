# Baseline DSA (Output 1-1 / 1-2)

Excel analogues: **`Baseline - external`** / **`Baseline - public`**, feeding
**Output 1-1** and **Output 1-2**.

Package: `lic_dsf.dsa`. Consumes Macro + Ext books; does not recompute instrument
PV schedules (`lic_dsf.pv`) or apply Input 6 shocks (`lic_dsf.stress`).

## What you get

| Piece | Excel role |
|-------|------------|
| `BaselineExternalBook` | External sustainability ratios |
| `BaselinePublicBook` | Public sustainability / Dom feeder ratios |
| `external_dsa_panel` | Output 1-1-shaped DataFrame |
| `public_dsa_panel` | Output 1-2-shaped DataFrame |

## Load and compute

```python
from pathlib import Path

from lic_dsf.dsa import (
    BaselineExternalBook,
    BaselinePublicBook,
    external_dsa_panel,
    public_dsa_panel,
)
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
        instruments=tuple(
            load_instruments_from_workbook(workbook, include_zero_disbursement=True)
        )
        + tuple(
            load_lc_nr_instruments_from_workbook(
                workbook, include_zero_disbursement=True
            )
        )
    ),
    inputs=load_external_debt_inputs(workbook),
)
macro = MacroDebtBook(inputs=load_macro_debt_inputs(workbook), external=ext)

ext_base = BaselineExternalBook(macro=macro, external=ext)
pub_base = BaselinePublicBook(macro=macro, external=ext)

external_dsa_panel(ext_base)
public_dsa_panel(pub_base)
```

## Panel rows (familiar indicators)

**External (`external_dsa_panel`)**

- PV of PPG external debt / GDP, / exports, / revenue
- PPG debt service / exports, / revenue
- External GFN (USD)

**Public (`public_dsa_panel`)**

- Public sector debt / GDP, PPG external debt / GDP
- PV of public debt / GDP, / revenue+grants
- Debt service / revenue+grants
- Public GFN / GDP

Book methods expose the same series individually (e.g.
`ext_base.pv_ppg_external_to_gdp()` ↔ Baseline R35 area).

## Excel cues

| Ratio | Baseline cue (approx.) |
|-------|-------------------------|
| PV PPG / GDP | R35 |
| PV PPG / exports | R36 |
| PPG DS / exports | R39 |
| PV public debt / GDP | R42 |
| Public GFN / GDP | R47 |

## Demo

[`demo/baseline_dsa.ipynb`](../demo/baseline_dsa.ipynb)

---

**Next:** [8. Stress DSA](08-stress-dsa.md)
