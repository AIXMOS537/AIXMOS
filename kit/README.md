# AIXMOS KIT

One command surface. The same commands on this Surface, on a plugged-in stick,
and on the bootable image the M1 is building.

```
aixmos              where am I, what is up, what is missing
aixmos lanes        every lane, where it resolves, what is retired
aixmos doctor       find drift: dead paths, dirty repos, schema gap
aixmos ai "q"       ask the offline brain (no internet needed)
aixmos online       the live side + the owner gates
aixmos manifest     rewrite MANIFEST.md from what is actually here
aixmos replicate E: stage this kit onto a drive
```

Windows: `bin\aixmos.ps1` · macOS/Linux: `bin/aixmos` · both read the same `kit.json`.

---

## The one rule

**No script hardcodes a path. Every lane comes from `kit.json`.**

This exists because of what happened here. `C:\Users\AIXMOS\TMMT` was retired on
2026-08-26 — a shallow orphan clone off a contractor's April base. Its `.git` was
removed and only an empty `node_modules` husk was left behind. But **eight
separate scripts still pointed at it**, including `ops dev`, `ops build`,
`ops audit`, `ops snapshot`, the Mission Control dev launcher, and the `tmmt`
shortcut in both shell profiles.

None of them errored. They just quietly did nothing, or worked on a folder with
no app in it, for a week. Each had to be found and fixed by hand.

With one map, repointing a lane is a single edit to `kit.json` and every caller
follows. `aixmos doctor` fails loudly the moment anything points at a retired
lane again.

---

## Lanes

| lane | what it is | note |
|---|---|---|
| `canon` | **the** TMMT app — `AIXMOS537/TMMT` | only source of truth for app code |
| `commandcenter` | ops CLI, dashboards, closed-loop, watchtower | |
| `tmmtos` | operator/ops surface | **holds the live prod keys** |
| `brain` | business brain: SOPs, playbooks, memory | product-safe |
| `vault` | private family/personal | **never leaves the house** |
| `teamdrive` | onboarding kit for a new machine | |
| `automation` | scheduled tasks (WorkSync, Free-RAM, crimson-shadow) | |
| `kit` | this | |

Retired, and never to be pointed at again:

- `C:\Users\AIXMOS\TMMT` → use `canon`
- `C:\Users\AIXMOS\Brain` → use `brain` (an empty stub; the real brain is `AIXMOS-Brain`)

Both are still on disk. Neither is referenced by any script any more.

---

## Adding or moving a lane

Edit `kit.json`. Nothing else.

```json
"lanes": {
  "newthing": {
    "local": "NewThing",
    "drive": "TMMT-WORK/NewThing",
    "role":  "what it is for"
  }
}
```

`local` is where it sits under a user profile. `drive` is where it sits on a
stick or a booted image. The kit picks the right one by noticing where it is
running from — no flags, no per-machine config.

When you retire something, move it into `retired` with a reason. That is what
arms `aixmos doctor` against it.

---

## The offline brain

Ollama on `:11434`, models in `~/.ollama/models` (6.16 GB).

| model | size | for |
|---|---|---|
| `qwen7b-max:latest` | 4.7 GB | default reasoning |
| `qwen3b-max:latest` | 1.9 GB | fast / low-RAM machines |
| `qwen2.5:3b` | 1.9 GB | base for the two Modelfiles |

7B Q4 is the ceiling on this Surface Pro 4 (2 cores, 1 GB iGPU). The Modelfiles
that build the two `-max` variants live in `LocalModels/`.

`aixmos ai "question"` works with the network unplugged. That is the point.

---

## Gates

These are owner decisions, not defaults. The kit prints them and never acts
around them.

- **push** — no blind push. Owner go required before commit/push on `canon`.
- **deploy** — Vercel deploy is blocked.
- **secrets** — live prod keys live only in `tmmt-os/.env.local`. They never go
  on a drive that leaves the house.
- **vault** — `Personal-Brain` goes to `_VAULT` only, never the business lane.
