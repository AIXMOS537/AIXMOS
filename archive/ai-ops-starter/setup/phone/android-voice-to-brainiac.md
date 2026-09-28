# Android → Brainiac 7 (Voice Tasks)

Requires **Tailscale** on Android.

---

## Option 1 — HTTP Shortcut app (easiest)

App: **HTTP Request Shortcuts** or **Tasker**

**POST** `http://brainiac-7:5678/webhook/voice-memo`

Headers:
```
X-Webhook-Secret: YOUR_SECRET
Content-Type: application/json
```

Body:
```json
{
  "source": "android",
  "transcript": "%VOICE_TEXT%",
  "verify_mode": "approve"
}
```

Trigger: voice command, widget, or share sheet.

---

## Option 2 — Termux + curl

```bash
curl -X POST "http://brainiac-7:5678/webhook/voice-memo" \
  -H "X-Webhook-Secret: YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"transcript":"Buy milk and call Dominique","verify_mode":"approve"}'
```

---

## SMS → Counsel draft

Apps like **SMS Forwarder** (filter by contact) → POST to:

`http://brainiac-7:5678/webhook/inbound-message`

```json
{
  "from": "%SMS_FROM%",
  "channel": "sms",
  "body": "%SMS_BODY%",
  "verify_mode": "approve"
}
```

Review draft on phone browser; copy/send yourself (or enable auto-rules in `.env`).

---

## Open WebUI

Chrome → `http://brainiac-7:3000` with Tailscale connected.
