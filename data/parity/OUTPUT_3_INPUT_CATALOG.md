# Output 3-1 / 3-2 input change catalog

Suggested single-story overlays for parity cases that exercise **Output 3-1 Stress-external** and **Output 3-2 Stress-public**. Defaults are from the bundled `lic-dsf-template-2025-08-12` template (resolved Python values).

**Write rule:** Prefer overwriting the **user** column with a constant (and the default column when Excel formulas ignore user overrides). For Input 6 standard shocks, write **C and D** on both the standalone row and the B6 combo row (see `tests.parity.presets`). For tailored sizes, write **G and H**.

**Probe tip:** Start with `catalog: output_31` or `output_32`, years `2024–2028`. One case = one row below.

---

## A. Standard stresses (Input 6) → mostly Output 3-1 (also feeds 3-2 public paths)

Sheet: `Input 6(optional)-Standard Test`

| ID | Story | Cells to set | Default → new | Hits (Excel scenarios) | Preset |
|---|---|---|---|---|---|
| S1 | Larger GDP shock | `C17`,`D17` + combo `C41`,`D41` | 1 → **2** SD | B1, B6 | `larger_gdp_shock` |
| S1b | Larger GDP shock, combo at Excel half | `C17`,`D17`=2; combo `C41`,`D41`=1 | standalone 2 / combo **1** (=D17/2) | B1 vs B6 size split | `larger_gdp_shock_standalone_only` |
| S2 | Larger primary-balance shock | `C21`,`D21` + `C47`,`D47` | 1 → **2** SD | B2, B6 | `larger_primary_balance_shock` |
| S3 | Larger exports shock | `C25`,`D25` + `C44`,`D44` | 1 → **2** SD | B3, B6 | `larger_exports_shock` |
| S4 | Larger other-flows (transfers) | `C29`,`D29` + `C50`,`D50` | 1 → **2** SD | B4, B6 | `larger_transfers_shock` |
| S5 | Larger FDI shock | `C32`,`D32` + `C53`,`D53` | 1 → **2** SD | B4/B6 FDI leg | `larger_fdi_shock` |
| S6 | Higher FX depreciation | `C38`,`D38` + combo FX `C58`,`D58` | 30% → **50%** (combo defaults track at half; dual-write 50 keeps B5/B6 aligned in mint) | B5, B6 | `higher_fx_shock` |
| S7 | Interactions off | `C8` | On → **Off** | B1–B6 interaction elasticities zero | `interactions_off` |
| S8 | Weaker FX passthrough | `G36`,`H36` | 0.3 → **0.1** | B5/B6 when interactions On | `weaker_fx_passthrough` |
| S9 | Higher inflation elasticity | `G17`,`H17` | 0.6 → **1.0** | B1/B6 with interactions On | `higher_inflation_elasticity` |
| S10 | Higher exports–GDP elasticity | `G25`,`H25` | 0.8 → **1.2** | B3/B6 with interactions On | `higher_exports_gdp_elasticity` |

Combo note: Excel combo rows are usually `standalone/2`. If you only change the standalone row, remint with live Excel and let formulas recompute combo. If you constant-patch (surgical / grapher), dual-write standalone **and** combo as in existing presets.

---

## B. Market access (Input 1) → Output 3-2 (and market-linked 3-1 rows)

Sheet: `Input 1 - Basics`

| ID | Story | Cells | Default → new | Hits | Preset |
|---|---|---|---|---|---|
| M1 | Market access off | `C27` | Yes → **No** | Public B6 / market financing paths on Output 3-2 | `market_access_off` |
| M2 | Market access on (if template ever No) | `C27` | No → **Yes** | Inverse of M1 | — |

---

## C. Tailored tests (Input 6 - Tailored) → Output 3-1 C-scenarios (and public mirrors)

Sheet: `Input 6 - Tailored Tests`

Applicability flags `C9`/`C10`/`C11` are often **formula-driven**. For parity overlays, force constants only when you intend to override applicability.

| ID | Story | Cells | Default → new | Hits | Preset |
|---|---|---|---|---|---|
| T1 | Natural disaster on + larger shock | `C9`=Yes; `G21`,`H21` | Off/10 → **Yes / 15** (% GDP) | C2 | `natural_disaster_on` |
| T2 | Larger disaster shock (force Yes) | `C9`=Yes; `G21`,`H21` | Off/10 → **Yes / 20** | C2 | `larger_disaster_shock` |
| T3 | Higher market financing cost | `G52`,`H52` | 400 → **600** bps | C4 | `higher_market_cost` |
| T4 | Higher tailored market FX | `G58`,`H58` | 15 → **25** % | C4 | `higher_market_fx` |
| T4b | Weaker tailored market FX passthrough | `K58`,`L58` | 0.3 → **0.1** | C4 deflator (not Input 6 G36) | `weaker_market_fx_passthrough` |
| T5 | Shorter market maturity cap | `G54`,`H54` | 5 → **3** years | C4 | `shorter_market_maturity_cap` |
| T5b | Lower market grace factor | `G56`,`H56` | 2/3 → **0.5** | C4 | `lower_market_grace_factor` |
| T6 | Commodity price shock more severe | `G46`,`H46` (+ derived `K26`/`L26`/`K27`/`L27`) | ≈ −0.23 → **−0.40** (GDP ppt ≈1.17→**2.0**, rev ppt ≈1.75→**3.0**) | C3 | `more_severe_commodity_price` |
| T6b | Fuel price more severe (components) | `G32`,`H32` (+ derived avg/`K26`/`K27`) | ≈ −0.31 → **−0.50** | C3 | `more_severe_fuel_price` |
| T7 | Contingent-liability size (via Input 2) | `F21`–`F24` (+ `F25` sum for Python loader) | template CL % → **×1.5** | C1 | `larger_cl_shock` |

Flags: template has C3 commodity **Yes**, C4 market **Yes**, C2 disaster **No**. Prefer T1 before T2.

---

## D. Residual financing (Input 7) → all stressed Output 3-x paths that refill gaps

Sheet: `Input 7 - Residual Financing`

Loader prefers user `J*` over `H*` when numeric. Write **both H and J** for a clean constant override.

| ID | Story | Cells | Default → new | Hits | Preset |
|---|---|---|---|---|---|
| R1 | Higher external MLT residual share | `H9`,`J9` | ≈0.43 → **0.70** | ResFin / B* / C* fill mix on 3-1 & 3-2 | `higher_resfin_external_share` |
| R2 | Higher domestic ST share | `H11`,`J11` (+ residualize `H9`/`J9`) | ≈0.34 → **0.50** | Public residual mix (3-2) | `higher_resfin_domestic_st_share` |
| R3 | Higher residual external interest | `C14`,`D14`,`E14` (E14 normally formula; write constant so cache matches) | ≈8.0% → **12%** (decimal **0.12**) | PV of residual PPG | `higher_resfin_external_interest` |
| R4 | Longer residual maturity | `C16`,`D16`,`E16` (E16 normally formula; write constant so cache matches) | 9 → **12** years | Grant element / PV | `longer_resfin_maturity` |
| R5 | Higher discount rate | `C15`,`D15`,`E15` (E15 normally formula; write constant so cache matches) | 5% → **7%** (decimal **0.07**) | Residual PV | `higher_resfin_discount` |
| R6 | Longer residual grace | `C17`,`D17`,`E17` | 4 → **6** years | Grant element / PV | `longer_resfin_grace` |
| R7 | Higher domestic MLT real rate | `H19`,`I19`,`J19` | ≈2.9% → **6%** (decimal **0.06**) | Public residual (3-2) | `higher_resfin_domestic_mlt_rate` |

Keep shares roughly adding to ~1 when changing R1/R2 together; for single-story cases change **one** share only.

---

## E. Suggested first wave (new cases)

**Landed** as case folders under `data/parity/cases/` (grapher-minted goldens):

| Priority | Case id (suggested) | Catalog row | Probe surface |
|---|---|---|---|
| 1 | `overlay-pb2-output31` | S2 | `output_31` |
| 2 | `overlay-transfers2-output31` | S4 | `output_31` |
| 3 | `overlay-fx-passthrough-low-output31` | S8 | `output_31` |
| 4 | `overlay-market-fx25-output31` | T4 | `output_31` |
| 5 | `overlay-resfin-domst50-output32` | R2 | `output_32` |
| 6 | `overlay-cl-up-output31` | T7 | `output_31` |

Existing corpus already covers: S1, S3, S6, S7, M1, T1, T3, R1.

---

## E2. Second wave (separate single-story cases)

**Landed** as one case folder per catalog row (no multi-preset combos):

| Case id | Catalog | Preset | Probe |
|---|---|---|---|
| `overlay-fdi2-output31` | S5 | `larger_fdi_shock` | `output_31` |
| `overlay-market-fx-passthrough-low-output31` | T4b | `weaker_market_fx_passthrough` | `output_31` |
| `overlay-inflation-elast-output31` | S9 | `higher_inflation_elasticity` | `output_31` |
| `overlay-exports-gdp-elast-output31` | S10 | `higher_exports_gdp_elasticity` | `output_31` |
| `overlay-resfin-rate12-output31` | R3 | `higher_resfin_external_interest` | `output_31` |
| `overlay-market-maturity3-output31` | T5 | `shorter_market_maturity_cap` | `output_31` |
| `overlay-commodity-price-severe-output31` | T6 | `more_severe_commodity_price` | `output_31` |

Still open for later single-story cases: optional public mirrors (`output_32`) of GDP/PB/market-access as **separate** case ids.

## E3. Third wave (stale-cache / shared-formula / residual-term pins)

**Landed** via grapher `FormulaEvaluator` mint:

| Case id | Catalog | Preset | Probe |
|---|---|---|---|
| `overlay-resfin-maturity12-output31` | R4 | `longer_resfin_maturity` | `output_31` |
| `overlay-resfin-discount7-output31` | R5 | `higher_resfin_discount` | `output_31` |
| `overlay-resfin-grace6-output31` | R6 | `longer_resfin_grace` | `output_31` |
| `overlay-resfin-dom-mlt-rate6-output32` | R7 | `higher_resfin_domestic_mlt_rate` | `output_32` |
| `overlay-disaster-shock20-output31` | T2 | `larger_disaster_shock` | `output_31` |
| `overlay-market-grace-factor-output31` | T5b | `lower_market_grace_factor` | `output_31` |
| `overlay-commodity-fuel-price-severe-output31` | T6b | `more_severe_fuel_price` | `output_31` |
| `overlay-gdp2-standalone-only-output31` | S1b | `larger_gdp_shock_standalone_only` | `output_31` |

Note: surgical overlays that replace a **shared-formula master** (e.g. Input 7 `D15`, `E14`, `J19`) must freeze sibling slaves to cached values — handled in `tests.parity.overlays._freeze_shared_formula_slaves`.

## F. Mint checklist for a new case

1. `cp -r` a sibling case → new folder; set `"id"` to the folder name.  
2. Set `"inputs": { "presets": ["…"] }` or raw `"overlays": […]`.  
3. Clear `oracle` / delete `expected.json`.  
4. `uv run python -m tests.parity.mint --case <id> --source grapher` (or `live`).  
5. `uv run pytest tests/test_parity_cases.py -k <id>`.

If failures concentrate on one scenario (B6, B2, C2, …), keep the case — that pin is the point.
