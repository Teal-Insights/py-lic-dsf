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
| `ProbabilityAssumptions` | Probit / distribution assumptions |
| `breach_probability` / `path_breach_probabilities` | Path vs threshold |
| `probability_panel` | Output 6-shaped probability summary |
| `borderline_bands` | Near-threshold bands |

## Typical use

```python
from lic_dsf.rating import ChartDataRegistry
from lic_dsf.scenario import (
    CustomizedScenarioSpec,
    ProbabilityAssumptions,
    probability_panel,
    register_custom_path,
)

registry = ChartDataRegistry()
# Build or load a custom PV/GDP (etc.) path, then:
# register_custom_path(registry, ...)
# probability_panel(...)  # with thresholds + ProbabilityAssumptions
```

Full wiring with baseline/stress books is in
[`demo/all_outputs.ipynb`](../demo/all_outputs.ipynb) (Output 6 section).

## Excel cues

| Concept | Template |
|---------|----------|
| User-defined shock / path | Customized Scenario |
| Probability of breach | Output 6 probability block |
| Feeds mechanical rating | Chart Data custom columns |

## Demo

Primary: [`demo/all_outputs.ipynb`](../demo/all_outputs.ipynb)

---

**Next:** [Docs hub](README.md) — end of the reading path.
