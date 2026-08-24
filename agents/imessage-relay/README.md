# Text-My-Mac — local iMessage assistant (Cursor not required)

M1 Max runtime. Incoming iMessages → local Ollama → T1 auto-reply as Rick (assistant). T2 draft. T3 never.

**Runtime is LaunchAgents + Terminal. Not Cursor. Not Claude Code.**

Owner doc: `~/Desktop/★ TEXT-MY-MAC.md`  
Homelab: `~/Desktop/★ LOCAL-HOMELAB.md`

## Commands

```bash
me on
node assistant.js --status
node assistant.js --mock-test    # synthetic — never Messages.app
node assistant.js --live
```

## Tiers

| Tier | What | Auto-send |
|------|------|-----------|
| T1 | Assistant fielding | Yes when `auto_send_assistant` (signed as Rick) |
| T2 | Commitment / Taha-voice | Never |
| T3 | Family / money / legal | Never |

## Gates

- Kill: `me kill` or `~/.config/tmmt/imessage-assistant/KILL`
- Rate: 40 drafts/h, 20 sends/h, 4 sends/sender/h
- LLM: `:4000` then Ollama `:11434`
- HTTP `/send` stays 403

## 24/7 without Cursor

Grant Full Disk Access to **`/usr/local/bin/node`** (not Cursor).  
Fallback: Terminal.app already has FDA → `me bind`
