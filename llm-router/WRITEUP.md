# How I stopped LLM costs from scaling with usage

I run a small vehicle rental and dispatch business, and I wrote its software
myself. At some point I put LLM agents into it — intake triage, dispatch
routing, payment reconciliation. The agents worked well enough that I started
routing real work through them.

Then the invoice arrived.

The problem wasn't that the bill was large. It was the *shape* of it. Every
agent call went to a frontier API, so cost tracked usage almost perfectly
linearly. That meant the better the product got, the worse the unit economics
became. A feature working well was indistinguishable, on the invoice, from a
feature being abused. That's a bad position for a business with thin margins,
and no amount of prompt tuning fixes it, because the problem isn't in the
prompt.

This is a writeup of what I built instead. The code is in this repository.

## First: measure, because my intuition was wrong

My assumption going in was that the expensive calls were the complicated ones —
the multi-step reasoning, the long context. So I started tagging every call
with the agent that made it and what it cost, and let it run for a couple of
weeks.

The distribution wasn't what I expected. The overwhelming majority of calls
were small, boring, and structural: classify this inbound message, extract a
date and a phone number from this text, decide which of four buckets this
ticket belongs in, turn this blob into JSON matching a schema. Individually
trivial. Collectively, most of the bill.

The genuinely hard calls — the ones where I actually wanted a frontier model's
judgment — were a small minority of the volume.

That reframed the whole thing. I wasn't looking at a prompt efficiency problem.
I was looking at a **routing** problem. I was paying frontier prices for work
that a 27B open-weight model on hardware I already owned could do
indistinguishably well.

## The three lanes

The design that came out of it is deliberately unclever. Callers ask for a
*capability*, not a vendor, and a gateway decides what actually serves the
request:

| Lane | Backed by | Marginal cost | Where it's right |
|---|---|---|---|
| `local` | Ollama on hardware I own | 0 | Classification, extraction, structured output |
| `hosted` | Free-tier hosted provider | 0 | Overflow when local is saturated |
| `paid` | Frontier API | Real money | Judgment calls, anything customer-visible |

The gateway speaks the OpenAI chat-completions shape, so moving an existing
caller onto it meant changing a base URL. Nothing was rebuilt, nothing was
redeployed, and I could roll it back by changing the URL again. That mattered
more than it sounds like it should — it meant I could try the whole idea in an
afternoon instead of committing to a migration.

Two properties turned out to matter more than the routing itself.

**Provider keys never leave the server.** Before this, keys lived in whatever
was making the call. Rotating one meant chasing it across machines. Now a
rotation is one deploy.

**Lane policy lives in one place.** Changing what a role is entitled to doesn't
require touching a single caller.

## The decision I'd defend hardest: running out degrades, it doesn't fail

The obvious behavior when someone exhausts their credit is to return `402` and
stop. I built that first. It was wrong, and it took about a day of real use to
find out why.

Returning an error converts a *billing state* into an *outage*. The person on
the other end doesn't experience "you are out of credit." They experience "the
thing is broken," and they say so, at an inconvenient hour, about a system that
is working exactly as designed.

So an out-of-credit caller now drops to the cheapest lane that costs nothing to
serve. They lose capability. They don't lose access.

```js
selectLane({ requested: 'paid', maxLane: 'paid', balance: 0 })
// → { lane: 'hosted', cost: 0, degraded: true, reason: 'insufficient-credit' }
```

The response carries `_lane`, `_degraded`, and `_reason`, so a caller that
cares can tell it was downgraded and why. Most don't care. The ones that do can
surface it.

## What broke: the ledger double-spent

This is the part I got wrong in a way I think is genuinely common, so it's
worth being specific about.

Metering needs a wallet, and the natural way to debit one on Cloudflare Workers
is read, check, write:

```js
const bal = parseInt(await KV.get(key));   // read
if (bal < cost) return DENIED;             // check
await KV.put(key, String(bal - cost));     // write
```

That is a lost-update race. On a platform that runs each request in its own
isolate, it is not a rare one.

Twenty concurrent calls against a balance of 100 all read `100`. All twenty
evaluate `100 >= 5` and pass. All twenty write `95`. **Twenty calls were served
and one debit was recorded.** Ninety-five credits were given away, and the spend
cap those debits existed to enforce simply did not exist.

Workers KV makes it worse than a textbook race, too: it's eventually
consistent, so a read can return a value that's already stale by more than the
width of the race window. There is no amount of "read it again to be sure" that
fixes this.

The fix was structural rather than probabilistic. Balances moved into a Durable
Object. One instance exists per object name, it's single-threaded, and its
storage is input-gated — while an await on storage is in flight, no other event
for that object is delivered. Check-then-write becomes atomic without any lock
a caller has to remember to take.

The test suite demonstrates both halves, because I think showing only the fix
would undersell the problem:

```
✓ naive read-check-write double-spends under concurrency
    20 approved, balance 100 → 95. 95 credits given away.
✓ serialized debits stay exact under the same concurrency
    20 approved, balance 100 → 0.
✓ serialized debits refuse to overdraw
    balance 20, 10 requests: 4 approved, 6 denied, balance 0.
```

**The cost of this choice, stated plainly:** every operation on one account
funnels through one object, so a hot account is a throughput ceiling. That is
the right trade here — wallets are per-user, and one user's own calls are
naturally close to serial. It would be the wrong choice for a global counter,
and I'd expect to be asked about that.

## Two smaller things I'd do the same way again

**Charge before serving, not after.** Charging after means a crash mid-request
is a free call, and the requests most likely to crash are exactly the expensive
ones.

**Constrain identifiers at the boundary, don't escape at render.** A caller can
POST `{ agent: "<img src=x onerror=...>" }`. That string becomes part of a
metrics key, and an admin dashboard later lists those keys — a low-privilege
input reaching a high-privilege viewer. Escaping at render time is the usual
advice, but it depends on every future render site remembering to do it.
Constraining the value where it enters the system means there's nothing
dangerous stored in the first place. The escaping is still there as a second
layer; it's just not the only thing standing between an attacker and an
operator's session.

## What I'd do differently

Streaming isn't in this repository. The production version proxies it, but the
interesting parts are Cloudflare-specific plumbing rather than design, so it
didn't earn a place here.

I'd also add quality sampling. Right now lane choice is the caller's declared
intent, bounded by entitlement and balance — the gateway never inspects a
prompt to guess whether a cheaper model could handle it. That's deliberate,
because a router that silently downgrades on a guess is a router you stop
trusting. But I'd want a sampled offline comparison telling me *where* the
local lane is quietly worse, rather than finding out from a customer.

---

MIT licensed. `npm test` runs the whole suite in about 200ms with no Cloudflare
runtime and no network.
