# Mobile Voice → Brainiac 7 → Tasks on PC

Speak into your phone. Brainiac 7 **hears**, **Operator** turns it into tasks, **you verify**, then tasks hit your PC and team NAS.

---

## What you get

| Step | What happens |
|------|----------------|
| 1. **Speak** | Phone records voice (Shortcut / app) |
| 2. **Transcribe** | Local Whisper on Brainiac 7 (via Tailscale) |
| 3. **Process** | **Operator** extracts tasks, follow-ups, calendar hints |
| 4. **Verify** | You approve on phone (default) or auto if you enable it |
| 5. **Deploy** | Tasks written to NAS + n8n notifies HQ / your PC |

**Default = verify before send.** You control auto-send in `.env`.

---

## Architecture

```
Phone (mic)
   │  Tailscale VPN
   ▼
Brainiac 7 ──► Faster-Whisper (STT)
   │
   ▼
n8n webhook /voice-memo
   │
   ▼
Ollama (Operator) ──► tasks JSON
   │
   ├──► W:\life\inbox\voice\pending\
   ├──► You approve (phone browser / notification)
   └──► W:\life\tasks\ + optional team routing
```

---

## Requirements

- **Tailscale** on phone + Brainiac 7 (same tailnet)
- Brainiac 7 running: `docker compose --profile voice up -d`
- n8n workflow imported: `n8n/voice-memo-to-task.json`
- `.env`: `MOBILE_WEBHOOK_SECRET`, `MOBILE_VERIFY_MODE=approve` (default)

---

## iPhone — Siri Shortcut (recommended)

See **`setup/phone/ios-voice-to-brainiac.md`**

Summary:
1. Record audio → POST to `http://brainiac-7:5678/webhook/voice-memo`
2. Or record → transcribe via `http://brainiac-7:8000` → POST transcript
3. Open approval URL returned in response

---

## Android

See **`setup/phone/android-voice-to-brainiac.md`**

---

## Verify modes (`.env`)

| Mode | Behavior |
|------|----------|
| `approve` (default) | Tasks stay in `pending/` until you tap Approve |
| `auto_low_risk` | Personal reminders auto-file; client-facing waits for approve |
| `auto` | **Not recommended** — files all tasks without review |

---

## Talk without opening n8n

Use **Open WebUI** on phone browser (Tailscale):

`http://brainiac-7:3000` → chat **Operator** → hold mic (browser speech) or paste transcript.

---

## Related

- Auto-reply to messages: `docs/auto-response-playbook.md`
- Deploy: `docs/DEPLOY-ORDER.md`
