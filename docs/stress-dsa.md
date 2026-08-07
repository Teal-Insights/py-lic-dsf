# Stress DSA (`lic_dsf.stress`)

Standard stress tests from Excel Input 6 / B-sheets, plus **applied residual
financing** (Input 7 → ext MLT / dom MLT / ST). Lives under **`lic_dsf.stress`**
(sibling of `lic_dsf.pv` and `lic_dsf.dsa`).

## Ownership

```text
Input 6 (shock sizes)          Input 7 (E/J value-used)
        │                              │
        ▼                              ▼
apply_*_shock(MacroDebtInputs)   ResidualFinancingParams
        │                              │
        ▼                              │
shocked MacroDebtBook                  │
        │                              │
        ├─ external gap (R86 / shortfall identity)
        │         │                    │
        │         ▼                    │
        │   ResFin ext MLT (100% for external DSA)
        │         │                    │
        ▼         ▼                    │
StressExternalBook                     │
                                       │
        ├─ public ΔGFN gap             │
        │         │                    │
        │         ▼                    ▼
        │   split_residual_financing (J9/J10/J11)
        │         │
        │         ├─ ext MLT USD
        │         ├─ dom MLT LCU
        │         └─ dom ST LCU
        │                 │
        ▼                 ▼
StressPublicBook  (B1_GDP_pub vertical slice)
```

## Package

[`src/lic_dsf/stress/`](../src/lic_dsf/stress/)

| Module | Role |
|--------|------|
| `types.py` / `workbook.py` | Input 6 params + loader |
| `shocks.py` | GDP / exports / flows / FX / combo |
| `residual_pv.py` | Gaps, share split, ext/dom/ST overlays |
| `scenario.py` | `StressExternalBook` + external runners |
| `public.py` | `StressPublicBook` + `run_b1_gdp_public` |
| `panels.py` | Output-shaped panels |

```python
from lic_dsf.pv import load_input7_residual_params
from lic_dsf.stress import (
    load_input6_standard,
    run_b1_gdp_external,
    run_b1_gdp_public,
    run_standard_external_stress,
)

input6 = load_input6_standard(path)
resfin = load_input7_residual_params(path)

ext = run_b1_gdp_external(macro, external, input6, resfin)
pub = run_b1_gdp_public(macro, external, input6, resfin)
pub.resfin.fill.external_mlt_usd
pub.resfin.fill.domestic_mlt_lcu
pub.resfin.fill.domestic_st_lcu
```

Pass ``public_gap=`` into `run_b1_gdp_public` to inject an Excel ΔGFN series
(for exact `PV_ResFin_pub` fill parity); otherwise the runner estimates GFN via
GDP-scaled baseline GFN plus ResFin feedback iterations.

## Scenarios

| Id | Shock | Excel sheet |
|----|--------|-------------|
| `B1_GDP` | Real GDP growth years 2–3 | `B1_GDP_ext` |
| `B3_Exports` | Export growth + GDP elasticity | `B3_Exports_ext` |
| `B4_OtherFlows` | Transfers / FDI to GDP | `B4_other flows_ext` |
| `B5_FX` | FX depreciation → deflator | `B5_depreciation_ext` |
| `B6_Combo` | Half-size combination | `B6_Combo_mkt_ext` |
| `B1_GDP_pub` | Same GDP shock + public ResFin | `B1_GDP_pub` / `PV_ResFin_pub` |

## Residual financing (applied)

| Leg | Role |
|-----|------|
| Ext MLT | `PresentValueInstrument` / `PV Stress` semantics |
| Dom MLT | LCU schedule (real rate + deflator), grace/maturity from Input 7 J20–J21 |
| Dom ST | One-year rollover; interest = prior stock × (ST real + deflator) |

Public split uses capped modality (B1/B5/B6): shares J9–J11 with FX conversion
for the external leg. Absolute modality is available for B2 PB shocks later.

## Out of scope (for now)

- Public B2 / B5 / B6 runners and add-cost / market interest overlays
- Tailored C* / CL / commodity / natural disaster
- Output 2–3 fan charts
- Mutating the Ext portfolio and re-stitching Macro for ResFin disbursements

Chart Data / ratings: [`lic_dsf.rating`](risk-rating.md). Realism tools:
[`lic_dsf.realism`](realism.md).