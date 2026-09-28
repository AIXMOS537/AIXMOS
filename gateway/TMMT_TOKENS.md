# TMMT Tokens + Free Lane — Access & Cost Control

This is how you give **most employees free AI** and **a limited few the premium stuff**, with a
built-in credit ("TMMT token") budget per person. No crypto, no extra services — it's all in the
Gateway you're deploying.

## The three lanes
| Lane | Model | Cost to you | Who |
|---|---|---|---|
| 🆓 **free** | your own Ollama (brain PC) | **$0** | most employees |
| 💵 **haiku** | AIXMOS Haiku (cloud) | ~pennies | staff who occasionally need cloud |
| 💎 **sonnet / opus** | AIXMOS (cloud) | metered | you + 1–2 trusted people |

## TMMT tokens (credits)
Every person has a **monthly allowance** and each cloud call **debits** by model:

| Model | Token cost / call |
|---|---|
| free (Ollama) | **0** |
| haiku | 1 |
| sonnet | 5 |
| opus | 25 |

- Allowances reset automatically each month.
- **Run out? You're not cut off** — the Gateway quietly drops you to the free lane (your Ollama) so work continues; premium just pauses till next month (or you raise their allowance).
- A person can never use a model above their `maxTier`, no matter what they request.

### Who gets what (edit in `src/index.js`, the `DEFS` table)
| Person/role | maxTier | monthly tokens | meaning |
|---|---|---|---|
| You (personal/work) | opus | effectively unlimited | everything |
| Team Lead (`SECRET_LEAD`) | sonnet | 2000 | good cloud, generous |
| VA (`SECRET_VA`) | haiku | 400 | cheap cloud, then free |
| Operator (`SECRET_OP`) | free | 100 | free lane; tiny cloud burst |
| Office (`SECRET_OFFICE`) | free | 50 | free lane only, basically |

To onboard a person: copy a row, give them their own `SECRET_…`, set their `maxTier` + `monthly`.
To cut someone off: `npx wrangler secret delete SECRET_…` — that person only, instantly.

Check spend anytime (admin): `GET /usage` with your secret in `x-aixmos-auth` → shows each person's used/remaining this month.

---

## Standing up the FREE lane (your Ollama, reached safely)
The Gateway lives on Cloudflare's public edge and **can't see your brain PC over Tailscale**. You
expose Ollama through a **free Cloudflare Tunnel**. Two phases:

### Phase A — quick test (5 min, on the brain PC)
```bash
# brain PC (brainiac-7) — Ollama already runs on :11434
cloudflared tunnel --url http://localhost:11434
```
It prints a temporary `https://<random>.trycloudflare.com` URL. Set that as the Gateway's `OLLAMA_URL`
(`npx wrangler secret put OLLAMA_URL`). Now a free-lane call from any employee routes to your model.
⚠️ This quick URL is **temporary and open** — fine to prove it works, not for daily use.

### Phase B — production (stable + locked down)
1. **Named tunnel** with a permanent hostname (e.g. `ollama.tmmt.<yourdomain>`):
   `cloudflared tunnel login` → `cloudflared tunnel create aixmos-ollama` → route the hostname →
   run it as a service so it survives reboots.
2. **Lock it** with Cloudflare Access (service token) so only the Gateway can call it.
   When you're ready, tell me and I'll update the free-lane code to send the Access token headers
   and give you the exact `cloudflared` service install for Windows.

Until the tunnel exists, the free lane returns a clear "not configured" message and premium people
still work normally — so you can deploy the Gateway today and add the free lane next.
