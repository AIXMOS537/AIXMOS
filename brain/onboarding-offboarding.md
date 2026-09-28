---
name: onboarding-offboarding
description: The fast HIRE / fast FIRE system — one-command onboarding and offboarding that links the entire ecosystem (TMMT app, Slack, ClickUp, OpenPhone, Google, GHL). Load whenever adding, provisioning, removing, or firing a person.
metadata:
  type: project
  domain: work
---

The integrated people-ops engine. Pairs with [[people-hub]] (the roster + role→systems map), [[command-center-dashboards]] (each person's role dashboard), [[work-team]] (schedules). **WORK domain** — keep family/personal out of this (see [[home-bot]]).

## 🌐 Ecosystem map (systems a person touches)
| System | Holds | MCP connected |
|---|---|---|
| TMMT app — Supabase `uapxakmlwnpfsftfeezx` | `profiles` (login/role), `employee_access_rights`, `org_roles`, `operator_profiles`, `vendors` | ✅ |
| Slack (`projectaixmos`) | channels, DMs | ✅ |
| ClickUp | workspace member, task assignments | ✅ |
| OpenPhone | contact, SMS line | ✅ |
| Google Workspace | calendar invite/share, email, Drive shares | ✅ (Calendar/Gmail/Drive) |
| GoHighLevel | `ghl_contacts`, pipelines (Rentals / Restoration-LTO) | via app + dashboard links |
| Command Center dashboard | their role-based personal launcher | brain ([[command-center-dashboards]]) |

## ⚡ FAST HIRE (onboard) — "onboard <name> as <role>"
1. **Capture & remember** → add to [[people-hub]] roster + schedule to [[work-team]].
2. **Provision by role** (confirm before each live write — see Safety):
   - TMMT `profiles` row + `employee_access_rights` via `org_roles` (role: admin / internal_team / operator / vendor).
   - Slack invite → their role channels · ClickUp member · OpenPhone contact · Google calendar share for shifts.
   - GHL contact if customer-facing.
3. **Generate their dashboard** → role preset from [[command-center-dashboards]]; give them the link.
4. **Confirm onboarded** → note date + systems in roster.

## 🔥 FAST FIRE (offboard) — "offboard <name>" / "fire <name>"
**Goal: cut access everywhere in minutes. Revoke access BEFORE deleting data.** Confirm the person + that it's intentional, then:
1. **Kill login first** → TMMT `profiles`: set inactive / revoke `employee_access_rights`; downgrade `org_roles`. (Highest priority — stops app access immediately.)
2. **Slack** → deactivate / remove from channels. **ClickUp** → remove from workspace, reassign their open tasks. **OpenPhone** → remove line access / reassign number.
3. **Google** → remove calendar shares, Drive access, suspend/forward email.
4. **GHL** → revoke user access if any.
5. **Shared credentials** → flag any shared passwords/keys for rotation (never leave a fired person with a working shared secret). See [[tmmt-cleanup-prefs]] re: secrets.
6. **Dashboard** → archive/disable their personal launcher.
7. **Records** → mark them former in roster + [[work-team]]; log date + who authorized. Reassign coverage.

## 🔒 SAFETY (firing is high-stakes + irreversible)
- Always **confirm the exact person and intent** before any revoke — name collisions are dangerous.
- Do access-revocation steps as **separate confirmed actions**; report what succeeded/failed per system so nothing is silently left open.
- Never delete business data the person created (tickets, cases) — reassign, don't destroy.
- Keep an **offboarding log** (who, when, which systems cut, by whose order).
