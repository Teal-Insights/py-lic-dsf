# Ext_Debt_Data ranges that reference PV_Base

Auto-generated from formula scan of `data/lic-dsf-template-2025-08-12.xlsx` (cached `data_only` values).

## Legend

| Section | Meaning |
|---------|---------|
| **external** | `PV_Base` **Output** block (new borrowing, stock, PV of debt, interest, amortization, …) |
| **internal** | `PV_Base` unit-loan / calc block (Base, debt stock, grant element, terms, …) |

- Unique Ext_Debt rows with PV_Base links: **136**
- Contiguous year ranges listed: **136**
- external ranges: **136**; internal: **0**

**Finding:** every link uses the **external (Output)** block only. Values below are what `Ext_Debt_Data` shows (same as `PV_Base` Output via `IFERROR`).

FX bond tenors appear twice (non-resident vs resident holder blocks).

## What Ext_Debt_Data uses each PV_Base metric for

Every instrument link is one of four **Output** series. Ext_Debt_Data copies them into four parallel creditor tables (same instrument list, different row bands), then rolls them into public external debt aggregates.

| PV_Base Output metric | Ext_Debt_Data band | Ext_Debt section header | Immediate roll-up | Used to calculate |
|-----------------------|--------------------|-------------------------|-------------------|-------------------|
| **Interest** | rows ~144–190 | **Interest** (row 142), under *New debt: Debt service* | Creditor-group subtotals → `Interest` total (R142) | **Total new debt service** (R140 = Interest + Amortization); **Total public debt service → of which: interest** (R396 includes R142); residual local-debt financing uses (interest+amort) for IMF; stress / baseline external DSA sheets |
| **Amortization** | rows ~194–240 | **Amortization** (row 192) | Creditor-group subtotals → `Amortization` total (R192) | **Total new debt service** (R140); **Total public debt service → of which: principal** (R395 includes R192); same IMF (interest+amort) residual path as Interest |
| **PV of debt** | rows ~281–327 | **PV of new MLT debt** (row 279) | Creditor-group subtotals → R279 | **Total PV of debt** (R391 = old MLT PV + arrears PV + **new MLT PV** + ST external + SDR PV); feeds baseline / stress external DSA PV ratios |
| **Stock of new forex debt (in USD)** | rows ~331–377 | **Nominal value of new MLT debt** (row 329) | Creditor-group subtotals → R329 | **Macro-Debt_Data** MLT public external stock (row 9 = existing MLT + arrears + **new MLT nominal**); **Nominal PPG debt check** (R393); stock/flow consistency vs macro debt |

Creditor-group subtotals inside each band (example for Interest): Multilaterals, Other Multilaterals, Official Bilaterals, Commercial, locally-issued held by non-residents, FX-denominated — then summed to the section total.

```text
PV_Base Output (per instrument)
  ├─ Interest ──────────► Ext_Debt Interest rows ──► R142 Interest
  │                                              └─► R140 Total new debt service
  │                                              └─► R396 … of which: interest
  ├─ Amortization ──────► Ext_Debt Amort rows ────► R192 Amortization
  │                                              └─► R140 / R395 … of which: principal
  ├─ PV of debt ────────► Ext_Debt PV rows ───────► R279 PV of new MLT debt
  │                                              └─► R391 Total PV of debt
  └─ Stock (nominal) ───► Ext_Debt Stock rows ────► R329 Nominal value of new MLT debt
                                                 └─► Macro-Debt_Data MLT external + R393 check
```


## Summary by instrument

| Instrument | # ranges | Sections | Ext_Debt rows | Nonzero metrics? |
|------------|---------:|----------|---------------|------------------|
| IMF | 4 | external | 144, 194, 281, 331 | no (all zero) |
| IDA - regular | 4 | external | 145, 195, 282, 332 | yes |
| IDA - 50Y loans | 4 | external | 146, 196, 283, 333 | yes |
| IDA - SML | 4 | external | 147, 197, 284, 334 | yes |
| IDA NEW 40-year credits | 4 | external | 148, 198, 285, 335 | yes |
| IDA NEW Regular | 4 | external | 149, 199, 286, 336 | yes |
| IDA NEW Blend floating | 4 | external | 150, 200, 287, 337 | yes |
| IDA NEW 60-year credits | 4 | external | 151, 201, 288, 338 | yes |
| MULTI1 | 4 | external | 152, 202, 289, 339 | no (all zero) |
| MULTI2 | 4 | external | 153, 203, 290, 340 | no (all zero) |
| OTH_MULTI1 | 4 | external | 155, 205, 292, 342 | no (all zero) |
| OTH_MULTI2 | 4 | external | 156, 206, 293, 343 | no (all zero) |
| OTH_MULTI3 | 4 | external | 157, 207, 294, 344 | no (all zero) |
| Export Credit Agencies | 4 | external | 160, 210, 297, 347 | yes |
| PC2 | 4 | external | 161, 211, 298, 348 | no (all zero) |
| PC3 | 4 | external | 162, 212, 299, 349 | no (all zero) |
| PC4 | 4 | external | 163, 213, 300, 350 | no (all zero) |
| PC5 | 4 | external | 164, 214, 301, 351 | no (all zero) |
| Export Import Bank of NPC | 4 | external | 166, 216, 303, 353 | yes |
| NPC2 | 4 | external | 167, 217, 304, 354 | no (all zero) |
| NPC3 | 4 | external | 168, 218, 305, 355 | no (all zero) |
| NPC4 | 4 | external | 169, 219, 306, 356 | no (all zero) |
| NPC5 | 4 | external | 170, 220, 307, 357 | no (all zero) |
| Eurobond | 4 | external | 172, 222, 309, 359 | yes |
| Commecial Bank | 4 | external | 173, 223, 310, 360 | yes |
| COM3 | 4 | external | 174, 224, 311, 361 | yes |
| COM4 | 4 | external | 175, 225, 312, 362 | no (all zero) |
| COM5 | 4 | external | 176, 226, 313, 363 | no (all zero) |
| Bonds (1 to 3 years)-FX | 8 | external | 183, 188, 233, 238, 320, 325, 370, 375 | no (all zero) |
| Bonds (4 to 7 years)-FX | 8 | external | 184, 189, 234, 239, 321, 326, 371, 376 | no (all zero) |
| Bonds (beyond 7 years)-FX | 8 | external | 185, 190, 235, 240, 322, 327, 372, 377 | no (all zero) |

## Detail by instrument

### IMF

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F144:BN144` | IMF | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D27:BL27` | 61 |
| `F194:BN194` | IMF | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D28:BL28` | 61 |
| `F281:BN281` | IMF | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D25:BL25` | 61 |
| `F331:BN331` | IMF | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D24:BL24` | 61 |

#### Values by Output metric

##### Interest (Ext `F144:BN144` → `PV_Base!D27:BL27`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F194:BN194` → `PV_Base!D28:BL28`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F281:BN281` → `PV_Base!D25:BL25`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F331:BN331` → `PV_Base!D24:BL24`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### IDA - regular

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F145:BN145` | IDA - regular | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D69:BL69` | 61 |
| `F195:BN195` | IDA - regular | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D70:BL70` | 61 |
| `F282:BN282` | IDA - regular | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D67:BL67` | 61 |
| `F332:BN332` | IDA - regular | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D66:BL66` | 61 |

#### Values by Output metric

##### Interest (Ext `F145:BN145` → `PV_Base!D69:BL69`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2025: **1.125**; 2026: **1.275**; 2027: **2.13523**; 2028: **2.92738**; 2029: **4.42738**; 2030: **5.92738**; 2031: **5.92738**; 2032: **5.89223**; 2033: **5.85238**; 2034: **5.78566**; 2035: **5.69418**; 2036: **5.55582** … +20 more … 2057: **1.66598**; 2058: **1.48075**; 2059: **1.29551**; 2060: **1.11028**; 2061: **0.925053**; 2062: **0.739822** _(n=61 years, 38 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 1.125 |
| 2026 | 1.275 |
| 2027 | 2.13523 |
| 2028 | 2.92738 |
| 2029 | 4.42738 |
| 2030 | 5.92738 |
| 2031 | 5.92738 |
| 2032 | 5.89223 |
| 2033 | 5.85238 |
| 2034 | 5.78566 |
| 2035 | 5.69418 |
| 2036 | 5.55582 |
| 2037 | 5.37059 |
| 2038 | 5.18536 |
| 2039 | 5.00013 |
| 2040 | 4.8149 |
| 2041 | 4.62967 |
| 2042 | 4.44444 |
| 2043 | 4.25921 |
| 2044 | 4.07398 |
| 2045 | 3.88875 |
| 2046 | 3.70351 |
| 2047 | 3.51828 |
| 2048 | 3.33305 |
| 2049 | 3.14782 |
| 2050 | 2.96259 |
| 2051 | 2.77736 |
| 2052 | 2.59213 |
| 2053 | 2.4069 |
| 2054 | 2.22167 |
| 2055 | 2.03644 |
| 2056 | 1.85121 |
| 2057 | 1.66598 |
| 2058 | 1.48075 |
| 2059 | 1.29551 |
| 2060 | 1.11028 |
| 2061 | 0.925053 |
| 2062 | 0.739822 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F195:BN195` → `PV_Base!D70:BL70`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2031: **4.6875**; 2032: **5.3125**; 2033: **8.89681**; 2034: **12.1974**; 2035: **18.4474**; 2036: **24.6974**; 2037: **24.6974**; 2038: **24.6974**; 2039: **24.6974**; 2040: **24.6974**; 2041: **24.6974**; 2042: **24.6974** … +14 more … 2057: **24.6974**; 2058: **24.6974**; 2059: **24.6974**; 2060: **24.6974**; 2061: **24.6974**; 2062: **24.6974** _(n=61 years, 32 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 4.6875 |
| 2032 | 5.3125 |
| 2033 | 8.89681 |
| 2034 | 12.1974 |
| 2035 | 18.4474 |
| 2036 | 24.6974 |
| 2037 | 24.6974 |
| 2038 | 24.6974 |
| 2039 | 24.6974 |
| 2040 | 24.6974 |
| 2041 | 24.6974 |
| 2042 | 24.6974 |
| 2043 | 24.6974 |
| 2044 | 24.6974 |
| 2045 | 24.6974 |
| 2046 | 24.6974 |
| 2047 | 24.6974 |
| 2048 | 24.6974 |
| 2049 | 24.6974 |
| 2050 | 24.6974 |
| 2051 | 24.6974 |
| 2052 | 24.6974 |
| 2053 | 24.6974 |
| 2054 | 24.6974 |
| 2055 | 24.6974 |
| 2056 | 24.6974 |
| 2057 | 24.6974 |
| 2058 | 24.6974 |
| 2059 | 24.6974 |
| 2060 | 24.6974 |
| 2061 | 24.6974 |
| 2062 | 24.6974 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F282:BN282` → `PV_Base!D67:BL67`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2024: **69.4845**; 2025: **81.0984**; 2026: **137.01**; 2027: **190.652**; 2028: **289.903**; 2029: **392.617**; 2030: **406.32**; 2031: **416.021**; 2032: **425.617**; 2033: **432.149**; 2034: **435.774**; 2035: **433.421** … +21 more … 2057: **164.106**; 2058: **146.133**; 2059: **127.446**; 2060: **108.011**; 2061: **87.789**; 2062: **66.7411** _(n=61 years, 39 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 69.4845 |
| 2025 | 81.0984 |
| 2026 | 137.01 |
| 2027 | 190.652 |
| 2028 | 289.903 |
| 2029 | 392.617 |
| 2030 | 406.32 |
| 2031 | 416.021 |
| 2032 | 425.617 |
| 2033 | 432.149 |
| 2034 | 435.774 |
| 2035 | 433.421 |
| 2036 | 424.838 |
| 2037 | 416.012 |
| 2038 | 406.93 |
| 2039 | 397.579 |
| 2040 | 387.946 |
| 2041 | 378.016 |
| 2042 | 367.775 |
| 2043 | 357.207 |
| 2044 | 346.296 |
| 2045 | 335.024 |
| 2046 | 323.375 |
| 2047 | 311.328 |
| 2048 | 298.864 |
| 2049 | 285.961 |
| 2050 | 272.599 |
| 2051 | 258.755 |
| 2052 | 244.403 |
| 2053 | 229.519 |
| 2054 | 214.075 |
| 2055 | 198.045 |
| 2056 | 181.399 |
| 2057 | 164.106 |
| 2058 | 146.133 |
| 2059 | 127.446 |
| 2060 | 108.011 |
| 2061 | 87.789 |
| 2062 | 66.7411 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F332:BN332` → `PV_Base!D66:BL66`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2024: **150**; 2025: **170**; 2026: **284.698**; 2027: **390.318**; 2028: **590.318**; 2029: **790.318**; 2030: **790.318**; 2031: **785.63**; 2032: **780.318**; 2033: **771.421**; 2034: **759.224**; 2035: **740.776** … +21 more … 2057: **197.433**; 2058: **172.735**; 2059: **148.038**; 2060: **123.34**; 2061: **98.6429**; 2062: **73.9455** _(n=61 years, 39 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 150 |
| 2025 | 170 |
| 2026 | 284.698 |
| 2027 | 390.318 |
| 2028 | 590.318 |
| 2029 | 790.318 |
| 2030 | 790.318 |
| 2031 | 785.63 |
| 2032 | 780.318 |
| 2033 | 771.421 |
| 2034 | 759.224 |
| 2035 | 740.776 |
| 2036 | 716.079 |
| 2037 | 691.381 |
| 2038 | 666.684 |
| 2039 | 641.987 |
| 2040 | 617.289 |
| 2041 | 592.592 |
| 2042 | 567.894 |
| 2043 | 543.197 |
| 2044 | 518.499 |
| 2045 | 493.802 |
| 2046 | 469.104 |
| 2047 | 444.407 |
| 2048 | 419.71 |
| 2049 | 395.012 |
| 2050 | 370.315 |
| 2051 | 345.617 |
| 2052 | 320.92 |
| 2053 | 296.222 |
| 2054 | 271.525 |
| 2055 | 246.828 |
| 2056 | 222.13 |
| 2057 | 197.433 |
| 2058 | 172.735 |
| 2059 | 148.038 |
| 2060 | 123.34 |
| 2061 | 98.6429 |
| 2062 | 73.9455 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### IDA - 50Y loans

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F146:BN146` | IDA - 50Y loans | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D95:BL95` | 61 |
| `F196:BN196` | IDA - 50Y loans | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D96:BL96` | 61 |
| `F283:BN283` | IDA - 50Y loans | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D93:BL93` | 61 |
| `F333:BN333` | IDA - 50Y loans | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D92:BL92` | 61 |

#### Values by Output metric

##### Interest (Ext `F146:BN146` → `PV_Base!D95:BL95`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F196:BN196` → `PV_Base!D96:BL96`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2036: **2.5**; 2037: **5**; 2038: **7.5**; 2039: **7.5**; 2040: **7.5**; 2041: **7.5**; 2042: **7.5**; 2043: **7.5**; 2044: **7.5**; 2045: **7.5**; 2046: **7.5**; 2047: **7.5** … +21 more … 2069: **7.5**; 2070: **7.5**; 2071: **7.5**; 2072: **7.5**; 2073: **7.5**; 2074: **7.5** _(n=61 years, 39 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 2.5 |
| 2037 | 5 |
| 2038 | 7.5 |
| 2039 | 7.5 |
| 2040 | 7.5 |
| 2041 | 7.5 |
| 2042 | 7.5 |
| 2043 | 7.5 |
| 2044 | 7.5 |
| 2045 | 7.5 |
| 2046 | 7.5 |
| 2047 | 7.5 |
| 2048 | 7.5 |
| 2049 | 7.5 |
| 2050 | 7.5 |
| 2051 | 7.5 |
| 2052 | 7.5 |
| 2053 | 7.5 |
| 2054 | 7.5 |
| 2055 | 7.5 |
| 2056 | 7.5 |
| 2057 | 7.5 |
| 2058 | 7.5 |
| 2059 | 7.5 |
| 2060 | 7.5 |
| 2061 | 7.5 |
| 2062 | 7.5 |
| 2063 | 7.5 |
| 2064 | 7.5 |
| 2065 | 7.5 |
| 2066 | 7.5 |
| 2067 | 7.5 |
| 2068 | 7.5 |
| 2069 | 7.5 |
| 2070 | 7.5 |
| 2071 | 7.5 |
| 2072 | 7.5 |
| 2073 | 7.5 |
| 2074 | 7.5 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F283:BN283` → `PV_Base!D93:BL93`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2025: **26.3355**; 2026: **53.9877**; 2027: **83.0226**; 2028: **87.1737**; 2029: **91.5324**; 2030: **96.109**; 2031: **100.914**; 2032: **105.96**; 2033: **111.258**; 2034: **116.821**; 2035: **122.662**; 2036: **126.295** … +32 more … 2069: **43.3132**; 2070: **37.9789**; 2071: **32.3778**; 2072: **26.4967**; 2073: **20.3215**; 2074: **13.8376** _(n=61 years, 50 nonzero)_


| Year | Value |
|-----:|------:|
| 2025 | 26.3355 |
| 2026 | 53.9877 |
| 2027 | 83.0226 |
| 2028 | 87.1737 |
| 2029 | 91.5324 |
| 2030 | 96.109 |
| 2031 | 100.914 |
| 2032 | 105.96 |
| 2033 | 111.258 |
| 2034 | 116.821 |
| 2035 | 122.662 |
| 2036 | 126.295 |
| 2037 | 127.61 |
| 2038 | 126.491 |
| 2039 | 125.315 |
| 2040 | 124.081 |
| 2041 | 122.785 |
| 2042 | 121.424 |
| 2043 | 119.995 |
| 2044 | 118.495 |
| 2045 | 116.92 |
| 2046 | 115.266 |
| 2047 | 113.529 |
| 2048 | 111.706 |
| 2049 | 109.791 |
| 2050 | 107.78 |
| 2051 | 105.669 |
| 2052 | 103.453 |
| 2053 | 101.126 |
| 2054 | 98.6818 |
| 2055 | 96.1159 |
| 2056 | 93.4217 |
| 2057 | 90.5928 |
| 2058 | 87.6224 |
| 2059 | 84.5036 |
| 2060 | 81.2287 |
| 2061 | 77.7902 |
| 2062 | 74.1797 |
| 2063 | 70.3887 |
| 2064 | 66.4081 |
| 2065 | 62.2285 |
| 2066 | 57.8399 |
| 2067 | 53.2319 |
| 2068 | 48.3935 |
| 2069 | 43.3132 |
| 2070 | 37.9789 |
| 2071 | 32.3778 |
| 2072 | 26.4967 |
| 2073 | 20.3215 |
| 2074 | 13.8376 |

##### Stock of new forex debt (in USD) (Ext `F333:BN333` → `PV_Base!D92:BL92`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2025: **100**; 2026: **200**; 2027: **300**; 2028: **300**; 2029: **300**; 2030: **300**; 2031: **300**; 2032: **300**; 2033: **300**; 2034: **300**; 2035: **300**; 2036: **297.5** … +32 more … 2069: **52.5**; 2070: **45**; 2071: **37.5**; 2072: **30**; 2073: **22.5**; 2074: **15** _(n=61 years, 50 nonzero)_


| Year | Value |
|-----:|------:|
| 2025 | 100 |
| 2026 | 200 |
| 2027 | 300 |
| 2028 | 300 |
| 2029 | 300 |
| 2030 | 300 |
| 2031 | 300 |
| 2032 | 300 |
| 2033 | 300 |
| 2034 | 300 |
| 2035 | 300 |
| 2036 | 297.5 |
| 2037 | 292.5 |
| 2038 | 285 |
| 2039 | 277.5 |
| 2040 | 270 |
| 2041 | 262.5 |
| 2042 | 255 |
| 2043 | 247.5 |
| 2044 | 240 |
| 2045 | 232.5 |
| 2046 | 225 |
| 2047 | 217.5 |
| 2048 | 210 |
| 2049 | 202.5 |
| 2050 | 195 |
| 2051 | 187.5 |
| 2052 | 180 |
| 2053 | 172.5 |
| 2054 | 165 |
| 2055 | 157.5 |
| 2056 | 150 |
| 2057 | 142.5 |
| 2058 | 135 |
| 2059 | 127.5 |
| 2060 | 120 |
| 2061 | 112.5 |
| 2062 | 105 |
| 2063 | 97.5 |
| 2064 | 90 |
| 2065 | 82.5 |
| 2066 | 75 |
| 2067 | 67.5 |
| 2068 | 60 |
| 2069 | 52.5 |
| 2070 | 45 |
| 2071 | 37.5 |
| 2072 | 30 |
| 2073 | 22.5 |
| 2074 | 15 |

### IDA - SML

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F147:BN147` | IDA - SML | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D120:BL120` | 61 |
| `F197:BN197` | IDA - SML | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D121:BL121` | 61 |
| `F284:BN284` | IDA - SML | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D118:BL118` | 61 |
| `F334:BN334` | IDA - SML | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D117:BL117` | 61 |

#### Values by Output metric

##### Interest (Ext `F147:BN147` → `PV_Base!D120:BL120`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F197:BN197` → `PV_Base!D121:BL121`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2033: **0.833333**; 2034: **1.66667**; 2035: **1.66667**; 2036: **1.66667**; 2037: **1.66667**; 2038: **1.66667**; 2039: **0.833333** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0.833333 |
| 2034 | 1.66667 |
| 2035 | 1.66667 |
| 2036 | 1.66667 |
| 2037 | 1.66667 |
| 2038 | 1.66667 |
| 2039 | 0.833333 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F284:BN284` → `PV_Base!D118:BL118`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2026: **3.1563**; 2027: **6.47041**; 2028: **6.79393**; 2029: **7.13363**; 2030: **7.49031**; 2031: **7.86483**; 2032: **8.25807**; 2033: **7.83764**; 2034: **6.56286**; 2035: **5.22433**; 2036: **3.81888**; 2037: **2.34316**; 2038: **0.793651** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 3.1563 |
| 2027 | 6.47041 |
| 2028 | 6.79393 |
| 2029 | 7.13363 |
| 2030 | 7.49031 |
| 2031 | 7.86483 |
| 2032 | 8.25807 |
| 2033 | 7.83764 |
| 2034 | 6.56286 |
| 2035 | 5.22433 |
| 2036 | 3.81888 |
| 2037 | 2.34316 |
| 2038 | 0.793651 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F334:BN334` → `PV_Base!D117:BL117`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2026: **5**; 2027: **10**; 2028: **10**; 2029: **10**; 2030: **10**; 2031: **10**; 2032: **10**; 2033: **9.16667**; 2034: **7.5**; 2035: **5.83333**; 2036: **4.16667**; 2037: **2.5**; 2038: **0.833333** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 5 |
| 2027 | 10 |
| 2028 | 10 |
| 2029 | 10 |
| 2030 | 10 |
| 2031 | 10 |
| 2032 | 10 |
| 2033 | 9.16667 |
| 2034 | 7.5 |
| 2035 | 5.83333 |
| 2036 | 4.16667 |
| 2037 | 2.5 |
| 2038 | 0.833333 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### IDA NEW 40-year credits

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F148:BN148` | IDA NEW 40-year credits | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D144:BL144` | 61 |
| `F198:BN198` | IDA NEW 40-year credits | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D145:BL145` | 61 |
| `F285:BN285` | IDA NEW 40-year credits | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D142:BL142` | 61 |
| `F335:BN335` | IDA NEW 40-year credits | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D141:BL141` | 61 |

#### Values by Output metric

##### Interest (Ext `F148:BN148` → `PV_Base!D144:BL144`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F198:BN198` → `PV_Base!D145:BL145`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2038: **0.344828**; 2039: **0.344828**; 2040: **0.344828**; 2041: **0.344828**; 2042: **0.344828**; 2043: **0.344828**; 2044: **0.344828**; 2045: **0.344828**; 2046: **0.344828**; 2047: **0.344828**; 2048: **0.344828**; 2049: **0.344828** … +9 more … 2059: **0.344828**; 2060: **0.344828**; 2061: **0.344828**; 2062: **0.344828**; 2063: **0.344828**; 2064: **0.344828** _(n=61 years, 27 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 0 |
| 2038 | 0.344828 |
| 2039 | 0.344828 |
| 2040 | 0.344828 |
| 2041 | 0.344828 |
| 2042 | 0.344828 |
| 2043 | 0.344828 |
| 2044 | 0.344828 |
| 2045 | 0.344828 |
| 2046 | 0.344828 |
| 2047 | 0.344828 |
| 2048 | 0.344828 |
| 2049 | 0.344828 |
| 2050 | 0.344828 |
| 2051 | 0.344828 |
| 2052 | 0.344828 |
| 2053 | 0.344828 |
| 2054 | 0.344828 |
| 2055 | 0.344828 |
| 2056 | 0.344828 |
| 2057 | 0.344828 |
| 2058 | 0.344828 |
| 2059 | 0.344828 |
| 2060 | 0.344828 |
| 2061 | 0.344828 |
| 2062 | 0.344828 |
| 2063 | 0.344828 |
| 2064 | 0.344828 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F285:BN285` → `PV_Base!D142:BL142`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2026: **3.05265**; 2027: **3.20528**; 2028: **3.36554**; 2029: **3.53382**; 2030: **3.71051**; 2031: **3.89604**; 2032: **4.09084**; 2033: **4.29538**; 2034: **4.51015**; 2035: **4.73566**; 2036: **4.97244**; 2037: **5.22106** … +21 more … 2059: **1.9953**; 2060: **1.75024**; 2061: **1.49292**; 2062: **1.22274**; 2063: **0.939051**; 2064: **0.641176** _(n=61 years, 39 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 3.05265 |
| 2027 | 3.20528 |
| 2028 | 3.36554 |
| 2029 | 3.53382 |
| 2030 | 3.71051 |
| 2031 | 3.89604 |
| 2032 | 4.09084 |
| 2033 | 4.29538 |
| 2034 | 4.51015 |
| 2035 | 4.73566 |
| 2036 | 4.97244 |
| 2037 | 5.22106 |
| 2038 | 5.13729 |
| 2039 | 5.04932 |
| 2040 | 4.95696 |
| 2041 | 4.85998 |
| 2042 | 4.75815 |
| 2043 | 4.65123 |
| 2044 | 4.53897 |
| 2045 | 4.42109 |
| 2046 | 4.29731 |
| 2047 | 4.16735 |
| 2048 | 4.03089 |
| 2049 | 3.88761 |
| 2050 | 3.73716 |
| 2051 | 3.57919 |
| 2052 | 3.41332 |
| 2053 | 3.23916 |
| 2054 | 3.05629 |
| 2055 | 2.86428 |
| 2056 | 2.66267 |
| 2057 | 2.45097 |
| 2058 | 2.22869 |
| 2059 | 1.9953 |
| 2060 | 1.75024 |
| 2061 | 1.49292 |
| 2062 | 1.22274 |
| 2063 | 0.939051 |
| 2064 | 0.641176 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F335:BN335` → `PV_Base!D141:BL141`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2026: **10**; 2027: **10**; 2028: **10**; 2029: **10**; 2030: **10**; 2031: **10**; 2032: **10**; 2033: **10**; 2034: **10**; 2035: **10**; 2036: **10**; 2037: **10** … +21 more … 2059: **2.41379**; 2060: **2.06897**; 2061: **1.72414**; 2062: **1.37931**; 2063: **1.03448**; 2064: **0.689655** _(n=61 years, 39 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 10 |
| 2027 | 10 |
| 2028 | 10 |
| 2029 | 10 |
| 2030 | 10 |
| 2031 | 10 |
| 2032 | 10 |
| 2033 | 10 |
| 2034 | 10 |
| 2035 | 10 |
| 2036 | 10 |
| 2037 | 10 |
| 2038 | 9.65517 |
| 2039 | 9.31034 |
| 2040 | 8.96552 |
| 2041 | 8.62069 |
| 2042 | 8.27586 |
| 2043 | 7.93103 |
| 2044 | 7.58621 |
| 2045 | 7.24138 |
| 2046 | 6.89655 |
| 2047 | 6.55172 |
| 2048 | 6.2069 |
| 2049 | 5.86207 |
| 2050 | 5.51724 |
| 2051 | 5.17241 |
| 2052 | 4.82759 |
| 2053 | 4.48276 |
| 2054 | 4.13793 |
| 2055 | 3.7931 |
| 2056 | 3.44828 |
| 2057 | 3.10345 |
| 2058 | 2.75862 |
| 2059 | 2.41379 |
| 2060 | 2.06897 |
| 2061 | 1.72414 |
| 2062 | 1.37931 |
| 2063 | 1.03448 |
| 2064 | 0.689655 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### IDA NEW Regular

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F149:BN149` | IDA NEW Regular | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D168:BL168` | 61 |
| `F199:BN199` | IDA NEW Regular | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D169:BL169` | 61 |
| `F286:BN286` | IDA NEW Regular | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D166:BL166` | 61 |
| `F336:BN336` | IDA NEW Regular | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D165:BL165` | 61 |

#### Values by Output metric

##### Interest (Ext `F149:BN149` → `PV_Base!D168:BL168`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2027: **0.75**; 2028: **0.75**; 2029: **0.75**; 2030: **0.75**; 2031: **0.75**; 2032: **0.75**; 2033: **0.75**; 2034: **0.72**; 2035: **0.69**; 2036: **0.66**; 2037: **0.63**; 2038: **0.6** … +13 more … 2052: **0.18**; 2053: **0.15**; 2054: **0.12**; 2055: **0.09**; 2056: **0.06**; 2057: **0.03** _(n=61 years, 31 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0.75 |
| 2028 | 0.75 |
| 2029 | 0.75 |
| 2030 | 0.75 |
| 2031 | 0.75 |
| 2032 | 0.75 |
| 2033 | 0.75 |
| 2034 | 0.72 |
| 2035 | 0.69 |
| 2036 | 0.66 |
| 2037 | 0.63 |
| 2038 | 0.6 |
| 2039 | 0.57 |
| 2040 | 0.54 |
| 2041 | 0.51 |
| 2042 | 0.48 |
| 2043 | 0.45 |
| 2044 | 0.42 |
| 2045 | 0.39 |
| 2046 | 0.36 |
| 2047 | 0.33 |
| 2048 | 0.3 |
| 2049 | 0.27 |
| 2050 | 0.24 |
| 2051 | 0.21 |
| 2052 | 0.18 |
| 2053 | 0.15 |
| 2054 | 0.12 |
| 2055 | 0.09 |
| 2056 | 0.06 |
| 2057 | 0.03 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F199:BN199` → `PV_Base!D169:BL169`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2033: **4**; 2034: **4**; 2035: **4**; 2036: **4**; 2037: **4**; 2038: **4**; 2039: **4**; 2040: **4**; 2041: **4**; 2042: **4**; 2043: **4**; 2044: **4** … +7 more … 2052: **4**; 2053: **4**; 2054: **4**; 2055: **4**; 2056: **4**; 2057: **4** _(n=61 years, 25 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 4 |
| 2034 | 4 |
| 2035 | 4 |
| 2036 | 4 |
| 2037 | 4 |
| 2038 | 4 |
| 2039 | 4 |
| 2040 | 4 |
| 2041 | 4 |
| 2042 | 4 |
| 2043 | 4 |
| 2044 | 4 |
| 2045 | 4 |
| 2046 | 4 |
| 2047 | 4 |
| 2048 | 4 |
| 2049 | 4 |
| 2050 | 4 |
| 2051 | 4 |
| 2052 | 4 |
| 2053 | 4 |
| 2054 | 4 |
| 2055 | 4 |
| 2056 | 4 |
| 2057 | 4 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F286:BN286` → `PV_Base!D166:BL166`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2026: **50.7582**; 2027: **52.5461**; 2028: **54.4234**; 2029: **56.3946**; 2030: **58.4643**; 2031: **60.6375**; 2032: **62.9194**; 2033: **61.3154**; 2034: **59.6612**; 2035: **57.9542**; 2036: **56.1919**; 2037: **54.3715** … +13 more … 2051: **20.8574**; 2052: **17.7202**; 2053: **14.4562**; 2054: **11.059**; 2055: **7.522**; 2056: **3.8381** _(n=61 years, 31 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 50.7582 |
| 2027 | 52.5461 |
| 2028 | 54.4234 |
| 2029 | 56.3946 |
| 2030 | 58.4643 |
| 2031 | 60.6375 |
| 2032 | 62.9194 |
| 2033 | 61.3154 |
| 2034 | 59.6612 |
| 2035 | 57.9542 |
| 2036 | 56.1919 |
| 2037 | 54.3715 |
| 2038 | 52.4901 |
| 2039 | 50.5446 |
| 2040 | 48.5318 |
| 2041 | 46.4484 |
| 2042 | 44.2908 |
| 2043 | 42.0554 |
| 2044 | 39.7381 |
| 2045 | 37.3351 |
| 2046 | 34.8418 |
| 2047 | 32.2539 |
| 2048 | 29.5666 |
| 2049 | 26.7749 |
| 2050 | 23.8737 |
| 2051 | 20.8574 |
| 2052 | 17.7202 |
| 2053 | 14.4562 |
| 2054 | 11.059 |
| 2055 | 7.522 |
| 2056 | 3.8381 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F336:BN336` → `PV_Base!D165:BL165`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2026: **100**; 2027: **100**; 2028: **100**; 2029: **100**; 2030: **100**; 2031: **100**; 2032: **100**; 2033: **96**; 2034: **92**; 2035: **88**; 2036: **84**; 2037: **80** … +13 more … 2051: **24**; 2052: **20**; 2053: **16**; 2054: **12**; 2055: **8**; 2056: **4** _(n=61 years, 31 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 100 |
| 2027 | 100 |
| 2028 | 100 |
| 2029 | 100 |
| 2030 | 100 |
| 2031 | 100 |
| 2032 | 100 |
| 2033 | 96 |
| 2034 | 92 |
| 2035 | 88 |
| 2036 | 84 |
| 2037 | 80 |
| 2038 | 76 |
| 2039 | 72 |
| 2040 | 68 |
| 2041 | 64 |
| 2042 | 60 |
| 2043 | 56 |
| 2044 | 52 |
| 2045 | 48 |
| 2046 | 44 |
| 2047 | 40 |
| 2048 | 36 |
| 2049 | 32 |
| 2050 | 28 |
| 2051 | 24 |
| 2052 | 20 |
| 2053 | 16 |
| 2054 | 12 |
| 2055 | 8 |
| 2056 | 4 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### IDA NEW Blend floating

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F150:BN150` | IDA NEW Blend (also enter) --> | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D192:BL192` | 61 |
| `F200:BN200` | IDA NEW Blend (also enter) --> | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D193:BL193` | 61 |
| `F287:BN287` | IDA NEW Blend (also enter) --> | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D190:BL190` | 61 |
| `F337:BN337` | IDA NEW Blend (also enter) --> | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D189:BL189` | 61 |

#### Values by Output metric

##### Interest (Ext `F150:BN150` → `PV_Base!D192:BL192`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2026: **0.648**; 2027: **1.944**; 2028: **3.888**; 2029: **3.888**; 2030: **3.888**; 2031: **3.888**; 2032: **3.8556**; 2033: **3.7584**; 2034: **3.564**; 2035: **3.3696**; 2036: **3.1752**; 2037: **2.9808**; 2038: **2.7864**; 2039: **2.592**; 2040: **2.3976**; 2041: **2.2032**; 2042: **2.0088**; 2043: **1.8144**; 2044: **1.62**; 2045: **1.4256**; 2046: **1.2312**; 2047: **1.0368**; 2048: **0.8424**; 2049: **0.648** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0.648 |
| 2027 | 1.944 |
| 2028 | 3.888 |
| 2029 | 3.888 |
| 2030 | 3.888 |
| 2031 | 3.888 |
| 2032 | 3.8556 |
| 2033 | 3.7584 |
| 2034 | 3.564 |
| 2035 | 3.3696 |
| 2036 | 3.1752 |
| 2037 | 2.9808 |
| 2038 | 2.7864 |
| 2039 | 2.592 |
| 2040 | 2.3976 |
| 2041 | 2.2032 |
| 2042 | 2.0088 |
| 2043 | 1.8144 |
| 2044 | 1.62 |
| 2045 | 1.4256 |
| 2046 | 1.2312 |
| 2047 | 1.0368 |
| 2048 | 0.8424 |
| 2049 | 0.648 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F200:BN200` → `PV_Base!D193:BL193`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2031: **1**; 2032: **3**; 2033: **6**; 2034: **6**; 2035: **6**; 2036: **6**; 2037: **6**; 2038: **6**; 2039: **6**; 2040: **6**; 2041: **6**; 2042: **6**; 2043: **6**; 2044: **6**; 2045: **6**; 2046: **6**; 2047: **6**; 2048: **6**; 2049: **6** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 1 |
| 2032 | 3 |
| 2033 | 6 |
| 2034 | 6 |
| 2035 | 6 |
| 2036 | 6 |
| 2037 | 6 |
| 2038 | 6 |
| 2039 | 6 |
| 2040 | 6 |
| 2041 | 6 |
| 2042 | 6 |
| 2043 | 6 |
| 2044 | 6 |
| 2045 | 6 |
| 2046 | 6 |
| 2047 | 6 |
| 2048 | 6 |
| 2049 | 6 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F287:BN287` → `PV_Base!D190:BL190`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2025: **16.3971**; 2026: **49.3631**; 2027: **99.0786**; 2028: **100.144**; 2029: **101.264**; 2030: **102.439**; 2031: **102.673**; 2032: **100.951**; 2033: **96.24**; 2034: **91.488**; 2035: **86.6928**; 2036: **81.8523** … +7 more … 2044: **41.1974**; 2045: **35.8317**; 2046: **30.3921**; 2047: **24.8749**; 2048: **19.2762**; 2049: **13.592** _(n=61 years, 25 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 16.3971 |
| 2026 | 49.3631 |
| 2027 | 99.0786 |
| 2028 | 100.144 |
| 2029 | 101.264 |
| 2030 | 102.439 |
| 2031 | 102.673 |
| 2032 | 100.951 |
| 2033 | 96.24 |
| 2034 | 91.488 |
| 2035 | 86.6928 |
| 2036 | 81.8523 |
| 2037 | 76.9641 |
| 2038 | 72.0259 |
| 2039 | 67.0352 |
| 2040 | 61.9894 |
| 2041 | 56.8856 |
| 2042 | 51.7211 |
| 2043 | 46.4928 |
| 2044 | 41.1974 |
| 2045 | 35.8317 |
| 2046 | 30.3921 |
| 2047 | 24.8749 |
| 2048 | 19.2762 |
| 2049 | 13.592 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F337:BN337` → `PV_Base!D189:BL189`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2025: **20**; 2026: **60**; 2027: **120**; 2028: **120**; 2029: **120**; 2030: **120**; 2031: **119**; 2032: **116**; 2033: **110**; 2034: **104**; 2035: **98**; 2036: **92** … +7 more … 2044: **44**; 2045: **38**; 2046: **32**; 2047: **26**; 2048: **20**; 2049: **14** _(n=61 years, 25 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 20 |
| 2026 | 60 |
| 2027 | 120 |
| 2028 | 120 |
| 2029 | 120 |
| 2030 | 120 |
| 2031 | 119 |
| 2032 | 116 |
| 2033 | 110 |
| 2034 | 104 |
| 2035 | 98 |
| 2036 | 92 |
| 2037 | 86 |
| 2038 | 80 |
| 2039 | 74 |
| 2040 | 68 |
| 2041 | 62 |
| 2042 | 56 |
| 2043 | 50 |
| 2044 | 44 |
| 2045 | 38 |
| 2046 | 32 |
| 2047 | 26 |
| 2048 | 20 |
| 2049 | 14 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### IDA NEW 60-year credits

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F151:BN151` | IDA NEW 60-year credits | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D216:BL216` | 61 |
| `F201:BN201` | IDA NEW 60-year credits | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D217:BL217` | 61 |
| `F288:BN288` | IDA NEW 60-year credits | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D214:BL214` | 61 |
| `F338:BN338` | IDA NEW 60-year credits | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D213:BL213` | 61 |

#### Values by Output metric

##### Interest (Ext `F151:BN151` → `PV_Base!D216:BL216`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F201:BN201` → `PV_Base!D217:BL217`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2046: **0.5**; 2047: **1.5**; 2048: **3**; 2049: **3**; 2050: **3**; 2051: **3**; 2052: **3**; 2053: **3**; 2054: **3**; 2055: **3**; 2056: **3**; 2057: **3** … +21 more … 2079: **3**; 2080: **3**; 2081: **3**; 2082: **3**; 2083: **3**; 2084: **3** _(n=61 years, 39 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 0 |
| 2038 | 0 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0.5 |
| 2047 | 1.5 |
| 2048 | 3 |
| 2049 | 3 |
| 2050 | 3 |
| 2051 | 3 |
| 2052 | 3 |
| 2053 | 3 |
| 2054 | 3 |
| 2055 | 3 |
| 2056 | 3 |
| 2057 | 3 |
| 2058 | 3 |
| 2059 | 3 |
| 2060 | 3 |
| 2061 | 3 |
| 2062 | 3 |
| 2063 | 3 |
| 2064 | 3 |
| 2065 | 3 |
| 2066 | 3 |
| 2067 | 3 |
| 2068 | 3 |
| 2069 | 3 |
| 2070 | 3 |
| 2071 | 3 |
| 2072 | 3 |
| 2073 | 3 |
| 2074 | 3 |
| 2075 | 3 |
| 2076 | 3 |
| 2077 | 3 |
| 2078 | 3 |
| 2079 | 3 |
| 2080 | 3 |
| 2081 | 3 |
| 2082 | 3 |
| 2083 | 3 |
| 2084 | 3 |

##### PV of debt (Ext `F288:BN288` → `PV_Base!D214:BL214`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2025: **3.23354**; 2026: **9.8623**; 2027: **20.056**; 2028: **21.0588**; 2029: **22.1118**; 2030: **23.2174**; 2031: **24.3782**; 2032: **25.5971**; 2033: **26.877**; 2034: **28.2208**; 2035: **29.6319**; 2036: **31.1135** … +42 more … 2079: **18.019**; 2080: **15.92**; 2081: **13.716**; 2082: **11.4018**; 2083: **8.97188**; 2084: **6.42047** _(n=61 years, 60 nonzero)_


| Year | Value |
|-----:|------:|
| 2025 | 3.23354 |
| 2026 | 9.8623 |
| 2027 | 20.056 |
| 2028 | 21.0588 |
| 2029 | 22.1118 |
| 2030 | 23.2174 |
| 2031 | 24.3782 |
| 2032 | 25.5971 |
| 2033 | 26.877 |
| 2034 | 28.2208 |
| 2035 | 29.6319 |
| 2036 | 31.1135 |
| 2037 | 32.6692 |
| 2038 | 34.3026 |
| 2039 | 36.0177 |
| 2040 | 37.8186 |
| 2041 | 39.7096 |
| 2042 | 41.695 |
| 2043 | 43.7798 |
| 2044 | 45.9688 |
| 2045 | 48.2672 |
| 2046 | 50.1806 |
| 2047 | 51.1896 |
| 2048 | 50.7491 |
| 2049 | 50.2866 |
| 2050 | 49.8009 |
| 2051 | 49.2909 |
| 2052 | 48.7555 |
| 2053 | 48.1932 |
| 2054 | 47.6029 |
| 2055 | 46.9831 |
| 2056 | 46.3322 |
| 2057 | 45.6488 |
| 2058 | 44.9313 |
| 2059 | 44.1778 |
| 2060 | 43.3867 |
| 2061 | 42.556 |
| 2062 | 41.6838 |
| 2063 | 40.768 |
| 2064 | 39.8064 |
| 2065 | 38.7968 |
| 2066 | 37.7366 |
| 2067 | 36.6234 |
| 2068 | 35.4546 |
| 2069 | 34.2273 |
| 2070 | 32.9387 |
| 2071 | 31.5856 |
| 2072 | 30.1649 |
| 2073 | 28.6732 |
| 2074 | 27.1068 |
| 2075 | 25.4622 |
| 2076 | 23.7353 |
| 2077 | 21.922 |
| 2078 | 20.0181 |
| 2079 | 18.019 |
| 2080 | 15.92 |
| 2081 | 13.716 |
| 2082 | 11.4018 |
| 2083 | 8.97188 |
| 2084 | 6.42047 |

##### Stock of new forex debt (in USD) (Ext `F338:BN338` → `PV_Base!D213:BL213`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2025: **20**; 2026: **60**; 2027: **120**; 2028: **120**; 2029: **120**; 2030: **120**; 2031: **120**; 2032: **120**; 2033: **120**; 2034: **120**; 2035: **120**; 2036: **120** … +42 more … 2079: **22**; 2080: **19**; 2081: **16**; 2082: **13**; 2083: **10**; 2084: **7** _(n=61 years, 60 nonzero)_


| Year | Value |
|-----:|------:|
| 2025 | 20 |
| 2026 | 60 |
| 2027 | 120 |
| 2028 | 120 |
| 2029 | 120 |
| 2030 | 120 |
| 2031 | 120 |
| 2032 | 120 |
| 2033 | 120 |
| 2034 | 120 |
| 2035 | 120 |
| 2036 | 120 |
| 2037 | 120 |
| 2038 | 120 |
| 2039 | 120 |
| 2040 | 120 |
| 2041 | 120 |
| 2042 | 120 |
| 2043 | 120 |
| 2044 | 120 |
| 2045 | 120 |
| 2046 | 119.5 |
| 2047 | 118 |
| 2048 | 115 |
| 2049 | 112 |
| 2050 | 109 |
| 2051 | 106 |
| 2052 | 103 |
| 2053 | 100 |
| 2054 | 97 |
| 2055 | 94 |
| 2056 | 91 |
| 2057 | 88 |
| 2058 | 85 |
| 2059 | 82 |
| 2060 | 79 |
| 2061 | 76 |
| 2062 | 73 |
| 2063 | 70 |
| 2064 | 67 |
| 2065 | 64 |
| 2066 | 61 |
| 2067 | 58 |
| 2068 | 55 |
| 2069 | 52 |
| 2070 | 49 |
| 2071 | 46 |
| 2072 | 43 |
| 2073 | 40 |
| 2074 | 37 |
| 2075 | 34 |
| 2076 | 31 |
| 2077 | 28 |
| 2078 | 25 |
| 2079 | 22 |
| 2080 | 19 |
| 2081 | 16 |
| 2082 | 13 |
| 2083 | 10 |
| 2084 | 7 |

### MULTI1

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F152:BN152` | MULTI1 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D250:BL250` | 61 |
| `F202:BN202` | MULTI1 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D251:BL251` | 61 |
| `F289:BN289` | MULTI1 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D248:BL248` | 61 |
| `F339:BN339` | MULTI1 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D247:BL247` | 61 |

#### Values by Output metric

##### Interest (Ext `F152:BN152` → `PV_Base!D250:BL250`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F202:BN202` → `PV_Base!D251:BL251`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F289:BN289` → `PV_Base!D248:BL248`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F339:BN339` → `PV_Base!D247:BL247`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### MULTI2

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F153:BN153` | MULTI2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D276:BL276` | 61 |
| `F203:BN203` | MULTI2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D277:BL277` | 61 |
| `F290:BN290` | MULTI2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D274:BL274` | 61 |
| `F340:BN340` | MULTI2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D273:BL273` | 61 |

#### Values by Output metric

##### Interest (Ext `F153:BN153` → `PV_Base!D276:BL276`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F203:BN203` → `PV_Base!D277:BL277`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F290:BN290` → `PV_Base!D274:BL274`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F340:BN340` → `PV_Base!D273:BL273`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### OTH_MULTI1

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F155:BN155` | OTH_MULTI1 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D302:BL302` | 61 |
| `F205:BN205` | OTH_MULTI1 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D303:BL303` | 61 |
| `F292:BN292` | OTH_MULTI1 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D300:BL300` | 61 |
| `F342:BN342` | OTH_MULTI1 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D299:BL299` | 61 |

#### Values by Output metric

##### Interest (Ext `F155:BN155` → `PV_Base!D302:BL302`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F205:BN205` → `PV_Base!D303:BL303`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F292:BN292` → `PV_Base!D300:BL300`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F342:BN342` → `PV_Base!D299:BL299`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### OTH_MULTI2

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F156:BN156` | OTH_MULTI2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D328:BL328` | 61 |
| `F206:BN206` | OTH_MULTI2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D329:BL329` | 61 |
| `F293:BN293` | OTH_MULTI2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D326:BL326` | 61 |
| `F343:BN343` | OTH_MULTI2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D325:BL325` | 61 |

#### Values by Output metric

##### Interest (Ext `F156:BN156` → `PV_Base!D328:BL328`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F206:BN206` → `PV_Base!D329:BL329`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F293:BN293` → `PV_Base!D326:BL326`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F343:BN343` → `PV_Base!D325:BL325`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### OTH_MULTI3

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F157:BN157` | OTH_MULTI3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D354:BL354` | 61 |
| `F207:BN207` | OTH_MULTI3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D355:BL355` | 61 |
| `F294:BN294` | OTH_MULTI3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D352:BL352` | 61 |
| `F344:BN344` | OTH_MULTI3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D351:BL351` | 61 |

#### Values by Output metric

##### Interest (Ext `F157:BN157` → `PV_Base!D354:BL354`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F207:BN207` → `PV_Base!D355:BL355`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F294:BN294` → `PV_Base!D352:BL352`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F344:BN344` → `PV_Base!D351:BL351`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### Export Credit Agencies

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F160:BN160` | Export Credit Agencies | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D380:BL380` | 61 |
| `F210:BN210` | Export Credit Agencies | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D381:BL381` | 61 |
| `F297:BN297` | Export Credit Agencies | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D378:BL378` | 61 |
| `F347:BN347` | Export Credit Agencies | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D377:BL377` | 61 |

#### Values by Output metric

##### Interest (Ext `F160:BN160` → `PV_Base!D380:BL380`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2025: **4.71008**; 2026: **14.0165**; 2027: **23.4963**; 2028: **35.4946**; 2029: **45.3877**; 2030: **51.0956**; 2031: **56.4137**; 2032: **65.2719**; 2033: **73.7682**; 2034: **81.54**; 2035: **88.5826**; 2036: **94.7023** … +9 more … 2046: **86.9567**; 2047: **78.248**; 2048: **69.5876**; 2049: **61.3056**; 2050: **53.3762**; 2051: **45.6135** _(n=61 years, 27 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 4.71008 |
| 2026 | 14.0165 |
| 2027 | 23.4963 |
| 2028 | 35.4946 |
| 2029 | 45.3877 |
| 2030 | 51.0956 |
| 2031 | 56.4137 |
| 2032 | 65.2719 |
| 2033 | 73.7682 |
| 2034 | 81.54 |
| 2035 | 88.5826 |
| 2036 | 94.7023 |
| 2037 | 100.061 |
| 2038 | 104.98 |
| 2039 | 109.491 |
| 2040 | 113.32 |
| 2041 | 114.698 |
| 2042 | 113.625 |
| 2043 | 110.101 |
| 2044 | 104.126 |
| 2045 | 95.7006 |
| 2046 | 86.9567 |
| 2047 | 78.248 |
| 2048 | 69.5876 |
| 2049 | 61.3056 |
| 2050 | 53.3762 |
| 2051 | 45.6135 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F210:BN210` → `PV_Base!D381:BL381`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2032: **20.4697**; 2033: **60.9149**; 2034: **102.114**; 2035: **154.257**; 2036: **197.252**; 2037: **222.058**; 2038: **245.17**; 2039: **283.667**; 2040: **322.167**; 2041: **360.628**; 2042: **399.09**; 2043: **437.551**; 2044: **476.013**; 2045: **494.005**; 2046: **492.021**; 2047: **489.284**; 2048: **467.909**; 2049: **447.992**; 2050: **438.57**; 2051: **423.15** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 20.4697 |
| 2033 | 60.9149 |
| 2034 | 102.114 |
| 2035 | 154.257 |
| 2036 | 197.252 |
| 2037 | 222.058 |
| 2038 | 245.17 |
| 2039 | 283.667 |
| 2040 | 322.167 |
| 2041 | 360.628 |
| 2042 | 399.09 |
| 2043 | 437.551 |
| 2044 | 476.013 |
| 2045 | 494.005 |
| 2046 | 492.021 |
| 2047 | 489.284 |
| 2048 | 467.909 |
| 2049 | 447.992 |
| 2050 | 438.57 |
| 2051 | 423.15 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F297:BN297` → `PV_Base!D378:BL378`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2024: **182.479**; 2025: **547.445**; 2026: **928.07**; 2027: **1,416**; 2028: **1,834**; 2029: **2,102**; 2030: **2,362**; 2031: **2,767**; 2032: **3,163**; 2033: **3,529**; 2034: **3,865**; 2035: **4,158** … +10 more … 2046: **3,736**; 2047: **3,355**; 2048: **2,985**; 2049: **2,625**; 2050: **2,265**; 2051: **1,909** _(n=61 years, 28 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 182.479 |
| 2025 | 547.445 |
| 2026 | 928.07 |
| 2027 | 1,416 |
| 2028 | 1,834 |
| 2029 | 2,102 |
| 2030 | 2,362 |
| 2031 | 2,767 |
| 2032 | 3,163 |
| 2033 | 3,529 |
| 2034 | 3,865 |
| 2035 | 4,158 |
| 2036 | 4,417 |
| 2037 | 4,658 |
| 2038 | 4,884 |
| 2039 | 5,078 |
| 2040 | 5,170 |
| 2041 | 5,159 |
| 2042 | 5,042 |
| 2043 | 4,815 |
| 2044 | 4,475 |
| 2045 | 4,109 |
| 2046 | 3,736 |
| 2047 | 3,355 |
| 2048 | 2,985 |
| 2049 | 2,625 |
| 2050 | 2,265 |
| 2051 | 1,909 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F347:BN347` → `PV_Base!D377:BL377`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2024: **266.106**; 2025: **791.894**; 2026: **1,327**; 2027: **2,005**; 2028: **2,564**; 2029: **2,887**; 2030: **3,187**; 2031: **3,688**; 2032: **4,168**; 2033: **4,607**; 2034: **5,005**; 2035: **5,350** … +10 more … 2046: **4,421**; 2047: **3,932**; 2048: **3,464**; 2049: **3,016**; 2050: **2,577**; 2051: **2,154** _(n=61 years, 28 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 266.106 |
| 2025 | 791.894 |
| 2026 | 1,327 |
| 2027 | 2,005 |
| 2028 | 2,564 |
| 2029 | 2,887 |
| 2030 | 3,187 |
| 2031 | 3,688 |
| 2032 | 4,168 |
| 2033 | 4,607 |
| 2034 | 5,005 |
| 2035 | 5,350 |
| 2036 | 5,653 |
| 2037 | 5,931 |
| 2038 | 6,186 |
| 2039 | 6,402 |
| 2040 | 6,480 |
| 2041 | 6,419 |
| 2042 | 6,220 |
| 2043 | 5,883 |
| 2044 | 5,407 |
| 2045 | 4,913 |
| 2046 | 4,421 |
| 2047 | 3,932 |
| 2048 | 3,464 |
| 2049 | 3,016 |
| 2050 | 2,577 |
| 2051 | 2,154 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### PC2

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F161:BN161` | PC2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D406:BL406` | 61 |
| `F211:BN211` | PC2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D407:BL407` | 61 |
| `F298:BN298` | PC2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D404:BL404` | 61 |
| `F348:BN348` | PC2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D403:BL403` | 61 |

#### Values by Output metric

##### Interest (Ext `F161:BN161` → `PV_Base!D406:BL406`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F211:BN211` → `PV_Base!D407:BL407`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F298:BN298` → `PV_Base!D404:BL404`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F348:BN348` → `PV_Base!D403:BL403`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### PC3

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F162:BN162` | PC3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D432:BL432` | 61 |
| `F212:BN212` | PC3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D433:BL433` | 61 |
| `F299:BN299` | PC3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D430:BL430` | 61 |
| `F349:BN349` | PC3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D429:BL429` | 61 |

#### Values by Output metric

##### Interest (Ext `F162:BN162` → `PV_Base!D432:BL432`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F212:BN212` → `PV_Base!D433:BL433`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F299:BN299` → `PV_Base!D430:BL430`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F349:BN349` → `PV_Base!D429:BL429`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### PC4

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F163:BN163` | PC4 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D458:BL458` | 61 |
| `F213:BN213` | PC4 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D459:BL459` | 61 |
| `F300:BN300` | PC4 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D456:BL456` | 61 |
| `F350:BN350` | PC4 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D455:BL455` | 61 |

#### Values by Output metric

##### Interest (Ext `F163:BN163` → `PV_Base!D458:BL458`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F213:BN213` → `PV_Base!D459:BL459`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F300:BN300` → `PV_Base!D456:BL456`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F350:BN350` → `PV_Base!D455:BL455`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### PC5

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F164:BN164` | PC5 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D484:BL484` | 61 |
| `F214:BN214` | PC5 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D485:BL485` | 61 |
| `F301:BN301` | PC5 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D482:BL482` | 61 |
| `F351:BN351` | PC5 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D481:BL481` | 61 |

#### Values by Output metric

##### Interest (Ext `F164:BN164` → `PV_Base!D484:BL484`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F214:BN214` → `PV_Base!D485:BL485`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F301:BN301` → `PV_Base!D482:BL482`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F351:BN351` → `PV_Base!D481:BL481`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### Export Import Bank of NPC

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F166:BN166` | Export Import Bank of NPC | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D510:BL510` | 61 |
| `F216:BN216` | Export Import Bank of NPC | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D511:BL511` | 61 |
| `F303:BN303` | Export Import Bank of NPC | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D508:BL508` | 61 |
| `F353:BN353` | Export Import Bank of NPC | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D507:BL507` | 61 |

#### Values by Output metric

##### Interest (Ext `F166:BN166` → `PV_Base!D510:BL510`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2025: **1.90982**; 2026: **1.90982**; 2027: **1.90982**; 2028: **1.90982**; 2029: **1.90982**; 2030: **1.90982**; 2031: **1.71884**; 2032: **1.52786**; 2033: **1.33687**; 2034: **1.14589**; 2035: **0.95491**; 2036: **0.763928**; 2037: **0.572946**; 2038: **0.381964**; 2039: **0.190982** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 1.90982 |
| 2026 | 1.90982 |
| 2027 | 1.90982 |
| 2028 | 1.90982 |
| 2029 | 1.90982 |
| 2030 | 1.90982 |
| 2031 | 1.71884 |
| 2032 | 1.52786 |
| 2033 | 1.33687 |
| 2034 | 1.14589 |
| 2035 | 0.95491 |
| 2036 | 0.763928 |
| 2037 | 0.572946 |
| 2038 | 0.381964 |
| 2039 | 0.190982 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F216:BN216` → `PV_Base!D511:BL511`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2030: **6.00573**; 2031: **6.00573**; 2032: **6.00573**; 2033: **6.00573**; 2034: **6.00573**; 2035: **6.00573**; 2036: **6.00573**; 2037: **6.00573**; 2038: **6.00573**; 2039: **6.00573** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 6.00573 |
| 2031 | 6.00573 |
| 2032 | 6.00573 |
| 2033 | 6.00573 |
| 2034 | 6.00573 |
| 2035 | 6.00573 |
| 2036 | 6.00573 |
| 2037 | 6.00573 |
| 2038 | 6.00573 |
| 2039 | 6.00573 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F303:BN303` → `PV_Base!D508:BL508`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2024: **51.4226**; 2025: **52.0839**; 2026: **52.7783**; 2027: **53.5074**; 2028: **54.2729**; 2029: **55.0768**; 2030: **49.9151**; 2031: **44.6863**; 2032: **39.387**; 2033: **34.0137**; 2034: **28.5628**; 2035: **23.0303**; 2036: **17.4122**; 2037: **11.7041**; 2038: **5.90163** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 51.4226 |
| 2025 | 52.0839 |
| 2026 | 52.7783 |
| 2027 | 53.5074 |
| 2028 | 54.2729 |
| 2029 | 55.0768 |
| 2030 | 49.9151 |
| 2031 | 44.6863 |
| 2032 | 39.387 |
| 2033 | 34.0137 |
| 2034 | 28.5628 |
| 2035 | 23.0303 |
| 2036 | 17.4122 |
| 2037 | 11.7041 |
| 2038 | 5.90163 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F353:BN353` → `PV_Base!D507:BL507`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2024: **60.0573**; 2025: **60.0573**; 2026: **60.0573**; 2027: **60.0573**; 2028: **60.0573**; 2029: **60.0573**; 2030: **54.0515**; 2031: **48.0458**; 2032: **42.0401**; 2033: **36.0344**; 2034: **30.0286**; 2035: **24.0229**; 2036: **18.0172**; 2037: **12.0115**; 2038: **6.00573** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 60.0573 |
| 2025 | 60.0573 |
| 2026 | 60.0573 |
| 2027 | 60.0573 |
| 2028 | 60.0573 |
| 2029 | 60.0573 |
| 2030 | 54.0515 |
| 2031 | 48.0458 |
| 2032 | 42.0401 |
| 2033 | 36.0344 |
| 2034 | 30.0286 |
| 2035 | 24.0229 |
| 2036 | 18.0172 |
| 2037 | 12.0115 |
| 2038 | 6.00573 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### NPC2

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F167:BN167` | NPC2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D536:BL536` | 61 |
| `F217:BN217` | NPC2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D537:BL537` | 61 |
| `F304:BN304` | NPC2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D534:BL534` | 61 |
| `F354:BN354` | NPC2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D533:BL533` | 61 |

#### Values by Output metric

##### Interest (Ext `F167:BN167` → `PV_Base!D536:BL536`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F217:BN217` → `PV_Base!D537:BL537`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F304:BN304` → `PV_Base!D534:BL534`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F354:BN354` → `PV_Base!D533:BL533`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### NPC3

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F168:BN168` | NPC3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D562:BL562` | 61 |
| `F218:BN218` | NPC3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D563:BL563` | 61 |
| `F305:BN305` | NPC3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D560:BL560` | 61 |
| `F355:BN355` | NPC3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D559:BL559` | 61 |

#### Values by Output metric

##### Interest (Ext `F168:BN168` → `PV_Base!D562:BL562`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F218:BN218` → `PV_Base!D563:BL563`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F305:BN305` → `PV_Base!D560:BL560`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F355:BN355` → `PV_Base!D559:BL559`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### NPC4

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F169:BN169` | NPC4 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D588:BL588` | 61 |
| `F219:BN219` | NPC4 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D589:BL589` | 61 |
| `F306:BN306` | NPC4 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D586:BL586` | 61 |
| `F356:BN356` | NPC4 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D585:BL585` | 61 |

#### Values by Output metric

##### Interest (Ext `F169:BN169` → `PV_Base!D588:BL588`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F219:BN219` → `PV_Base!D589:BL589`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F306:BN306` → `PV_Base!D586:BL586`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F356:BN356` → `PV_Base!D585:BL585`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### NPC5

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F170:BN170` | NPC5 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D614:BL614` | 61 |
| `F220:BN220` | NPC5 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D615:BL615` | 61 |
| `F307:BN307` | NPC5 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D612:BL612` | 61 |
| `F357:BN357` | NPC5 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D611:BL611` | 61 |

#### Values by Output metric

##### Interest (Ext `F170:BN170` → `PV_Base!D614:BL614`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F220:BN220` → `PV_Base!D615:BL615`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F307:BN307` → `PV_Base!D612:BL612`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F357:BN357` → `PV_Base!D611:BL611`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### Eurobond

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F172:BN172` | Eurobond | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D640:BL640` | 61 |
| `F222:BN222` | Eurobond | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D641:BL641` | 61 |
| `F309:BN309` | Eurobond | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D638:BL638` | 61 |
| `F359:BN359` | Eurobond | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D637:BL637` | 61 |

#### Values by Output metric

##### Interest (Ext `F172:BN172` → `PV_Base!D640:BL640`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2028: **22.5**; 2029: **45**; 2030: **67.5**; 2031: **157.5**; 2032: **187.5**; 2033: **217.5**; 2034: **247.5**; 2035: **247.5**; 2036: **277.5**; 2037: **307.5**; 2038: **337.5**; 2039: **337.5**; 2040: **337.5**; 2041: **337.5**; 2042: **337.5**; 2043: **337.5**; 2044: **337.5**; 2045: **337.5**; 2046: **317.5**; 2047: **297.5**; 2048: **265**; 2049: **237.5**; 2050: **212.5**; 2051: **185** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 22.5 |
| 2029 | 45 |
| 2030 | 67.5 |
| 2031 | 157.5 |
| 2032 | 187.5 |
| 2033 | 217.5 |
| 2034 | 247.5 |
| 2035 | 247.5 |
| 2036 | 277.5 |
| 2037 | 307.5 |
| 2038 | 337.5 |
| 2039 | 337.5 |
| 2040 | 337.5 |
| 2041 | 337.5 |
| 2042 | 337.5 |
| 2043 | 337.5 |
| 2044 | 337.5 |
| 2045 | 337.5 |
| 2046 | 317.5 |
| 2047 | 297.5 |
| 2048 | 265 |
| 2049 | 237.5 |
| 2050 | 212.5 |
| 2051 | 185 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F222:BN222` → `PV_Base!D641:BL641`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2037: **83.3333**; 2038: **166.667**; 2039: **250**; 2040: **500**; 2041: **527.778**; 2042: **555.556**; 2043: **333.333**; 2044: **222.222**; 2045: **222.222**; 2046: **222.222**; 2047: **361.111**; 2048: **305.556**; 2049: **277.778**; 2050: **305.556**; 2051: **425.926** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 0 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 83.3333 |
| 2038 | 166.667 |
| 2039 | 250 |
| 2040 | 500 |
| 2041 | 527.778 |
| 2042 | 555.556 |
| 2043 | 333.333 |
| 2044 | 222.222 |
| 2045 | 222.222 |
| 2046 | 222.222 |
| 2047 | 361.111 |
| 2048 | 305.556 |
| 2049 | 277.778 |
| 2050 | 305.556 |
| 2051 | 425.926 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F309:BN309` → `PV_Base!D638:BL638`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2027: **250**; 2028: **500**; 2029: **750**; 2030: **1,750**; 2031: **2,083**; 2032: **2,417**; 2033: **2,750**; 2034: **2,750**; 2035: **3,083**; 2036: **3,417**; 2037: **3,750**; 2038: **3,750** … +7 more … 2046: **3,306**; 2047: **2,944**; 2048: **2,639**; 2049: **2,361**; 2050: **2,056**; 2051: **1,630** _(n=61 years, 25 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 250 |
| 2028 | 500 |
| 2029 | 750 |
| 2030 | 1,750 |
| 2031 | 2,083 |
| 2032 | 2,417 |
| 2033 | 2,750 |
| 2034 | 2,750 |
| 2035 | 3,083 |
| 2036 | 3,417 |
| 2037 | 3,750 |
| 2038 | 3,750 |
| 2039 | 3,750 |
| 2040 | 3,750 |
| 2041 | 3,750 |
| 2042 | 3,750 |
| 2043 | 3,750 |
| 2044 | 3,750 |
| 2045 | 3,528 |
| 2046 | 3,306 |
| 2047 | 2,944 |
| 2048 | 2,639 |
| 2049 | 2,361 |
| 2050 | 2,056 |
| 2051 | 1,630 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F359:BN359` → `PV_Base!D637:BL637`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2027: **250**; 2028: **500**; 2029: **750**; 2030: **1,750**; 2031: **2,083**; 2032: **2,417**; 2033: **2,750**; 2034: **2,750**; 2035: **3,083**; 2036: **3,417**; 2037: **3,750**; 2038: **3,750** … +7 more … 2046: **3,306**; 2047: **2,944**; 2048: **2,639**; 2049: **2,361**; 2050: **2,056**; 2051: **1,630** _(n=61 years, 25 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 250 |
| 2028 | 500 |
| 2029 | 750 |
| 2030 | 1,750 |
| 2031 | 2,083 |
| 2032 | 2,417 |
| 2033 | 2,750 |
| 2034 | 2,750 |
| 2035 | 3,083 |
| 2036 | 3,417 |
| 2037 | 3,750 |
| 2038 | 3,750 |
| 2039 | 3,750 |
| 2040 | 3,750 |
| 2041 | 3,750 |
| 2042 | 3,750 |
| 2043 | 3,750 |
| 2044 | 3,750 |
| 2045 | 3,528 |
| 2046 | 3,306 |
| 2047 | 2,944 |
| 2048 | 2,639 |
| 2049 | 2,361 |
| 2050 | 2,056 |
| 2051 | 1,630 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### Commecial Bank

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F173:BN173` | Commecial Bank | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D666:BL666` | 61 |
| `F223:BN223` | Commecial Bank | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D667:BL667` | 61 |
| `F310:BN310` | Commecial Bank | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D664:BL664` | 61 |
| `F360:BN360` | Commecial Bank | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D663:BL663` | 61 |

#### Values by Output metric

##### Interest (Ext `F173:BN173` → `PV_Base!D666:BL666`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2025: **12.289**; 2026: **27.2193**; 2027: **40.4892**; 2028: **57.2822**; 2029: **89.1668**; 2030: **136.892**; 2031: **185.015**; 2032: **235.093**; 2033: **295.434**; 2034: **354.354**; 2035: **411.882**; 2036: **467.893** … +9 more … 2046: **830.656**; 2047: **728.951**; 2048: **620.892**; 2049: **506.039**; 2050: **401.068**; 2051: **306.587** _(n=61 years, 27 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 12.289 |
| 2026 | 27.2193 |
| 2027 | 40.4892 |
| 2028 | 57.2822 |
| 2029 | 89.1668 |
| 2030 | 136.892 |
| 2031 | 185.015 |
| 2032 | 235.093 |
| 2033 | 295.434 |
| 2034 | 354.354 |
| 2035 | 411.882 |
| 2036 | 467.893 |
| 2037 | 521.193 |
| 2038 | 573.036 |
| 2039 | 623.647 |
| 2040 | 672.719 |
| 2041 | 720.501 |
| 2042 | 768.725 |
| 2043 | 819.18 |
| 2044 | 871.589 |
| 2045 | 926.396 |
| 2046 | 830.656 |
| 2047 | 728.951 |
| 2048 | 620.892 |
| 2049 | 506.039 |
| 2050 | 401.068 |
| 2051 | 306.587 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F223:BN223` → `PV_Base!D667:BL667`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2028: **27.309**; 2029: **60.4873**; 2030: **89.976**; 2031: **127.294**; 2032: **201.183**; 2033: **313.96**; 2034: **430.898**; 2035: **556.325**; 2036: **712.771**; 2037: **851.278**; 2038: **993.818**; 2039: **1,151**; 2040: **1,311**; 2041: **1,447**; 2042: **1,557**; 2043: **1,677**; 2044: **1,803**; 2045: **1,915**; 2046: **2,034**; 2047: **2,161**; 2048: **2,297**; 2049: **2,099**; 2050: **1,890**; 2051: **1,667** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 0 |
| 2027 | 0 |
| 2028 | 27.309 |
| 2029 | 60.4873 |
| 2030 | 89.976 |
| 2031 | 127.294 |
| 2032 | 201.183 |
| 2033 | 313.96 |
| 2034 | 430.898 |
| 2035 | 556.325 |
| 2036 | 712.771 |
| 2037 | 851.278 |
| 2038 | 993.818 |
| 2039 | 1,151 |
| 2040 | 1,311 |
| 2041 | 1,447 |
| 2042 | 1,557 |
| 2043 | 1,677 |
| 2044 | 1,803 |
| 2045 | 1,915 |
| 2046 | 2,034 |
| 2047 | 2,161 |
| 2048 | 2,297 |
| 2049 | 2,099 |
| 2050 | 1,890 |
| 2051 | 1,667 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F310:BN310` → `PV_Base!D664:BL664`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2024: **245.781**; 2025: **544.386**; 2026: **809.784**; 2027: **1,146**; 2028: **1,783**; 2029: **2,738**; 2030: **3,700**; 2031: **4,702**; 2032: **5,909**; 2033: **7,087**; 2034: **8,238**; 2035: **9,358** … +10 more … 2046: **1.458e+04**; 2047: **1.242e+04**; 2048: **1.012e+04**; 2049: **8,021**; 2050: **6,132**; 2051: **4,465** _(n=61 years, 28 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 245.781 |
| 2025 | 544.386 |
| 2026 | 809.784 |
| 2027 | 1,146 |
| 2028 | 1,783 |
| 2029 | 2,738 |
| 2030 | 3,700 |
| 2031 | 4,702 |
| 2032 | 5,909 |
| 2033 | 7,087 |
| 2034 | 8,238 |
| 2035 | 9,358 |
| 2036 | 1.042e+04 |
| 2037 | 1.146e+04 |
| 2038 | 1.247e+04 |
| 2039 | 1.345e+04 |
| 2040 | 1.441e+04 |
| 2041 | 1.537e+04 |
| 2042 | 1.638e+04 |
| 2043 | 1.743e+04 |
| 2044 | 1.853e+04 |
| 2045 | 1.661e+04 |
| 2046 | 1.458e+04 |
| 2047 | 1.242e+04 |
| 2048 | 1.012e+04 |
| 2049 | 8,021 |
| 2050 | 6,132 |
| 2051 | 4,465 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F360:BN360` → `PV_Base!D663:BL663`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2024: **245.781**; 2025: **544.386**; 2026: **809.784**; 2027: **1,146**; 2028: **1,783**; 2029: **2,738**; 2030: **3,700**; 2031: **4,702**; 2032: **5,909**; 2033: **7,087**; 2034: **8,238**; 2035: **9,358** … +10 more … 2046: **1.458e+04**; 2047: **1.242e+04**; 2048: **1.012e+04**; 2049: **8,021**; 2050: **6,132**; 2051: **4,465** _(n=61 years, 28 nonzero)_


| Year | Value |
|-----:|------:|
| 2024 | 245.781 |
| 2025 | 544.386 |
| 2026 | 809.784 |
| 2027 | 1,146 |
| 2028 | 1,783 |
| 2029 | 2,738 |
| 2030 | 3,700 |
| 2031 | 4,702 |
| 2032 | 5,909 |
| 2033 | 7,087 |
| 2034 | 8,238 |
| 2035 | 9,358 |
| 2036 | 1.042e+04 |
| 2037 | 1.146e+04 |
| 2038 | 1.247e+04 |
| 2039 | 1.345e+04 |
| 2040 | 1.441e+04 |
| 2041 | 1.537e+04 |
| 2042 | 1.638e+04 |
| 2043 | 1.743e+04 |
| 2044 | 1.853e+04 |
| 2045 | 1.661e+04 |
| 2046 | 1.458e+04 |
| 2047 | 1.242e+04 |
| 2048 | 1.012e+04 |
| 2049 | 8,021 |
| 2050 | 6,132 |
| 2051 | 4,465 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### COM3

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F174:BN174` | COM3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D692:BL692` | 61 |
| `F224:BN224` | COM3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D693:BL693` | 61 |
| `F311:BN311` | COM3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D690:BL690` | 61 |
| `F361:BN361` | COM3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D689:BL689` | 61 |

#### Values by Output metric

##### Interest (Ext `F174:BN174` → `PV_Base!D692:BL692`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: 2025: **17.5**; 2026: **17.5**; 2027: **13.125**; 2028: **8.75**; 2029: **4.375** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 17.5 |
| 2026 | 17.5 |
| 2027 | 13.125 |
| 2028 | 8.75 |
| 2029 | 4.375 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 0 |
| 2038 | 0 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Amortization (Ext `F224:BN224` → `PV_Base!D693:BL693`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: 2026: **87.5**; 2027: **87.5**; 2028: **87.5**; 2029: **87.5** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 0 |
| 2025 | 0 |
| 2026 | 87.5 |
| 2027 | 87.5 |
| 2028 | 87.5 |
| 2029 | 87.5 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 0 |
| 2038 | 0 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### PV of debt (Ext `F311:BN311` → `PV_Base!D690:BL690`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: 2024: **350**; 2025: **350**; 2026: **262.5**; 2027: **175**; 2028: **87.5** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 350 |
| 2025 | 350 |
| 2026 | 262.5 |
| 2027 | 175 |
| 2028 | 87.5 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 0 |
| 2038 | 0 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

##### Stock of new forex debt (in USD) (Ext `F361:BN361` → `PV_Base!D689:BL689`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: 2024: **350**; 2025: **350**; 2026: **262.5**; 2027: **175**; 2028: **87.5** _(other years 0; n=61)_


| Year | Value |
|-----:|------:|
| 2024 | 350 |
| 2025 | 350 |
| 2026 | 262.5 |
| 2027 | 175 |
| 2028 | 87.5 |
| 2029 | 0 |
| 2030 | 0 |
| 2031 | 0 |
| 2032 | 0 |
| 2033 | 0 |
| 2034 | 0 |
| 2035 | 0 |
| 2036 | 0 |
| 2037 | 0 |
| 2038 | 0 |
| 2039 | 0 |
| 2040 | 0 |
| 2041 | 0 |
| 2042 | 0 |
| 2043 | 0 |
| 2044 | 0 |
| 2045 | 0 |
| 2046 | 0 |
| 2047 | 0 |
| 2048 | 0 |
| 2049 | 0 |
| 2050 | 0 |
| 2051 | 0 |
| 2052 | 0 |
| 2053 | 0 |
| 2054 | 0 |
| 2055 | 0 |
| 2056 | 0 |
| 2057 | 0 |
| 2058 | 0 |
| 2059 | 0 |
| 2060 | 0 |
| 2061 | 0 |
| 2062 | 0 |
| 2063 | 0 |
| 2064 | 0 |
| 2065 | 0 |
| 2066 | 0 |
| 2067 | 0 |
| 2068 | 0 |
| 2069 | 0 |
| 2070 | 0 |
| 2071 | 0 |
| 2072 | 0 |
| 2073 | 0 |
| 2074 | 0 |
| 2075 | 0 |
| 2076 | 0 |
| 2077 | 0 |
| 2078 | 0 |
| 2079 | 0 |
| 2080 | 0 |
| 2081 | 0 |
| 2082 | 0 |
| 2083 | 0 |
| 2084 | 0 |

### COM4

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F175:BN175` | COM4 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D718:BL718` | 61 |
| `F225:BN225` | COM4 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D719:BL719` | 61 |
| `F312:BN312` | COM4 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D716:BL716` | 61 |
| `F362:BN362` | COM4 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D715:BL715` | 61 |

#### Values by Output metric

##### Interest (Ext `F175:BN175` → `PV_Base!D718:BL718`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F225:BN225` → `PV_Base!D719:BL719`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F312:BN312` → `PV_Base!D716:BL716`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F362:BN362` → `PV_Base!D715:BL715`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### COM5

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F176:BN176` | COM5 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D744:BL744` | 61 |
| `F226:BN226` | COM5 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D745:BL745` | 61 |
| `F313:BN313` | COM5 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D742:BL742` | 61 |
| `F363:BN363` | COM5 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D741:BL741` | 61 |

#### Values by Output metric

##### Interest (Ext `F176:BN176` → `PV_Base!D744:BL744`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (Ext `F226:BN226` → `PV_Base!D745:BL745`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (Ext `F313:BN313` → `PV_Base!D742:BL742`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (Ext `F363:BN363` → `PV_Base!D741:BL741`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### Bonds (1 to 3 years)-FX

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F183:BN183` | Bonds (1 to 3 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D770:BL770` | 61 |
| `F188:BN188` | Bonds (1 to 3 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D848:BL848` | 61 |
| `F233:BN233` | Bonds (1 to 3 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D771:BL771` | 61 |
| `F238:BN238` | Bonds (1 to 3 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D849:BL849` | 61 |
| `F320:BN320` | Bonds (1 to 3 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D768:BL768` | 61 |
| `F325:BN325` | Bonds (1 to 3 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D846:BL846` | 61 |
| `F370:BN370` | Bonds (1 to 3 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D767:BL767` | 61 |
| `F375:BN375` | Bonds (1 to 3 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D845:BL845` | 61 |

#### Values by Output metric

##### Interest (block 1: Ext `F183:BN183`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Interest (block 2: Ext `F188:BN188`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (block 1: Ext `F233:BN233`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (block 2: Ext `F238:BN238`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (block 1: Ext `F320:BN320`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (block 2: Ext `F325:BN325`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (block 1: Ext `F370:BN370`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (block 2: Ext `F375:BN375`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### Bonds (4 to 7 years)-FX

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F184:BN184` | Bonds (4 to 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D796:BL796` | 61 |
| `F189:BN189` | Bonds (4 to 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D874:BL874` | 61 |
| `F234:BN234` | Bonds (4 to 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D797:BL797` | 61 |
| `F239:BN239` | Bonds (4 to 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D875:BL875` | 61 |
| `F321:BN321` | Bonds (4 to 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D794:BL794` | 61 |
| `F326:BN326` | Bonds (4 to 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D872:BL872` | 61 |
| `F371:BN371` | Bonds (4 to 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D793:BL793` | 61 |
| `F376:BN376` | Bonds (4 to 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D871:BL871` | 61 |

#### Values by Output metric

##### Interest (block 1: Ext `F184:BN184`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Interest (block 2: Ext `F189:BN189`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (block 1: Ext `F234:BN234`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (block 2: Ext `F239:BN239`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (block 1: Ext `F321:BN321`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (block 2: Ext `F326:BN326`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (block 1: Ext `F371:BN371`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (block 2: Ext `F376:BN376`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


### Bonds (beyond 7 years)-FX

| Ext_Debt_Data range | Ext_Debt label | Section | PV_Base metric | Ext_Debt calculates | PV_Base range | # cells |
|---------------------|----------------|---------|----------------|---------------------|---------------|--------:|
| `F185:BN185` | Bonds (beyond 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D822:BL822` | 61 |
| `F190:BN190` | Bonds (beyond 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D900:BL900` | 61 |
| `F235:BN235` | Bonds (beyond 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D823:BL823` | 61 |
| `F240:BN240` | Bonds (beyond 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D901:BL901` | 61 |
| `F322:BN322` | Bonds (beyond 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D820:BL820` | 61 |
| `F327:BN327` | Bonds (beyond 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D898:BL898` | 61 |
| `F372:BN372` | Bonds (beyond 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D819:BL819` | 61 |
| `F377:BN377` | Bonds (beyond 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D897:BL897` | 61 |

#### Values by Output metric

##### Interest (block 1: Ext `F185:BN185`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Interest (block 2: Ext `F190:BN190`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Interest** (R142) → **Total new debt service** (R140) and **Total public debt service → of which: interest** (R396).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (block 1: Ext `F235:BN235`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Amortization (block 2: Ext `F240:BN240`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Amortization** (R192) → **Total new debt service** (R140) and **Total public debt service → of which: principal** (R395).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (block 1: Ext `F322:BN322`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### PV of debt (block 2: Ext `F327:BN327`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **PV of new MLT debt** (R279) → **Total PV of debt** (R391).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (block 1: Ext `F372:BN372`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


##### Stock of new forex debt (in USD) (block 2: Ext `F377:BN377`)

- Section: **external** (Output)
- Used to calculate: Ext_Debt **Nominal value of new MLT debt** (R329) → Macro-Debt_Data MLT public external stock and **Nominal PPG debt check** (R393).
- Values: _all zero / empty_ (2024–2084, 61 years)


## Full flat list (by Ext_Debt row)

| Ext_Debt range | Label | Instrument | Section | Metric | Ext_Debt calculates | PV_Base range | Values (nonzero) |
|----------------|-------|------------|---------|--------|---------------------|---------------|------------------|
| `F144:BN144` | IMF | IMF | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D27:BL27` | _all zero / empty_ (2024–2084, 61 years) |
| `F145:BN145` | IDA - regular | IDA - regular | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D69:BL69` | 2025: **1.125**; 2026: **1.275**; 2027: **2.13523**; 2028: **2.92738**; 2029: **4.42738**; 2030: **5.92738**; 2031: **5.92738**; 2032: **5.89223**; 2033: **5.85238**; 2034: **5.78566**; 2035: **5.69418**; 2036: **5.55582** … +20 more … 2057: **1.66598**; 2058: **1.48075**; 2059: **1.29551**; 2060: **1.11028**; 2061: **0.925053**; 2062: **0.739822** _(n=61 years, 38 nonzero)_ |
| `F146:BN146` | IDA - 50Y loans | IDA - 50Y loans | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D95:BL95` | _all zero / empty_ (2024–2084, 61 years) |
| `F147:BN147` | IDA - SML | IDA - SML | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D120:BL120` | _all zero / empty_ (2024–2084, 61 years) |
| `F148:BN148` | IDA NEW 40-year credits | IDA NEW 40-year credits | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D144:BL144` | _all zero / empty_ (2024–2084, 61 years) |
| `F149:BN149` | IDA NEW Regular | IDA NEW Regular | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D168:BL168` | 2027: **0.75**; 2028: **0.75**; 2029: **0.75**; 2030: **0.75**; 2031: **0.75**; 2032: **0.75**; 2033: **0.75**; 2034: **0.72**; 2035: **0.69**; 2036: **0.66**; 2037: **0.63**; 2038: **0.6** … +13 more … 2052: **0.18**; 2053: **0.15**; 2054: **0.12**; 2055: **0.09**; 2056: **0.06**; 2057: **0.03** _(n=61 years, 31 nonzero)_ |
| `F150:BN150` | IDA NEW Blend (also enter) --> | IDA NEW Blend floating | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D192:BL192` | 2026: **0.648**; 2027: **1.944**; 2028: **3.888**; 2029: **3.888**; 2030: **3.888**; 2031: **3.888**; 2032: **3.8556**; 2033: **3.7584**; 2034: **3.564**; 2035: **3.3696**; 2036: **3.1752**; 2037: **2.9808** … +6 more … 2044: **1.62**; 2045: **1.4256**; 2046: **1.2312**; 2047: **1.0368**; 2048: **0.8424**; 2049: **0.648** _(n=61 years, 24 nonzero)_ |
| `F151:BN151` | IDA NEW 60-year credits | IDA NEW 60-year credits | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D216:BL216` | _all zero / empty_ (2024–2084, 61 years) |
| `F152:BN152` | MULTI1 | MULTI1 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D250:BL250` | _all zero / empty_ (2024–2084, 61 years) |
| `F153:BN153` | MULTI2 | MULTI2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D276:BL276` | _all zero / empty_ (2024–2084, 61 years) |
| `F155:BN155` | OTH_MULTI1 | OTH_MULTI1 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D302:BL302` | _all zero / empty_ (2024–2084, 61 years) |
| `F156:BN156` | OTH_MULTI2 | OTH_MULTI2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D328:BL328` | _all zero / empty_ (2024–2084, 61 years) |
| `F157:BN157` | OTH_MULTI3 | OTH_MULTI3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D354:BL354` | _all zero / empty_ (2024–2084, 61 years) |
| `F160:BN160` | Export Credit Agencies | Export Credit Agencies | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D380:BL380` | 2025: **4.71008**; 2026: **14.0165**; 2027: **23.4963**; 2028: **35.4946**; 2029: **45.3877**; 2030: **51.0956**; 2031: **56.4137**; 2032: **65.2719**; 2033: **73.7682**; 2034: **81.54**; 2035: **88.5826**; 2036: **94.7023** … +9 more … 2046: **86.9567**; 2047: **78.248**; 2048: **69.5876**; 2049: **61.3056**; 2050: **53.3762**; 2051: **45.6135** _(n=61 years, 27 nonzero)_ |
| `F161:BN161` | PC2 | PC2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D406:BL406` | _all zero / empty_ (2024–2084, 61 years) |
| `F162:BN162` | PC3 | PC3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D432:BL432` | _all zero / empty_ (2024–2084, 61 years) |
| `F163:BN163` | PC4 | PC4 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D458:BL458` | _all zero / empty_ (2024–2084, 61 years) |
| `F164:BN164` | PC5 | PC5 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D484:BL484` | _all zero / empty_ (2024–2084, 61 years) |
| `F166:BN166` | Export Import Bank of NPC | Export Import Bank of NPC | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D510:BL510` | 2025: **1.90982**; 2026: **1.90982**; 2027: **1.90982**; 2028: **1.90982**; 2029: **1.90982**; 2030: **1.90982**; 2031: **1.71884**; 2032: **1.52786**; 2033: **1.33687**; 2034: **1.14589**; 2035: **0.95491**; 2036: **0.763928**; 2034: **1.14589**; 2035: **0.95491**; 2036: **0.763928**; 2037: **0.572946**; 2038: **0.381964**; 2039: **0.190982** _(n=61 years, 15 nonzero)_ |
| `F167:BN167` | NPC2 | NPC2 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D536:BL536` | _all zero / empty_ (2024–2084, 61 years) |
| `F168:BN168` | NPC3 | NPC3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D562:BL562` | _all zero / empty_ (2024–2084, 61 years) |
| `F169:BN169` | NPC4 | NPC4 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D588:BL588` | _all zero / empty_ (2024–2084, 61 years) |
| `F170:BN170` | NPC5 | NPC5 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D614:BL614` | _all zero / empty_ (2024–2084, 61 years) |
| `F172:BN172` | Eurobond | Eurobond | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D640:BL640` | 2028: **22.5**; 2029: **45**; 2030: **67.5**; 2031: **157.5**; 2032: **187.5**; 2033: **217.5**; 2034: **247.5**; 2035: **247.5**; 2036: **277.5**; 2037: **307.5**; 2038: **337.5**; 2039: **337.5** … +6 more … 2046: **317.5**; 2047: **297.5**; 2048: **265**; 2049: **237.5**; 2050: **212.5**; 2051: **185** _(n=61 years, 24 nonzero)_ |
| `F173:BN173` | Commecial Bank | Commecial Bank | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D666:BL666` | 2025: **12.289**; 2026: **27.2193**; 2027: **40.4892**; 2028: **57.2822**; 2029: **89.1668**; 2030: **136.892**; 2031: **185.015**; 2032: **235.093**; 2033: **295.434**; 2034: **354.354**; 2035: **411.882**; 2036: **467.893** … +9 more … 2046: **830.656**; 2047: **728.951**; 2048: **620.892**; 2049: **506.039**; 2050: **401.068**; 2051: **306.587** _(n=61 years, 27 nonzero)_ |
| `F174:BN174` | COM3 | COM3 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D692:BL692` | 2025: **17.5**; 2026: **17.5**; 2027: **13.125**; 2028: **8.75**; 2029: **4.375** _(other years 0; n=61)_ |
| `F175:BN175` | COM4 | COM4 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D718:BL718` | _all zero / empty_ (2024–2084, 61 years) |
| `F176:BN176` | COM5 | COM5 | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D744:BL744` | _all zero / empty_ (2024–2084, 61 years) |
| `F183:BN183` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D770:BL770` | _all zero / empty_ (2024–2084, 61 years) |
| `F184:BN184` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D796:BL796` | _all zero / empty_ (2024–2084, 61 years) |
| `F185:BN185` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D822:BL822` | _all zero / empty_ (2024–2084, 61 years) |
| `F188:BN188` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D848:BL848` | _all zero / empty_ (2024–2084, 61 years) |
| `F189:BN189` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D874:BL874` | _all zero / empty_ (2024–2084, 61 years) |
| `F190:BN190` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | Interest | Interest → total new debt service / public DS interest | `PV_Base!D900:BL900` | _all zero / empty_ (2024–2084, 61 years) |
| `F194:BN194` | IMF | IMF | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D28:BL28` | _all zero / empty_ (2024–2084, 61 years) |
| `F195:BN195` | IDA - regular | IDA - regular | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D70:BL70` | 2031: **4.6875**; 2032: **5.3125**; 2033: **8.89681**; 2034: **12.1974**; 2035: **18.4474**; 2036: **24.6974**; 2037: **24.6974**; 2038: **24.6974**; 2039: **24.6974**; 2040: **24.6974**; 2041: **24.6974**; 2042: **24.6974** … +14 more … 2057: **24.6974**; 2058: **24.6974**; 2059: **24.6974**; 2060: **24.6974**; 2061: **24.6974**; 2062: **24.6974** _(n=61 years, 32 nonzero)_ |
| `F196:BN196` | IDA - 50Y loans | IDA - 50Y loans | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D96:BL96` | 2036: **2.5**; 2037: **5**; 2038: **7.5**; 2039: **7.5**; 2040: **7.5**; 2041: **7.5**; 2042: **7.5**; 2043: **7.5**; 2044: **7.5**; 2045: **7.5**; 2046: **7.5**; 2047: **7.5** … +21 more … 2069: **7.5**; 2070: **7.5**; 2071: **7.5**; 2072: **7.5**; 2073: **7.5**; 2074: **7.5** _(n=61 years, 39 nonzero)_ |
| `F197:BN197` | IDA - SML | IDA - SML | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D121:BL121` | 2033: **0.833333**; 2034: **1.66667**; 2035: **1.66667**; 2036: **1.66667**; 2037: **1.66667**; 2038: **1.66667**; 2039: **0.833333** _(other years 0; n=61)_ |
| `F198:BN198` | IDA NEW 40-year credits | IDA NEW 40-year credits | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D145:BL145` | 2038: **0.344828**; 2039: **0.344828**; 2040: **0.344828**; 2041: **0.344828**; 2042: **0.344828**; 2043: **0.344828**; 2044: **0.344828**; 2045: **0.344828**; 2046: **0.344828**; 2047: **0.344828**; 2048: **0.344828**; 2049: **0.344828** … +9 more … 2059: **0.344828**; 2060: **0.344828**; 2061: **0.344828**; 2062: **0.344828**; 2063: **0.344828**; 2064: **0.344828** _(n=61 years, 27 nonzero)_ |
| `F199:BN199` | IDA NEW Regular | IDA NEW Regular | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D169:BL169` | 2033: **4**; 2034: **4**; 2035: **4**; 2036: **4**; 2037: **4**; 2038: **4**; 2039: **4**; 2040: **4**; 2041: **4**; 2042: **4**; 2043: **4**; 2044: **4** … +7 more … 2052: **4**; 2053: **4**; 2054: **4**; 2055: **4**; 2056: **4**; 2057: **4** _(n=61 years, 25 nonzero)_ |
| `F200:BN200` | IDA NEW Blend (also enter) --> | IDA NEW Blend floating | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D193:BL193` | 2031: **1**; 2032: **3**; 2033: **6**; 2034: **6**; 2035: **6**; 2036: **6**; 2037: **6**; 2038: **6**; 2039: **6**; 2040: **6**; 2041: **6**; 2042: **6** … +1 more … 2044: **6**; 2045: **6**; 2046: **6**; 2047: **6**; 2048: **6**; 2049: **6** _(n=61 years, 19 nonzero)_ |
| `F201:BN201` | IDA NEW 60-year credits | IDA NEW 60-year credits | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D217:BL217` | 2046: **0.5**; 2047: **1.5**; 2048: **3**; 2049: **3**; 2050: **3**; 2051: **3**; 2052: **3**; 2053: **3**; 2054: **3**; 2055: **3**; 2056: **3**; 2057: **3** … +21 more … 2079: **3**; 2080: **3**; 2081: **3**; 2082: **3**; 2083: **3**; 2084: **3** _(n=61 years, 39 nonzero)_ |
| `F202:BN202` | MULTI1 | MULTI1 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D251:BL251` | _all zero / empty_ (2024–2084, 61 years) |
| `F203:BN203` | MULTI2 | MULTI2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D277:BL277` | _all zero / empty_ (2024–2084, 61 years) |
| `F205:BN205` | OTH_MULTI1 | OTH_MULTI1 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D303:BL303` | _all zero / empty_ (2024–2084, 61 years) |
| `F206:BN206` | OTH_MULTI2 | OTH_MULTI2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D329:BL329` | _all zero / empty_ (2024–2084, 61 years) |
| `F207:BN207` | OTH_MULTI3 | OTH_MULTI3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D355:BL355` | _all zero / empty_ (2024–2084, 61 years) |
| `F210:BN210` | Export Credit Agencies | Export Credit Agencies | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D381:BL381` | 2032: **20.4697**; 2033: **60.9149**; 2034: **102.114**; 2035: **154.257**; 2036: **197.252**; 2037: **222.058**; 2038: **245.17**; 2039: **283.667**; 2040: **322.167**; 2041: **360.628**; 2042: **399.09**; 2043: **437.551** … +2 more … 2046: **492.021**; 2047: **489.284**; 2048: **467.909**; 2049: **447.992**; 2050: **438.57**; 2051: **423.15** _(n=61 years, 20 nonzero)_ |
| `F211:BN211` | PC2 | PC2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D407:BL407` | _all zero / empty_ (2024–2084, 61 years) |
| `F212:BN212` | PC3 | PC3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D433:BL433` | _all zero / empty_ (2024–2084, 61 years) |
| `F213:BN213` | PC4 | PC4 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D459:BL459` | _all zero / empty_ (2024–2084, 61 years) |
| `F214:BN214` | PC5 | PC5 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D485:BL485` | _all zero / empty_ (2024–2084, 61 years) |
| `F216:BN216` | Export Import Bank of NPC | Export Import Bank of NPC | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D511:BL511` | 2030: **6.00573**; 2031: **6.00573**; 2032: **6.00573**; 2033: **6.00573**; 2034: **6.00573**; 2035: **6.00573**; 2036: **6.00573**; 2037: **6.00573**; 2038: **6.00573**; 2039: **6.00573**; 2034: **6.00573**; 2035: **6.00573**; 2036: **6.00573**; 2037: **6.00573**; 2038: **6.00573**; 2039: **6.00573** _(n=61 years, 10 nonzero)_ |
| `F217:BN217` | NPC2 | NPC2 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D537:BL537` | _all zero / empty_ (2024–2084, 61 years) |
| `F218:BN218` | NPC3 | NPC3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D563:BL563` | _all zero / empty_ (2024–2084, 61 years) |
| `F219:BN219` | NPC4 | NPC4 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D589:BL589` | _all zero / empty_ (2024–2084, 61 years) |
| `F220:BN220` | NPC5 | NPC5 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D615:BL615` | _all zero / empty_ (2024–2084, 61 years) |
| `F222:BN222` | Eurobond | Eurobond | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D641:BL641` | 2037: **83.3333**; 2038: **166.667**; 2039: **250**; 2040: **500**; 2041: **527.778**; 2042: **555.556**; 2043: **333.333**; 2044: **222.222**; 2045: **222.222**; 2046: **222.222**; 2047: **361.111**; 2048: **305.556**; 2046: **222.222**; 2047: **361.111**; 2048: **305.556**; 2049: **277.778**; 2050: **305.556**; 2051: **425.926** _(n=61 years, 15 nonzero)_ |
| `F223:BN223` | Commecial Bank | Commecial Bank | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D667:BL667` | 2028: **27.309**; 2029: **60.4873**; 2030: **89.976**; 2031: **127.294**; 2032: **201.183**; 2033: **313.96**; 2034: **430.898**; 2035: **556.325**; 2036: **712.771**; 2037: **851.278**; 2038: **993.818**; 2039: **1,151** … +6 more … 2046: **2,034**; 2047: **2,161**; 2048: **2,297**; 2049: **2,099**; 2050: **1,890**; 2051: **1,667** _(n=61 years, 24 nonzero)_ |
| `F224:BN224` | COM3 | COM3 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D693:BL693` | 2026: **87.5**; 2027: **87.5**; 2028: **87.5**; 2029: **87.5** _(other years 0; n=61)_ |
| `F225:BN225` | COM4 | COM4 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D719:BL719` | _all zero / empty_ (2024–2084, 61 years) |
| `F226:BN226` | COM5 | COM5 | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D745:BL745` | _all zero / empty_ (2024–2084, 61 years) |
| `F233:BN233` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D771:BL771` | _all zero / empty_ (2024–2084, 61 years) |
| `F234:BN234` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D797:BL797` | _all zero / empty_ (2024–2084, 61 years) |
| `F235:BN235` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D823:BL823` | _all zero / empty_ (2024–2084, 61 years) |
| `F238:BN238` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D849:BL849` | _all zero / empty_ (2024–2084, 61 years) |
| `F239:BN239` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D875:BL875` | _all zero / empty_ (2024–2084, 61 years) |
| `F240:BN240` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | Amortization | Amortization → total new debt service / public DS principal | `PV_Base!D901:BL901` | _all zero / empty_ (2024–2084, 61 years) |
| `F281:BN281` | IMF | IMF | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D25:BL25` | _all zero / empty_ (2024–2084, 61 years) |
| `F282:BN282` | IDA - regular | IDA - regular | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D67:BL67` | 2024: **69.4845**; 2025: **81.0984**; 2026: **137.01**; 2027: **190.652**; 2028: **289.903**; 2029: **392.617**; 2030: **406.32**; 2031: **416.021**; 2032: **425.617**; 2033: **432.149**; 2034: **435.774**; 2035: **433.421** … +21 more … 2057: **164.106**; 2058: **146.133**; 2059: **127.446**; 2060: **108.011**; 2061: **87.789**; 2062: **66.7411** _(n=61 years, 39 nonzero)_ |
| `F283:BN283` | IDA - 50Y loans | IDA - 50Y loans | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D93:BL93` | 2025: **26.3355**; 2026: **53.9877**; 2027: **83.0226**; 2028: **87.1737**; 2029: **91.5324**; 2030: **96.109**; 2031: **100.914**; 2032: **105.96**; 2033: **111.258**; 2034: **116.821**; 2035: **122.662**; 2036: **126.295** … +32 more … 2069: **43.3132**; 2070: **37.9789**; 2071: **32.3778**; 2072: **26.4967**; 2073: **20.3215**; 2074: **13.8376** _(n=61 years, 50 nonzero)_ |
| `F284:BN284` | IDA - SML | IDA - SML | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D118:BL118` | 2026: **3.1563**; 2027: **6.47041**; 2028: **6.79393**; 2029: **7.13363**; 2030: **7.49031**; 2031: **7.86483**; 2032: **8.25807**; 2033: **7.83764**; 2034: **6.56286**; 2035: **5.22433**; 2036: **3.81888**; 2037: **2.34316**; 2033: **7.83764**; 2034: **6.56286**; 2035: **5.22433**; 2036: **3.81888**; 2037: **2.34316**; 2038: **0.793651** _(n=61 years, 13 nonzero)_ |
| `F285:BN285` | IDA NEW 40-year credits | IDA NEW 40-year credits | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D142:BL142` | 2026: **3.05265**; 2027: **3.20528**; 2028: **3.36554**; 2029: **3.53382**; 2030: **3.71051**; 2031: **3.89604**; 2032: **4.09084**; 2033: **4.29538**; 2034: **4.51015**; 2035: **4.73566**; 2036: **4.97244**; 2037: **5.22106** … +21 more … 2059: **1.9953**; 2060: **1.75024**; 2061: **1.49292**; 2062: **1.22274**; 2063: **0.939051**; 2064: **0.641176** _(n=61 years, 39 nonzero)_ |
| `F286:BN286` | IDA NEW Regular | IDA NEW Regular | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D166:BL166` | 2026: **50.7582**; 2027: **52.5461**; 2028: **54.4234**; 2029: **56.3946**; 2030: **58.4643**; 2031: **60.6375**; 2032: **62.9194**; 2033: **61.3154**; 2034: **59.6612**; 2035: **57.9542**; 2036: **56.1919**; 2037: **54.3715** … +13 more … 2051: **20.8574**; 2052: **17.7202**; 2053: **14.4562**; 2054: **11.059**; 2055: **7.522**; 2056: **3.8381** _(n=61 years, 31 nonzero)_ |
| `F287:BN287` | IDA NEW Blend (also enter) --> | IDA NEW Blend floating | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D190:BL190` | 2025: **16.3971**; 2026: **49.3631**; 2027: **99.0786**; 2028: **100.144**; 2029: **101.264**; 2030: **102.439**; 2031: **102.673**; 2032: **100.951**; 2033: **96.24**; 2034: **91.488**; 2035: **86.6928**; 2036: **81.8523** … +7 more … 2044: **41.1974**; 2045: **35.8317**; 2046: **30.3921**; 2047: **24.8749**; 2048: **19.2762**; 2049: **13.592** _(n=61 years, 25 nonzero)_ |
| `F288:BN288` | IDA NEW 60-year credits | IDA NEW 60-year credits | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D214:BL214` | 2025: **3.23354**; 2026: **9.8623**; 2027: **20.056**; 2028: **21.0588**; 2029: **22.1118**; 2030: **23.2174**; 2031: **24.3782**; 2032: **25.5971**; 2033: **26.877**; 2034: **28.2208**; 2035: **29.6319**; 2036: **31.1135** … +42 more … 2079: **18.019**; 2080: **15.92**; 2081: **13.716**; 2082: **11.4018**; 2083: **8.97188**; 2084: **6.42047** _(n=61 years, 60 nonzero)_ |
| `F289:BN289` | MULTI1 | MULTI1 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D248:BL248` | _all zero / empty_ (2024–2084, 61 years) |
| `F290:BN290` | MULTI2 | MULTI2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D274:BL274` | _all zero / empty_ (2024–2084, 61 years) |
| `F292:BN292` | OTH_MULTI1 | OTH_MULTI1 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D300:BL300` | _all zero / empty_ (2024–2084, 61 years) |
| `F293:BN293` | OTH_MULTI2 | OTH_MULTI2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D326:BL326` | _all zero / empty_ (2024–2084, 61 years) |
| `F294:BN294` | OTH_MULTI3 | OTH_MULTI3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D352:BL352` | _all zero / empty_ (2024–2084, 61 years) |
| `F297:BN297` | Export Credit Agencies | Export Credit Agencies | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D378:BL378` | 2024: **182.479**; 2025: **547.445**; 2026: **928.07**; 2027: **1,416**; 2028: **1,834**; 2029: **2,102**; 2030: **2,362**; 2031: **2,767**; 2032: **3,163**; 2033: **3,529**; 2034: **3,865**; 2035: **4,158** … +10 more … 2046: **3,736**; 2047: **3,355**; 2048: **2,985**; 2049: **2,625**; 2050: **2,265**; 2051: **1,909** _(n=61 years, 28 nonzero)_ |
| `F298:BN298` | PC2 | PC2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D404:BL404` | _all zero / empty_ (2024–2084, 61 years) |
| `F299:BN299` | PC3 | PC3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D430:BL430` | _all zero / empty_ (2024–2084, 61 years) |
| `F300:BN300` | PC4 | PC4 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D456:BL456` | _all zero / empty_ (2024–2084, 61 years) |
| `F301:BN301` | PC5 | PC5 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D482:BL482` | _all zero / empty_ (2024–2084, 61 years) |
| `F303:BN303` | Export Import Bank of NPC | Export Import Bank of NPC | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D508:BL508` | 2024: **51.4226**; 2025: **52.0839**; 2026: **52.7783**; 2027: **53.5074**; 2028: **54.2729**; 2029: **55.0768**; 2030: **49.9151**; 2031: **44.6863**; 2032: **39.387**; 2033: **34.0137**; 2034: **28.5628**; 2035: **23.0303**; 2033: **34.0137**; 2034: **28.5628**; 2035: **23.0303**; 2036: **17.4122**; 2037: **11.7041**; 2038: **5.90163** _(n=61 years, 15 nonzero)_ |
| `F304:BN304` | NPC2 | NPC2 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D534:BL534` | _all zero / empty_ (2024–2084, 61 years) |
| `F305:BN305` | NPC3 | NPC3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D560:BL560` | _all zero / empty_ (2024–2084, 61 years) |
| `F306:BN306` | NPC4 | NPC4 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D586:BL586` | _all zero / empty_ (2024–2084, 61 years) |
| `F307:BN307` | NPC5 | NPC5 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D612:BL612` | _all zero / empty_ (2024–2084, 61 years) |
| `F309:BN309` | Eurobond | Eurobond | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D638:BL638` | 2027: **250**; 2028: **500**; 2029: **750**; 2030: **1,750**; 2031: **2,083**; 2032: **2,417**; 2033: **2,750**; 2034: **2,750**; 2035: **3,083**; 2036: **3,417**; 2037: **3,750**; 2038: **3,750** … +7 more … 2046: **3,306**; 2047: **2,944**; 2048: **2,639**; 2049: **2,361**; 2050: **2,056**; 2051: **1,630** _(n=61 years, 25 nonzero)_ |
| `F310:BN310` | Commecial Bank | Commecial Bank | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D664:BL664` | 2024: **245.781**; 2025: **544.386**; 2026: **809.784**; 2027: **1,146**; 2028: **1,783**; 2029: **2,738**; 2030: **3,700**; 2031: **4,702**; 2032: **5,909**; 2033: **7,087**; 2034: **8,238**; 2035: **9,358** … +10 more … 2046: **1.458e+04**; 2047: **1.242e+04**; 2048: **1.012e+04**; 2049: **8,021**; 2050: **6,132**; 2051: **4,465** _(n=61 years, 28 nonzero)_ |
| `F311:BN311` | COM3 | COM3 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D690:BL690` | 2024: **350**; 2025: **350**; 2026: **262.5**; 2027: **175**; 2028: **87.5** _(other years 0; n=61)_ |
| `F312:BN312` | COM4 | COM4 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D716:BL716` | _all zero / empty_ (2024–2084, 61 years) |
| `F313:BN313` | COM5 | COM5 | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D742:BL742` | _all zero / empty_ (2024–2084, 61 years) |
| `F320:BN320` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D768:BL768` | _all zero / empty_ (2024–2084, 61 years) |
| `F321:BN321` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D794:BL794` | _all zero / empty_ (2024–2084, 61 years) |
| `F322:BN322` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D820:BL820` | _all zero / empty_ (2024–2084, 61 years) |
| `F325:BN325` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D846:BL846` | _all zero / empty_ (2024–2084, 61 years) |
| `F326:BN326` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D872:BL872` | _all zero / empty_ (2024–2084, 61 years) |
| `F327:BN327` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | PV of debt | PV of new MLT debt → Total PV of debt | `PV_Base!D898:BL898` | _all zero / empty_ (2024–2084, 61 years) |
| `F331:BN331` | IMF | IMF | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D24:BL24` | _all zero / empty_ (2024–2084, 61 years) |
| `F332:BN332` | IDA - regular | IDA - regular | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D66:BL66` | 2024: **150**; 2025: **170**; 2026: **284.698**; 2027: **390.318**; 2028: **590.318**; 2029: **790.318**; 2030: **790.318**; 2031: **785.63**; 2032: **780.318**; 2033: **771.421**; 2034: **759.224**; 2035: **740.776** … +21 more … 2057: **197.433**; 2058: **172.735**; 2059: **148.038**; 2060: **123.34**; 2061: **98.6429**; 2062: **73.9455** _(n=61 years, 39 nonzero)_ |
| `F333:BN333` | IDA - 50Y loans | IDA - 50Y loans | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D92:BL92` | 2025: **100**; 2026: **200**; 2027: **300**; 2028: **300**; 2029: **300**; 2030: **300**; 2031: **300**; 2032: **300**; 2033: **300**; 2034: **300**; 2035: **300**; 2036: **297.5** … +32 more … 2069: **52.5**; 2070: **45**; 2071: **37.5**; 2072: **30**; 2073: **22.5**; 2074: **15** _(n=61 years, 50 nonzero)_ |
| `F334:BN334` | IDA - SML | IDA - SML | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D117:BL117` | 2026: **5**; 2027: **10**; 2028: **10**; 2029: **10**; 2030: **10**; 2031: **10**; 2032: **10**; 2033: **9.16667**; 2034: **7.5**; 2035: **5.83333**; 2036: **4.16667**; 2037: **2.5**; 2033: **9.16667**; 2034: **7.5**; 2035: **5.83333**; 2036: **4.16667**; 2037: **2.5**; 2038: **0.833333** _(n=61 years, 13 nonzero)_ |
| `F335:BN335` | IDA NEW 40-year credits | IDA NEW 40-year credits | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D141:BL141` | 2026: **10**; 2027: **10**; 2028: **10**; 2029: **10**; 2030: **10**; 2031: **10**; 2032: **10**; 2033: **10**; 2034: **10**; 2035: **10**; 2036: **10**; 2037: **10** … +21 more … 2059: **2.41379**; 2060: **2.06897**; 2061: **1.72414**; 2062: **1.37931**; 2063: **1.03448**; 2064: **0.689655** _(n=61 years, 39 nonzero)_ |
| `F336:BN336` | IDA NEW Regular | IDA NEW Regular | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D165:BL165` | 2026: **100**; 2027: **100**; 2028: **100**; 2029: **100**; 2030: **100**; 2031: **100**; 2032: **100**; 2033: **96**; 2034: **92**; 2035: **88**; 2036: **84**; 2037: **80** … +13 more … 2051: **24**; 2052: **20**; 2053: **16**; 2054: **12**; 2055: **8**; 2056: **4** _(n=61 years, 31 nonzero)_ |
| `F337:BN337` | IDA NEW Blend (also enter) --> | IDA NEW Blend floating | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D189:BL189` | 2025: **20**; 2026: **60**; 2027: **120**; 2028: **120**; 2029: **120**; 2030: **120**; 2031: **119**; 2032: **116**; 2033: **110**; 2034: **104**; 2035: **98**; 2036: **92** … +7 more … 2044: **44**; 2045: **38**; 2046: **32**; 2047: **26**; 2048: **20**; 2049: **14** _(n=61 years, 25 nonzero)_ |
| `F338:BN338` | IDA NEW 60-year credits | IDA NEW 60-year credits | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D213:BL213` | 2025: **20**; 2026: **60**; 2027: **120**; 2028: **120**; 2029: **120**; 2030: **120**; 2031: **120**; 2032: **120**; 2033: **120**; 2034: **120**; 2035: **120**; 2036: **120** … +42 more … 2079: **22**; 2080: **19**; 2081: **16**; 2082: **13**; 2083: **10**; 2084: **7** _(n=61 years, 60 nonzero)_ |
| `F339:BN339` | MULTI1 | MULTI1 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D247:BL247` | _all zero / empty_ (2024–2084, 61 years) |
| `F340:BN340` | MULTI2 | MULTI2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D273:BL273` | _all zero / empty_ (2024–2084, 61 years) |
| `F342:BN342` | OTH_MULTI1 | OTH_MULTI1 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D299:BL299` | _all zero / empty_ (2024–2084, 61 years) |
| `F343:BN343` | OTH_MULTI2 | OTH_MULTI2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D325:BL325` | _all zero / empty_ (2024–2084, 61 years) |
| `F344:BN344` | OTH_MULTI3 | OTH_MULTI3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D351:BL351` | _all zero / empty_ (2024–2084, 61 years) |
| `F347:BN347` | Export Credit Agencies | Export Credit Agencies | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D377:BL377` | 2024: **266.106**; 2025: **791.894**; 2026: **1,327**; 2027: **2,005**; 2028: **2,564**; 2029: **2,887**; 2030: **3,187**; 2031: **3,688**; 2032: **4,168**; 2033: **4,607**; 2034: **5,005**; 2035: **5,350** … +10 more … 2046: **4,421**; 2047: **3,932**; 2048: **3,464**; 2049: **3,016**; 2050: **2,577**; 2051: **2,154** _(n=61 years, 28 nonzero)_ |
| `F348:BN348` | PC2 | PC2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D403:BL403` | _all zero / empty_ (2024–2084, 61 years) |
| `F349:BN349` | PC3 | PC3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D429:BL429` | _all zero / empty_ (2024–2084, 61 years) |
| `F350:BN350` | PC4 | PC4 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D455:BL455` | _all zero / empty_ (2024–2084, 61 years) |
| `F351:BN351` | PC5 | PC5 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D481:BL481` | _all zero / empty_ (2024–2084, 61 years) |
| `F353:BN353` | Export Import Bank of NPC | Export Import Bank of NPC | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D507:BL507` | 2024: **60.0573**; 2025: **60.0573**; 2026: **60.0573**; 2027: **60.0573**; 2028: **60.0573**; 2029: **60.0573**; 2030: **54.0515**; 2031: **48.0458**; 2032: **42.0401**; 2033: **36.0344**; 2034: **30.0286**; 2035: **24.0229**; 2033: **36.0344**; 2034: **30.0286**; 2035: **24.0229**; 2036: **18.0172**; 2037: **12.0115**; 2038: **6.00573** _(n=61 years, 15 nonzero)_ |
| `F354:BN354` | NPC2 | NPC2 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D533:BL533` | _all zero / empty_ (2024–2084, 61 years) |
| `F355:BN355` | NPC3 | NPC3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D559:BL559` | _all zero / empty_ (2024–2084, 61 years) |
| `F356:BN356` | NPC4 | NPC4 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D585:BL585` | _all zero / empty_ (2024–2084, 61 years) |
| `F357:BN357` | NPC5 | NPC5 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D611:BL611` | _all zero / empty_ (2024–2084, 61 years) |
| `F359:BN359` | Eurobond | Eurobond | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D637:BL637` | 2027: **250**; 2028: **500**; 2029: **750**; 2030: **1,750**; 2031: **2,083**; 2032: **2,417**; 2033: **2,750**; 2034: **2,750**; 2035: **3,083**; 2036: **3,417**; 2037: **3,750**; 2038: **3,750** … +7 more … 2046: **3,306**; 2047: **2,944**; 2048: **2,639**; 2049: **2,361**; 2050: **2,056**; 2051: **1,630** _(n=61 years, 25 nonzero)_ |
| `F360:BN360` | Commecial Bank | Commecial Bank | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D663:BL663` | 2024: **245.781**; 2025: **544.386**; 2026: **809.784**; 2027: **1,146**; 2028: **1,783**; 2029: **2,738**; 2030: **3,700**; 2031: **4,702**; 2032: **5,909**; 2033: **7,087**; 2034: **8,238**; 2035: **9,358** … +10 more … 2046: **1.458e+04**; 2047: **1.242e+04**; 2048: **1.012e+04**; 2049: **8,021**; 2050: **6,132**; 2051: **4,465** _(n=61 years, 28 nonzero)_ |
| `F361:BN361` | COM3 | COM3 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D689:BL689` | 2024: **350**; 2025: **350**; 2026: **262.5**; 2027: **175**; 2028: **87.5** _(other years 0; n=61)_ |
| `F362:BN362` | COM4 | COM4 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D715:BL715` | _all zero / empty_ (2024–2084, 61 years) |
| `F363:BN363` | COM5 | COM5 | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D741:BL741` | _all zero / empty_ (2024–2084, 61 years) |
| `F370:BN370` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D767:BL767` | _all zero / empty_ (2024–2084, 61 years) |
| `F371:BN371` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D793:BL793` | _all zero / empty_ (2024–2084, 61 years) |
| `F372:BN372` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D819:BL819` | _all zero / empty_ (2024–2084, 61 years) |
| `F375:BN375` | Bonds (1 to 3 years)-FX | Bonds (1 to 3 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D845:BL845` | _all zero / empty_ (2024–2084, 61 years) |
| `F376:BN376` | Bonds (4 to 7 years)-FX | Bonds (4 to 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D871:BL871` | _all zero / empty_ (2024–2084, 61 years) |
| `F377:BN377` | Bonds (beyond 7 years)-FX | Bonds (beyond 7 years)-FX | **external** | Stock of new forex debt (in USD) | Nominal new MLT debt → Macro-Debt MLT stock / PPG check | `PV_Base!D897:BL897` | _all zero / empty_ (2024–2084, 61 years) |
