# Your Channel Stack — WhatsApp (rentals) · GHL (everything) · Slack (credit)

**Your rule:** English in all chats. VA enforces shift templates (see `VA_SETUP_TODAY.md`).

---

## Who owns what

| Channel | Business | Role |
|---------|----------|------|
| **WhatsApp** (via GHL) | **Car rentals (TMMT)** | Customer texts, rental leads, payment reminders, collections |
| **GoHighLevel (GHL)** | **Everything** | CRM, pipelines, SMS/email, workflows, WhatsApp connection, internal tasks |
| **Slack** | **Credit repair + business funding** | Team commands, lead alerts, tasks, owner approvals — **not** rentals |

**Do not** run rental ops main chat in Slack. **Do not** expect raw WhatsApp groups on your Mac to sync — WhatsApp for rentals goes **through GHL**.

---

## Architecture

```text
                    ┌─────────────────────────────────────┐
                    │         GoHighLevel (HUB)            │
                    │  contacts · pipelines · workflows    │
                    │  WhatsApp · SMS · email · tasks      │
                    └───────────┬─────────────────────────┘
                                │
        WhatsApp customers ─────┤ rental pipeline
        (GHL WhatsApp inbox)    │ overdue / booking automations
                                │
                                │ webhooks
                                ▼
                    ┌─────────────────────────────────────┐
                    │              n8n                     │
                    │     POST /command-router             │
                    └───────────┬─────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        Supabase log      ClickUp tasks     TMMT OS /api/intake
              │                 │
              │                 └──► Slack #credit-commands (credit only)
              │
              └──► Owner: SMS/email/Telegram DM (brief)
```

**Read truth:** TMMT OS + Supabase (fleet, overdue list)  
**Act on rentals:** GHL + WhatsApp (in GHL)  
**Act on credit:** Slack + GHL credit pipeline  

---

## Part 1 — GHL as hub (set up first)

### A. Connect WhatsApp to GHL (rentals)

1. GHL → **Settings → Phone numbers → WhatsApp** (or WhatsApp Business via GHL partner).
2. Use **one rental ops number** — team and customers see the same business line.
3. Turn on **Conversations** inbox — all rental WhatsApp lands here (not a random group on personal WhatsApp).

**Ops team habit:** Internal coordination can stay in a **separate** WhatsApp group if you want, but **customer** and **lead** traffic should be in **GHL Conversations** so automations work.

### B. Rental pipeline in GHL

Document stages in: `TMMT MANAGEMENT/CUSTOMERS/RENTAL_GHL_PIPELINE.md`

Minimum stages:

`New lead` → `Contacted` → `Qualified` → `Booking sent` → `Booked` → `Active rental` → `Payment overdue` → `Returned` / `Lost`

Custom fields: `payment_due_date`, `payment_status`, `amount_due`, `vehicle_assigned`, `pickup_date`, `return_date`

### C. First GHL automation (do this week)

**Overdue payment alert** — step-by-step:  
`TMMT MANAGEMENT/AUTOMATIONS/GHL_OVERDUE_WORKFLOW_SETUP.md`

Trigger: tag `payment-overdue` OR stage **Payment overdue**  
Actions: notify you + create task + optional customer reminder SMS/WhatsApp from template library.

### D. GHL webhooks → n8n (when ready)

GHL → **Automation → Webhook** on:

- Pipeline stage change (rental)
- Tag applied (`payment-overdue`, `new-credit-lead`, etc.)
- Inbound message (optional — high volume)

Webhook URL: `https://YOUR-N8N-URL/webhook/command-router`

Body example:

```json
{
  "source_channel": "ghl",
  "sender_id": "{{contact.id}}",
  "sender_name": "{{contact.name}}",
  "message_text": "Stage: {{opportunity.stage}} | Tag: payment-overdue | Amount: {{custom.amount_due}}"
}
```

n8n blueprint: `TMMT MANAGEMENT/AUTOMATIONS/WORKFLOWS/N8N_COMMAND_ROUTER_BLUEPRINT.md`

---

## Part 2 — WhatsApp for car rentals (through GHL only)

| Use WhatsApp for | Route |
|------------------|--------|
| Customer booking questions | GHL Conversations → rental pipeline |
| Payment reminders / overdue | GHL workflow → WhatsApp template |
| New lead from ad/form | GHL trigger → WhatsApp welcome |
| **Internal ops shift posts** | Separate WhatsApp **group** OR move internal to **Slack #ops** — GHL does **not** read private groups |

**Owner morning (rentals):**

1. GHL inbox — red/hot conversations  
2. TMMT OS — cases / vendor / fleet  
3. `TODAY_COLLECTIONS.md` + daily brief  
4. Not: scraping WhatsApp Desktop on Mac  

**Internal shift templates (SHIFT START/END):**

- If team stays in WhatsApp group → **VA** still sends **OWNER BRIEF** in English (manual until bot).  
- **Better long-term:** move **internal** ops to **Slack #tmmt-ops** (rentals) and keep **WhatsApp in GHL for customers only**.

---

## Part 3 — Slack for credit only

### Channels to create

| Channel | Purpose |
|---------|---------|
| `#credit-commands` | Credit repair + funding tasks, lead alerts, `/command` |
| `#credit-approvals` | Owner approve before customer-facing sends (optional) |
| `#credit-wins` | Funded clients, disputes won (morale + metrics) |

**Do not** put rental dispatch, fleet, or pick-up/return in these channels.

### Slack app → n8n

1. [api.slack.com/apps](https://api.slack.com/apps) → Create app **TMMT Credit Command**.  
2. Scopes: `chat:write`, `channels:history`, `channels:read`, `commands`.  
3. Event subscription → n8n webhook → `message.channels` for `#credit-commands` only.  
4. Slash command `/credit` → same webhook.

**Classifier in n8n:** if `source_channel == slack` → force `business = credit_education` (skip TMMT/rental keywords).

Example owner message in Slack:

```text
New lead: Mike wants business funding checklist — follow up tomorrow 10am high
```

n8n creates: GHL contact (credit pipeline) + ClickUp task + Slack confirmation reply.

### Credit GHL pipeline (separate from rental)

Fill in GHL (mirror rental doc):

- Stages: New lead → Contacted → Qualified → Enrolled → Active → Complete / Lost  
- Connect Slack: when stage = **New lead**, post to `#credit-commands` via n8n.

Reference tasks: `TMMT MANAGEMENT/EXECUTION/TODAY.md` (credit Slack + GHL list).

---

## Part 4 — n8n routing rules (one router)

| Incoming | Route `business` | Actions |
|----------|------------------|---------|
| GHL + rental pipeline / keywords TMMT, rental, fleet | `tmmt_rentals` | GHL task, Supabase log, optional TMMT `/api/intake` |
| GHL + credit pipeline / keywords credit, funding, dispute | `credit_education` | GHL + **Slack #credit-commands** + ClickUp |
| Slack `#credit-commands` only | `credit_education` | Same |
| WhatsApp message **inside GHL** | Classify by pipeline attached to contact | Same as row 1 or 2 |

**Approval required** before: send customer message, charge, refund, legal language (see `COMMAND_ROUTER.md`).

---

## Part 5 — TMMT OS + Supabase (rentals back end)

- **Overdue $ truth:** Supabase / daily brief → n8n can tag contact **payment-overdue** in GHL.  
- **Cases (tow, damage, vendor):** `POST https://tmmt-c919-two.vercel.app/api/intake` with `source: "ghl"`.  
- Checklist: `TMMT MANAGEMENT/tmmt-os/docs/VERCEL_PRODUCTION_CHECKLIST.md`

---

## Build order (4 weeks)

| Week | Focus | Owner | Tech VA |
|------|--------|-------|---------|
| **1** | GHL WhatsApp live + rental pipeline stages + overdue workflow | Confirm stage names | Wire GHL_OVERDUE_WORKFLOW_SETUP |
| **2** | Slack `#credit-commands` + app + pin credit team rules (English) | Create channels | n8n Slack → credit route only |
| **3** | GHL webhooks → n8n → command-router | Test one rental + one credit event | Build blueprint workflow |
| **4** | Supabase overdue → GHL tag sync | Review brief vs GHL | Scheduled n8n job |

---

## What you do vs team

| You | Ops / rental VA | Credit team | Tech VA |
|-----|-----------------|-------------|---------|
| GHL inbox 10 min/day | WhatsApp **customers** via GHL | Slack `#credit-commands` | n8n + webhooks |
| Approve money/legal in Slack | Shift templates in **internal** chat | Post leads + follow-ups in Slack | GHL ↔ Supabase sync |
| Top 3 from OWNER BRIEF | ENGLISH OWNER BRIEF to you | Use credit templates | Slack app |

---

## Checklist — copy to THIS_WEEK

**GHL / WhatsApp (rentals)**

- [ ] WhatsApp connected in GHL  
- [ ] Rental pipeline stages match `RENTAL_GHL_PIPELINE.md`  
- [ ] Overdue workflow live (`GHL_OVERDUE_WORKFLOW_SETUP.md`)  
- [ ] Payment reminder templates from `MESSAGE_TEMPLATE_LIBRARY.md`  

**Slack (credit)**

- [ ] `#credit-commands` created  
- [ ] Slack app installed, n8n webhook tested  
- [ ] Credit pipeline in GHL named and linked  

**Hub**

- [ ] n8n `command-router` workflow from blueprint  
- [ ] Secrets in n8n / Vercel only (not chat)  

---

## Related files

| File | Topic |
|------|--------|
| `CHANNEL_SETUP_GUIDE.md` | All channels + Telegram/iMessage optional |
| `TMMT MANAGEMENT/EXECUTION/COMMAND_ROUTER.md` | Router spec |
| `AIXMOSXTMMT-OPS/docs/ghl-pipelines.md` | Dealer pipeline (not rental) |
| `GROUP_CHAT_OPERATING_SYSTEM.md` | English shift templates + owner AI |

*Stack: WhatsApp rentals via GHL · GHL hub · Slack credit only.*
