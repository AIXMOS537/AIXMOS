# Automation Priority Backlog — Established Operator (ROI Ranked)

**Goal:** Wire the highest **cash and risk** automations first—not the full map.  
**Sources:** `AIX_AI_COMMAND_SYSTEM/AUTOMATION_MAP.md` · `TMMT MANAGEMENT/AUTOMATIONS/AUTOMATION_BACKLOG.md` · live daily brief pain.

**Rule:** Each item should save owner time weekly **or** protect revenue within 30 days.

---

## Tier 0 — Already active (keep running)

| Rank | Automation | ROI | Status | Path |
|------|------------|-----|--------|------|
| — | Daily command center / brief | Visibility → faster collections | **Active** | `AUTOMATIONS/SCRIPTS/daily_command_center.py` |
| — | Maintenance reminders | Avoids downtime + surprise repairs | **Active** | `SCRIPTS/maintenance_reminders.py` |
| — | Customer follow-up reminders | Conversion + retention | **Active** | `SCRIPTS/customer_followup_reminders.py` |

---

## Tier 1 — Wire first (this week → 2 weeks)

| Rank | Automation | Problem solved | Est. ROI | Tool | Blueprint / config |
|------|------------|----------------|----------|------|-------------------|
| **1** | Overdue payment alert (daily until cleared) | Cash — #1 brief pain | **Very high** | GHL workflow / n8n / Supabase trigger | `AUTOMATION_MAP.md` P1 |
| **2** | Payment due reminders (before due + day-of) | Prevents overdue pile-up | **Very high** | GHL + OpenPhone | `AUTOMATION_MAP.md` P2 |
| **3** | Return reminder (24h before) | Late returns, extensions chaos | **High** | OpenPhone scheduled / n8n | `AUTOMATION_BACKLOG.md` row 21 |
| **4** | Booking confirmation + payment link | Faster close, less manual typing | **High** | GHL / OpenPhone | `AUTOMATION_BACKLOG.md` row 18 |
| **5** | Pick-up reminder (24h + day-of) | No-shows, wrong vehicle | **High** | OpenPhone / n8n | Rows 19–20 |
| **6** | Bill due reminder (7d / 3d / due) | Owner solvency | **High** | Zapier/Make → Airtable Bills | `AUTOMATION_MAP.md` P1 |
| **7** | New lead → immediate text + Airtable | Speed-to-lead | **High** | GHL native + `Leads_Deals.csv` | `AUTOMATION_MAP.md` P2 |

**Week 1 owner focus:** Ranks **1–2** only. Do not start Tier 3 until 1–2 fire daily without babysitting.

---

## Tier 2 — Next 30 days (ops scale)

| Rank | Automation | ROI | Tool | Notes |
|------|------------|-----|------|-------|
| 8 | Late return → team alert | Medium-high | n8n | `AUTOMATION_MAP.md` |
| 9 | Idle vehicle 24h → marketing task | Utilization | Airtable task / ClickUp | Map P2 |
| 10 | Vehicle maintenance due → task | Fleet uptime | Cron + `maintenance_reminders.json` | Already scripted — wire to ClickUp |
| 11 | No lead response 2h → follow-up task | Pipeline | GHL | Map P2 |
| 12 | Credit card utilization alert | Personal/biz bleed | Airtable `Credit_Cards.csv` | Map P1 |
| 13 | Expense tagged Unknown → review | Leak detection | Airtable `Money_Leaks.csv` | Map P1 |
| 14 | Weekly operations report | Investor metrics input | Script → sheet | Backlog row 14 |

---

## Tier 3 — Command layer (after cash automations stable)

| Rank | Automation | ROI | Path |
|------|------------|-----|------|
| 15 | Supabase command log | Audit trail before scale | `COMMAND_AGENT_IMPLEMENTATION_PLAN.md` |
| 16 | Telegram owner command bot | Owner capture speed | Backlog row 9 |
| 17 | GHL command intake webhooks | CRM → tasks | `WEBHOOKS/command_router_test_payloads.json` |
| 18 | n8n command router MVP | Multi-channel | `WORKFLOWS/N8N_COMMAND_ROUTER_BLUEPRINT.md` |
| 19 | ClickUp task assignment | Delegation | Backlog row 13 |
| 20 | Local business memory index (RAG) | AI accuracy | `LOCAL_AI_ASSISTANT_ARCHITECTURE.md` |

---

## Tier 4 — Defer (low ROI until team size / dealer live)

| Item | Why defer |
|------|-----------|
| Credit repair / funding automations | Distraction from rental + raise |
| Ecommerce automations | Map P4 — not core |
| Review request automation | Nice after return reminders work |
| Full Zapier mirror of entire map | Expensive, fragile |
| USB-local AI fleet (hardware doc) | Separate from rental ops ROI |

---

## ROI scoring rubric (how ranked)

| Score | Criteria |
|-------|----------|
| 5 | Direct $ in 7 days (collections, payment due) |
| 4 | Prevents loss event (maintenance, late return) |
| 3 | Saves owner 2+ hrs/week |
| 2 | Reporting / investor metrics only |
| 1 | Convenience |

---

## Implementation order (copy to COMMAND_CENTER)

```text
Week 1:  #1 Overdue alert + #2 Payment due reminders
Week 2:  #3 Return reminder + #4 Booking confirmation
Week 3:  #5 Pick-up reminders + #6 Bill due
Week 4:  #7 Lead instant response + review Tier 2 pick one
```

**Integration registry:** Update `TMMT MANAGEMENT/INTEGRATIONS/INTEGRATION_REGISTRY.md` when each goes live (GHL / n8n / Airtable).

---

## Investor talking point

"We run a **ranked automation backlog** tied to unit economics—not random Zapier sprawl. Tier 1 is collections and booking confirmations; command router comes after cash automations are proven."

---

*Revisit monthly. Mark Status column in `AUTOMATION_BACKLOG.md` when promoted from Proposed → Active.*
