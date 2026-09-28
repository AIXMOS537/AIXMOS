# iPhone Setup — Brainiac 7 (complete)

Speak into your iPhone → tasks on **Brainiac 7** → you **approve** → filed on NAS / sent to team.

**Requires:** Tailscale on iPhone + Brainiac 7 running at home.

---

## Part 0 — One-time on Brainiac 7 (PC)

Do this before touching the iPhone.

```powershell
cd C:\AI-OPS-STARTER
Copy-Item .env.example .env
notepad .env
```

Set in `.env`:

```env
MOBILE_WEBHOOK_SECRET=pick-a-long-random-password-here
MOBILE_VERIFY_MODE=approve
WEBUI_NAME=Brainiac 7
```

Then:

```powershell
.\scripts\phase1-windows-bootstrap.ps1
docker compose --profile voice up -d
```

1. Open http://127.0.0.1:5678 → **n8n** → import:
   - `n8n/voice-memo-to-task.json`
   - `n8n/inbound-message-draft-response.json`
2. **Activate** both workflows (toggle ON).
3. Tailscale on Windows → note name **`brainiac-7`** works in admin console (MagicDNS).

---

## Part 1 — Tailscale on iPhone

1. App Store → **Tailscale** → install → sign in (**same account** as PC).
2. Connect VPN (toggle on).
3. Open Tailscale app → confirm **brainiac-7** is online (green).
4. Safari test: `http://brainiac-7:3000` → Open WebUI login (optional bookmark).

If that URL fails, use the PC’s Tailscale IP from the app (e.g. `http://100.x.y.z:3000`).

---

## Part 2 — Shortcut: “Brainiac Task” (voice → tasks)

Uses **dictation** (fastest on iPhone). No audio upload needed.

### Build the Shortcut

1. Open **Shortcuts** → **+** → name: **Brainiac Task**
2. Add actions in order:

| # | Action | Settings |
|---|--------|----------|
| 1 | **Dictate Text** | Stop Listening: After Pause |
| 2 | **Text** | (pass-through — optional) |
| 3 | **Get Contents of URL** | See below |
| 4 | **Show Result** | Shows Brainiac reply |
| 5 | **Quick Look** | Optional — pretty JSON |

**Get Contents of URL:**

- URL: `http://brainiac-7:5678/webhook/voice-memo`
- Method: **POST**
- Headers:
  - `Content-Type` = `application/json`
  - `X-Webhook-Secret` = `YOUR_MOBILE_WEBHOOK_SECRET` (same as `.env`)
- Request Body: **JSON**
  ```json
  {
    "source": "iphone",
    "operator": "Muhammad Taha",
    "transcript": "[Dictated Text]",
    "verify_mode": "approve"
  }
  ```
  Tap **Dictated Text** variable where shown for `transcript`.

3. **Shortcuts** → **Brainiac Task** → **ⓘ** → Add to Home Screen.
4. **Siri:** “Hey Siri, Brainiac Task” (rename in shortcut settings).

### Use it

1. Tailscale **ON**
2. Run **Brainiac Task** → speak: *“Call Dominique tomorrow, P1, and email Michael the warehouse list.”*
3. Read **Show Result** — status `pending_approval`, task summary from Operator.
4. On PC later: check NAS `W:\life\inbox\voice\pending\` or Open WebUI **Operator** to confirm.

---

## Part 3 — Shortcut: “Brainiac Reply” (message → draft)

When someone texts/emails you and you want a reply draft:

1. **Copy** their message (long-press → Copy).
2. Run shortcut **Brainiac Reply** (create below).

| # | Action | Settings |
|---|--------|----------|
| 1 | **Get Clipboard** | |
| 2 | **Ask for Input** | Prompt: “Who is this from?” → store as Contact |
| 3 | **Get Contents of URL** | POST `http://brainiac-7:5678/webhook/inbound-message` |
| 4 | **Show Result** | Counsel draft |

**POST body (JSON):**

```json
{
  "from": "[Provided Input]",
  "channel": "sms",
  "body": "[Clipboard]",
  "verify_mode": "approve"
}
```

Headers: same `Content-Type` + `X-Webhook-Secret`.

Copy the **DRAFT** from the result → paste into Messages.

---

## Part 4 — Safari: talk without Shortcuts

1. Tailscale ON.
2. Safari → `http://brainiac-7:3000`
3. Log in to Open WebUI.
4. Open chat **Operator** (tasks) or **Counsel** (replies).
5. Tap **microphone** on keyboard (iOS dictation) → speak → send.

Pin to Home Screen: Share → **Add to Dock** / Add to Home Screen.

---

## Part 5 — Train “already knows how to respond”

On NAS (or ask **Counsel** on PC to format), create:

`W:\life\relationships\<name>.md`

Use template: `nas/templates/contact-response-profile.md`

Example for a client:

- Tone: professional, brief  
- Never promise dates without checking with Taha  
- Sample replies: paste 2 real texts you sent  

**Counsel** + inbound webhook use this over time (RAG in Open WebUI Documents).

---

## Part 6 — Approve tasks (verify mode)

Default: `MOBILE_VERIFY_MODE=approve`

- Phone shows summary after shortcut runs.
- Full task list: Brainiac 7 → Open WebUI → **Operator** → paste: *“Show pending voice tasks and file to NAS.”*
- Or on PC: `W:\life\inbox\voice\pending\`

To auto-file personal reminders only (later), change `.env` to `auto_low_risk` — see `docs/mobile-voice-command-center.md`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| URL won’t load | Tailscale on? PC awake? Try `http://100.x.y.z:5678` |
| 401 / invalid secret | `X-Webhook-Secret` must match `.env` exactly |
| n8n 404 | Workflow activated? Path `voice-memo` / `inbound-message` |
| Empty draft | Paste full message in clipboard; fill “Who is this from?” |
| Slow | PC sleeping — disable sleep on Brainiac 7 or wake on LAN |

---

## Quick reference

| Action | How |
|--------|-----|
| Voice → tasks | Siri: **“Brainiac Task”** |
| Message → draft | **Brainiac Reply** after copy text |
| Free chat | Safari → brainiac-7:3000 → Operator / Counsel |
| Supreme decisions | Safari → Counsel/Oracle or wait for PC |

---

## Files in this kit

- `setup/phone/ios-voice-to-brainiac.md` — technical notes  
- `docs/mobile-voice-command-center.md` — architecture  
- `docs/auto-response-playbook.md` — contact training  

After Brainiac 7 Phase 1, do **this guide** — ~20 minutes on iPhone.
