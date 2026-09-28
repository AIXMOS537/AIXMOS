---
name: operator-instance-model
description: "What a paying operator receives — stick + workstation + their own app instance paired to the house server. What is already built and what has never been switched on."
metadata:
  node_type: memory
  type: project
  domain: work
---

The shape, stated 2026-08-26: a **stick paired with a workstation or laptop**
ships to a paying operator, they get **their own build of the app** that pairs
with the house instance, and through that pairing they reach the agents and
tools on the private server — with the TMMT team doing the management side.

**Almost all of that is already built.** It has simply never been switched on.

## What exists

`organization_licenses` is the pairing spine, and it already models the whole
hardware story:

| column | what it is for |
|---|---|
| `install_token_hash` / `install_token_used` | one-time token, redeemed on first boot |
| `license_key_hash` | the issued key |
| `hardware_uuid` | binds the licence to **one machine** — the workstation |
| `enclave_pubkey_pem` | the stick's signing key |
| `last_heartbeat_at` | the paired instance phoning home |
| `kill_command` | remote revocation |
| `license_tier`, `modules[]`, `max_ventures`, `valid_until` | what they bought |

Alongside it:

- **`/api/license/provision`, `/heartbeat`, `/revoke`** — the three endpoints
  the pairing needs, all present.
- **`guard.ts`** — live licence check on every agent entry point, with the kill
  switch honoured.
- **`partner_app_endpoints`** — `partner_app_slug`, `webhook_url`,
  `webhook_secret`, `case_types[]`, `work_types[]`. This is how a partner's own
  build talks back to the house instance.
- **`scripts/provision-dealer-instance.mjs`** — "mom & pop dedicated deploy",
  dry-run by default, with manual gates on creating the Supabase and Vercel
  projects. Plus `provision-tenant-seat.mjs`, `provision-partner.sh`,
  `provision-operators.mjs`.

## What has never happened

Four licence rows exist. Across all four:

- `hardware_uuid` — **null on every row.** No licence has ever been bound to a machine.
- `enclave_pubkey_pem` — **null on every row.** No stick has ever been keyed.
- `last_heartbeat_at` — **null on every row.** Nothing has ever checked in.

So the spine is built and has never carried weight. The first real pairing is
still the first pairing, and that is where the bugs will be.

Also: **`TMMT RENTALS` own licence is `active: false` with no key issued**, and
`guardOrganization` throws on an inactive licence. Fixed in code so the house
orgs are exempt (PR #175) — but whether TMMT should hold an active row with a
key is a business decision still open.

## The one architectural fork still to call

"Their own build" splits two ways, and the choice sets the team's workload
forever:

**Dedicated deploy per operator** — their own Vercel project, their own
Supabase. Maximum isolation. `provision-dealer-instance.mjs` already scaffolds
it. The cost is that every operator is a deployment your team maintains, and
twenty operators means twenty upgrades every time the app changes.

**One multi-tenant app, their own domain and branding** — one deploy, N orgs,
isolation enforced by the RLS that has been live since 2026-08-25. The team
maintains one thing. An operator who insists on their own box does not get one.

`license_tier` and `modules[]` already support a hybrid: shared instance for
most, dedicated deploy as the premium tier. That is probably the answer, but it
should be chosen deliberately rather than arrived at.

## What actually has to be online

Not everything waits on the server — see [[hub-and-operator-server]]:

- the **kit** on the stick works offline, needs nothing
- the **app** is on Vercel already
- only the **shared agents and tools** need the private hub

Which means operators can be sold and onboarded before the hub's uptime problem
is solved.

Related: [[hub-and-operator-server]] · [[operator-os]] · [[projectx-licensing]]
