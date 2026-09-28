---
name: hub-and-operator-server
description: "Which machine is the HUB, and why the box that runs your heavy work is not yet the box operators can pay to use"
metadata:
  node_type: memory
  type: project
  domain: work
---

Decided 2026-08-26. `brainiac-7` is the hub, with the M1 MacBook as the second.
That is right for **your own** heavy work and wrong, today, for **anything a
customer pays for** — and the difference is measured, not felt.

## The number that decides it

`ClosedLoop\logs\flaps.jsonl`, the 26 hours to 2026-08-26 18:36:

| | |
|---|---|
| Drops | 9 |
| Time offline | 15.7 h |
| Time online | 10.1 h |
| **Measured uptime** | **39%** |
| Longest single gap | 12.4 h (overnight) |

`brainiac-7` is the flappiest node on the mesh by a wide margin — 18 state
changes against `tmmts-macbook-pro`'s 4. See [[brainiac-flapping]] for the
diagnosis.

39% is fine for a machine you walk up to. It is not a service.

## So split the role in two

The mistake would be one "hub" that does both jobs, because the two have
opposite requirements.

**Compute hub — `brainiac-7` + the M1.** Docker, containers, local Postgres,
model runs, long builds. Uptime genuinely does not matter here: you use these
when you are at them, and a drop costs you a restart. Both machines qualify on
capability. This is settled — run `ops device` on each to confirm the tier.

**Operator server — not yet either of them.** The thing operators pay for and
connect to over Tailscale has one hard requirement that has nothing to do with
CPU: it answers when they knock. A person paying monthly who finds it down
overnight does not file a bug, they leave. Neither box clears that bar today,
and a laptop that sleeps on lid-close never will.

## Before selling access to anything

1. **Apply the flapping fix on `brainiac-7` and confirm it held.** The script
   has been delivered by Taildrop more than once; it has never been confirmed
   *applied*, because the box allows no remote execution — SSH needs
   credentials, WinRM and RDP are closed, Tailscale SSH has no host keys.
   Someone has to sit at it. Then watch `ops flaps` for a week.
2. **Decide whether it stays powered on.** The 12.4-hour overnight gap is the
   shape of a machine being shut down, and no software setting survives that.
   This is a decision about the room, not the registry.
3. **Only then** put anything customer-facing on it. Until uptime is measured
   above ~99% across a full week, treat brainiac-7 as compute, not as a service.

If leaving it on is not the answer, the operator server wants a small
always-on host joined to the mesh — the local-first principle is about *where
the data lives*, and a Tailscale node that holds no data of its own does not
break it.

## What operators are actually buying

Worth being clear before pricing it, because it changes what has to be online:

- the **operator kit** — ships on a stick, works offline, needs no server
- the **app** — already hosted on Vercel, nothing to do with this hub
- the **shared services** — a mesh address, dispatch, a model endpoint, backups

Only the third needs the hub. The first two are already solved, which means the
paid tier can start smaller than it looks.

Related: [[brainiac-flapping]] · [[device-architecture]] · [[tailscale-mesh]] ·
[[operator-os]]
