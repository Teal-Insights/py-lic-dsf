# lic-dsf

The `py-lic-dsf` library is an **unofficial** Python implementation of the [IMF/World Bank Debt Sustainability Framework for Low-Income Countries](https://www.worldbank.org/en/programs/debt-toolkit/dsf), or LIC-DSF. This library is **under active construction** and should be treated as an unstable alpha release.

Created by [Teal Insights](https://tealinsights.com/) and (Nature Finance)[https://www.naturefinance.net/], `py-lic-dsf` aims to faithfully replicate the logic of the official August 12, 2025 ["New LIC-DSF template (Excel file)"](https://thedocs.worldbank.org/en/doc/f0ade6bcf85b6f98dbeb2c39a2b7770c-0360012025/original/LIC-DSF-IDA21-Template-08-12-2025-vf.xlsm) published by the World Bank.

Read the [full documentation](https://teal-insights.github.io/py-lic-dsf/) for more detail.

## Installation

Install from GitHub:

``` bash
uv add "lic-dsf @ git+https://github.com/Teal-Insights/py-lic-dsf"
```

Or from a local checkout:

```bash
uv sync --all-groups
# optional: live-Excel oracle on Windows
uv sync --extra excel
```

## Tests

```bash
uv run pytest                          # skips live_excel (Linux CI)
LIC_DSF_EXCEL=1 uv run pytest -m live_excel   # Windows + Microsoft Excel
```

## Quick Start

Follow the [Getting Started](02-getting-started.qmd) and bookmark the [Excel Map](01-excel-map.qmd) to understand how the library maps to sheets.

```python
from pathlib import Path

from lic_dsf.dsa import (
    BaselineExternalBook,
    BaselinePublicBook,
)
from lic_dsf.output import external_dsa_panel, public_dsa_panel
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

## Repo Layout

| Path | Contents |
|---|---|
| `src/lic_dsf/pv/` | Instruments, Ext/Dom/Macro books, workbook loaders |
| `src/lic_dsf/dsa/` | Baseline sustainability ratios |
| `src/lic_dsf/output/` | Output-sheet DataFrames (panels and Excel-geometry tables) |
| `src/lic_dsf/stress/` | Input 6 stresses + residual financing |
| `src/lic_dsf/realism/` | Realism 1–4 math |
| `src/lic_dsf/rating/` | CI thresholds, Chart Data, mechanical ratings |
| `src/lic_dsf/scenario/` | Customized Scenario / Probability math |
| `docs/` | Economist-facing guides (Excel → Python) |
| `demo/` | Runnable notebooks paired with `docs/` |
| `data/` | Bundled LIC-DSF template (see `NOTICE.md`) |
| `tests/` | Unit tests; `tests/parity/` golden-master helpers (not installed); `live_excel` is Windows + Excel only |

## License

MIT for source code. The bundled Excel template is an IMF/World Bank work — see [`NOTICE.md`](https://github.com/Teal-Insights/py-lic-dsf/blob/main/NOTICE.md) and [`data/PROVENANCE.md`](https://github.com/Teal-Insights/py-lic-dsf/blob/main/data/PROVENANCE.md).

Created by [Teal Insights](https://tealinsights.com).
