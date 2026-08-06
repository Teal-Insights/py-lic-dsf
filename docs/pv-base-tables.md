# PV_Base table breakdown

Sheet: `PV_Base` in `data/lic-dsf-template-2025-08-12.xlsx`  
Extent: `A1:BM901` (≈901 rows × 65 columns)  
Title (A2): **NPV Calculations for New Loans**

## How many tables?

**34 instrument tables**, plus a thin header and a few category banners.

| Kind | Count | What it is |
|------|------:|------------|
| Instrument NPV tables | **34** | One repeated template per external financing line |
| Category banners | 6 | Section labels pulled from `Ext_Debt_Data` |
| Year header | 1 | Projection years across columns |
| Sheet title | 1 | “NPV Calculations for New Loans” |

There is **no separate grand-total table** on this sheet. Aggregation happens downstream (mainly `Ext_Debt_Data`), which consumes each instrument’s **Output** block.

Year axis: row 7, columns **D–BL** → **2024–2084** (61 years).

---

## Anatomy of one instrument table

Every one of the 34 blocks is the same machine with different terms and disbursements (names/terms come from `Input 4 - External Financing`).

```text
┌─ Instrument name          (e.g. IMF)          ← from Input 4 col B
├─ Grace / Maturity / Interest / Discount       ← loan terms (time series)
├─ Internal calc rows (col C labels):
│    Base, Debt stock, Amortization, Interest,
│    Total debt service, PV of debt,
│    Grant element, t-g>0, t-m condition
└─ Output <name>                                ← what Ext_Debt_Data reads
     New forex borrowing (gross, USD)
     cumulative
     Stock of new forex debt (in USD)
     PV of debt   <name>
     Total debt service (in USD)
     Interest
     Amortization
```

**Goal of each table:** take that line’s **new disbursements + contractual terms**, build the repayment path, discount it, and emit USD stock / PV / debt-service series.

**Typical outputs (per year):**

| Output row | Role |
|------------|------|
| New forex borrowing (gross, USD) | Disbursements in the year |
| cumulative | Running sum of disbursements |
| Stock of new forex debt (in USD) | Outstanding stock |
| PV of debt \<name\> | Present value of remaining debt service |
| Total debt service (in USD) | Interest + amortization |
| Interest / Amortization | Split of service |

**Internal checks:**

| Label | Role |
|-------|------|
| Grant element | Concessionality of the loan |
| `t-g>0` | Term vs grace sanity check |
| `t-m condition` | Term vs maturity condition |

IMF’s Output block is slightly richer (extra repayment-schedule / IDA-term subtype rows: Small economy, Regular, Blend, SML, 50Y loans) before the next instrument starts.

---

## Category map (6 banners + 34 instruments)

Category labels are formulas pointing at `Ext_Debt_Data` section headers.

### 1. Multilaterals (banner row 3)

IMF + IDA family + other named multilaterals.

| # | Rows (approx.) | Instrument | Source name (`Input 4`) |
|--:|----------------|------------|-------------------------|
| 1 | 8–48 | **IMF** | `B10` |
| 2 | 49–74 | **IDA - regular** | IDA terms block |
| 3 | 75–99 | **IDA - 50Y loans** | |
| 4 | 100–123 | **IDA - SML** | |
| 5 | 124–147 | **IDA NEW 40-year credits** | |
| 6 | 148–171 | **IDA NEW Regular** | |
| 7 | 172–195 | **IDA NEW Blend floating** | |
| 8 | 196–229 | **IDA NEW 60-year credits** | |
| 9 | 230–255 | **MULTI1** | `B18` |
| 10 | 256–281 | **MULTI2** | `B19` |

**Doing:** NPV of new borrowing from IMF/IDA/generic multilateral slots under baseline programmed terms.

### 2. Other Multilaterals (banner row 280)

| # | Rows (approx.) | Instrument | Source |
|--:|----------------|------------|--------|
| 11 | 282–307 | **OTH_MULTI1** | `Input 4!B21` |
| 12 | 308–333 | **OTH_MULTI2** | `B22` |
| 13 | 334–359 | **OTH_MULTI3** | `B23` |

**Doing:** Same NPV template for three additional multilateral creditor slots.

### 3. Official Bilaterals → Paris Club (banners rows 358–359)

| # | Rows (approx.) | Instrument | Source |
|--:|----------------|------------|--------|
| 14 | 360–385 | **Export Credit Agencies** | `B26` |
| 15 | 386–411 | **PC2** | `B27` |
| 16 | 412–437 | **PC3** | `B28` |
| 17 | 438–463 | **PC4** | `B29` |
| 18 | 464–489 | **PC5** | `B30` |

**Doing:** NPV for ECA + Paris Club bilateral lines (PC2–PC5 are parameterized Paris Club creditor slots).

### 4. Non-Paris Club (banner row 488)

| # | Rows (approx.) | Instrument | Source |
|--:|----------------|------------|--------|
| 19 | 490–515 | **Export Import Bank of NPC** | `B32` |
| 20 | 516–541 | **NPC2** | `B33` |
| 21 | 542–567 | **NPC3** | `B34` |
| 22 | 568–593 | **NPC4** | `B35` |
| 23 | 594–619 | **NPC5** | `B36` |

**Doing:** NPV for non–Paris Club official bilateral slots.

### 5. Commercial (banner row 618)

| # | Rows (approx.) | Instrument | Source |
|--:|----------------|------------|--------|
| 24 | 620–645 | **Eurobond** | `B38` |
| 25 | 646–671 | **Commecial Bank** *(workbook spelling)* | `B39` |
| 26 | 672–697 | **COM3** | `B40` |
| 27 | 698–723 | **COM4** | `B41` |
| 28 | 724–749 | **COM5** | `B42` |

**Doing:** NPV for market / commercial external borrowing lines.

### 6. FX locally issued bonds (no extra banner; two holder groups)

Same tenor labels appear twice because Input 4 has two holder sections:

1. **FX locally issued, held by non-residents** (`Input 4` rows 52–56)  
2. **FX locally issued, held by residents** (`Input 4` rows 57–61)

| # | Rows (approx.) | Instrument | Holder | Source |
|--:|----------------|------------|--------|--------|
| 29 | 750–775 | **Bonds (1 to 3 years)-FX** | Non-residents | `B54` |
| 30 | 776–801 | **Bonds (4 to 7 years)-FX** | Non-residents | `B55` |
| 31 | 802–827 | **Bonds (beyond 7 years)-FX** | Non-residents | `B56` |
| 32 | 828–853 | **Bonds (1 to 3 years)-FX** | Residents | `B59` |
| 33 | 854–879 | **Bonds (4 to 7 years)-FX** | Residents | `B60` |
| 34 | 880–901 | **Bonds (beyond 7 years)-FX** | Residents | `B61` |

**Doing:** NPV of new FX-denominated *locally issued* bonds, split by tenor and by residency of the holder. (LC non-resident bonds are handled on `PV_LC_NR1/2/3`, not here.)

---

## Count by family

| Family | Tables |
|--------|-------:|
| IMF | 1 |
| IDA / IDA NEW | 7 |
| Other named multilaterals (MULTI / OTH_MULTI) | 5 |
| Paris Club / ECA | 5 |
| Non-Paris Club | 5 |
| Commercial | 5 |
| FX local bonds (NR + resident × 3 tenors) | 6 |
| **Total** | **34** |

---

## Data flow (why these tables exist)

```text
Input 4 (disbursements + terms per line)
        │
        ▼
   PV_Base  × 34 instrument tables
        │  Output: PV, stock, debt service, interest, amortization
        ▼
 Ext_Debt_Data  (aggregates into external DSA stocks/service)
        │
        ▼
   Chart Data / ratings / stress consumers
```

Discount rate for PV comes from the workbook discounting setup (tied to **Input 1 – Basics** discount rate for the DSA), applied inside each instrument’s Discount / PV rows.

---

## Practical reading tip

When the sheet looks like “lots of tables,” it is almost entirely **one template copied 34 times**. Differences are:

1. **Which creditor/instrument** (name + Input 4 link)  
2. **Terms and disbursement paths** for that line  
3. **IMF-only** extra repayment-schedule subtype rows  
4. **Duplicate FX bond tenors** for non-resident vs resident holders  

Everything else (stock, PV, service) is the same output contract repeated.
