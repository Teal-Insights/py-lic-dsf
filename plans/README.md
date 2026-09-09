# Package boundary plans (index)

Ordered refactor plans for clearing ownership boundaries in `lic_dsf`. Do not mix formula/parity fixes into these PRs.

| # | Plan | Break | Depends on |
|---|---|---|---|
| 01 | [`01-excel-parity-differential-testing.md`](01-excel-parity-differential-testing.md) | JSON Excel-oracle corpus | — |
| 02 | [`02-output-parameter-sensitivity.md`](02-output-parameter-sensitivity.md) | Sensitivity analysis | Prefer 01 for cleared baselines |
| 03 | [`03-resfin-off-pv.md`](03-resfin-off-pv.md) | ResFin domain off `pv` | — |
| 04 | [`04-books-off-pv.md`](04-books-off-pv.md) | Ext/Dom/Macro books off `pv` | Prefer 03 first |
| 05 | [`05-compare-helpers-out-of-domain.md`](05-compare-helpers-out-of-domain.md) | `compare_*` → tests/tools | **Done** |
| 06 | [`06-shared-debt-dynamics.md`](06-shared-debt-dynamics.md) | Shared automatic debt-dynamics helper | — (small) |
| 07 | [`07-stress-internal-seams.md`](07-stress-internal-seams.md) | Stress shocks / runners / ratios | 03 |
| 08 | [`08-scenario-and-presentation.md`](08-scenario-and-presentation.md) | Scenario clarity + `output_map` / panels | Soft: after 07A |

## Suggested dependency graph

```text
03 ResFin
 ├── 04 Books off pv
 └── 07 Stress seams ── 08 Presentation / scenario
05 Compare helpers (parallel)
06 Debt-dynamics helper (parallel, small)
```

## Target end-state (packages)

```text
pv            instruments only          ← Plan 04
books         Ext / Dom / Macro         ← Plan 04
resfin        residual financing        ← Plan 03
dsa           baseline ratios (+ shared dynamics)
realism       Realism 1–4
stress        shocks + runners + ratios
scenario      customized + probability (docs-split; optional later split)
rating        CI / Chart Data / mechanical ratings
output        all Output-sheet geometry / panels
load          parsers
```

Compare/CSV oracle helpers live under **tests**, not domain packages.
