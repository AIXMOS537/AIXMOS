# 🔌 Onboarding — Two Front Doors
_The Plug layer of the [[operator-os]]. Built on the existing [[onboarding-offboarding]] fast-hire flow + [[people-hub]] role->systems map._

## 🟢 Path A — Your machines (trusted)
Tablet, carry Mac, work Mac, Brainiac. Full access. Uses the [[team-drive-kit]] one-command kit:
install tools -> clone TMMT app + write `.env` -> clone/sync the brain from the NAS -> drop the owner/manager dashboard. Service-role/Stripe keys allowed here only.

## 🔵 Path B — Overseas assistants (their own PCs)
**Browser-only. No install, no `.env`, no brain repo, NO secrets on their machine.** Each assistant gets ONE link (their personal start page) that holds:
1. Their **role dashboard** (operator/sales/dispatch tiles only — owner tiles never render)
2. **Cloud app login**, scoped to their vertical
3. Their **vertical playbook** (read-only) — see `../playbooks/`
4. Their **tools**: Slack, ClickUp, OpenPhone invites
5. Their **scorecard** so they can see their own tier/progress

If their laptop dies, re-send the link. Nothing to clean up.

## How to make one (per person)
1. Copy `overseas-assistant-template.md` -> `onboarding/<name>.md`
2. Fill name, vertical, role, and their tool links
3. (When hosting is up) publish it as their web link; until then it's their written start guide

> Hosting options for the live links: **Vercel** (already in the stack, fastest) or the **UGREEN NAS** web station on the LAN. TBD with user.

## Security (carried from [[command-center-dashboards]] + [[people-hub]])
- Overseas PCs: browser-only, least access, **no keys ever**
- Owner-only tiles (Stripe/Supabase/Vercel/GitHub/dev) never render for non-owners
- Creating accounts / granting access / inviting to Slack/ClickUp = confirm with owner first
