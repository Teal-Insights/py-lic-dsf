# PV_Base remodel audit

Prototype reshape-to-keys pass for `PV_Base` and `PV_Base-add.cost.mkt`.
Original catalogs: `internals-pv-base.bindings.yaml` (618),
`constants.bindings.yaml` (84 PV_Base + 2 add.cost.mkt),
`internals-graph-coverage.bindings.yaml` (74 PV_Base + 14 add.cost.mkt),
`inputs.bindings.yaml` (1).

## Counts

- Original series: **793**
  - constants.bindings.yaml: 86
  - inputs.bindings.yaml: 1
  - internals-graph-coverage.bindings.yaml: 88
  - internals-pv-base.bindings.yaml: 618
- Remodeled series: **78**
- Lifted groups (one series each): **62**
- Passthrough series: **16**
- Headline unit-loan / new-loan output copies: **544 → 32** (9 discount + 7 output indicators; 28 instruments + 6 FX `*_fx`)

## Cell coverage

- Original unique cells: **17877**
- Remodeled unique cells: **21989**
- Original ⊆ remodeled: **True**
- Missing original cells: **0**
- Extra remodeled cells: **4112**

Extra cells are bbox fill on member rows: unit-loan and output rows have ragged right edges (long-maturity IDA windows vs shorter commercial rows). `exclude_rows` carves the inter-block separators; it cannot drop trailing blanks on a member row (`exclude_columns` would drop original cells of wider members).

### Largest bounding-rectangle extras

| id | members | orig cells | remodeled | extras | on member rows | hole rows |
|---|---:|---:|---:|---:|---:|---:|
| `pv_base_output_new_forex_borrowing_gross_usd` | 28 | 869 | 1708 | 839 | 839 | 690 |
| `pv_base_output_cumulative` | 28 | 869 | 1708 | 839 | 839 | 690 |
| `pv_base_discount_amortization` | 28 | 1238 | 1708 | 470 | 470 | 690 |
| `pv_base_discount_debt_stock` | 28 | 1210 | 1680 | 470 | 470 | 690 |
| `pv_base_discount_interest` | 28 | 1210 | 1680 | 470 | 470 | 690 |
| `pv_base_discount_total_debt_service` | 28 | 1210 | 1680 | 470 | 470 | 690 |
| `pv_base_block_index` | 26 | 1130 | 1586 | 456 | 456 | 624 |
| `pv_base_discount_repayment_schedule` | 5 | 238 | 305 | 67 | 67 | 143 |

## TIME_PERIOD header_row unification

Output blocks copy projection years onto a per-instrument header row (IMF row 21, IDA regular row 63, …). Discount schedules already share row 7. Remodeled output series read years from the first block header (PV_Base row 21; add.cost.mkt row 2).

| id | original header_row | remodeled |
|---|---|---:|
| `pv_base_constant_output_interest` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_constant_output_interest_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_amortization` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_amortization_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_interest` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_interest_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_new_forex_borrowing_gross_usd` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_new_forex_borrowing_gross_usd_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_pv_of_debt` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_pv_of_debt_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_stock_of_new_forex_debt_in_usd` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_stock_of_new_forex_debt_in_usd_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_total_debt_service_in_usd` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_total_debt_service_in_usd_fx` | [764, 790, 816, 842, 868, 894] | 21 |
| `pv_base_output_cumulative` | [21, 63, 89, 114, 138, 162, 186, 210, 244, 270, 296, 322, 348, 374, 400, 426, 452, 478, 504, 530, 556, 582, 608, 634, 660, 686, 712, 738] | 21 |
| `pv_base_output_cumulative_fx` | [764, 790, 816, 842, 868, 894] | 21 |

## Lifted series (id → keys)

| id | n | dir | layout | TABLE | INDICATOR | keys |
|---|---:|---|---|---|---|---|
| `pv_base_block_index` | 26 | internal | series | `pv_base.block_index` | schedule_index | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_block_index_fx` | 6 | internal | series | `pv_base.block_index` | schedule_index | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_block_labels` | 28 | internal | series | `pv_base.block_labels` | block_labels | `INSTRUMENT, INDICATOR` |
| `pv_base_block_labels_fx` | 6 | internal | series | `pv_base.block_labels` | block_labels | `INSTRUMENT, HOLDER, INDICATOR` |
| `pv_base_constant_discount_schedule_period` | 1 | constant | scalar | `pv_base.discount_schedule` | Schedule period | `INSTRUMENT` |
| `pv_base_constant_output_interest` | 28 | constant | series | `pv_base.new_loan_output` | Interest | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_constant_output_interest_fx` | 6 | constant | series | `pv_base.new_loan_output` | Interest | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_amortization` | 28 | internal | series | `pv_base.discount_schedule` | Amortization | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_amortization_fx` | 6 | internal | series | `pv_base.discount_schedule` | Amortization | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_debt_stock` | 28 | internal | series | `pv_base.discount_schedule` | Debt stock | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_debt_stock_fx` | 6 | internal | series | `pv_base.discount_schedule` | Debt stock | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_interest` | 28 | internal | series | `pv_base.discount_schedule` | Interest | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_interest_fx` | 6 | internal | series | `pv_base.discount_schedule` | Interest | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_post_grace_cumulative` | 28 | internal | series | `pv_base.discount_schedule` | post-grace cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_post_grace_cumulative_fx` | 6 | internal | series | `pv_base.discount_schedule` | post-grace cumulative | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_post_maturity_cumulative` | 28 | internal | series | `pv_base.discount_schedule` | post-maturity cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_post_maturity_cumulative_fx` | 6 | internal | series | `pv_base.discount_schedule` | post-maturity cumulative | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_pv_of_debt` | 28 | internal | series | `pv_base.discount_schedule` | PV of debt | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_pv_of_debt_fx` | 6 | internal | series | `pv_base.discount_schedule` | PV of debt | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_repayment_schedule` | 5 | internal | series | `pv_base.discount_schedule` | Repayment schedule | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_schedule_period` | 1 | internal | series | `pv_base.discount_schedule` | Schedule period | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_selected_instrument` | 2 | internal | scalar | `pv_base.discount_schedule` | Selected instrument | `INSTRUMENT` |
| `pv_base_discount_t_g_0` | 28 | internal | series | `pv_base.discount_schedule` | t-g>0 | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_t_g_0_fx` | 6 | internal | series | `pv_base.discount_schedule` | t-g>0 | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_t_m_condition` | 28 | internal | series | `pv_base.discount_schedule` | t-m condition | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_t_m_condition_fx` | 6 | internal | series | `pv_base.discount_schedule` | t-m condition | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_discount_total_debt_service` | 28 | internal | series | `pv_base.discount_schedule` | Total debt service | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_discount_total_debt_service_fx` | 6 | internal | series | `pv_base.discount_schedule` | Total debt service | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_ida_scale_name` | 9 | constant | scalar | `pv_base.ida_scale` | scale_name | `INSTRUMENT` |
| `pv_base_ida_scale_short_name` | 5 | constant | scalar | `pv_base.ida_scale` | short_name | `INSTRUMENT` |
| `pv_base_ida_terms_repayment_schedule` | 9 | internal | series | `pv_base.ida_terms` | Repayment schedule | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_input_output_cumulative` | 1 | input | series | `pv_base.new_loan_output` | cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_instrument_title` | 5 | internal | scalar | `pv_base.instrument_title` | instrument_name | `INSTRUMENT` |
| `pv_base_opening_percent_of_face` | 28 | constant | scalar | `pv_base.opening_stock` | percent_of_face | `INSTRUMENT` |
| `pv_base_opening_percent_of_face_fx` | 6 | constant | scalar | `pv_base.opening_stock` | percent_of_face | `INSTRUMENT, HOLDER` |
| `pv_base_output_amortization` | 28 | internal | series | `pv_base.new_loan_output` | Amortization | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_amortization_fx` | 6 | internal | series | `pv_base.new_loan_output` | Amortization | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_output_cumulative` | 28 | internal | series | `pv_base.new_loan_output` | cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_cumulative_fx` | 6 | internal | series | `pv_base.new_loan_output` | cumulative | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_output_interest` | 28 | internal | series | `pv_base.new_loan_output` | Interest | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_interest_fx` | 6 | internal | series | `pv_base.new_loan_output` | Interest | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_output_new_forex_borrowing_gross_usd` | 28 | internal | series | `pv_base.new_loan_output` | New forex borrowing (gross, USD) | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_new_forex_borrowing_gross_usd_fx` | 6 | internal | series | `pv_base.new_loan_output` | New forex borrowing (gross, USD) | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_output_projection_year` | 1 | internal | series | `pv_base.new_loan_output` | Projection year | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_pv_of_debt` | 28 | internal | series | `pv_base.new_loan_output` | PV of debt | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_pv_of_debt_fx` | 6 | internal | series | `pv_base.new_loan_output` | PV of debt | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_output_stock_of_new_forex_debt_in_usd` | 28 | internal | series | `pv_base.new_loan_output` | Stock of new forex debt (in USD) | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_stock_of_new_forex_debt_in_usd_fx` | 6 | internal | series | `pv_base.new_loan_output` | Stock of new forex debt (in USD) | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_output_total_debt_service_in_usd` | 28 | internal | series | `pv_base.new_loan_output` | Total debt service (in USD) | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_output_total_debt_service_in_usd_fx` | 6 | internal | series | `pv_base.new_loan_output` | Total debt service (in USD) | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `pv_base_add_cost_mkt_discount_interest_rate` | 5 | internal | scalar | `pv_base_add_cost_mkt.discount_schedule` | Interest rate | `INSTRUMENT` |
| `pv_base_add_cost_mkt_discount_post_grace_cumulative` | 5 | internal | series | `pv_base_add_cost_mkt.discount_schedule` | post-grace cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_discount_post_maturity_cumulative` | 5 | internal | series | `pv_base_add_cost_mkt.discount_schedule` | post-maturity cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_discount_t_g_0` | 5 | internal | series | `pv_base_add_cost_mkt.discount_schedule` | t-g>0 | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_discount_t_m_condition` | 5 | internal | series | `pv_base_add_cost_mkt.discount_schedule` | t-m condition | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_grace` | 5 | internal | scalar | `pv_base_add_cost_mkt.block_labels` | Grace | `INSTRUMENT` |
| `pv_base_add_cost_mkt_maturity` | 5 | internal | scalar | `pv_base_add_cost_mkt.block_labels` | Maturity | `INSTRUMENT` |
| `pv_base_add_cost_mkt_output_amortization` | 5 | internal | series | `pv_base_add_cost_mkt.new_loan_output` | Amortization | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_output_cumulative` | 5 | internal | series | `pv_base_add_cost_mkt.new_loan_output` | cumulative | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_output_interest` | 5 | internal | series | `pv_base_add_cost_mkt.new_loan_output` | Interest | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_output_new_forex_borrowing_gross_usd` | 5 | internal | series | `pv_base_add_cost_mkt.new_loan_output` | New forex borrowing (gross, USD) | `INSTRUMENT, TIME_PERIOD` |
| `pv_base_add_cost_mkt_output_stock_of_new_forex_debt_in_usd` | 5 | internal | series | `pv_base_add_cost_mkt.new_loan_output` | Stock of new forex debt (in USD) | `INSTRUMENT, TIME_PERIOD` |

## Holder split

FX local bonds reuse the same `INSTRUMENT` string for non-residents and residents. A single `INSTRUMENT` value_map cannot name both rows without colliding, and filling a dummy `HOLDER` for IMF/IDA would invent a key. Those copies are a second series (`*_fx`) keyed by `INSTRUMENT` + `HOLDER`. Original holder strings are preserved (`non-residents` / `residents` on internals; `non_residents` / `residents` on opening-stock constants).

## Graph-coverage leftovers

Draft leftovers without `TABLE` were grouped by geometry, not by the instrument name that the extractor stuffed into `INDICATOR`:

- `pv_base_block_labels` — column B four-row `Grace …` labels (`row_label` on A).
- `pv_base_block_index` — year-grid row three above each unit-loan `Debt stock`.
- `pv_base_instrument_title` — column A IDA instrument titles.
- `pv_base_add_cost_mkt_grace` / `_maturity` — column B scalars on the shock sheet.

## Passthrough (not lifted)

| id | orig id | dir | TABLE | INDICATOR | reason |
|---|---|---|---|---|---|
| `pv_base_add_cost_mkt_opening_percent_of_face` | `pv_base_add_cost_mkt_opening` | constant | `pv_base_add_cost_mkt.opening_stock` | percent_of_face | no INSTRUMENT |
| `pv_base_add_cost_mkt_opening_stock_percent_of_face` | `pv_base_add_cost_mkt_seed` | constant | `pv_base_add_cost_mkt.opening_stock` | percent_of_face | no INSTRUMENT |
| `pv_base_add_cost_mkt_or` | `pv_base_add_cost_mkt_or` | internal | `` |  | graph leftover / no lift family |
| `pv_base_add_cost_mkt_pb_baseline` | `pv_base_add_cost_mkt_pb_baseline` | internal | `` | PB - baseline | graph leftover / no lift family |
| `pv_base_add_cost_mkt_shock` | `pv_base_add_cost_mkt_shock` | internal | `` | - shock | graph leftover / no lift family |
| `pv_base_add_cost_mkt_shock_addition_nominal_interest_payments_on_external_debt` | `pv_base_add_cost_mkt_shock_addition_nominal_interest_payments_on_external_debt` | internal | `pv_base_add_cost_mkt.market_financing_shock` | Addition nominal interest payments on external debt | no INSTRUMENT |
| `pv_base_add_cost_mkt_shock_average` | `pv_base_add_cost_mkt_shock_average` | internal | `pv_base_add_cost_mkt.market_financing_shock` | Average | no INSTRUMENT |
| `pv_base_add_cost_mkt_shock_deviation_from_baseline` | `pv_base_add_cost_mkt_shock_deviation_from_baseline` | internal | `pv_base_add_cost_mkt.market_financing_shock` | Deviation from baseline | no INSTRUMENT |
| `pv_base_add_cost_mkt_shock_increase_in_borrowing_costs` | `pv_base_add_cost_mkt_shock_increase_in_borrowing_costs` | internal | `pv_base_add_cost_mkt.market_financing_shock` | Increase in borrowing costs | no INSTRUMENT |
| `pv_base_add_cost_mkt_shock_schedule_period` | `pv_base_add_cost_mkt_shock_schedule_period` | internal | `pv_base_add_cost_mkt.market_financing_shock` | Schedule period | no INSTRUMENT |
| `pv_base_add_cost_mkt_whichever_lower` | `pv_base_add_cost_mkt_whichever_lower` | internal | `` |  | graph leftover / no lift family |
| `pv_base_grace_ida_regular_by_year` | `pv_base_grace_ida_regular_by_year` | internal | `` | Grace IDA - regular | graph leftover / no lift family |
| `pv_base_ida_scale_new_product_count` | `pv_base_new_ida_product_count` | constant | `pv_base.ida_scale` | new_ida_product_count | no INSTRUMENT |
| `pv_base_ida_terms_schedule_column_index` | `pv_base_ida_terms_schedule_column_index` | internal | `pv_base.ida_terms` | Schedule column index | no INSTRUMENT |
| `pv_base_multilaterals` | `pv_base_multilaterals` | internal | `` | Multilaterals | graph leftover / no lift family |
| `pv_base_multilaterals_by_year` | `pv_base_multilaterals_by_year` | internal | `` | Multilaterals | graph leftover / no lift family |

## Rules

- Do not merge `input` / `internal` / `constant` of the same concept (year-1 output Interest leaves stay `constant`; formula years stay `internal`).
- Preserve original instrument strings, including `Commecial Bank`.
- `schema_version: 1.13.0`; `value_map` may list disjoint row specs for FX `INSTRUMENT` bands.
- `exclude_rows` uses RowSpec (`11` or `"11:17"`) for bbox holes between instrument blocks.
- Ids match `^[a-z][a-z0-9_]*$`. One YAML entry per series.

