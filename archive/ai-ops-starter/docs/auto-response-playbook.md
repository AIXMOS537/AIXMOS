# Auto-Response — Messages & Contacts

When someone texts, emails, or contacts you, **Counsel** drafts a reply using **your** tone and rules — stored on NAS. You approve before send (default).

---

## What “knows how to respond already” means

Brainiac does **not** blindly spam replies. It:

1. **Identifies** who contacted you (name, client, family, vendor)
2. **Loads** their file from NAS (`life/relationships/`, `work/clients/`)
3. **Applies** your rules (`knowledge/templates/comms/`, Counsel agent)
4. **Drafts** a reply in your voice
5. **Waits** for approve — or auto-sends only if you enabled safe auto-rules

---

## NAS — teach it how you respond

Create one file per important contact:

```
W:\life\relationships\<name>.md
W:\work\clients\<client>\comms-rules.md
```

Template: `nas/templates/contact-response-profile.md`

Each file includes:
- Relationship (client / family / vendor / team)
- Tone (warm, firm, brief)
- Always / never say
- Escalate to Taha if…
- Sample good replies (2–3)

**Counsel** reads these via RAG or you paste path in webhook body.

---

## Inbound message flow

```
Message arrives (forwarded to n8n)
        ▼
Counsel (Ollama) + contact profile
        ▼
Draft → W:\life\comms\drafts\pending\
        ▼
Phone notification → Approve / Edit / Reject
        ▼
You send manually OR auto-send (if rule matched)
```

Import: `n8n/inbound-message-draft-response.json`

---

## How messages get to Brainiac 7

Pick one or more (local-first):

| Source | Method |
|--------|--------|
| **Email** | n8n IMAP trigger → draft only |
| **SMS (Android)** | SMS forwarder app → webhook |
| **iPhone** | Forward copy to email → IMAP; or manual paste to webhook |
| **Slack/Teams** | n8n trigger (if you use it) |
| **Manual** | iOS Shortcut “Forward to Brainiac” with message body |

Full SMS auto-send on iPhone is **limited by Apple** — draft + one-tap copy is the realistic path.

---

## Auto-send rules (optional, `.env`)

```env
MOBILE_VERIFY_MODE=approve
AUTO_REPLY_ENABLED=false
AUTO_REPLY_ALLOWED_CONTACTS=family,team-internal
AUTO_REPLY_NEVER=legal,contracts,angry-clients,new-leads
```

When `AUTO_REPLY_ENABLED=true` and contact tag matches `AUTO_REPLY_ALLOWED_CONTACTS`, Counsel may auto-file to `drafts/sent/` — you still log everything on NAS.

**Never auto-send** without profiles on NAS.

---

## Claryn (Ryn / Mystique) lane

**Claryn’s PC** → Counsel executive → comms drafts.  
Escalate to **Brainiac 7** for final send on high-stakes threads.

---

## Daily training (5 min)

When you reply to someone well, tell Operator:

> “Save this as a sample reply for [Name] on NAS.”

Or add to their `relationships/<name>.md` file.

Over time Counsel “already knows” because **you taught it on NAS**, not because it guesses.

---

## Security

- Webhook secret required (`MOBILE_WEBHOOK_SECRET`)
- Tailscale only — no public n8n webhooks
- No credentials in contact files
