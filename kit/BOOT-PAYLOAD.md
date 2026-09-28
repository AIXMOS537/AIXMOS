# BOOT PAYLOAD — what the bootable stick has to carry

For the M1 build. This is the spec for what goes **on** the bootable OS so that
booting this Surface from the stick gives a working operation, online or not.

Measured on `DESKTOP-1IT6EL5`, 2026-09-01.

---

## 1. Size it honestly

The code is nearly free. The brain is the weight.

| what | size | notes |
|---|---|---|
| `canon` source | 0.02 GB | app code, migrations, scripts |
| `canon/.git` | 0.02 GB | full history |
| `commandcenter` + `tmmt-os` | 0.01 GB | ops CLI, dashboards |
| `brain` (AIXMOS-Brain) | < 0.01 GB | SOPs, playbooks, memory |
| `teamdrive` | < 0.01 GB | onboarding kit |
| `automation` | 0.21 GB | includes crimson-shadow whisper models |
| `AIXMOS-KIT` | < 0.01 GB | this kit |
| **code subtotal** | **≈ 0.25 GB** | |
| **ollama models** | **6.16 GB** | the actual payload |
| **total** | **≈ 6.5 GB** | before the OS itself |

`node_modules` and `.next` are **not** carried — they are 4 GB of regenerable
cache. `npm ci` rebuilds them. Carrying them wastes space and guarantees they
are stale on arrival.

A 32 GB stick is comfortable. A 16 GB stick works if you carry only
`qwen3b-max` (1.9 GB) instead of all three models.

---

## 2. Layout on the stick

The kit already knows this layout — it is the `drive` field of every lane in
`kit.json`. Match it and `aixmos` works the moment it boots, with no config.

```
<stick root>/
  AIXMOS-KIT/            <- the command surface. bin/aixmos runs on the Mac side.
  TMMT-WORK/
    TMMT-canon/          <- the app
    CommandCenter/       <- ops CLI + tmmt-os
    TMMT-TEAM-DRIVE/
    Automation/
  AIXMOS-BRAIN/          <- business brain (SOPs, playbooks, memory)
  _VAULT/
    personal-brain/      <- private. see §5.
  _RUNTIME/
    ollama/models/       <- the 6.16 GB
```

`aixmos` detects it is running off a stick rather than a user profile and
resolves every lane to the `drive` path automatically. Same commands, no flags.

---

## 3. The runtime the image needs

Boot-time requirements, in priority order:

1. **ollama** + the models at `_RUNTIME/ollama/models`. Point `OLLAMA_MODELS` at
   that folder so the models are read off the stick instead of being re-pulled.
   This is the whole offline capability.
2. **git**, **node** (for `npm ci`), **python3** — `bin/aixmos` uses `python3`
   to read `kit.json`, because `jq` is not on every image and `python3` is.
3. **tailscale** — the mesh is how the stick reaches `fleet`, `brainiac-7`,
   `watchtower` and the MacBook when it does have a network.
4. **curl** — the reachability checks in `aixmos status`.

Everything else is optional.

---

## 4. Online ↔ offline: how the bridge actually works

The rule from the Operator OS blueprint holds: **the Brain is the only source of
truth, devices are disposable windows into it.** The stick is a device.

| lane | offline | when a network appears |
|---|---|---|
| `canon` | full git history — commit, branch, diff, build | `git pull` / owner-gated push |
| `brain` | full vault, readable and writable | `git pull`/`push` to `AIXMOS537/aixmos-brain` |
| Supabase | **no local copy** — read-only cache at best | `uapxakmlwnpfsftfeezx` is the truth |
| Vercel | nothing | deploy is owner-gated anyway |
| offline AI | fully local, always | unchanged |

**The honest limit:** the live Postgres cannot ride on the stick. 213 migrations
of live schema and its data belong to Supabase. Booted offline you get the code,
the history, the brain and the local AI — a full development and thinking
environment. You do not get live bookings, leads, or customers until a network
comes back. Do not design the boot flow as if you will.

**Reconnect order** when the network returns:

1. `aixmos doctor` — before syncing anything, see what drifted.
2. `git pull` on `canon` and `brain`.
3. Resolve any migration gap (see §6) — never assume the repo is current.
4. Only then push, and only through the owner gate.

---

## 5. What must never go on the stick

Non-negotiable, and worth re-checking every time a drive is built:

- **`tmmt-os/.env.local`** — the live production keys, 37 of them including
  `SUPABASE_SERVICE_ROLE_KEY`. If the stick is lost, this key is the whole
  business. Carry the app; leave the key.
- **`TMMT-canon/.env`** — 86 keys, same reason.
- **`Personal-Brain`** — family and personal material. If the drive will ever be
  plugged into a machine that is not yours, leave it off entirely. If it stays
  home-only, it goes in `_VAULT/` and nowhere else.

The existing Go-Kit rule already says this: work-only drives carry no brain, no
personal lane, no keys. The bootable stick is a *bigger* version of the same
decision, not an exception to it.

---

## 6. Two things to settle before the build is final

**Schema drift.** The live database has 213 migrations. The `canon` repo has 32.
181 applied straight to production and were never written back. A stick built
today carries a repo that cannot rebuild the database it talks to. This is a
decision, not a script: either backfill the repo from live, or write down
explicitly that the repo is app-code-only and Supabase is the schema of record.

**Two sync systems disagree.** `ops sync` is additive and routes personal
material to `_VAULT`. The scheduled `TMMT-WorkSync-USB` task mirrors with
`/MIR` and routes the same material to a plaintext `PERSONAL\` lane, and it
writes the brain to `AIXMOS-BRAIN\AIXMOS-Brain\` where `ops sync` writes
`AIXMOS-BRAIN\`. Two different trees on the same stick, one of them deleting.
Pick one before pointing either at the bootable drive.
