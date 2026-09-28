# Cost-Cap Adoption — route agents through the gateway

Goal: no agent/automation calls `api.anthropic.com` directly (uncapped).
Everything goes through this gateway, which caps spend per-role and auto-drops
to the free lane (Ollama / Cloudflare Workers AI) when tokens run out.

## Request contract
`POST /` with header `x-aixmos-auth: <role secret>` and JSON body:
```json
{
  "prompt": "…",                // or "messages": [{role,content}]
  "system": "…",                // optional; APPENDED to the per-secret persona
  "tier": "free",               // free|haiku|sonnet|opus (never exceeds role maxTier)
  "max_tokens": 1024
}
```
Response: free lane → `{ text }`; paid lane → raw Anthropic body (`content[0].text`).
The persona set per-secret is always the authoritative system prompt; `system`
adds task/schema instructions on top of it (cannot override the persona).

## AIXMOS-AGENTS (done — branch feat/gateway-backend-cost-cap)
Set in `~/.config/tmmt/*.env` (NEVER in the repo):
```
AIXMOS_LLM_BACKEND=gateway
AIXMOS_GATEWAY_URL=https://aixmos-gateway.<acct>.workers.dev
AIXMOS_GATEWAY_SECRET=<role secret>
AIXMOS_GATEWAY_TIER=free
```
`lib/llm.js` routes all agent traffic through here. Routine work = $0.

## TMMT (ready — adopt when you choose)
- `src/lib/ops-ai.ts` (draft review / fact-check, NOT latency-critical): already
  single-user-message shaped — point its fetch at the gateway with a role secret.
- `src/lib/agent/llm-router.ts` (LIVE Twilio SMS agent): only migrate AFTER
  load-testing against Twilio's 15s webhook window. Pass its schema `systemPrompt`
  via the `system` field (now honored). Keep the 8s timeout + fail-open fallback.

## Rule
Automation/loops/scheduled/backgrounded → gateway (capped/free). Never direct to
`api.anthropic.com`. Brain-work by hand → paid tier, foreground only.
