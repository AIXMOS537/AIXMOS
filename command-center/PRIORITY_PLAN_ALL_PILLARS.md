# 90-Day Priority Plan — All Four Pillars

**Business arc:** proven rental operator ($1M+ revenue) → scale utilization & collections → raise capital → dealership transition  
**Working folder:** `~/Desktop/AIX_Command_Center`  
**Owner daily routine:** [`OWNER_DAILY_COMMAND.md`](./OWNER_DAILY_COMMAND.md)

---

## ESTABLISHED OPERATOR TRACK (parallel — not sequential)

**You are not pre-revenue.** Revenue, fleet, and customer proof exist. Investor and dealership materials run **in parallel** with ops maintenance—not after a 4-week stabilization wait.

```text
TRACK A — OPS MAINTENANCE (daily)          TRACK B — INVESTOR / DEALER (this week)
─────────────────────────────────          ─────────────────────────────────────
Collections + maintenance discipline       Pitch deck + financial model scaffolds
Daily brief + TMMT OS truth                Dealership transition roadmap
Top 3 automations (collections first)      One-pager + metrics baseline filled
Weekly money review                        Dealer pipeline stages in GHL
                                           USB kit refresh when numbers are in
```

| This week — Ops | This week — Investor / Dealer |
|-----------------|-------------------------------|
| Close top overdue payments from brief | Fill `[FILL:]` in [`docs/INVESTOR_PITCH_DECK.md`](./docs/INVESTOR_PITCH_DECK.md) |
| Schedule overdue maintenance | Complete [`docs/INVESTOR_FINANCIAL_MODEL.md`](./docs/INVESTOR_FINANCIAL_MODEL.md) base case |
| Run money morning prompt daily | Read [`docs/DEALERSHIP_TRANSITION_ROADMAP.md`](./docs/DEALERSHIP_TRANSITION_ROADMAP.md) — mark your state |
| Wire overdue payment alert (see backlog) | Export 12-mo revenue proof for data room (bank/P&L — not on USB) |
| Keep daily brief habit | Book 1–2 investor conversations with deck + one-pager |

**Investor kit entry points:** [`docs/INVESTOR_PITCH_DECK.md`](./docs/INVESTOR_PITCH_DECK.md) · [`docs/INVESTOR_FINANCIAL_MODEL.md`](./docs/INVESTOR_FINANCIAL_MODEL.md) · [`docs/DEALERSHIP_TRANSITION_ROADMAP.md`](./docs/DEALERSHIP_TRANSITION_ROADMAP.md) · [`docs/INVESTOR_ONE_PAGER.md`](./docs/INVESTOR_ONE_PAGER.md)  
**Sanitized copies:** `~/Desktop/INVESTOR_FLASH_MASTER/docs/`  
**Automations:** [`docs/AUTOMATION_PRIORITY_BACKLOG.md`](./docs/AUTOMATION_PRIORITY_BACKLOG.md) — ROI order, not build-everything

**Credibility rule (established operator):** Lead with traction and unit economics. Show collections and maintenance discipline as **operational excellence**, not as a reason to delay the raise.

---

## How the four pillars connect

```text
BOOKINGS (leads, contracts, calendar)
    ↓ assigns vehicle
FLEET (availability, maintenance, condition)
    ↓ drives revenue & costs
MONEY (collections, bills, P&L, unit economics)
    ↓ proves the model
INVESTORS (ops story, metrics, installable OS)
```

**Rule:** No pillar gets 90 days alone. Each week must move all four at least one notch.

| Cross-link | If this breaks… |
|------------|-----------------|
| Booking → Fleet | Double-books, wrong car, late maintenance surprises |
| Fleet → Money | Idle units, repair blowups, toll/ticket leaks |
| Money → Booking | Can't approve extensions; chase instead of sell |
| Money → Investors | No credible unit economics or cash discipline |
| Investors → Ops | Deck without live metrics = trust loss — keep numbers synced weekly |

---

## Asset audit summary (what you already have)

### Fleet

| Asset | Path | Status |
|-------|------|--------|
| Fleet register (template) | `TMMT MANAGEMENT/FLEET/FLEET_REGISTER.md` | Empty — not synced to live DB |
| Maintenance tracker | `TMMT MANAGEMENT/FLEET/MAINTENANCE_TRACKER.md` | Empty |
| Inspection log | `TMMT MANAGEMENT/FLEET/INSPECTION_LOG.md` | Exists |
| Maintenance reminders output | `TMMT MANAGEMENT/FLEET/MAINTENANCE_REMINDERS_2026-05-16.md` | Generated |
| Vehicle schema (sample CSV) | `AIX_AI_COMMAND_SYSTEM/aix-command-system/airtable_templates/Vehicles.csv` | Sample only |
| Daily brief fleet section | `TMMT MANAGEMENT/OPERATIONS/DAILY_BRIEF_*.md` | **Live from Supabase** |
| Fleet SOPs | `TMMT MANAGEMENT/SOPS/SOP_INDEX.md` | Check-out/return/damage = **Needed** |
| AI fleet hardware doc | `docs/LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md` | **Computer fleet**, not GPS trackers |

### Bookings

| Asset | Path | Status |
|-------|------|--------|
| Bookings CSV template | `AIX_AI_COMMAND_SYSTEM/aix-command-system/airtable_templates/Bookings.csv` | Sample only |
| Communication SOP | `TMMT MANAGEMENT/SOPS/CAR_RENTAL_COMMUNICATION_SOP.md` | **Active** |
| CRM tracker | `TMMT MANAGEMENT/CUSTOMERS/CRM_TRACKER.md` | Empty |
| Message templates | `TMMT MANAGEMENT/CUSTOMERS/MESSAGE_TEMPLATE_LIBRARY.md` | Exists |
| Follow-ups export | `TMMT MANAGEMENT/CUSTOMERS/FOLLOW_UPS_2026-05-16.md` | Generated |
| GHL pipeline spec | `AIXMOSXTMMT-OPS/docs/ghl-pipelines.md` | **Dealership** stages, not rental pipeline |
| Sales pipeline (generic) | `AIX_AI_COMMAND_SYSTEM/02_SALES_ENGINE/sales_pipeline.md` | Generic |
| Automation map | `AIX_AI_COMMAND_SYSTEM/AUTOMATION_MAP.md` | Designed, mostly not wired |
| Daily brief (leads/customers) | `TMMT MANAGEMENT/OPERATIONS/DAILY_BRIEF_*.md` | **Live** — 17+ overdue payments flagged |
| tmmt-os app | `TMMT MANAGEMENT/tmmt-os/` | Deployed; internal dashboard |

### Money

| Asset | Path | Status |
|-------|------|--------|
| Money Command Center | `AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md` | **Strong playbook** |
| Weekly money SOP | `AIX_AI_COMMAND_SYSTEM/sops/WEEKLY_MONEY_ROUTINE.md` | Exists |
| Airtable money templates | `AIX_AI_COMMAND_SYSTEM/airtable_templates/` (Bills, Income, Expenses, etc.) | CSV templates |
| Finance tracker | `TMMT MANAGEMENT/FINANCE/FINANCE_TRACKER.md` | Empty |
| Execution workbook | `TMMT MANAGEMENT/outputs/execution/TMMT_Three_Business_Command_Center.xlsx` | Exists |
| Payment exceptions | Daily brief | **Live** — collections is #1 priority |
| Integration registry | `TMMT MANAGEMENT/INTEGRATIONS/INTEGRATION_REGISTRY.md` | GHL/Airtable/n8n = **Planned** |

### Investors

| Asset | Path | Status |
|-------|------|--------|
| Investor flash master | `~/Desktop/INVESTOR_FLASH_MASTER/` | Sanitized clone kit |
| Install checklist | `INVESTOR_FLASH_MASTER/INVESTOR_INSTALL_CHECKLIST.md` | Ready |
| Operating system doc | `AIX_AI_COMMAND_SYSTEM/TMMT_OPERATING_SYSTEM.md` | Framework |
| Investor UI scaffold | `TMMT MANAGEMENT/tmmt-os/src/app/(investor)/investor/dashboard/` | Needs data + updates |
| One-pager | `docs/INVESTOR_ONE_PAGER.md` | **New** |
| Pitch deck | `docs/INVESTOR_PITCH_DECK.md` | **Scaffold ready — fill numbers** |
| Financial model | `docs/INVESTOR_FINANCIAL_MODEL.md` | **Scaffold ready — fill numbers** |
| Dealership roadmap | `docs/DEALERSHIP_TRANSITION_ROADMAP.md` | **Ready — fill state** |
| Automation ROI backlog | `docs/AUTOMATION_PRIORITY_BACKLOG.md` | **Ready** |

---

## Gap analysis (biggest holes)

### Fleet — gap

**Live data in Supabase; local markdown registers empty; fleet SOPs unowned; no documented GPS/tracker SOP.**

- Populate `FLEET_REGISTER.md` from Supabase export OR retire it in favor of TMMT OS as source of truth.
- Write and assign owners for check-out, return, damage, maintenance intake (`SOP_INDEX.md`).
- Close 4+ overdue maintenance items visible in daily brief.

### Bookings — gap

**Communication SOP exists; rental booking pipeline not documented in GHL; CRM markdown empty; automations proposed not deployed.**

- Define rental-specific pipeline stages in GHL (parallel to dealership doc).
- Wire confirmation / pick-up / return reminders per `CAR_RENTAL_COMMUNICATION_SOP.md`.
- Attack overdue lead follow-ups and payment-linked booking status daily.

### Money — gap

**Excellent money *playbook*; weak money *ledger* in repo; Airtable not connected per registry; no monthly P&L template in tree.**

- Stand up Airtable base from `airtable_templates/` OR sync Supabase payments → weekly export.
- Run `MONEY_COMMAND_CENTER.md` daily prompt against real numbers.
- Build simple monthly P&L view (spreadsheet tab or Airtable) — see Week 3–6.

### Investors — gap

**Flash kit = software + SOPs; narrative scaffolds now exist — gap is real numbers and data room proof.**

- Fill all `[FILL:]` placeholders in pitch deck, financial model, one-pager (revenue, fleet, markets, ask).
- Add historical P&L / bank summary to data room (not on USB).
- Refresh `INVESTOR_FLASH_MASTER/docs/` after each metrics update; USB clone when drives ready.

---

# Phase 1 — Stabilize (Week 1–2)

**Goal:** Stop bleeding — collections, maintenance, one source of truth per pillar.

## Fleet (Week 1–2)

| When | Owner action | Use this file/tool | Build next |
|------|--------------|-------------------|------------|
| Daily | Review fleet/maintenance section of brief | `TMMT MANAGEMENT/OPERATIONS/DAILY_BRIEF_*.md` | — |
| Daily | Close or schedule each overdue maintenance | TMMT OS + vendor | Maintenance intake SOP draft |
| Week 1 | Export vehicle list from Supabase → reconcile | `tmmt-os` / Supabase | One-row-per-vehicle in `FLEET_REGISTER.md` OR mark OS as canonical |
| Week 2 | Assign SOP owner for check-out + return | `SOPS/SOP_INDEX.md` | Draft `SOPS/VEHICLE_CHECKOUT_SOP.md` |

## Bookings (Week 1–2)

| When | Owner action | Use this file/tool | Build next |
|------|--------------|-------------------|------------|
| Daily | Top 3 from brief: overdue payments + open leads | `DAILY_BRIEF_*.md`, TMMT OS | — |
| Daily | Log every customer touch | `CUSTOMERS/MESSAGE_TEMPLATE_LIBRARY.md` | — |
| Week 1 | Run communication triggers manually per matrix | `SOPS/CAR_RENTAL_COMMUNICATION_SOP.md` | Checklist taped to dispatch |
| Week 2 | Map GHL rental stages (Lead → Qualified → Active → Return → Closed) | New: `TMMT MANAGEMENT/SOPS/RENTAL_PIPELINE_GHL.md` | Copy from `AIXMOSXTMMT-OPS/docs/ghl-pipelines.md` pattern |

## Money (Week 1–2)

| When | Owner action | Use this file/tool | Build next |
|------|--------------|-------------------|------------|
| Daily (10 min) | Money morning prompt | [`MONEY_COMMAND_CENTER.md`](./AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md) | — |
| Daily | Work overdue payment list from brief | Supabase / GHL | — |
| Week 1 | List all business bills + card due dates | Import `airtable_templates/Bills.csv`, `Credit_Cards.csv` | Airtable base or finance sheet tab |
| Week 2 | First weekly money review | `sops/WEEKLY_MONEY_ROUTINE.md` | `FINANCE_TRACKER.md` first week of real rows |

## Investors (Week 1–2) — parallel track

| When | Owner action | Use this file/tool | Build next |
|------|--------------|-------------------|------------|
| Week 1 | Fill traction + unit economics in pitch deck | [`docs/INVESTOR_PITCH_DECK.md`](./docs/INVESTOR_PITCH_DECK.md) | Paste to Slides/Canva |
| Week 1 | Complete base-case rows in financial model | [`docs/INVESTOR_FINANCIAL_MODEL.md`](./docs/INVESTOR_FINANCIAL_MODEL.md) | Link Airtable templates |
| Week 2 | One-pager + metrics snapshot (same numbers as deck) | [`docs/INVESTOR_ONE_PAGER.md`](./docs/INVESTOR_ONE_PAGER.md), daily brief | Data room folder |
| Week 2 | Mark dealership roadmap for your state | [`docs/DEALERSHIP_TRANSITION_ROADMAP.md`](./docs/DEALERSHIP_TRANSITION_ROADMAP.md) | Counsel review |
| Week 2 | First investor calls with deck + one-pager | `~/Desktop/INVESTOR_FLASH_MASTER/docs/` | FAQ when objections repeat |

**Cross-pillar Week 1–2:** Every overdue payment ties to a vehicle ID and customer record before end of day.

---

# Phase 2 — Grow (Week 3–6)

**Goal:** Repeatable booking flow, fleet utilization, weekly money rhythm, investor-ready metrics.

## Fleet (Week 3–6)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Weekly | Inspection round — photos + mileage | `FLEET/INSPECTION_LOG.md` | Link inspection to vehicle ID |
| Weekly | Review idle units (24h+ no booking) | `AUTOMATION_MAP.md` Priority 2 | Marketing task per idle unit |
| Week 4 | Activate maintenance reminder automation | `AUTOMATIONS/CONFIG/maintenance_reminders.json` | n8n or cron |
| Week 6 | Unit economics per vehicle (revenue − maint − insurance) | Spreadsheet or Airtable | Column on fleet register |

## Bookings (Week 3–6)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Daily | 11 AM sales push pattern | `04_OPERATIONS_MANUAL/daily_manager_routine.md` | — |
| Week 3 | Automate booking confirmation + pick-up reminder (one channel) | `AUTOMATIONS/AUTOMATION_BACKLOG.md` | OpenPhone or GHL workflow |
| Week 4 | Sync Bookings table (Airtable or Supabase view) | `Bookings.csv` schema | Live calendar conflicts check |
| Week 6 | Extension / late-return playbook tested | `CAR_RENTAL_COMMUNICATION_SOP.md` | Owner escalation log |

## Money (Week 3–6)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Weekly | CFO-style review | `MONEY_COMMAND_CENTER.md` + `WEEKLY_MONEY_ROUTINE.md` | — |
| Week 3 | Monthly P&L v1 (revenue, COGS, fleet, software, net) | `outputs/execution/TMMT_Three_Business_Command_Center.xlsx` | New tab or `FINANCE/MONTHLY_PL_ANDL.md` |
| Week 4 | Money automations tier 1 | `AUTOMATION_MAP.md` Priority 1 | Bill due reminders |
| Week 6 | Collection rate KPI (paid on time / active accounts) | Baseline from Week 2 | Target % in owner dashboard |

## Investors (Week 3–6)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Week 4 | Update investor one-pager with real unit economics | `docs/INVESTOR_ONE_PAGER.md` | Fill placeholders |
| Week 5 | Refine pitch deck from meeting feedback | [`docs/INVESTOR_PITCH_DECK.md`](./docs/INVESTOR_PITCH_DECK.md) | PDF export for data room |
| Week 6 | Publish first investor update in tmmt-os (if using) | `tmmt-os` investor dashboard | One monthly memo |

**Cross-pillar Week 3–6:** Booking calendar must read fleet status (Available / Rented / Maintenance) before confirming.

---

# Phase 3 — Scale (Week 7–12)

**Goal:** Automations running, delegation, dealership documentation started, investor kit clone-ready.

## Fleet (Week 7–12)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Week 8 | Delegate inspection + maintenance scheduling | SOPs + ClickUp/n8n tasks | Role in `03_TRAINING_ACADEMY/role_index.md` |
| Week 10 | Evaluate GPS/telematics standard | — | `FLEET/TELEMATICS_VENDOR_SOP.md` (create) |
| Week 12 | Fleet cap plan (# units vs cash) | P&L + investor metrics | Acquisition checklist |

## Bookings (Week 7–12)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Week 8 | Command router MVP | `AUTOMATIONS/WORKFLOWS/N8N_COMMAND_ROUTER_BLUEPRINT.md` | Telegram → task |
| Week 10 | Full rental automation tier from map | `AUTOMATION_MAP.md` | Late return alerts |
| Week 12 | Hire/train dispatcher using academy | `03_TRAINING_ACADEMY/30_day_onboarding.md` | — |

## Money (Week 7–12)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Week 8 | Separate business vs personal in reports | `MONEY_COMMAND_CENTER.md` rule | Chart of accounts doc |
| Week 10 | Investor-grade 3-month trend export | P&L + Supabase | CSV for data room |
| Week 12 | Credit/funding/ecom only if rental P&L clean | `TMMT MANAGEMENT/02 ECOMMERCE`, `03 CREDIT...` | Defer distraction |

## Investors (Week 7–12)

| When | Owner action | Use | Build next |
|------|--------------|-----|------------|
| Week 8 | Sync `INVESTOR_FLASH_MASTER` from command center | `CONSOLIDATION_REPORT.md` process | Re-run secret scan |
| Week 10 | Clone 3 USB drives | `prepare-three-drives.sh` | — |
| Week 12 | First investor conversation with deck + one-pager + 90-day metrics | Kit + live demo TMMT OS | FAQ doc |

**Cross-pillar Week 7–12:** Weekly owner update (`00_COMMAND_CENTER/WEEKLY_OWNER_UPDATE.md`) covers all four pillars in one page.

---

# Dealership path — parallel with rental (established operator)

**Full roadmap:** [`docs/DEALERSHIP_TRANSITION_ROADMAP.md`](./docs/DEALERSHIP_TRANSITION_ROADMAP.md)

| Run in parallel now | Phase by capital / license readiness |
|---------------------|--------------------------------------|
| GHL applicant stages (`AIXMOSXTMMT-OPS/docs/ghl-pipelines.md`) | Dealer license + bond (`[FILL: state]`) |
| `airtable_templates/Dealership_Fleets.csv`, `Shared_Lot_Inventory.csv` | Floorplan line + lot acquisition |
| Rental→dealer lead field in GHL | F&I menu + service lane hire |
| Partner scorecard prompt | Physical lot grand opening |
| Use-of-funds split: rental scale + dealer bridge | Investor $ for dealer only with rental metrics attached |

**Bridge metric:** % of rental customers qualified for dealer pipeline (`rental_customer_yn` in GHL spec).

---

# Weekly owner rhythm (all pillars)

| Day | Focus |
|-----|--------|
| Mon | Money review + week priorities in `COMMAND_CENTER.md` |
| Tue–Thu | Collections + bookings + fleet maintenance |
| Fri | SOP/automation progress + brief cleanup |
| Sun | Optional: weekly money prompt (`MONEY_COMMAND_CENTER.md`) |

---

# Key file index (open in Cursor)

| Pillar | Start here |
|--------|------------|
| All | [`OWNER_DAILY_COMMAND.md`](./OWNER_DAILY_COMMAND.md) |
| Ops hub | `TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md` |
| Live snapshot | `TMMT MANAGEMENT/OPERATIONS/DAILY_BRIEF_*.md` |
| Money | `AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md` |
| Automations | `AIX_AI_COMMAND_SYSTEM/AUTOMATION_MAP.md` |
| Investors | `docs/INVESTOR_PITCH_DECK.md` → `docs/INVESTOR_FINANCIAL_MODEL.md` → `docs/INVESTOR_ONE_PAGER.md` |
| Dealership | `docs/DEALERSHIP_TRANSITION_ROADMAP.md` |
| Automations (ROI) | `docs/AUTOMATION_PRIORITY_BACKLOG.md` |
| Cursor entry | `OPEN_IN_CURSOR.md` |

*Last updated: 2026-05-16 — Established Operator Track added*
