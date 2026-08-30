# llm-lane-router

A cost-controlled LLM gateway on Cloudflare Workers. It routes requests across
local, free-hosted, and paid inference behind one OpenAI-compatible endpoint,
and meters them against a credit ledger that cannot double-spend under
concurrency.

```bash
npm install && npm test
```

---

## The problem

I put LLM agents into a business I run — intake, dispatch routing, payment
reconciliation. The agents worked. The bill did not.

Every call went to a frontier API, so cost scaled linearly with usage. The more
the product succeeded, the worse the unit economics got. That is a bad shape for
a business to be in, and no amount of prompt tuning fixes it, because the
problem is not in the prompt. It is in the routing.

This is the routing layer, extracted and generalized.

## The approach

Most agent traffic does not need a frontier model. Classification, extraction,
routine summarization, and structured-output filling are handled well by a 27B
open-weight model running on hardware I already own. Only a minority of calls
genuinely need the expensive lane.

So callers ask for a **capability**, not a vendor, and the gateway picks the
cheapest lane that satisfies the request and the caller's entitlement:

| Lane | Backed by | Marginal cost | Notes |
|---|---|---|---|
| `local` | Self-hosted (Ollama, vLLM) | 0 | Hardware you already run |
| `hosted` | Free-tier hosted provider | 0 | Rate limited upstream |
| `paid` | Frontier API | Real money | Metered per call |

Clients switch by changing a base URL. No caller was rebuilt or redeployed.

## Three decisions worth explaining

### 1. Running out of credit degrades; it does not fail

The obvious implementation returns `402 Payment Required` and stops. That is
the wrong behavior. It converts a billing state into an outage, and the person
on the other end experiences it as the product being broken — which generates a
support ticket, on a Saturday, about a system that is working exactly as
designed.

An out-of-credit caller instead drops to the cheapest lane that costs nothing
to serve. They lose capability, not access.

```js
selectLane({ requested: 'paid', maxLane: 'paid', balance: 0 })
// → { lane: 'hosted', cost: 0, degraded: true, reason: 'insufficient-credit' }
```

### 2. Balances live in a Durable Object, not in KV

This is the part I would most want to be asked about.

The natural way to debit a wallet on Workers is read, check, write:

```js
const bal = parseInt(await KV.get(key));   // read
if (bal < cost) return DENIED;             // check
await KV.put(key, String(bal - cost));     // write
```

That is a lost-update race, and on a request-per-isolate platform it is not a
rare one. Twenty concurrent calls against a balance of 100 all read `100`, all
evaluate `100 >= 5`, and all write `95`. **Twenty calls were served and one
debit was recorded.** The spend cap those debits were supposed to enforce does
not exist. Workers KV compounds it: it is eventually consistent, so a read can
return a value already stale by more than the width of the race window.

A Durable Object fixes this structurally instead of probabilistically. One
instance exists per object name, it is single-threaded, and its storage is
input-gated — while an await on storage is in flight, no other event for that
object is delivered. Check-then-write becomes atomic without any lock a caller
has to remember to take.

The test suite demonstrates both halves rather than only asserting the fix:

```
✓ naive read-check-write double-spends under concurrency
    20 calls approved, balance 100 → 95. 95 credits given away.
✓ serialized debits stay exact under the same concurrency
    20 calls approved, balance 100 → 0.
✓ serialized debits refuse to overdraw
    balance 20, 10 requests: 4 approved, 6 denied, balance 0.
```

**The trade, stated plainly:** every operation on one account funnels through
one object, so a hot account is a throughput ceiling. That is correct here —
wallets are per-user and a user's own calls are naturally serial — and it would
be the wrong choice for a global counter.

### 3. Identifiers are constrained at the boundary, not escaped at render

A caller can POST `{ agent: "<img src=x onerror=...>" }`. That string becomes
part of a metrics key. An admin dashboard later lists those keys. If the key
reaches the page as markup, a low-privilege caller has stored XSS in an
operator's browser.

Escaping at render time is the usual answer, but it depends on every future
render site remembering to do it. Constraining the value where it enters the
system means there is nothing dangerous stored to begin with. `escapeHtml` is
still exported and still used — defense in depth — but it is not the only thing
standing between an attacker and an operator's session.

Secrets are compared in constant time for the same reason: `a === b` returns as
soon as it finds a differing byte, and that timing leaks how many leading bytes
were correct.

## Layout

```
src/lanes.js     Lane selection and degradation policy
src/ledger.js    Durable Object — atomic debits and daily free-call caps
src/auth.js      Constant-time comparison, identifier sanitizing, HTML escaping
src/index.js     Worker entry — OpenAI-compatible /v1/chat/completions
test/            16 tests, no Cloudflare runtime required
```

## Running it

```bash
npm install
npm test                        # 16 tests, ~200ms, no network

npx wrangler kv namespace create ACCOUNTS
# put the returned id into wrangler.toml

npx wrangler secret put PAID_KEY
npx wrangler secret put HOSTED_KEY
npx wrangler deploy
```

Point any OpenAI-compatible client at the deployed URL:

```bash
curl https://your-worker.workers.dev/v1/chat/completions \
  -H "authorization: Bearer $ACCOUNT_SECRET" \
  -H "x-account: dispatch-agent" \
  -H "content-type: application/json" \
  -d '{"lane":"paid","model":"claude-sonnet-4-6","messages":[{"role":"user","content":"hi"}]}'
```

The response carries `_lane`, `_degraded`, and `_reason` so a caller can tell
which lane actually served it and why.

## Scope

This is the routing and metering layer extracted from a system running in
production for a business I operate. It is not a load balancer, not a caching
layer, and not a model-quality router — it does not inspect a prompt to guess
which model can handle it. Lane choice is the caller's declared intent, bounded
by entitlement and balance.

Streaming responses are not implemented here; the production version proxies
them, but the interesting parts of that are Cloudflare-specific plumbing rather
than design.

MIT licensed.
