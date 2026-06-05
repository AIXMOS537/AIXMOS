# Open in Cursor

**Open this folder in Cursor:**

```
~/Desktop/AIX_Command_Center
```

(File → Open Folder… → Desktop → **AIX_Command_Center**)

## What to use first

| Path | Use |
|------|-----|
| **`TMMT MANAGEMENT/INTEGRATIONS/GHL_AGENCY_SETUP_TODAY.md`** | **Agency: pipeline + WF-07 + WF-00 today** |
| **`WEEK_1_GHL_WHATSAPP.md`** | **Week 1: connect WhatsApp + pipeline + overdue workflow** |
| **`CHANNEL_STACK_GHL_WHATSAPP_SLACK.md`** | **Your stack: WhatsApp rentals · GHL hub · Slack credit** |
| **`CHANNEL_SETUP_GUIDE.md`** | **All channels + Telegram/iMessage optional** |
| **`VA_SETUP_TODAY.md`** | **Send to VA — pin templates + rollout (30 min)** |
| **`GROUP_CHAT_OPERATING_SYSTEM.md`** | **Owner + VA chat templates + Admin Recorder role** |
| **`THIS_WEEK.md`** | **Start here — this week's checklist** |
| **`OWNER_DAILY_COMMAND.md`** | **20-min morning — all 4 pillars** |
| `TMMT MANAGEMENT/OPERATIONS/TODAY_COLLECTIONS.md` | Today's collection queue (ranked) |
| `TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md` | Today's tasks, follow-ups, EOD |
| `docs/INVESTOR_METRICS_SNAPSHOT.md` | Daily investor metrics log |
| `docs/INVESTOR_PITCH_DECK.md` | Pitch deck — fill remaining [FILL:] |
| **`PRIORITY_PLAN_ALL_PILLARS.md`** | **90-day fleet · bookings · money · investors** |
| `AIX_AI_COMMAND_SYSTEM/MONEY_COMMAND_CENTER.md` | Bills, cards, weekly CFO review |
| `AIX_AI_COMMAND_SYSTEM/` | Main command system — run `scripts/setup-mac.sh` |
| `TMMT MANAGEMENT/` | AI_BRAIN, AUTOMATIONS, tmmt-os |
| `docs/INVESTOR_ONE_PAGER.md` | Investor narrative + unit economics placeholders |
| `agents/` | Agent instruction markdown files |
| `ops/moose-stack/` | MOOSE multi-agent brain (`start-moose-mac.sh`) |
| `ops/chummo-stack/` | CHUMMO messaging + local portal (`serve.js`) |
| `credit_business_corporate_system/` | Cursor build pack + Milestone 1 status |
| `docs/LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md` | Multi-machine + Ollama fleet setup |

## Ollama (local AI first)

- **Start everything:** `bash scripts/start-command-center-mac.sh`
- Agents (CHUMMO, MOOSE, BRAIN) use **Ollama first**, Anthropic as fallback (`ops/files/llm-client.js`)
- **Do not** store large models on FAT32 USB drives (4 GB file limit).
- Install on Mac: `brew install ollama` → `ollama pull qwen2.5-coder:14b`
- Fleet GPU host: `OLLAMA_BASE_URL=http://ai-1:11434` (see `docs/LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md`)
- Force cloud only: `export AI_PROVIDER=anthropic`

## Investor flash drives

Operator clones from `~/Desktop/INVESTOR_FLASH_MASTER` — not from this working folder if it contains secrets in `.env` under BROTHER I originals.
