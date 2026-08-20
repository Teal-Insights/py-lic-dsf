# Customized scenario & probability (Output 6)

Excel analogues: **Customized Scenario** and the **Probability** approach on
**Output 6**. Custom ratio paths can be registered into Chart Data for rating;
probability tools map path-vs-threshold gaps into breach probabilities.

Package: `lic_dsf.scenario`. Input 8 SDR remains in Ext via `lic_dsf.pv`.

## What you get

| Piece | Role |
|-------|------|
| `CustomizedScenarioSpec` | Named custom path deltas / levels |
| `apply_customized_deltas` | Apply deltas to a baseline series |
| `register_custom_path` | Push a path into `ChartDataRegistry` |
| `ProbabilityAssumptions` | Borderline bandwidth (and simple Φ helper) |
| `DistressCovariates` / `distress_probability` | Excel `NORMDIST` regression (CPIA, growth, …) |
| `load_distress_covariates` | Input 3 + Imported data `H77:H81` averages |
| `breach_probability` / `path_breach_probabilities` | Simple path vs threshold Φ |
| `probability_panel` | Output 6-shaped probability summary |
| `borderline_bands` | Near-threshold bands |

## Typical use

```python
from lic_dsf.rating import ChartDataRegistry
from lic_dsf.scenario import (
    CustomizedScenarioSpec,
    load_distress_covariates,
    probability_panel,
    register_custom_path,
)

registry = ChartDataRegistry()
# Build or load a custom PV/GDP (etc.) path, then:
# register_custom_path(registry, ...)
# probability_panel(..., covariates=load_distress_covariates(workbook))
```

Full wiring with baseline/stress books is in
[`demo/output_6.ipynb`](../demo/output_6.ipynb).

## Excel cues

| Concept | Template |
|---------|----------|
| User-defined shock / path | Customized Scenario |
| Probability of distress | Output 6 / Probability approach `NORMDIST` |
| Most-extreme shock path | Chart Data `D63` (`lic_dsf.rating.most_extreme_shock_id`) |
| Historical scenario | `A1_historical_ext` |

## Demo

Primary: [`demo/output_6.ipynb`](../demo/output_6.ipynb)

---

**Next:** [Docs hub](README.md) — end of the reading path.
