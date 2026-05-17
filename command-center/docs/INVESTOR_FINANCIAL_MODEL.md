# Investor Financial Model — Scaffold

**Purpose:** Spreadsheet-ready tables for 12–36 month scenarios and return math. Copy into Excel/Google Sheets or link from Airtable.  
**Fill every `[FILL]` with audited or bank-supported numbers before investor meetings.**

**Airtable templates (import to base `appcenWUju039rD7b` or your base):**

| Template | Path | Use in model |
|----------|------|----------------|
| Vehicles | `AIX_AI_COMMAND_SYSTEM/airtable_templates/Vehicles.csv` | Fleet count, status |
| Bookings | `AIX_AI_COMMAND_SYSTEM/aix-command-system/airtable_templates/Bookings.csv` | Utilization, ADR |
| Income | `airtable_templates/Income.csv` | Revenue actuals |
| Expenses | `airtable_templates/Expenses.csv` | COGS + opex |
| Bills | `airtable_templates/Bills.csv` | Fixed cost timing |
| Weekly Money Review | `airtable_templates/Weekly_Money_Review.csv` | Owner rhythm |
| Dealership Fleets | `airtable_templates/Dealership_Fleets.csv` | Dealer track |
| Shared Lot Inventory | `airtable_templates/Shared_Lot_Inventory.csv` | Lot mix |

**Config reference:** `AIX_AI_COMMAND_SYSTEM/config/AIRTABLE_BASE.md`  
**Do not run `sync-templates` on live base without intent.**

**Workbook (if used):** `TMMT MANAGEMENT/outputs/execution/TMMT_Three_Business_Command_Center.xlsx` — add tabs mirroring sections below.

---

## 0. Historical anchor (required for credibility)

| Line | TTM / LTM | Notes |
|------|-----------|-------|
| Gross rental revenue | [FILL: $ exact TTM] — **$1M+ lifetime (operator)** | Bank + platform deposits |
| Trailing 12 mo net (est.) | [FILL: $] | After known COGS |
| Peak month revenue | [FILL: $] | |
| Current fleet | [FILL: # units total] | ~16 active renters in brief 2026-05-16 — reconcile to titled units |
| Active overdue accounts | **19** | `INVESTOR_METRICS_SNAPSHOT.md` · `TODAY_COLLECTIONS.md` |
| Overdue maintenance (jobs) | **4** | [customer], [customer], [customer], [customer] |
| TMMT OS / data | **Live** | Vercel + Supabase (see pitch deck platform slide) |
| Markets | [FILL: cities/states] | |

---

## 1. Revenue drivers (monthly model)

**Core formula:**  
`Monthly revenue ≈ Active units × Utilization % × Days in month × (ADR or implied daily rate)`

| Driver | Month 0 (actual) | Month 12 | Month 24 | Month 36 |
|--------|------------------|----------|----------|----------|
| Fleet units (rental) | [FILL] | [FILL] | [FILL] | [FILL] |
| Utilization % | [FILL] | [FILL] | [FILL] | [FILL] |
| ADR / avg daily rate | $[FILL] | $[FILL] | $[FILL] | $[FILL] |
| **Rental revenue** | $[FILL] | $[FILL] | $[FILL] | $[FILL] |
| Extension / late fees | $[FILL] | | | |
| Deposits / damage (net) | $[FILL] | | | |
| Dealer retail units sold | 0 | [FILL] | [FILL] | [FILL] |
| Avg gross per retail unit | — | $[FILL] | $[FILL] | $[FILL] |
| F&I per unit | — | $[FILL] | $[FILL] | $[FILL] |
| **Total revenue** | $[FILL] | $[FILL] | $[FILL] | $[FILL] |

---

## 2. Fleet count & acquisition schedule

| Quarter | Starting units | Adds | Disposals | Ending units | Capex / unit | Total capex |
|---------|----------------|------|-----------|--------------|--------------|-------------|
| Q1 | [FILL] | | | | $[FILL] | |
| Q2 | | | | | | |
| Q3 | | | | | | |
| Q4 | | | | | | |

**Funding source per add:** [FILL: cash / floorplan / investor / mix]

---

## 3. Unit economics (one vehicle, one month)

| Item | $/unit/month |
|------|----------------|
| Gross rental revenue | [FILL] |
| Marketplace / channel fees | [FILL] |
| Insurance alloc | [FILL] |
| Maintenance & repairs | [FILL] |
| Registration / tolls alloc | [FILL] |
| **Contribution margin** | [FILL] |
| Allocated overhead (software, labor) | [FILL] |
| **Net contribution** | [FILL] |

**Breakeven utilization at current ADR:** [FILL: %]  
**Payback months per acquired unit:** [FILL]

---

## 4. Operating expenses (monthly)

| Category | M0 | M12 | M24 |
|----------|-----|-----|-----|
| Labor (dispatch, collections) | | | |
| Software (GHL, Supabase, etc.) | | | |
| Marketing / lead gen | | | |
| Lot rent (dealer phase) | | | |
| Professional (legal, CPA) | | | |
| G&A | | | |
| **Total opex** | | | |

---

## 5. EBITDA bridge (monthly → annual)

| Line | Year 1 | Year 2 | Year 3 |
|------|--------|--------|--------|
| Total revenue | | | |
| Direct COGS (fleet) | | | |
| **Gross profit** | | | |
| Operating expenses | | | |
| **EBITDA** | | | |
| D&A (if applicable) | | | |
| Interest (floorplan) | | | |
| **Net operating income (est.)** | | | |

---

## 6. Cash flow essentials

| Line | Y1 | Y2 | Y3 |
|------|----|----|-----|
| EBITDA | | | |
| Fleet capex | | | |
| Dealer inventory (floorplan net) | | | |
| Working capital / collections float | | | |
| Debt service | | | |
| **Free cash flow (est.)** | | | |
| Opening cash | [FILL] | | |
| + Raise ([FILL: $]) | | | |
| **Ending cash** | | | |

**Runway months at base case:** [FILL]

---

## 7. Scenarios (12–36 months)

Duplicate section 1–6 for each case:

| Assumption | Conservative | Base | Aggressive |
|------------|--------------|------|------------|
| Unit growth / yr | [FILL] | [FILL] | [FILL] |
| Utilization | [FILL]% | [FILL]% | [FILL]% |
| ADR change | [FILL]% | [FILL]% | [FILL]% |
| Collection rate | [FILL]% | [FILL]% | [FILL]% |
| Dealer units sold Y2 | [FILL] | [FILL] | [FILL] |
| Y3 revenue | $[FILL] | $[FILL] | $[FILL] |
| Y3 EBITDA | $[FILL] | $[FILL] | $[FILL] |

---

## 8. Investor return scenarios

**Raise:** [FILL: $________] · **Pre-money valuation:** [FILL: $________] · **Ownership sold:** [FILL: %]

| Exit / outcome | Year | EBITDA multiple | Enterprise value | Investor proceeds | MOIC | IRR (approx.) |
|----------------|------|-----------------|------------------|-------------------|------|---------------|
| Strategic sale | 3 | [FILL]x | | | | |
| Strategic sale | 5 | [FILL]x | | | | |
| Dividend / cash sweep | 3 | n/a | [FILL] | | | |
| Downside (flat fleet) | 3 | [FILL]x | | | | |

**Revenue share alternative (if used):** [FILL: % of gross rental revenue until X cap]

---

## 9. Sensitivity (one-page for deck appendix)

| Variable | -20% | Base | +20% |
|----------|------|------|------|
| Utilization | EBITDA $ | $ | $ |
| ADR | | | |
| Collection rate | | | |
| Fleet adds delayed 6 mo | | | |

---

## 10. Monthly sync checklist (operator)

- [ ] Supabase payments → Income table or export tab  
- [ ] Fleet count matches TMMT OS / Vehicles table  
- [ ] Deck traction slide = model Month 0 row  
- [ ] One-pager unit economics = Section 3  
- [ ] Copy sanitized model summary to `INVESTOR_FLASH_MASTER/docs/` (no bank account numbers)

---

*Model is illustrative until populated with operator-verified actuals. Not tax or securities advice.*
