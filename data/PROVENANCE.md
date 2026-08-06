# Provenance of the bundled workbook

| Field | Value |
|---|---|
| Files | `lic-dsf-template-2025-08-12.xlsm`, `lic-dsf-template-2025-08-12.xlsx` |
| What it is | The IMF/World Bank Low-Income Country Debt Sustainability Framework (LIC-DSF) template, IDA21 version |
| SHA-256 (`.xlsm`) | `3a0a0b80c7cbc95ac953f25ecae0b437129d669ceb8aeefb54ab86dc8727ea86` |
| SHA-256 (`.xlsx`) | `afb423dbfd38665aff48ab44ce1dda6ba606a38249e490d51c720259dbc893e3` |
| Obtained | August 2025, from the official LIC-DSF distribution |
| Author / rights | International Monetary Fund and World Bank (see `../NOTICE.md`) |

The `.xlsx` is a macros-stripped mirror of the same template used by
`lic_dsf.pv` workbook loaders and parity tests. Prefer the `.xlsm` when you need
the official macro-enabled artifact.

## Official sources

- World Bank, Debt Sustainability Framework (DSF): https://www.worldbank.org/en/programs/debt-toolkit/dsf
- IMF, LIC-DSF: https://www.imf.org/dsalic

## How to confirm you have the same file

```bash
shasum -a 256 data/lic-dsf-template-2025-08-12.xlsm
# expect: 3a0a0b80c7cbc95ac953f25ecae0b437129d669ceb8aeefb54ab86dc8727ea86

shasum -a 256 data/lic-dsf-template-2025-08-12.xlsx
# expect: afb423dbfd38665aff48ab44ce1dda6ba606a38249e490d51c720259dbc893e3
```
