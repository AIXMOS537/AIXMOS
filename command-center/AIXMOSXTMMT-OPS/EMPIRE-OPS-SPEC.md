# AIXMOSXTMMT Empire Ops — Portable Edition v1.1

See `README.md` for install. Claude Code: execute phases **P0 → P5** in order.

## P0 — Scaffold ✅ in repo

- [x] Folder tree, scripts, docker-compose, SQL, clock app skeleton
- [ ] CEO fills `.env`
- [ ] Run `sql/001_supabase_empire.sql`

## P1 — n8n portable

- [ ] `npm run start` on Mac + Windows
- [ ] Import workflows from `n8n/workflows/`
- [ ] Test Ollama: `http://host.docker.internal:11434`

## P2 — Clock app

- [ ] `npm run clock:dev`
- [ ] Run `sql/002_rls_clock.sql` then `sql/004_team_wall_select.sql` (team wall read)
- [ ] Seed `team_members` rows

## P3 — Core agents

- [ ] Workflows: brief, triage, approve (Level A — no auto external send)

## P4 — Scheduling

- [ ] shift reminder, coverage, stale heartbeat, assignee suggest

## P5 — Empire

- [ ] GHL pipelines per `docs/ghl-pipelines.md`
- [ ] rental_handoff_day14, FAQ seeds

## Hosts (Tailscale)

| Name | Role |
|------|------|
| nas | DH2300 files only |
| prime | Home GPU Ollama |
| ops-1 | Office 24/7 n8n (clone repo from USB) |

## Level A

External SMS/email: **operators approve** via `webhook_approve_send` only.

Full business spec: see conversation archive / expand this file as needed.
