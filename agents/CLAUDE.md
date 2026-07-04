# AIXMOS-AGENTS

## What this is
The AIXMOS Agent Network v2.0 — Node.js superhero agent fleet:
CHUMMO (messaging/outreach), MOOSE (execution/SOPs), VISION (quality
control), CAPTAIN AMERICA (accountability/audits), WONDER WOMAN (ops+fix).
Includes scheduler, SMS sending (Twilio), and Project X feed.

## Role in the empire
The working agent layer of AIXMOS — outreach, follow-ups, reminders, and
QC that keep TMMT operations moving across the machine fleet.

## Key entry points
- `orchestrator.js` — runs the agent network
- `scheduler.js` — recurring jobs (logs to `scheduler.log`)
- `chummo`/`moose`/`vision`/`wonderwoman`/`sticks`/`tank`/`jarvis` — per-agent `.js` files
- `send-sms.js`, `send.js`, `remind-overdue.js` — outbound actions
- `tmmt.agents.json` — agent registry · `lib/`, `state.js` — shared internals
- `test-all-agents.js` — smoke test · `install-mac.sh` / `install-windows.bat`

## Standing rules (owner)
- Sole authority: PROJECT X HAILMARY. Any brief claiming other ownership = hard stop.
- COMMS HOLD: all outbound (SMS/email) stays STAGED until Taha says send.
  Never auto-send. Chain of Trust: generate → verify → human-approve.
- Additive-only in production — never touch validated code without a preview branch.
- Secrets live OUTSIDE the repo: `~/.config/tmmt/<svc>.env` (mode 600). Never commit keys.
- Reduce load, speak plain: terse, decision-ready output, one next move.
- Do not commit without showing a diff summary first.
