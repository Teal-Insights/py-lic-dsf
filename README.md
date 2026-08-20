# lic-dsf

Python implementation of the IMF/World Bank **LIC-DSF** (Low-Income Country Debt
Sustainability Framework) Excel template.

Aimed at economists who already know the workbook: load a country file, compute
the same Ext/Macro/Baseline/stress/rating panels as DataFrames.

**Start here:** [`docs/README.md`](docs/README.md) · [`docs/01-excel-map.md`](docs/01-excel-map.md) ·
[`docs/02-getting-started.md`](docs/02-getting-started.md)

## Install

```bash
uv add "lic-dsf @ git+https://github.com/Teal-Insights/lic-dsf"
```

Or from a local checkout:

```bash
uv sync --all-groups
```

## Quick start

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

external_dsa_panel(ext_base)  # Output 1-1
public_dsa_panel(pub_base)  # Output 1-2
```

For Ext-only exploration, see the older portfolio recipe in
[`docs/03-pv-instruments.md`](docs/03-pv-instruments.md) and [`demo/ext_debt.ipynb`](demo/ext_debt.ipynb).

## Layout

| Path | Contents |
|---|---|
| `src/lic_dsf/pv/` | Instruments, Ext/Dom/Macro books, workbook loaders |
| `src/lic_dsf/dsa/` | Baseline sustainability ratios (Output 1-1 / 1-2) |
| `src/lic_dsf/stress/` | Input 6 stresses + residual financing (Output 2–3) |
| `src/lic_dsf/realism/` | Realism 1–4 / Output 4 |
| `src/lic_dsf/rating/` | CI thresholds, Chart Data, Output 5 / 7 |
| `src/lic_dsf/scenario/` | Customized Scenario / Probability / Output 6 |
| `docs/` | Economist-facing guides (Excel → Python) |
| `demo/` | Runnable notebooks paired with `docs/` |
| `data/` | Bundled LIC-DSF template (see `NOTICE.md`) |
| `tests/` | Unit tests; FormulaEvaluator differential via `pytest -m differential` |

## License

MIT for source code. The bundled Excel template is an IMF/World Bank work —
see `NOTICE.md` and `data/PROVENANCE.md`.

Created by [Teal Insights](https://tealinsights.com).
