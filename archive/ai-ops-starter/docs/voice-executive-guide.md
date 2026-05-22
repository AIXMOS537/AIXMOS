# Voice & Talk — Three Executives

Use **Brainiac 7** (Open WebUI on Windows; Mac via Tailscale) to **speak** with Oracle, Operator, and Counsel.

---

## Recommended flow

```
You speak (mic)
    → Faster-Whisper (local STT)  OR  browser speech-to-text
    → Open WebUI chat (pick executive)
    → Ollama (qwen2.5:7b / llama3.2)
    → Read answer aloud (browser TTS or you read screen)
    → Operator files summary to NAS W:\life\inbox\processed\
```

---

## 1. Enable Faster-Whisper (local transcription)

On Windows AI machine:

```powershell
cd C:\AI-OPS-STARTER
docker compose --profile voice up -d
```

Service: `http://127.0.0.1:8000` (localhost only)

Test:
```powershell
# Record or use a sample WAV, then POST per faster-whisper API docs
```

---

## 2. Open WebUI voice

1. Open http://127.0.0.1:3000 (or Tailscale IP from Mac)
2. **Settings** → enable voice/speech features if available in your build
3. Create **three chats** pinned:
   - `Oracle — Strategist`
   - `Operator — Daily`
   - `Counsel — Comms`
4. Paste system prompts from `agents/*.md` into each chat's system prompt (or Workspace → Prompts with `/oracle`, `/operator`, `/counsel`)

### Which executive when (spoken)

| You say… | Open chat |
|----------|-----------|
| "Should I…", "What matters today", "Risk of…" | **Oracle** |
| "Process my day", "What's on my plate", "Remind me" | **Operator** |
| "Help me reply", "How do I say", "Research X" | **Counsel** |

---

## 3. Daily voice rituals (suggested)

| Time | Executive | Prompt example |
|------|-----------|----------------|
| Morning | Operator | "Morning brief — my 3 priorities and what's waiting on others." |
| Midday | Oracle | "I'm torn between A and B — 2 minute decision." |
| Evening | Operator | "Close out — what moved, what carries to tomorrow, file to NAS." |
| As needed | Counsel | "Read this draft aloud and make it warmer." |

---

## 4. Save voice sessions to NAS

After important chats, ask Operator:

> "Summarize this thread for NAS under life/inbox/processed/today.md"

Or automate via n8n: `n8n/daily-recap.json` (weekday 5pm).

---

## 5. MacBook voice

- **Option A:** Tailscale → Windows Open WebUI (best — uses GPU brain)
- **Option B:** Mac mic + paste transcript into WebUI
- Do **not** duplicate Ollama on Mac for daily use unless testing offline

---

## 6. Hardware tips

- Quiet room + USB mic improves Whisper accuracy
- Headphones prevent speaker bleed into mic
- For long rambles: speak in **one topic per message** — better for Operator processing

---

## 7. Privacy

- Voice stays local (Whisper + Ollama on Windows)
- Raw audio optional on NAS `hot/voice-notes/` — set retention in `security-checklist.md`
- No cloud STT unless you explicitly enable paid APIs in `.env` (disabled by default)
