# Getting started

End-to-end recipe for economists who already know the LIC-DSF template.

## Install

From a local checkout:

```bash
uv sync --all-groups
```

Or as a dependency:

```bash
uv add "lic-dsf @ git+https://github.com/Teal-Insights/lic-dsf"
```

Run Python through `uv run` (or a Jupyter kernel from this environment).

## Workbook

Demos and tests use the macros-stripped template:

`data/lic-dsf-template-2025-08-12.xlsx`

Point the same loaders at **your filled country workbook** by changing the path.
Sheet layout must match the LIC-DSF template generation this library targets
(see `data/PROVENANCE.md`).

Template copyright: IMF/World Bank — [`NOTICE.md`](../NOTICE.md).

## Minimal script: Ext + Macro → Output 1-1 / 1-2

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

instruments = load_instruments_from_workbook(workbook, include_zero_disbursement=True)
lc_nr = load_lc_nr_instruments_from_workbook(workbook, include_zero_disbursement=True)
external = ExternalDebtBook(
    portfolio=PVPortfolio(instruments=tuple(instruments) + tuple(lc_nr)),
    inputs=load_external_debt_inputs(workbook),
)
macro = MacroDebtBook(
    inputs=load_macro_debt_inputs(workbook),
    external=external,
)

ext_base = BaselineExternalBook(macro=macro, external=external)
pub_base = BaselinePublicBook(macro=macro, external=external)

out_1_1 = external_dsa_panel(ext_base)  # Output 1-1 shape
out_1_2 = public_dsa_panel(pub_base)  # Output 1-2 shape
```

`include_zero_disbursement=True` keeps empty Input 4/5 slots so creditor
grouping matches Excel row structure.

## Next steps

| Goal | Doc | Demo |
|------|-----|------|
| Inspect Ext headlines / PV | [04-ext-debt-module-design.md](04-ext-debt-module-design.md) | `demo/ext_debt.ipynb` |
| Stress paths (Input 6) | [08-stress-dsa.md](08-stress-dsa.md) | `demo/stress_dsa.ipynb` |
| Mechanical risk rating | [10-risk-rating.md](10-risk-rating.md) | `demo/risk_rating.ipynb` |
| All Outputs in one place | [01-excel-map.md](01-excel-map.md) | `demo/all_outputs.ipynb` |

Quick stress sketch after the books above:

```python
from lic_dsf.pv import load_input7_residual_params
from lic_dsf.stress import (
    load_input6_standard,
    run_b1_gdp_external,
    stress_external_panel,
)

input6 = load_input6_standard(workbook)
residual = load_input7_residual_params(workbook)
stressed = run_b1_gdp_external(macro, external, input6, residual)
stress_external_panel(stressed)
```

## Caveats

- **Parity goal.** Numerics aim to match the Excel engine; treat differences as
  bugs unless a doc/demo notes an intentional approximation (e.g. some public
  stress GFN / ResFin feedback).
- **Your workbook.** Loaders expect the official sheet structure. Renamed sheets
  or older template vintages may fail or misalign years.
- **Not a replacement UI.** Panels are DataFrames — chart chrome, i18n labels,
  and VBA macros are out of scope.
- **License.** MIT for code; do not redistribute the template beyond the terms
  in `NOTICE.md`.

## Jupyter

```bash
uv run jupyter notebook demo/all_outputs.ipynb
```

Each demo resolves `REPO_ROOT` whether you start from the repo root or `demo/`.

---

**Next:** [3. PV instruments](03-pv-instruments.md)
