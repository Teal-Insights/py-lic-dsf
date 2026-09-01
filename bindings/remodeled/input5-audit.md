# Input 5 remodel audit

Prototype reshape-to-keys pass for `Input 5 - Local-debt Financing`.
Original catalogs: `internals-input5.bindings.yaml` (1062),
`inputs.bindings.yaml` (41), `constants.bindings.yaml` (8),
`internals-graph-coverage.bindings.yaml` (14).

## Counts

- Original series: **1125**
- Remodeled series: **116**
- Lifted groups (one series each): **52**
- Passthrough series: **64**
- Headline vintage_output: **871 → 3** (`input5_vintage_stock`, `input5_vintage_principal`, `input5_vintage_interest`)

## Cell coverage

- Original unique cells: **13504**
- Remodeled unique cells: **22326**
- Original ⊆ remodeled: **True**
- Missing original cells: **0**
- Extra remodeled cells: **8822**

### Vintage output extras (expected triangular / trailing blanks)

| id | original members | original cells | remodeled cells | extras | of which on member rows | excluded hole rows |
|---|---:|---:|---:|---:|---:|---:|
| `input5_vintage_stock` | 310 | 3360 | 6510 | 3150 | 3150 | 41 |
| `input5_vintage_principal` | 309 | 3340 | 6489 | 3149 | 3149 | 41 |
| `input5_vintage_interest` | 252 | 2770 | 5292 | 2522 | 2522 | 31 |

Issuance year *t* occupies a lower triangle: 2024 is `I230:AC230` (stock), 2025 is `J231:AC231` (range starts one column later), and similarly for principal (`AE:AY` / `AF:AY`) and interest (`BA:BU` / `BB:BU`). The remodeled `data_range` is the bounding rectangle of all members, so cells west of the per-year start column (and, for some non-resident bands, column `AC`/`AY` past the original end) are extra blanks. No original cell is dropped. `exclude_rows` carves instrument-block separators out of the bbox; it cannot remove intra-row triangle blanks.

### Other bounding-rectangle extras

| id | extras | note |
|---|---:|---|
| `input5_internal_interest_rate_on_domestic_debt` | 54 | resident rows are originally `O:AC` (projection) while non-resident rows are `I:AC`; the one-rectangle bbox fills resident `I:N` (54 cells) that are already the **input** interest series. `exclude_columns: I:N` would drop original non-resident `I:N` cells |
| `input5_new_debt_debt_stock_on_new_debt_denominated_in_local_currency` | 1 | holes excluded via `exclude_rows`; remaining extras are blank cells on member rows inside the bbox |

## Lifted series (id → keys)

| id | n | direction | layout | TABLE | INDICATOR | keys |
|---|---:|---|---|---|---|---|
| `input5_gfn_share` | 16 | input | series | `input5.gfn_allocation` | share | `INSTRUMENT, HOLDER, VARIANT` |
| `input5_constant_grace_period` | 4 | constant | scalar | `input5.instrument_terms` | Grace period | `INSTRUMENT, HOLDER` |
| `input5_grace_period` | 7 | input | scalar | `input5.instrument_terms` | Grace period | `INSTRUMENT, HOLDER` |
| `input5_internal_grace_period` | 6 | internal | scalar | `input5.instrument_terms` | Grace period | `INSTRUMENT, HOLDER` |
| `input5_interest_rate_on_domestic_debt` | 9 | input | series | `input5.instrument_terms` | Interest rate on domestic debt | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `input5_internal_interest_rate_on_domestic_debt` | 17 | internal | series | `input5.instrument_terms` | Interest rate on domestic debt | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `input5_constant_maturity` | 4 | constant | scalar | `input5.instrument_terms` | Maturity | `INSTRUMENT, HOLDER` |
| `input5_internal_maturity` | 6 | internal | scalar | `input5.instrument_terms` | Maturity | `INSTRUMENT, HOLDER` |
| `input5_maturity` | 7 | input | scalar | `input5.instrument_terms` | Maturity | `INSTRUMENT, HOLDER` |
| `input5_instrument_terms_instrument_label` | 2 | internal | series | `input5.instrument_terms` | instrument label | `INSTRUMENT, HOLDER` |
| `input5_new_debt_debt_stock_on_new_debt_denominated_in_foreign_currency` | 1 | internal | series | `input5.new_debt` | Debt stock on NEW debt denominated in foreign currency | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_debt_stock_on_new_debt_denominated_in_local_currency` | 2 | internal | series | `input5.new_debt` | Debt stock on NEW debt denominated in local currency | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_interest_payment_on_new_debt_denominated_in_foreign_currency` | 1 | internal | series | `input5.new_debt` | Interest payment on NEW debt denominated in foreign currency | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_interest_payment_on_new_debt_denominated_in_foreign_currency_ow_short_term` | 2 | internal | series | `input5.new_debt` | Interest payment on NEW debt denominated in foreign currency / o/w short-term | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_interest_payment_on_new_debt_denominated_in_local_currency` | 1 | internal | series | `input5.new_debt` | Interest payment on NEW debt denominated in local currency | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_interest_payment_on_new_debt_denominated_in_local_currency_ow_short_term` | 1 | internal | series | `input5.new_debt` | Interest payment on NEW debt denominated in local currency / o/w short-term | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_principal_payments_on_new_debt_denominated_in_foreign_currency` | 1 | internal | series | `input5.new_debt` | Principal payments on NEW debt denominated in foreign currency | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_principal_payments_on_new_debt_denominated_in_foreign_currency_ow_short_term` | 2 | internal | series | `input5.new_debt` | Principal payments on NEW debt denominated in foreign currency / o/w short-term | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_principal_payments_on_new_debt_denominated_in_local_currency` | 1 | internal | series | `input5.new_debt` | Principal payments on NEW debt denominated in local currency | `HOLDER, TIME_PERIOD` |
| `input5_new_debt_principal_payments_on_new_debt_denominated_in_local_currency_ow_short_term` | 1 | internal | series | `input5.new_debt` | Principal payments on NEW debt denominated in local currency / o/w short-term | `HOLDER, TIME_PERIOD` |
| `input5_new_issuance_denominated_in_foreign_currency_fx` | 2 | internal | series | `input5.new_issuance` | Denominated in foreign currency (FX) | `HOLDER, TIME_PERIOD` |
| `input5_new_issuance_denominated_in_local_currency_lc` | 2 | internal | series | `input5.new_issuance` | Denominated in local currency (LC) | `HOLDER, TIME_PERIOD` |
| `input5_new_issuance_financing_strategy_share` | 1 | internal | series | `input5.new_issuance` | Financing strategy share | `INSTRUMENT, HOLDER, VARIANT` |
| `input5_new_issuance_locally_issued_debt` | 2 | internal | series | `input5.new_issuance` | Locally-issued debt | `HOLDER, TIME_PERIOD` |
| `input5_new_issuance_mlt_debt` | 2 | internal | series | `input5.new_issuance` | MLT debt | `HOLDER, TIME_PERIOD` |
| `input5_new_issuance` | 17 | internal | series | `input5.new_issuance` | New issuance | `INSTRUMENT, HOLDER, TIME_PERIOD` |
| `input5_new_issuance_short_term_debt` | 2 | internal | series | `input5.new_issuance` | Short-term debt | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_interest_payment_on_old_debt_denominated_in_foreign_currency` | 2 | internal | series | `input5.old_debt` | Interest payment on OLD debt denominated in foreign currency | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_interest_payment_on_old_debt_denominated_in_local_currency` | 2 | internal | series | `input5.old_debt` | Interest payment on OLD debt denominated in local currency | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_outstanding_from_old_debt_in_foreign_currency` | 2 | internal | series | `input5.old_debt` | Outstanding from OLD debt in foreign currency | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_outstanding_from_old_debt_in_foreign_currency_usd` | 2 | internal | series | `input5.old_debt` | Outstanding from OLD debt in foreign currency (USD) | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_outstanding_from_old_debt_in_local_currency` | 2 | internal | series | `input5.old_debt` | Outstanding from OLD debt in local currency | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_principal_payments_on_old_debt_denominated_in_foreign_currency` | 2 | internal | series | `input5.old_debt` | Principal payments on OLD debt denominated in foreign currency | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_principal_payments_on_old_debt_denominated_in_foreign_currency_usd` | 2 | internal | series | `input5.old_debt` | Principal payments on OLD debt denominated in foreign currency (USD) | `HOLDER, TIME_PERIOD` |
| `input5_old_debt_principal_payments_on_old_debt_denominated_in_local_currency` | 2 | internal | series | `input5.old_debt` | Principal payments on OLD debt denominated in local currency | `HOLDER, TIME_PERIOD` |
| `input5_residual_terms_average_grace_period_on_new_debt` | 1 | internal | series | `input5.residual_terms` | Average grace period on new debt | `INSTRUMENT, TIME_PERIOD` |
| `input5_residual_terms_average_grace_period_on_new_debt_average` | 1 | internal | scalar | `input5.residual_terms` | Average grace period on new debt | `INSTRUMENT` |
| `input5_residual_terms_average_grace_period_on_new_debt_rounded_average` | 1 | internal | scalar | `input5.residual_terms` | Average grace period on new debt | `INSTRUMENT` |
| `input5_residual_terms_average_maturity_of_new_debt` | 1 | internal | series | `input5.residual_terms` | Average maturity of new debt | `INSTRUMENT, TIME_PERIOD` |
| `input5_residual_terms_average_maturity_of_new_debt_average` | 1 | internal | scalar | `input5.residual_terms` | Average maturity of new debt | `INSTRUMENT` |
| `input5_residual_terms_average_maturity_of_new_debt_rounded_average` | 1 | internal | scalar | `input5.residual_terms` | Average maturity of new debt | `INSTRUMENT` |
| `input5_residual_terms_average_nominal_interest_rate_on_new_debt` | 2 | internal | series | `input5.residual_terms` | Average nominal interest rate on new debt | `INSTRUMENT, TIME_PERIOD` |
| `input5_residual_terms_average_real_interest_rate_on_new_debt` | 2 | internal | series | `input5.residual_terms` | Average real interest rate on new debt | `INSTRUMENT, TIME_PERIOD` |
| `input5_residual_terms_average_real_interest_rate_on_new_debt_average` | 2 | internal | scalar | `input5.residual_terms` | Average real interest rate on new debt | `INSTRUMENT` |
| `input5_residual_terms_gdp_deflator` | 2 | internal | series | `input5.residual_terms` | GDP deflator | `INSTRUMENT, TIME_PERIOD` |
| `input5_vintage_interest` | 252 | internal | series | `input5.vintage_output` | Interest Payments | `INSTRUMENT, HOLDER, ISSUANCE_YEAR, TIME_PERIOD` |
| `input5_vintage_principal` | 309 | internal | series | `input5.vintage_output` | Principal Payments | `INSTRUMENT, HOLDER, ISSUANCE_YEAR, TIME_PERIOD` |
| `input5_vintage_stock` | 310 | internal | series | `input5.vintage_output` | Stock of debt | `INSTRUMENT, HOLDER, ISSUANCE_YEAR, TIME_PERIOD` |
| `input5_vintage_terms` | 15 | internal | matrix | `input5.vintage_terms` |  | `INSTRUMENT, HOLDER, ISSUANCE_YEAR, INDICATOR` |
| `input5_vintage_instrument_label` | 6 | internal | series | `input5.vintage_terms` | instrument label | `INSTRUMENT, HOLDER, ISSUANCE_YEAR` |
| `input5_vintage_instrument_title` | 5 | internal | scalar | `input5.vintage_terms` | instrument label | `INSTRUMENT, HOLDER` |
| `input5_vintage_issuance_year` | 15 | internal | series | `input5.vintage_terms` | issuance year | `INSTRUMENT, HOLDER, ISSUANCE_YEAR` |

## Inputs vs internals (same INDICATOR, not smashed)

| INDICATOR | TABLE | input id | internal id |
|---|---|---|---|
| Interest rate on domestic debt | `input5.instrument_terms` | `input5_interest_rate_on_domestic_debt` | `input5_internal_interest_rate_on_domestic_debt` |
| Grace period | `input5.instrument_terms` | `input5_grace_period` | `input5_internal_grace_period` |
| Maturity | `input5.instrument_terms` | `input5_maturity` | `input5_internal_maturity` |

Constants for T-bill grace/maturity (`input5_constant_grace_period`, `input5_constant_maturity`) stay on `constant: {}` and are not merged with the input or internal series of the same INDICATOR.

Merged inputs expose a single setter `set_<id>` (e.g. `set_input5_gfn_share`, `set_input5_grace_period`).

## Issuance-year series

Kept `input5_vintage_issuance_year` as a published series (column B of each vintage block). Those cells are the ISSUANCE_YEAR `row_label` source for `input5_vintage_stock` / `_principal` / `_interest` and `input5_vintage_terms`. Dropping the series would lose column-B cells from the inventory because row_label sources are not in those series' `data_range`. The observation *is* the year, so the key is `[INSTRUMENT, HOLDER, ISSUANCE_YEAR]` (ISSUANCE_YEAR via `data_cell`, same as the original per-block series) — `[INSTRUMENT, HOLDER]` alone would collide across the 21 vintage rows.

## Groups not lifted

| original id | direction | layout | TABLE | INDICATOR | reason |
|---|---|---|---|---|---|
| `in5_lcfin_central_bank_financing` | internal | scalar | `None` | Central bank financing | graph-coverage / no TABLE |
| `in5_lcfin_t_bills_denominated_in_lc` | internal | scalar | `None` | T-bills (denominated in local currency) | graph-coverage / no TABLE |
| `in5_lcfin_t_bills_denominated_in_fx` | internal | scalar | `None` | T-bills (denominated in foreign currency) | graph-coverage / no TABLE |
| `in5_lcfin_bonds_1_3_years_lc` | internal | scalar | `None` | Bonds (1 to 3 years)-LC | graph-coverage / no TABLE |
| `in5_lcfin_bonds_4_7_years_lc` | internal | scalar | `None` | Bonds (4 to 7 years)-LC | graph-coverage / no TABLE |
| `in5_lcfin_bonds_beyond_7_years_lc` | internal | scalar | `None` | Bonds (beyond 7 years)-LC | graph-coverage / no TABLE |
| `in5_lcfin_bonds_1_3_years_fx` | internal | scalar | `None` | Bonds (1 to 3 years)-FX | graph-coverage / no TABLE |
| `in5_lcfin_bonds_4_7_years_fx` | internal | scalar | `None` | Bonds (4 to 7 years)-FX | graph-coverage / no TABLE |
| `in5_lcfin_bonds_beyond_7_years_fx` | internal | scalar | `None` | Bonds (beyond 7 years)-FX | graph-coverage / no TABLE |
| `in5_lcfin_average_real_interest_rate_new_debt` | internal | scalar | `None` | Average real interest rate on new debt | graph-coverage / no TABLE |
| `in5_lcfin_domestic_st_debt_average_real_interest_rate_new_debt` | internal | scalar | `None` | Average real interest rate on new debt | graph-coverage / no TABLE |
| `in5_lcfin_debt_dynamics_calculations_per_debt_types` | internal | scalar | `None` | Debt dynamics calculations per debt types | graph-coverage / no TABLE |
| `in5_lcfin_economic_indicators_debt_dynamics_calculations_per_debt_types` | internal | scalar | `None` | Debt dynamics calculations per debt types | graph-coverage / no TABLE |
| `in5_lcfin_economic_indicators_debt_dynamics_calculations_per_debt_types_2` | internal | scalar | `None` | Debt dynamics calculations per debt types | graph-coverage / no TABLE |
| `input5_public_gfns_other_adjustment` | input | series | `input5.public_gfns` | (11) Other adjustment (including disbursements / debt service associated with SoEs) - when users want to remove impacts of SoEs' debt on a government's domestic borrowing | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_1_primary_deficit` | internal | series | `input5.public_gfns` | (1) Primary deficit | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_10_drawdown_of_reserves_to_repay_the_imf` | internal | series | `input5.public_gfns` | (10) Drawdown of reserves to repay the IMF | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_12_domestic_financing` | internal | series | `input5.public_gfns` | (12) Domestic financing | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_2_debt_services_from_existing_debt_domestic_including_st_debt_from_previous_year` | internal | series | `input5.public_gfns` | (2) Debt services from existing debt / Domestic (including ST debt from previous year) | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_2_debt_services_from_existing_debt_external_debt_mlt` | internal | series | `input5.public_gfns` | (2) Debt services from existing debt / External debt (MLT) | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_2_debt_services_from_existing_debt_o_w_imf` | internal | series | `input5.public_gfns` | (2) Debt services from existing debt / o/w: IMF | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_2_debt_services_from_existing_debt` | internal | series | `input5.public_gfns` | (2) Debt services from existing debt | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_3_debt_services_from_new_debt_domestic_including_st_debt_from_previous_year` | internal | series | `input5.public_gfns` | (3) Debt services from new debt / Domestic (including ST debt from previous year) | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_3_debt_services_from_new_debt_external_debt_mlt` | internal | series | `input5.public_gfns` | (3) Debt services from new debt / External debt (MLT) | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_3_debt_services_from_new_debt_o_w_imf` | internal | series | `input5.public_gfns` | (3) Debt services from new debt / o/w: IMF | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_3_debt_services_from_new_debt` | internal | series | `input5.public_gfns` | (3) Debt services from new debt | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_4_debt_services_from_st_external_debt` | internal | series | `input5.public_gfns` | (4) Debt services from ST external debt | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_5_other_debt_creating_or_reducing_flows` | internal | series | `input5.public_gfns` | (5) Other debt creating or reducing flows | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_6_public_gfns` | internal | series | `input5.public_gfns` | (6) Public GFNs | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_7_external_financing_mlt_o_w_imf` | internal | series | `input5.public_gfns` | (7) External financing (MLT) / o/w: IMF | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_7_external_financing_mlt_excluding_locally_issued_debt` | internal | series | `input5.public_gfns` | (7) External financing (MLT)- excluding locally-issued debt | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_8_external_financing_st_excluding_locally_issued_debt` | internal | series | `input5.public_gfns` | (8) External financing (ST) - excluding locally-issued debt | public GFN line item (already one series per indicator) |
| `in5_input5_public_gfns_t_9_changes_in_liquid_assets` | internal | series | `input5.public_gfns` | (9) Changes in liquid assets | public GFN line item (already one series per indicator) |
| `in5_input5_instrument_terms_assumptions_header` | internal | scalar | `input5.instrument_terms` | Assumptions on domestic financial instruments | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_controls_blue_cells_note` | internal | scalar | `input5.controls` | Blue cells are populated automatically | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_old_debt_debt_service_from_old_debt_2` | internal | series | `input5.old_debt` | Debt service from OLD debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_debt_debt_services_from_new_debt_2` | internal | series | `input5.new_debt` | Debt services from NEW debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_controls_definition_of_external_domestic_debt` | internal | scalar | `input5.controls` | Definition of external/domestic debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `input_5_domestic_financing_source` | input | scalar | `input5.gfn_allocation` | Domestic financing (from macro-framework: 0, input here: 1) | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_issuance_domestic_residual_financing_to_close_gap` | internal | series | `input5.new_issuance` | Domestic residual financing to close gap | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_issuance_gfns_to_be_financed_with_domestic_debt` | internal | series | `input5.new_issuance` | GFNs to be financed with domestic debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_instrument_terms_grace_period_header` | internal | scalar | `input5.instrument_terms` | Grace period | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_debt_interest_payment_on_new_debt_2` | internal | series | `input5.new_debt` | Interest payment on NEW debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_old_debt_interest_payment_on_old_debt_2` | internal | series | `input5.old_debt` | Interest payment on OLD debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_summary_interest_payment` | internal | series | `input5.summary` | Interest payment | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_instrument_terms_interest_rate_header` | internal | scalar | `input5.instrument_terms` | Interest rate on domestic debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_summary_mlt` | internal | series | `input5.summary` | MLT | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_instrument_terms_maturity_header` | internal | scalar | `input5.instrument_terms` | Maturity | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_issuance_new_issuance_of_locally_issued_debt` | internal | series | `input5.new_issuance` | NEW Issuance of locally-issued debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_macro_nominal_exchange_rate_average_lcu_usd` | internal | series | `input5.macro` | Nominal Exchange Rate -- average (LCU/USD) | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_macro_nominal_exchange_rate_end_of_period_lcu_usd` | internal | series | `input5.macro` | Nominal Exchange Rate -- end of period (LCU/USD) | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_debt_outstanding_of_new_debt_2` | internal | series | `input5.new_debt` | Outstanding of NEW debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_old_debt_outstanding_of_old_debt_2` | internal | series | `input5.old_debt` | Outstanding of OLD debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_summary_outstanding_stock` | internal | series | `input5.summary` | Outstanding stock | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_new_debt_principal_payment_on_new_debt_2` | internal | series | `input5.new_debt` | Principal payment on NEW debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_old_debt_principal_payment_on_old_debt_2` | internal | series | `input5.old_debt` | Principal payment on OLD debt | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_summary_principal_payment` | internal | series | `input5.summary` | Principal payment | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_disbursements_public_domestic_mlt_disbursements_2` | internal | series | `input5.disbursements` | Public domestic MLT disbursements | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_disbursements_public_domestic_st_disbursements_2` | internal | series | `input5.disbursements` | Public domestic ST disbursements | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_summary_short_term` | internal | series | `input5.summary` | Short-term | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_disbursements_total_public_new_domestic_disbursements_2` | internal | series | `input5.disbursements` | Total public new domestic disbursements | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_vintage_projection_years_interest` | internal | series | `input5.vintage_projection_years` | year | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_vintage_projection_years_principal` | internal | series | `input5.vintage_projection_years` | year | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |
| `in5_input5_projection_years` | internal | series | `input5.projection_years` | year | no INSTRUMENT/HOLDER/ISSUANCE_YEAR in series_context |

Public GFN line items (`input5.public_gfns`) stay one year-keyed series per indicator; they are not instrument copies. Graph-coverage scalars with no TABLE (column-A GFN labels, vintage header anchors `I222`/`AE222`/`BA222`, and `C130`/`C137` average-rate seeds) are not attached to another series' cells — mixing label/header dtypes into numeric `data_range`s would be wrong, and those cells are not members of the nearby numeric series.

## Holder strings

Original strings are preserved. Internals use `residents` / `non-residents`; GFN-share **inputs** use `residents` / `non_residents` (underscore). Those input and internal series are not smashed, so both spellings remain.

## Schema notes

- `schema_version: 1.13.0`; `concept_scheme` copied from internals-input5 (includes ISSUANCE_YEAR, HOLDER, INSTRUMENT).
- `value_map` values are a row number, a `"230:250"` range, or a list of those for disjoint bands (excel-grapher BindValueMap).
- `exclude_rows` uses the same RowSpec (`251` or `"251:253"`) for bbox holes between instrument blocks.
- Ids match `^[a-z][a-z0-9_]*$` (schema 1.13.0; stricter than the authoring prompt's mixed-case class).
- `layout: matrix` only for vintage_terms (ISSUANCE_YEAR × INDICATOR rectangle). Vintage output stays `series` with keys `[INSTRUMENT, HOLDER, ISSUANCE_YEAR, TIME_PERIOD]`.
- One YAML entry per lifted series (no shared-id shards).

