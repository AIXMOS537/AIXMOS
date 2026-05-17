# Rental → Dealership Transition Roadmap

**For:** Established rental operator scaling to licensed dealer / partner lot model  
**Primary state:** **[FILL: state]** — verify all items with automotive counsel in that jurisdiction  
**Parallel principle:** Keep rental cash flow running while dealer prerequisites advance on a second track.

**Related:** [`INVESTOR_PITCH_DECK.md`](./INVESTOR_PITCH_DECK.md) · [`PRIORITY_PLAN_ALL_PILLARS.md`](../PRIORITY_PLAN_ALL_PILLARS.md) · `AIXMOSXTMMT-OPS/docs/ghl-pipelines.md`

---

## Phase map (parallel tracks)

```text
NOW (rental revenue)          PARALLEL (dealer prep)           LATER (dealer revenue)
────────────────────          ──────────────────────           ──────────────────────
Collections + fleet           License + bond research          Retail sales
Booking SOP + GHL rental      Entity / DBAs / lot zoning       F&I products
Daily brief + TMMT OS         Floorplan application            Service lane
Rental→dealer lead tagging      Inventory mix policy             Used + wholesale
Partner scorecards            Compliance binder                Staff: sales + F&I
```

---

## Track 1 — Licensing & entity (start now)

| Step | Action | Owner | Status |
|------|--------|-------|--------|
| 1.1 | Confirm **[FILL: state]** motor vehicle dealer license type (new/used/both) | Counsel | ☐ |
| 1.2 | Dealer bond amount + carrier | Counsel | ☐ |
| 1.3 | Business entity fit (LLC → dealer entity if required) | CPA/Counsel | ☐ |
| 1.4 | Registered agent + dealer license application timeline | Ops | ☐ |
| 1.5 | Salesperson licenses (if required per state) | HR | ☐ |
| 1.6 | Rental license continuity — ensure dealer transition doesn't gap rental authority | Counsel | ☐ |

**State-specific notes ([FILL: state]):**
- Bond: [FILL: $ amount range]
- Application portal: [FILL: URL or agency name]
- Typical timeline: [FILL: weeks]
- Rental + dealer same entity allowed? [FILL: Y/N + notes]

---

## Track 2 — Lot, zoning & inventory mix (parallel)

| Step | Action | Notes |
|------|--------|-------|
| 2.1 | Lot location criteria (visibility, zoning, sq ft) | [FILL: target metros] |
| 2.2 | Lease vs purchase decision | Tie to use-of-funds in deck |
| 2.3 | **Inventory mix policy** | e.g. % rental float vs retail front line |
| 2.4 | Shared lot inventory in Airtable | `airtable_templates/Shared_Lot_Inventory.csv` |
| 2.5 | Dealership partner table | `airtable_templates/Dealership_Partners.csv` |
| 2.6 | Recon / inspection standard for retail units | Link fleet inspection SOP |
| 2.7 | Signage, hours, ADA, security | Ops checklist |

**What you can run in parallel while renting:**
- Scout lots (no license required for research)
- Build dealer pipeline in GHL (applicant stages)
- Tag rental customers `rental_customer_yn` → dealer qualified
- Standardize recon vendors and pricing
- Floorplan **application prep** (financials from rental P&L)

---

## Track 3 — Floorplan & capital structure

| Step | Action | [FILL] |
|------|--------|--------|
| 3.1 | Floorplan lenders shortlist | |
| 3.2 | Personal guarantee / corporate guarantee terms | |
| 3.3 | Advance rate by vehicle class | |
| 3.4 | Curtailment schedule understood | |
| 3.5 | Investor $ split: rental fleet vs dealer inventory | See financial model |
| 3.6 | Minimum cash reserve policy | $ |

**Rule:** Do not let floorplan carry rental fleet and retail stock in one undifferentiated bucket—segment in books and Airtable.

---

## Track 4 — F&I, sales process & GHL

| Step | Action | Tool |
|------|--------|------|
| 4.1 | Applicant pipeline stages live | `ghl-pipelines.md` |
| 4.2 | Credit / income verification SOP | [FILL: vendor or manual] |
| 4.3 | F&I product menu (warranty, GAP, etc.) | Counsel + lender rules |
| 4.4 | Doc fee / compliance disclosures | [FILL: state max / forms] |
| 4.5 | Delivery checklist (title, temp tag, insurance) | New SOP |
| 4.6 | Partner scorecard automation | Empire ops prompts |

---

## Track 5 — Service lane (phase by volume)

| Step | When | Action |
|------|------|--------|
| 5.1 | Pre-open | Vendor network for warranty/recon overflow |
| 5.2 | Soft launch | Oil/tire/inspection packages for sold units |
| 5.3 | Scale | Hire service advisor; bay or sublet agreement |
| 5.4 | Rental synergy | Maintenance SOP doubles for retail CPO prep |

---

## Track 6 — Compliance binder (generic + state)

Build a single folder (data room + lot office):

| Document | Rental | Dealer |
|----------|--------|--------|
| Business license | ☐ | ☐ |
| Insurance (GL, garage, fleet) | ☐ | ☐ |
| Rental agreements / T&C | ☐ | — |
| Retail purchase agreement template | — | ☐ |
| OFAC / Red Flags (if applicable) | ☐ | ☐ |
| Privacy / GLBA (if credit pulled) | ☐ | ☐ |
| Odometer / title policies | ☐ | ☐ |
| Advertising compliance ([FILL: state]) | ☐ | ☐ |
| Employee handbook + sales licenses | ☐ | ☐ |

---

## Track 7 — Metrics (report weekly — same as owner daily)

| Metric | Source |
|--------|--------|
| Rental utilization % | Daily brief / Supabase |
| Collection rate | Payments view |
| Dealer pipeline count by stage | GHL |
| Qualified rental→dealer % | GHL custom field |
| Units on floorplan vs cash | Airtable / finance sheet |
| Gross per retail unit (when live) | P&L |

---

## 90-day milestone checklist (established operator)

| Week | Rental (keep running) | Dealer (parallel) |
|------|----------------------|-------------------|
| 1–2 | Collections + maintenance | Counsel call on [FILL: state] license |
| 3–4 | Booking automation tier 1 | GHL dealer stages + lead tagging |
| 5–6 | P&L v1 with unit economics | Floorplan lender package submitted |
| 7–8 | Fleet cap plan | Lot shortlist (3 sites) |
| 9–10 | Investor metrics export | Compliance binder draft |
| 11–12 | Delegate dispatch | License filed or opening date set |

---

## What NOT to pause

- Daily brief and TMMT OS as source of truth  
- Collections (investors and floorplan lenders both care)  
- Rental revenue while waiting on license — **license timing ≠ revenue timing**

---

*Template only — not legal advice. Confirm all regulatory steps with qualified automotive counsel in [FILL: state].*
