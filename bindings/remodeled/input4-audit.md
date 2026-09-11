# Input 4 reshape-to-keys audit

Prototype catalog: `bindings/remodeled/input4.bindings.yaml` (schema 1.13.0).
Original shards were not modified.

## Counts

- Original series: **211**
  - inputs.bindings.yaml: 78
  - constants.bindings.yaml: 23
  - internals-graph-coverage.bindings.yaml: 56
  - internals-rest.bindings.yaml: 54
- Original direction: input 78, internal 110, constant 23
- Remodeled series: **26**
  - semantic / named: 26
  - leftover unlifted: 0

## Cell coverage

- Original unique cells: **1054**
- Remodeled unique cells (data_range minus exclude_rows): **1291**
- Original cells missing from remodeled: **0**
- Extra cells introduced by bounding boxes: **237** (blanks and same-row neighbors are expected)

Extra cells are the bbox fill: group-header rows are excluded via `exclude_rows`,
but blank or other-direction cells on a member row stay inside the rectangle
(schema 1.13.0 has `exclude_rows`, not `exclude_cols`). Input disbursement cells
and internal disbursement cells can therefore share a row and appear as extras
on the other series.

## Grouping

Original series were grouped by `(INDICATOR, VARIANT, TABLE, layout, direction)`
and merged when members differ only by `INSTRUMENT` (and `HOLDER` where it is a
single constant on the series). Instrument labels come from original
`series_context.INSTRUMENT` (typos preserved, including `Commecial Bank`) or,
for draft row-blocks, from column B of the member rows via `value_map`.

Direction is not merged: input vs internal vs constant of the same concept stay
as separate series (`input4_disbursements` vs `input4_disbursements_internal`,
`input4_ida_scale_principal` vs `input4_ida_scale_principal_internal`).

| Remodeled id | dir | keys | orig series | orig cells | members |
|---|---|---|---:|---:|---|
| `input4_interest_rate` | input | INSTRUMENT | 22 | 22 | input4_interest_imf, input4_interest_multi1, input4_interest_multi2, input4_interest_oth_multi1, input4_interest_oth_multi2, input4_interest_oth_multi3, input4_interest_export_credit_agencies, input4_interest_pc2, … +14 |
| `input4_grace_period` | input | INSTRUMENT | 21 | 21 | input_4_grace_imf, input_4_grace_multi1, input_4_grace_multi2, input_4_grace_oth_multi1, input_4_grace_oth_multi2, input_4_grace_oth_multi3, input_4_grace_export_credit_agencies, input_4_grace_export_import_bank_of_npc, … +13 |
| `input4_loan_maturity` | input | INSTRUMENT | 21 | 21 | input_4_maturity_imf, input_4_maturity_multi1, input_4_maturity_multi2, input_4_maturity_oth_multi1, input_4_maturity_oth_multi2, input_4_maturity_oth_multi3, input_4_maturity_export_credit_agencies, input_4_maturity_export_import_bank_of_npc, … +13 |
| `input4_disbursements` | input | INSTRUMENT, TIME_PERIOD | 7 | 18 | input4_disbursements_imf, input4_disbursements_ida_regular, input4_disbursements_ida_new_40_year_credits, input4_disbursements_ida_new_regular, input4_disbursements_ida_new_blend_also_enter, input4_disbursements_ida_new_60_year_credits, input4_disbursements_multi1 |
| `input4_instrument_names` | input | INSTRUMENT | 1 | 7 | input_4_ida_instrument_names |
| `input4_blend_variant` | input | — | 1 | 1 | input_4_ida_blend_variant |
| `input4_blend_scale_key` | input | INSTRUMENT | 5 | 5 | input_4_blend_scale_key_ida_50y_loans, input_4_blend_scale_key_ida_sml, input_4_blend_scale_key_ida_new_40_year_credits, input_4_blend_scale_key_ida_new_regular, input_4_blend_scale_key_ida_new_60_year_credits |
| `input4_ida_scale_name` | constant | INSTRUMENT | 9 | 9 | input_4_ida_scale_ida_small_economy, input_4_ida_scale_ida_regular, input_4_ida_scale_ida_blend, input_4_ida_scale_ida_sml, input_4_ida_scale_ida_50y_loans, input_4_ida_scale_ida_new_40_year_credits, input_4_ida_scale_ida_new_regular, input_4_ida_scale_ida_new_blend_also_enter, … +1 |
| `input4_ida_scale_service_fee` | constant | INSTRUMENT | 2 | 8 | input_4_ida_scale_service_fee, input_4_ida_scale_service_fee_60y |
| `input4_ida_scale_grace` | constant | INSTRUMENT | 1 | 9 | input_4_ida_scale_grace |
| `input4_ida_scale_maturity` | constant | INSTRUMENT | 1 | 9 | input_4_ida_scale_maturity |
| `input4_ida_scale_principal` | constant | INSTRUMENT, TIME_PERIOD | 9 | 122 | input_4_ida_scale_principal_ida_small_economy, input_4_ida_scale_principal_ida_regular, input_4_ida_scale_principal_ida_blend_y6, input_4_ida_scale_principal_ida_blend_y26, input_4_ida_scale_principal_ida_sml, input_4_ida_scale_principal_ida_50y, input_4_ida_scale_principal_ida_new_regular, input_4_ida_scale_principal_ida_new_blend, … +1 |
| `input4_ida_scale_blend_fixed` | constant | — | 1 | 1 | input_4_ida_scale_blend_fixed |
| `input4_discount_rate` | internal | INSTRUMENT | 5 | 28 | in4_extfin_imf_by_row, in4_extfin_oth_multi1_by_row, in4_extfin_export_credit_agencies_by_row, in4_extfin_export_import_bank_of_npc_by_row, in4_extfin_eurobond_by_row |
| `input4_discount_rate_bonds_fx_non_residents` | internal | INSTRUMENT, HOLDER | 1 | 3 | in4_extfin_bonds_1_3_years_fx_by_row |
| `input4_discount_rate_bonds_fx_residents` | internal | INSTRUMENT, HOLDER | 1 | 3 | in4_extfin_bonds_1_3_years_fx_by_row_2 |
| `input4_terms_ida_regular` | internal | INSTRUMENT, INDICATOR | 1 | 3 | in4_extfin_ida_regular_by_indicator |
| `input4_terms_ida_and_lc` | internal | INSTRUMENT, INDICATOR | 9 | 27 | in4_extfin_ida_50y_loans, in4_extfin_ida_sml, in4_extfin_ida_new_40_year_credits, in4_extfin_ida_new_regular, in4_extfin_ida_new_blend_also_enter, in4_extfin_ida_new_60_year_credits, in4_extfin_bonds_1_3_years_lc, in4_extfin_bonds_4_7_years_lc, … +1 |
| `input4_terms_bonds_fx_non_residents` | internal | INSTRUMENT, HOLDER, INDICATOR | 3 | 9 | in4_extfin_bonds_1_3_years_fx, in4_extfin_bonds_4_7_years_fx, in4_extfin_bonds_beyond_7_years_fx |
| `input4_terms_bonds_fx_residents` | internal | INSTRUMENT, HOLDER, INDICATOR | 3 | 9 | in4_extfin_bonds_1_3_years_fx_by_indicator, in4_extfin_bonds_4_7_years_fx_by_indicator, in4_extfin_bonds_beyond_7_years_fx_by_indicator |
| `input4_disbursements_internal` | internal | INSTRUMENT, TIME_PERIOD | 33 | 570 | in4_extfin_imf_by_year, in4_extfin_ida_regular_l, in4_extfin_ida_regular_by_year, in4_extfin_ida_50y_loans_by_year, in4_extfin_ida_sml_by_year, in4_extfin_ida_new_40_year_credits_by_year, in4_extfin_ida_new_40_year_credits_o, in4_extfin_ida_new_regular_by_year, … +25 |
| `input4_ida_scale_principal_internal` | internal | INSTRUMENT, TIME_PERIOD | 50 | 125 | in4_extfin_ida_s_lending_terms_ida_regular, in4_extfin_ida_blend, in4_extfin_ida_s_lending_terms_ida_sml, in4_extfin_ida_s_lending_terms_ida_50y_loans, in4_extfin_ida_s_lending_terms_ida_regular_2, in4_extfin_ida_s_lending_terms_ida_blend, in4_extfin_ida_s_lending_terms_ida_50y_loans_2, in4_extfin_ida_s_lending_terms_ida_regular_3, … +42 |
| `input4_disbursement_totals` | internal | TIME_PERIOD | 1 | 21 | in4_extfin_ida_new_blend_team_needs_choose_floating_fixed |
| `input4_grace_period_column_header` | internal | — | 1 | 1 | in4_extfin_discount_rate |
| `input4_ida_regular_translated_name` | internal | — | 1 | 1 | in4_extfin_ida_regular |
| `input4_ida_scale_blend_fixed_interest` | internal | — | 1 | 1 | in4_extfin_ida_s_lending_terms_ida_new_blend_also_enter |

## Reclassified graph-coverage leftovers

Year-grid series whose `INDICATOR` was an instrument name (`in4_extfin_eurobond_by_year`
and siblings on L:AF of terms rows) were lifted onto `input4_disbursements_internal`
with `INSTRUMENT` from that label and `TIME_PERIOD` from header row 6.

Column E series keyed by `INDICATOR` via row labels were lifted onto
`input4_discount_rate` (and HOLDER-split FX bond shards) because E is the discount-rate column.

IDA-scale graph-coverage cells on rows 68–72 (P:BF and the AG:BF scalars) sit on the
principal-repayment schedule, not the terms/disbursement grid. They were lifted onto
`input4_ida_scale_principal_internal` with `TIME_PERIOD` header row **66** (year of loan life).
Several of those leftovers originally bound header row 6 (calendar years on the disbursement
header); that bind is a draft-pass mismatch and is called out below rather than preserved.

FX local-bond rows reuse instrument labels for non-residents (54:56) and residents (59:61).
`value_map` cannot give one INSTRUMENT key two disjoint row specs, so those blocks are
HOLDER-split series with `bind.kind: constant` for HOLDER (one fixed residency per series).

### TIME_PERIOD header_row corrections

- `input4_ida_scale_principal_internal`: original [6, 66] → remodeled `66`. IDA scale principal uses year-of-loan-life headers on row 66; graph-coverage leftovers were bound to disbursement years on row 6.

### Measure dtype unifications

- `input4_disbursements_internal`: original ['float', 'int'] → `float` (amounts; int vs float was a draft split).

### Input domains

Grace period members all share `between: {min: 0, max: 50}`; loan maturity members
all share `between: {min: 0, max: 80}`. Those domains are preserved on the merged
input series. Interest and disbursement members had no domain.

## Unique one-offs (not merged)

- `input4_blend_variant` — D16 floating/fixed control for IDA NEW Blend.
- `input4_grace_period_column_header` — G6 column header (original id `in4_extfin_discount_rate`).
- `input4_ida_scale_blend_fixed` — C74 fixed-blend label.
- `input4_ida_regular_translated_name` — D11 translated name.
- `input4_ida_scale_blend_fixed_interest` — D74 `#N/A` placeholder (VARIANT `fixed`).
- `input4_disbursement_totals` — L8:AF8 total disbursements by year (not an instrument row).

## Leftover unlifted

None.

## Extra cells

Bounding-box extras by remodeled series (cells in `data_range` minus `exclude_rows`
that were not in any original Input 4 series). Blanks and same-row neighbors of
sparse principal/disbursement shards dominate.

| Series | remodeled cells | extras vs original |
|---|---:|---:|
| `input4_ida_scale_principal` | 440 | 222 |
| `input4_ida_scale_principal_internal` | 220 | 89 |

Sample of 20 extra addresses (of 237):

- AA70
- AA75
- AB70
- AB75
- AC70
- AD70
- AE70
- AF70
- AG70
- AH70
- AH74
- AI70
- AI74
- AJ70
- AJ74
- AK70
- AK74
- AL70
- AL74
- AM69
