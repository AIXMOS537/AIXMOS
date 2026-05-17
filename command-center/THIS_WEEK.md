# This Week — Running Checklist

**Week of:** May 16–22, 2026  
**Workspace:** `~/Desktop/AIX_Command_Center`  
**Rule:** Check boxes as you complete. Regenerate brief each morning (see Daily).

---

## Status board (update daily)

| Pillar | This week’s focus | Status |
|--------|-------------------|--------|
| Money | Priority 1 collections (5) + GHL overdue workflow | 🔴 In progress |
| Fleet | 4 overdue oil changes + SOP owners | 🔴 In progress |
| Bookings | [customer] + [customer] + rental pipeline doc | 🟡 Started |
| Investors | Deck slides 9–11 + model S0 + 1–2 calls | 🟡 Started |

**Live brief:** [`DAILY_BRIEF_2026-05-16.md`](./TMMT%20MANAGEMENT/OPERATIONS/DAILY_BRIEF_2026-05-16.md) (Supabase snapshot restored)  
**Today’s queue:** [`TODAY_COLLECTIONS.md`](./TMMT%20MANAGEMENT/OPERATIONS/TODAY_COLLECTIONS.md) · [`COMMAND_CENTER.md`](./TMMT%20MANAGEMENT/OPERATIONS/COMMAND_CENTER.md)

---

## Daily (every morning ~20 min)

- [x] Brief restored from live Supabase snapshot (2026-05-16)
- [x] `COMMAND_CENTER.md` + `TODAY_COLLECTIONS.md` ready
- [ ] Run [`OWNER_DAILY_COMMAND.md`](./OWNER_DAILY_COMMAND.md)
- [ ] Regenerate brief: `cd "TMMT MANAGEMENT" && python3 AUTOMATIONS/SCRIPTS/daily_command_center.py`  
  *(If empty data: use restored brief until Supabase connects)*
- [ ] Complete **≥1** collection call/text ([`TODAY_COLLECTIONS.md`](./TMMT%20MANAGEMENT/OPERATIONS/TODAY_COLLECTIONS.md))
- [ ] EOD: update **COMMAND_CENTER** → Wins / Problems / Carryover

---

## Money

| Task | Owner | Due | Done |
|------|-------|-----|------|
| Call [customer] (#1) | You | Sat | [ ] |
| Call [customer] (#2) | You | Sat–Sun | [ ] |
| Call [customer] (#3) | You | Sun | [ ] |
| Call [customer] (#4) | You | Sun | [ ] |
| Call [customer] (#5) | You | Mon | [ ] |
| Wire GHL overdue alert | You + VA | Mon–Fri | [ ] → **[`WEEK_1_GHL_WHATSAPP.md`](./WEEK_1_GHL_WHATSAPP.md)** (day-by-day) · [`GHL_OVERDUE_WORKFLOW_SETUP.md`](./TMMT%20MANAGEMENT/AUTOMATIONS/GHL_OVERDUE_WORKFLOW_SETUP.md) |
| Bank numbers → financial model §0 | You | Tue | [ ] → [`docs/INVESTOR_FINANCIAL_MODEL.md`](./docs/INVESTOR_FINANCIAL_MODEL.md) |

**Scripts:** [`docs/INVESTOR_METRICS_SNAPSHOT.md`](./docs/INVESTOR_METRICS_SNAPSHOT.md) · [`MONEY_COMMAND_CENTER.md`](./AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md)

---

## Fleet

| Task | Owner | Due | Done |
|------|-------|-----|------|
| Oil change — [customer] | Fleet | Mon | [ ] |
| Oil change — [customer] | Fleet | Mon | [ ] |
| Oil change — [customer] | Fleet | Tue | [ ] |
| Oil change — [customer] | Fleet | Tue | [ ] |
| Assign 6 SOP owners | You | Wed | [ ] → [`SOP_OWNERS.md`](./TMMT%20MANAGEMENT/SOPS/SOP_OWNERS.md) |
| Export vehicles → `FLEET_REGISTER.md` | You | Thu | [ ] |

**Schedule:** [`MAINTENANCE_WEEK_SCHEDULE.md`](./TMMT%20MANAGEMENT/FLEET/MAINTENANCE_WEEK_SCHEDULE.md)

---

## Bookings

| Task | Owner | Due | Done |
|------|-------|-----|------|
| Text/call **[customer]** (3 days no response) | You | Sat | [ ] → [`LEAD_FOLLOWUPS_THIS_WEEK.md`](./TMMT%20MANAGEMENT/CUSTOMERS/LEAD_FOLLOWUPS_THIS_WEEK.md) |
| Call **[customer]** (JV lead) | You | Mon | [ ] |
| Confirm rental GHL stages in CRM | You | Wed | [ ] → [`RENTAL_GHL_PIPELINE.md`](./TMMT%20MANAGEMENT/CUSTOMERS/RENTAL_GHL_PIPELINE.md) |

---

## Investors / dealer

| Task | Owner | Due | Done |
|------|-------|-----|------|
| Deck slides 4–5 (traction + unit economics) | You | Tue | [x] partial — finish [FILL] fields |
| Deck slides 9–11 (funds, team, ask) | You | Wed | [ ] scaffold in deck |
| Friday metrics log | You | Fri | [ ] → `INVESTOR_METRICS_SNAPSHOT.md` |
| Book 1–2 investor calls | You | Thu–Fri | [ ] |
| Dealer counsel — pick state | You | This week | [ ] → [`docs/DEALERSHIP_TRANSITION_ROADMAP.md`](./docs/DEALERSHIP_TRANSITION_ROADMAP.md) |

**Deck:** [`docs/INVESTOR_PITCH_DECK.md`](./docs/INVESTOR_PITCH_DECK.md) · **One-pager:** [`docs/INVESTOR_ONE_PAGER.md`](./docs/INVESTOR_ONE_PAGER.md)

---

## Hardware (when ready)

- [ ] Lexar → `AIX_AI_COMMAND_SYSTEM/scripts/sync-to-lexar.sh`
- [ ] 3 investor USBs → `cd ~/Desktop/INVESTOR_FLASH_MASTER && ./prepare-three-drives.sh`

---

## Day map (suggested)

| Day | Focus |
|-----|--------|
| **Sat 16** | Owner daily + collections #1–2 + [customer] lead |
| **Sun 17** | Collections #3–4 + brief regen |
| **Mon 18** | Collection #5 + 2 oil changes + [customer] JV |
| **Tue 19** | GHL overdue workflow + 2 oil changes + financial model |
| **Wed 20** | SOP owners + rental pipeline doc + deck slides 9–11 |
| **Thu 21** | Fleet register export + investor call #1 |
| **Fri 22** | Metrics snapshot + investor call #2 + week review |

---

## Agent setup (already done)

- [x] `THIS_WEEK.md` running checklist
- [x] `TODAY_COLLECTIONS.md` ranked queue
- [x] `INVESTOR_METRICS_SNAPSHOT.md`
- [x] `GHL_OVERDUE_WORKFLOW_SETUP.md`
- [x] `RENTAL_GHL_PIPELINE.md` + `LEAD_FOLLOWUPS_THIS_WEEK.md` + `MAINTENANCE_WEEK_SCHEDULE.md`
- [x] Supabase brief restored to `OPERATIONS/DAILY_BRIEF_2026-05-16.md`

*Last updated: 2026-05-16*
