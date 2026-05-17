# Owner Daily Command — 20 Minutes, All Four Pillars

Use this **every morning** before new work. Full plan (ops + investor/dealer in parallel): [`PRIORITY_PLAN_ALL_PILLARS.md`](./PRIORITY_PLAN_ALL_PILLARS.md).

| Pillar | Time | One outcome |
|--------|------|-------------|
| Money | 4 min | Know what's due / overdue |
| Bookings | 4 min | Know top leads + active renters at risk |
| Fleet | 4 min | Know maintenance + vehicle conflicts |
| Investors / Dealer | 5 min | Metrics snapshot + pipeline (see §4) |
| Close | 3 min | Top 3 + one blocker in COMMAND_CENTER |

---

## 0. Open (1 min)

1. **Cursor folder:** `~/Desktop/AIX_Command_Center`
2. **Live ops:** TMMT OS internal dashboard (or latest brief below)
3. **Today's board:** [`TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md`](./TMMT%20MANAGEMENT/OPERATIONS/COMMAND_CENTER.md) — fill Top 3

**Latest auto-brief (if generated):**  
`TMMT MANAGEMENT/OPERATIONS/DAILY_BRIEF_YYYY-MM-DD.md`  
Regenerate: `TMMT MANAGEMENT/AUTOMATIONS/SCRIPTS/daily_command_center.py`

---

## 1. Money — 4 min

**Playbook:** [`AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md`](./AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md)

**Do:**
- Scan daily brief **Customer Payments – Exceptions** (or TMMT OS payments view)
- Pick **one** collection action to complete before noon
- Note any bill/card due in 7 days (Airtable or spreadsheet when live)

**AI shortcut (paste into Cursor/Claude):**
```text
Act as my money operator. From today's overdue payments and known bills: what is the single highest-impact payment to collect or pay today?
```

**Weekly (Mon or Sun):** run full prompt in `MONEY_COMMAND_CENTER.md` → Weekly Money Review.

---

## 2. Bookings — 4 min

**Do:**
- Brief → **Top 3 Priorities** + **Incoming Leads** + **Active Customers**
- Send **one** follow-up using [`MESSAGE_TEMPLATE_LIBRARY.md`](./TMMT%20MANAGEMENT/CUSTOMERS/MESSAGE_TEMPLATE_LIBRARY.md)
- Confirm no booking conflicts for pick-ups/returns today

**SOP:** [`TMMT MANAGEMENT/SOPS/CAR_RENTAL_COMMUNICATION_SOP.md`](./TMMT%20MANAGEMENT/SOPS/CAR_RENTAL_COMMUNICATION_SOP.md)

**AI shortcut:**
```text
Act as my rental dispatcher. From today's leads and active customers: who needs a message in the next 2 hours and what template trigger applies?
```

---

## 3. Fleet — 4 min

**Do:**
- Brief → **Fleet Alerts** + **Maintenance Appointments**
- Schedule or assign **one** overdue maintenance item
- If handoff today: verify vehicle status (Available / Rented / Maintenance) before customer arrival

**Registers:**  
[`FLEET_REGISTER.md`](./TMMT%20MANAGEMENT/FLEET/FLEET_REGISTER.md) · [`MAINTENANCE_TRACKER.md`](./TMMT%20MANAGEMENT/FLEET/MAINTENANCE_TRACKER.md)  
*(Sync from Supabase/TMMT OS — don't maintain two truths.)*

**SOP gaps:** [`SOPS/SOP_INDEX.md`](./TMMT%20MANAGEMENT/SOPS/SOP_INDEX.md)

---

## 4. Investors / Dealer — 5 min

**Every day (metrics snapshot):**
- Log in COMMAND_CENTER or deck appendix: **active units** · **utilization %** · **collection rate** · **overdue $** · **dealer pipeline count** (qualified applicants)
- Pull overdue $ and fleet alerts from today's brief — same numbers investors will ask about

**Rotate (one item per day):**
- **Mon:** Update one row in [`docs/INVESTOR_FINANCIAL_MODEL.md`](./docs/INVESTOR_FINANCIAL_MODEL.md)
- **Tue:** Fix one `[FILL:]` in [`docs/INVESTOR_PITCH_DECK.md`](./docs/INVESTOR_PITCH_DECK.md)
- **Wed:** One dealership roadmap checkbox — [`docs/DEALERSHIP_TRANSITION_ROADMAP.md`](./docs/DEALERSHIP_TRANSITION_ROADMAP.md)
- **Thu:** One dealer/applicant touch or GHL stage move (`AIXMOSXTMMT-OPS/docs/ghl-pipelines.md`)
- **Fri:** Sync flash kit docs if numbers changed — `~/Desktop/INVESTOR_FLASH_MASTER/docs/`

**Kit:** [`docs/INVESTOR_ONE_PAGER.md`](./docs/INVESTOR_ONE_PAGER.md) · [`docs/INVESTOR_KIT_GAPS.md`](./docs/INVESTOR_KIT_GAPS.md)

---

## 5. Close (3 min)

Write in **COMMAND_CENTER.md**:
- Top 3 for today (one per pillar if possible)
- One **blocker** with owner + due time

**Optional power move (if keys set):**
```bash
cd ~/Desktop/AIX_Command_Center/AIX_AI_COMMAND_SYSTEM
./scripts/tmmt-day
```
Paste morning output into AI → act on top 3 only. See [`ONE_PAGE_START.md`](./AIX_AI_COMMAND_SYSTEM/ONE_PAGE_START.md).

---

## Links (not duplicated here)

| Doc | Purpose |
|-----|---------|
| [`PRIORITY_PLAN_ALL_PILLARS.md`](./PRIORITY_PLAN_ALL_PILLARS.md) | 90-day all-pillar plan |
| [`MONEY_COMMAND_CENTER.md`](./AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md) | Bills, cards, leaks, weekly CFO review |
| [`TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md`](./TMMT%20MANAGEMENT/OPERATIONS/COMMAND_CENTER.md) | Tasks, follow-ups, decisions, EOD notes |
| [`OPEN_IN_CURSOR.md`](./OPEN_IN_CURSOR.md) | Folder path + first files |

*Established operator: maintain cash and fleet daily; build investor and dealer proof in parallel—no waiting period.*
