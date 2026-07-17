# CHUMMO ↔ GHL Webhook

Local Node service that lets any GHL workflow request a CHUMMO-drafted message and write it back into the contact as a custom field. Keeps outbound at Level A (human approves before send).

## Endpoints

| Method | Path | Body |
|---|---|---|
| GET | `/health` | — |
| POST | `/draft` | `{ agent, channel, context }` |
| POST | `/draft/sms` | `{ context }` (defaults agent=chummo, channel=sms) |
| POST | `/draft/email` | `{ context }` |
| POST | `/draft/dm` | `{ context }` |

All POSTs require header: `X-Webhook-Secret: <env GHL_WEBHOOK_SHARED_SECRET>`

### `context` fields

```json
{
  "first_name": "Marcus",
  "last_name": "Hayes",
  "vertical": "credit",
  "geo": "md",
  "lifecycle": "lead",
  "source": "ig_paid",
  "last_action": "downloaded credit starter pack",
  "score_baseline": 580,
  "intent": "wants to qualify for fleet financing",
  "notes": "tried Lexington Law, frustrated",
  "offer": "(optional override — default is the $97 membership pitch)"
}
```

### Response

```json
{
  "draft": "Marcus — saw you grabbed the starter pack...",
  "length": 142,
  "length_ok": true,
  "agent": "chummo",
  "channel": "sms",
  "backend": "claude",
  "took_ms": 2810
}
```

## Setup (one-time)

```powershell
setx GHL_WEBHOOK_SHARED_SECRET "<32+ chars random>"
setx PORT "4099"
```

Open a NEW terminal. Then double-click `START-WEBHOOK.bat` (or schedule it to run at login via Task Scheduler).

## Wiring it into GHL

1. In your GHL Workflow, add a step: **Custom Webhook** (POST).
2. URL: `http://YOUR-PC-IP:4099/draft/sms` (or expose via Cloudflare Tunnel / ngrok for cloud reach).
3. Headers: `X-Webhook-Secret: <your secret>`, `Content-Type: application/json`.
4. Body (use GHL merge fields):
   ```json
   {
     "context": {
       "first_name": "{{contact.first_name}}",
       "vertical": "{{contact.vertical}}",
       "lifecycle": "{{contact.lifecycle}}",
       "source": "{{contact.lead_source}}"
     }
   }
   ```
5. Map response `draft` into a contact custom field (e.g. `chummo_draft_sms`).
6. Next step in the workflow: **Send SMS** with body `{{contact.chummo_draft_sms}}`. Add a manual approval gate before send if Level A required.

## Exposing the local server to GHL (cloud reach)

GHL workflows run in the cloud and can't hit `localhost:4099` directly. Options:

| Option | Effort | Cost |
|---|---|---|
| **Cloudflare Tunnel** (recommended) | 15 min — install `cloudflared`, run `cloudflared tunnel create chummo-ghl`, route subdomain | Free |
| **ngrok** | 5 min — but URL changes unless paid | $8/mo for stable URL |
| **Run on a VPS** | 1-2 hr — DigitalOcean droplet, point GHL there, but then you need to babysit | $6+/mo |

Cloudflare Tunnel is best long-term because you keep the brain on your own machine but get a stable public URL like `chummo-webhook.aixmos.com`.

## Backend selection

Inherits `AIXMOS_LLM_BACKEND` from your User env (set during AIXMOS install):
- `claude` — AIXMOS API
- `ollama` — local LLM (offline)
- `auto` — AIXMOS with Ollama fallback

Smoke-test with:

```powershell
curl -X POST http://localhost:4099/draft/sms `
  -H "X-Webhook-Secret: $env:GHL_WEBHOOK_SHARED_SECRET" `
  -H "Content-Type: application/json" `
  -d '{"context":{"first_name":"Marcus","vertical":"credit","lifecycle":"lead","source":"ig_paid"}}'
```
