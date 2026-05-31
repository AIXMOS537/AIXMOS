# AIXMOS Operator Portable Kit (OPK)

Universal orchestrator that deploys the AIXMOS/TMMT operations stack to any owner or operator machine.

**Spec:** [`AIXMOS537/TMMT` → docs/superpowers/specs/2026-05-26-operator-portable-kit-design.md](https://github.com/AIXMOS537/TMMT/blob/master/docs/superpowers/specs/2026-05-26-operator-portable-kit-design.md)

**Plan:** [`AIXMOS537/TMMT` → docs/superpowers/plans/2026-05-26-operator-portable-kit.md](https://github.com/AIXMOS537/TMMT/blob/master/docs/superpowers/plans/2026-05-26-operator-portable-kit.md)

## What is this?

A single USB flash drive that, plugged into any Mac or Windows machine, installs the right stack for the right role (owner / operator / Brainiac 7) and keeps that machine updated from GitHub.

## First-time use

Plug the USB drive into your computer, then double-click:
- **macOS:** `START_HERE.command`
- **Windows:** `START_HERE.bat`

The wizard takes ~15 minutes for operators, ~30 minutes for owners.

## Roles

| Role | Profile | Purpose |
|------|---------|---------|
| OWNER | `owner-carry` | M5 Pro carry MacBook — minimal remote terminal |
| OWNER | `owner-work` | M1 Max work MacBook — full dev stack, all 5 repos |
| OWNER | `owner-brain` | Brainiac 7 Windows PC — always-on AI brain |
| OPERATOR | `operator` | Office workstation or operator laptop — thin client (browser + Tailscale) |

## Updates

Auto-pulls from this repo on every login and every 30 minutes. Owners push to `main`; operators see changes within 30 minutes.

## Help

Operators: click "Help" on your daily-driver brief.
Owner: see `docs/OWNER_RUNBOOK.md`.
