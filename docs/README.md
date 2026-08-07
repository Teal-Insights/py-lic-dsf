# lic-dsf documentation (for LIC-DSF users)

Python parity layer over the IMF/World Bank **LIC-DSF** Excel template.
If you already know the workbook (Inputs, Ext/Dom/Macro, Baseline, stresses, CI,
Outputs), these pages map sheets to packages and point at runnable demos.

## 10-minute path

1. Install (from a checkout): `uv sync --all-groups`
2. Open [`getting-started.md`](getting-started.md) or run
   [`demo/all_outputs.ipynb`](../demo/all_outputs.ipynb)
3. Bookmark [`excel-map.md`](excel-map.md) for sheet → code lookup

Bundled template: [`data/lic-dsf-template-2025-08-12.xlsx`](../data/lic-dsf-template-2025-08-12.xlsx)
(see [`NOTICE.md`](../NOTICE.md) for IMF/World Bank provenance).

## Python mental model

| Idea | Role |
|------|------|
| **Loader** | Reads Input / sheet blocks from a `.xlsx` into typed inputs |
| **Book** | Sheet engine (`ExternalDebtBook`, `MacroDebtBook`, baseline/stress books) |
| **Panel** | Output-shaped `pandas.DataFrame` (rows ≈ Excel indicators, columns = years) |
| **Portfolio** | New MLT instruments behind Ext (`PVPortfolio`) |

Typical flow: load workbook → build Ext + Macro books → baseline / stress panels →
rating.

## Reading order

| Start here | Excel analogue | Demo |
|------------|----------------|------|
| [excel-map.md](excel-map.md) | Full sheet map | — |
| [getting-started.md](getting-started.md) | End-to-end recipe | `all_outputs` |
| [pv-instruments.md](pv-instruments.md) | PV_Base / PV_LC_NR | `pv`, `lc_nr`, `portfolio` |
| [ext-debt-module-design.md](ext-debt-module-design.md) | Ext_Debt_Data | `ext_debt` |
| [dom-debt-indicators.md](dom-debt-indicators.md) | Dom_Debt_* | `dom_debt` |
| [macro-debt-bridge.md](macro-debt-bridge.md) | Macro-Debt_Data | `macro_debt` |
| [baseline-dsa.md](baseline-dsa.md) | Baseline / Output 1-1, 1-2 | `baseline_dsa` |
| [stress-dsa.md](stress-dsa.md) | Input 6 / B & B1 / Output 2–3 | `stress_dsa` |
| [realism.md](realism.md) | Realism / Output 4 | `realism` |
| [risk-rating.md](risk-rating.md) | CI / Chart Data / Output 5, 7 | `risk_rating` |
| [scenario.md](scenario.md) | Customized / Probability / Output 6 | `all_outputs` |

## License note

MIT covers the Python source. The bundled LIC-DSF template remains an IMF/World
Bank work — see [`NOTICE.md`](../NOTICE.md) and [`data/PROVENANCE.md`](../data/PROVENANCE.md).
