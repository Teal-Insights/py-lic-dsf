# lic-dsf

The `py-lic-dsf` library is an **unofficial** Python implementation of the [IMF/World Bank Debt Sustainability Framework for Low-Income Countries](https://www.worldbank.org/en/programs/debt-toolkit/dsf), or LIC-DSF. This library is **under active construction** and should be treated as an unstable alpha release.

Created by [Teal Insights](https://tealinsights.com/) and [Nature Finance](https://www.naturefinance.net/), `py-lic-dsf` aims to faithfully replicate the logic of the official August 12, 2025 ["New LIC-DSF template (Excel file)"](https://thedocs.worldbank.org/en/doc/f0ade6bcf85b6f98dbeb2c39a2b7770c-0360012025/original/LIC-DSF-IDA21-Template-08-12-2025-vf.xlsm) published by the World Bank.

Read the [full documentation](https://teal-insights.github.io/py-lic-dsf/) for more detail.

## Installation

Install from GitHub:

``` bash
uv add "lic-dsf @ git+https://github.com/Teal-Insights/py-lic-dsf"
```

Or from a local checkout:

```bash
uv sync --all-groups
# optional: Excel extras for contributors (see Developer Guide)
uv sync --extra excel
```


## Quick Start

Edit inputs in the LIC-DSF **Excel** workbook, save, then load in Python.
Start with [Getting started](https://teal-insights.github.io/py-lic-dsf/user-guide/getting-started.html),
then follow the output-oriented guide from
[Baseline DSA](https://teal-insights.github.io/py-lic-dsf/user-guide/baseline-dsa.html).

```python
from pathlib import Path

from lic_dsf.load import load_core
from lic_dsf.output import external_dsa_panel, public_dsa_panel

workbook = Path("data/lic-dsf-template-2025-08-12.xlsx")
macro, external, ext_base, pub_base = load_core(workbook)

external_dsa_panel(ext_base)  # Output 1-1
public_dsa_panel(pub_base)  # Output 1-2
```

Economist load packages: `load_core`, `load_domestic`, `load_stress`,
`load_rating`, `load_realism`, `load_probability`.

To compute and export all panels at once:

```python
from lic_dsf.export import to_workbook_from_path

to_workbook_from_path(workbook, "outputs/panels.xlsx")
```

This writes a new sidecar workbook; it does not overwrite the LIC-DSF
template.

## License

MIT for source code. The bundled Excel template is an IMF/World Bank work — see [`NOTICE.md`](https://github.com/Teal-Insights/py-lic-dsf/blob/main/NOTICE.md) and [`data/PROVENANCE.md`](https://github.com/Teal-Insights/py-lic-dsf/blob/main/data/PROVENANCE.md).

Created by [Teal Insights](https://tealinsights.com).
