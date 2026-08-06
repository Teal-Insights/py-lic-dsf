# lic-dsf

Python implementation of the IMF/World Bank **LIC-DSF** (Low-Income Country Debt
Sustainability Framework) Excel template.

This repository will grow sheet-by-sheet toward full template coverage. The first
shipped submodule is **`lic_dsf.pv`**: present-value instruments (`PV_Base`,
`PV_LC_NR`), portfolios, and workbook loaders.

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

from lic_dsf.pv import (
    PresentValueInstrument,
    PVPortfolio,
    load_instruments_from_workbook,
    load_lc_nr_instruments_from_workbook,
)

workbook = Path("data/lic-dsf-template-2025-08-12.xlsx")
instruments = load_instruments_from_workbook(workbook)
portfolio = PVPortfolio(instruments)
portfolio.new_debt_service()
```

## Layout

| Path | Contents |
|---|---|
| `src/lic_dsf/pv/` | Present-value instruments, portfolio, loaders |
| `demo/` | Notebooks (`pv`, `ext_debt`, `lc_nr`) |
| `docs/` | Design notes for Ext_Debt / PV_Base / PV↔Ext_Debt refs |
| `data/` | Bundled LIC-DSF template (see `NOTICE.md`) |
| `tests/` | Unit + workbook parity tests |

## License

MIT for source code. The bundled Excel template is an IMF/World Bank work —
see `NOTICE.md` and `data/PROVENANCE.md`.

Created by [Teal Insights](https://tealinsights.com).
