# lic-dsf documentation (for LIC-DSF users)

Python parity layer over the IMF/World Bank **LIC-DSF** Excel template.
If you already know the workbook (Inputs, Ext/Dom/Macro, Baseline, stresses, CI,
Outputs), these pages map sheets to packages and point at runnable demos.

## 10-minute path

1. Install (from a checkout): `uv sync --all-groups`
2. Open [`02-getting-started.md`](02-getting-started.md) or run
   [`demo/all_outputs.ipynb`](../demo/all_outputs.ipynb)
3. Bookmark [`01-excel-map.md`](01-excel-map.md) for sheet → code lookup

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

Each page links to the next at the bottom.

| # | Doc | Excel analogue | Demo |
|---|-----|----------------|------|
| 1 | [01-excel-map.md](01-excel-map.md) | Full sheet map | — |
| 2 | [02-getting-started.md](02-getting-started.md) | End-to-end recipe | `all_outputs` |
| 3 | [03-pv-instruments.md](03-pv-instruments.md) | PV_Base / PV_LC_NR | `pv`, `lc_nr`, `portfolio` |
| 4 | [04-ext-debt-module-design.md](04-ext-debt-module-design.md) | Ext_Debt_Data | `ext_debt` |
| 5 | [05-dom-debt-indicators.md](05-dom-debt-indicators.md) | Dom_Debt_* | `dom_debt` |
| 6 | [06-macro-debt-bridge.md](06-macro-debt-bridge.md) | Macro-Debt_Data | `macro_debt` |
| 7 | [07-baseline-dsa.md](07-baseline-dsa.md) | Baseline / Output 1-1, 1-2 | `baseline_dsa` |
| 8 | [08-stress-dsa.md](08-stress-dsa.md) | Input 6 / B & B1 / Output 2–3 | `stress_dsa` |
| 9 | [09-realism.md](09-realism.md) | Realism / Output 4 | `realism` |
| 10 | [10-risk-rating.md](10-risk-rating.md) | CI / Chart Data / Output 5, 7 | `risk_rating` |
| 11 | [11-scenario.md](11-scenario.md) | Customized / Probability / Output 6 | `output_6` |

## License note

MIT covers the Python source. The bundled LIC-DSF template remains an IMF/World
Bank work — see [`NOTICE.md`](../NOTICE.md) and [`data/PROVENANCE.md`](../data/PROVENANCE.md).

## FormulaEvaluator differential tests

Default `uv run pytest` stays fast (`-m 'not differential'`). Cell-level parity
against `excel-grapher`'s `FormulaEvaluator` is opt-in:

```bash
uv run pytest -m differential
# or build the graph cache + CSV reports without pytest:
uv run python -m tests.differential
uv run python scripts/regenerate_graph_cache.py   # --force rebuild
```

The first graph build takes a few minutes (~100k+ nodes) and is pickled under
`.cache/dependency-graph/` (gitignored). Later runs reuse that cache.

Reports: [`data/differential/evaluator_vs_python.csv`](../data/differential/)
(`golden` = evaluator, `sut` = `lic_dsf`). Group filters:
`uv run python scripts/compare_realism1.py` and
`uv run python scripts/compare_outputs_5_7.py`.

Linux evaluator values can differ from live Excel / xlwings. This suite is
evaluator-only; known remaining identities are xfails listed in [`issues.md`](../issues.md).

---

**Next:** [1. Excel map](01-excel-map.md)
