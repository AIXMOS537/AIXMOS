# AIX Business Ops — Terminal Driver

One command on your work Mac to sync live data, refresh your command center, queue collections, and draft lead outreach.

## Quick start

```bash
cd ~/dev/AIX_Command_Center
./scripts/aix-biz morning
```

Or after opening a new terminal (alias in `~/.zshrc`):

```bash
aix-biz morning
```

## Commands

| Command | What it does |
|---------|----------------|
| `aix-biz` / `aix-biz morning` | Full run: Supabase brief → command center → collections → lead drafts |
| `aix-biz sync` | Regenerate `DAILY_BRIEF_YYYY-MM-DD.md` from Supabase only |
| `aix-biz leads [N]` | Draft N lead messages under `OPERATIONS/VA_LEAD_DRAFTS/` |
| `aix-biz collections` | Refresh `TODAY_COLLECTIONS.md` from latest brief |
| `aix-biz cleanup` | Update command center date/priorities; flag stale tasks |
| `aix-biz status` | Integration + service health |
| `aix-biz watch` | Re-sync every 30 minutes |
| `aix-biz channels` | iMessage / GHL / WhatsApp readiness |
| `aix-biz send` | Interactive queue: approve each draft → GHL / iMessage / WhatsApp |
| `aix-biz send-one FILE --channel ghl` | Send one approved draft |
| `aix-biz open-ghl` | Open GHL Conversations inbox |
| `aix-biz say imessage "+1…" "text"` | Quick one-off message |

## Channels (iMessage · WhatsApp · GHL)

- **GHL (default for rentals)** — SMS API routes to **WhatsApp in GHL** when your business line is connected there. Use for customers and leads.
- **iMessage** — Mac Messages.app (`imessage_send.sh`). Good for personal contacts and your own team.
- **WhatsApp (wa.me)** — Opens compose in personal WhatsApp; use GHL for customer traffic when possible.

```bash
aix-biz channels    # verify keys
aix-biz open-ghl      # inbox
aix-biz send          # g = GHL, i = iMessage, w = WhatsApp, c = copy, s = skip
```

Config: `TMMT MANAGEMENT/AUTOMATIONS/CONFIG/outbound_channels.json`  
Stack doc: `CHANNEL_STACK_GHL_WHATSAPP_SLACK.md`

## Safety

- **Drafts first** — `morning` does not auto-send. Use `aix-biz send` and confirm each message.
- Credentials: `AUTOMATIONS/.env` + `tmmt-os/.env.local` (`GHL_API_KEY`, `GHL_LOCATION_ID`).

## What gets updated live

1. `OPERATIONS/DAILY_BRIEF_*.md` — payments, fleet, leads, tickets from Supabase
2. `OPERATIONS/COMMAND_CENTER.md` — today's date + Top 3 from brief
3. `OPERATIONS/TODAY_COLLECTIONS.md` — ranked collection queue
4. `OPERATIONS/VA_LEAD_DRAFTS/<date>/` — CHUMMO-style outreach drafts

## Related scripts

- `./AIX_AI_COMMAND_SYSTEM/scripts/tmmt-day` — morning prompt + optional AI snapshot
- `./scripts/start-command-center-mac.sh` — CHUMMO portal + Ollama stack
- `OWNER_DAILY_COMMAND.md` — 20-minute owner ritual

## Midday / rescue

```bash
./AIX_AI_COMMAND_SYSTEM/scripts/tmmt-day --midday
```
