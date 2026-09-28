# Channel Setup — WhatsApp, Telegram, iMessage, Slack

**Goal:** Messages from chat → your computer / n8n → tasks, brief, Airtable (not you copying by hand).

**Your stack already defines the hub:** one webhook `POST /command-router` (n8n). Every channel feeds that.

**Important:** Personal WhatsApp **group** chats cannot be officially “read” by your Mac like email. Use the routes below.

---

## Architecture (one picture)

```text
WhatsApp (GHL/Business API) ──┐
Telegram Bot ─────────────────┼──► n8n (command-router) ──► Supabase log
Slack App ────────────────────┤         │
iMessage Shortcut ────────────┘         ├──► ClickUp / Airtable / GHL
                                        ├──► VA: OWNER BRIEF (email/Telegram DM)
                                        └──► Optional: TMMT OS POST /api/intake
```

**Owner:** you send **commands** (Telegram/Slack best).  
**Ops group:** team posts **SHIFT START/END** in English → bot or VA summarizes → you get OWNER BRIEF.

---

## Difficulty & honesty

| Channel | Read group chat automatically? | You send commands? | Best for you |
|---------|-------------------------------|--------------------|--------------|
| **Telegram** | Yes (bot in group) | Yes | **Build first** |
| **Slack** | Yes (Slack app) | Yes | Credit team + internal ops |
| **WhatsApp** | Only via **Business API** or **GHL** — not normal WhatsApp groups | Via GHL/Twilio | Customer + team if already on GHL |
| **iMessage** | No official API | Shortcut → webhook only | Quick personal capture |

---

## Phase 1 — Telegram bot (recommended first, ~2–4 hours)

### What you get

- Message your bot: `TMMT: follow up Chris rental pickup tomorrow 9am`
- Bot replies: task created / needs approval
- Optional: bot in **ops group** reads SHIFT posts → nightly summary to you

### Steps

1. **Create bot** — Telegram → [@BotFather](https://t.me/BotFather) → `/newbot` → save **token**.
2. **Run n8n** — Mac: `brew install n8n` or [n8n.cloud](https://n8n.io) free trial.
3. **Import workflow** — build from `TMMT MANAGEMENT/AUTOMATIONS/WORKFLOWS/N8N_COMMAND_ROUTER_BLUEPRINT.md`
4. **Webhook node** — path `command-router`, method POST.
5. **Telegram Trigger** — n8n node “Telegram Trigger” OR “Telegram” → On message → map to same normalize step as blueprint Step 1.
6. **Test payload** — `TMMT MANAGEMENT/AUTOMATIONS/WEBHOOKS/command_router_test_payloads.json`

### Bot in ops group (read shift posts)

1. Add bot to group.
2. BotFather: `/setprivacy` → **Disable** (so bot sees all messages).
3. n8n: Telegram Trigger (group) → Filter if message contains `SHIFT START` or `SHIFT END` or `BLOCKED` → append to Google Sheet / Airtable / email **OWNER BRIEF**.

**Security:** Only allow your Telegram user ID as `sender` for **commands**; group read can be separate workflow.

---

## Phase 2 — Slack (~1–2 hours)

### What you get

- `#credit-commands` or `#ops` — messages and slash commands → n8n
- Credit team gets task pings

### Steps

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch.
2. **OAuth scopes:** `chat:write`, `channels:history`, `channels:read`, `commands` (add `groups:*` if private channels).
3. **Event Subscriptions** → Enable → Request URL = your n8n webhook URL → Subscribe `message.channels` (and `message.groups` if private).
4. **Slash command** `/command` → same n8n URL (optional).
5. Install to workspace → copy **Bot Token** → n8n Slack credentials.
6. n8n: Slack Trigger → normalize → same `command-router` logic.

Map `source_channel: "slack"` in JSON to blueprint.

---

## Phase 3 — WhatsApp (realistic options)

### Option A — You already use GoHighLevel (best match for your docs)

- WhatsApp conversations live in **GHL**.
- GHL workflow or webhook → n8n → `command-router`.
- See `TMMT MANAGEMENT/AUTOMATIONS/GHL_OVERDUE_WORKFLOW_SETUP.md`.
- **Does not** read random WhatsApp **group** unless that group is connected through GHL Business.

### Option B — WhatsApp Business API (Meta / Twilio / 360dialog)

- For **official** automation and templates.
- Costs money; business verification.
- Good for customer SMS-style ops, not always for internal ops group.

### Option C — What does NOT work well

- “Scan my WhatsApp Web on Mac” scripts — breaks often, against Meta ToS, not safe for business.
- Expecting Cursor/your Mac to **listen** to personal WhatsApp desktop without Business API.

### Practical workaround (until Business API)

1. Team keeps posting English SHIFT templates in WhatsApp (current plan).
2. **VA** sends **OWNER BRIEF** to you (or forwards to **Telegram bot** DM).
3. Or: Zapier/Make **WhatsApp Business** trigger if you migrate the ops number to Business.

---

## Phase 4 — iMessage (capture only, ~30 min)

Apple does not offer a business API for iMessage.

### Mac Shortcut → webhook

1. iPhone/Mac **Shortcuts** → New Shortcut.
2. Trigger: Share sheet or quick command.
3. Actions: Get text → Get contents of clipboard → **Get contents of URL** POST to n8n:

```text
https://YOUR-N8N.app.n8n.cloud/webhook/command-router
```

Body JSON:

```json
{
  "source_channel": "imessage",
  "sender_id": "owner",
  "message_text": "[Shortcut Input]"
}
```

4. Use for: quick notes, forward a customer text, “remind me to call X”.

**Mac relay (advanced):** Messages.app + AppleScript only works with Mac awake — skip unless you have a tech lead.

---

## Phase 5 — “Computer picks up” shift posts → OWNER BRIEF

Even without full AI, automate **structure**:

| Source | n8n does |
|--------|----------|
| Telegram ops group | On `SHIFT END` → parse BLOCKED / overdue lines → Telegram DM to you |
| Slack `#ops` | Same on message event |
| WhatsApp | VA DM to Telegram bot, or manual until Business API |

Optional: OpenAI node in n8n with prompt from `GROUP_CHAT_OPERATING_SYSTEM.md` Part 1 → formatted OWNER BRIEF.

---

## Secrets (never in chat)

| Secret | Where |
|--------|--------|
| Telegram bot token | n8n credentials |
| Slack bot token | n8n credentials |
| n8n webhook URL | n8n + Vercel if needed |
| `INTAKE_WEBHOOK_SECRET` | Vercel TMMT OS — see `tmmt-os/README.md` `/api/intake` |
| OpenAI | n8n only |

---

## Build order (your registry agrees)

1. **Telegram** owner bot + optional group reader  
2. **Slack** credit/ops channel  
3. **GHL WhatsApp** webhooks (if on GHL)  
4. **iMessage** Shortcut for owner capture only  
5. Full **WhatsApp group** automation only after Business API or GHL path  

---

## Files in this repo

| File | Purpose |
|------|---------|
| `TMMT MANAGEMENT/EXECUTION/COMMAND_ROUTER.md` | Product spec |
| `TMMT MANAGEMENT/AUTOMATIONS/WORKFLOWS/N8N_COMMAND_ROUTER_BLUEPRINT.md` | n8n steps |
| `TMMT MANAGEMENT/AUTOMATIONS/WEBHOOKS/command_router_test_payloads.json` | Test JSON |
| `TMMT MANAGEMENT/INTEGRATIONS/INTEGRATION_REGISTRY.md` | Status tracker |
| `TMMT MANAGEMENT/tmmt-os/README.md` | `/api/intake` for cases |

---

## Who builds this

| Role | Task |
|------|------|
| **You** | Create Telegram bot, Slack app, approve channels |
| **Tech VA / freelancer** | n8n workflows (4–8 hrs from blueprint) |
| **Ops VA** | English shift posts until bots live |

*Not legal advice. WhatsApp/Meta policies change — prefer Business API or GHL for production.*
