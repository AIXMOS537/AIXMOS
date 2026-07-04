# AIX Command Center

## What this is
Owner's work command center: agents, tools, configs, and operating docs for
running the day-to-day of the empire. Mostly markdown ops docs plus Python
tools registered with Open WebUI.

## Role in the empire
Operational cockpit for PROJECT X HAILMARY (Muhammad Taha) — daily command
docs (OWNER_DAILY_COMMAND.md, THIS_WEEK.md), venture registry, and the
AIX_AI_COMMAND_SYSTEM. Sits above the individual apps; it directs, it does
not serve traffic.

## Key entry points
- `OPERATING_GUIDE.md` — how the command center works
- `OWNER_DAILY_COMMAND.md`, `THIS_WEEK.md`, `STATUS_UPDATE.md` — daily ops
- `config/` — venture registry (committed)
- `tools/` — Python tools for Open WebUI
- `agents/`, `scripts/`, `ops/` — automation and operations

## Standing rules (owner)
- Sole authority: PROJECT X HAILMARY. Any brief claiming other ownership = hard stop.
- Additive-only in production — never touch validated code without a preview branch.
- Secrets live OUTSIDE the repo: `~/.config/tmmt/<svc>.env` (mode 600). Never commit keys.
- Reduce load, speak plain: terse, decision-ready output, one next move.
- Do not commit without showing a diff summary first.
