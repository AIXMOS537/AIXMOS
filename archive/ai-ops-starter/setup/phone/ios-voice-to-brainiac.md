# iPhone → Brainiac 7 (technical reference)

**Start here:** `setup/phone/IPHONE-SETUP.md` (full step-by-step).

Requires **Tailscale** connected on iPhone.

---

## Shortcut A — “Brainiac Voice Task” (record → Brainiac)

Create in **Shortcuts** app:

1. **Record Audio** (stop on tap)
2. **Get Contents of URL**
   - URL: `http://brainiac-7:5678/webhook/voice-memo`
   - Method: POST
   - Headers: `X-Webhook-Secret: YOUR_SECRET_FROM_ENV`
   - Request Body: JSON
   ```json
   {
     "source": "iphone",
     "operator": "Muhammad Taha",
     "audio_base64": "[Audio - Base64 Encode]",
     "verify_mode": "approve"
   }
   ```
   (Use Shortcut variable for base64 audio, or send transcript only — see B)

3. **Show Result** — displays approval link + task summary

Add to **Home Screen** and **Siri**: “Hey Siri, Brainiac task”

---

## Shortcut B — “Brainiac Voice” (transcript text)

If Whisper HTTP is awkward in Shortcuts, use **Dictate Text** then POST:

```json
{
  "source": "iphone",
  "transcript": "[Dictated Text]",
  "verify_mode": "approve"
}
```

Same webhook: `/webhook/voice-memo`

---

## Shortcut C — “Forward message to Counsel”

When you copy a text/iMessage:

1. **Text** from clipboard
2. POST `http://brainiac-7:5678/webhook/inbound-message`
   ```json
   {
     "from": "Contact Name",
     "channel": "sms",
     "body": "[Clipboard]",
     "verify_mode": "approve"
   }
   ```
3. Open URL from response → review Counsel draft in browser

---

## Open WebUI on phone

Safari → `http://brainiac-7:3000` (Tailscale on)

Pin **Operator** for tasks, **Counsel** for replies.

---

## Approve tasks

Browser → `http://brainiac-7:5678/webhook/approve-task?id=...`  
(Link returned by voice-memo workflow; or check NAS `life\inbox\voice\pending\`)
