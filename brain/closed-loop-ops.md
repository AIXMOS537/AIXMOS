---
name: closed-loop-ops
description: Tablet closed-loop ops system — hourly KPI cycle grading Tailscale mesh + local services against KPI-STANDARDS.md
metadata: 
  node_type: memory
  type: project
  originSessionId: c0397b4e-80db-436d-88b3-41c8643364a1
  modified: 2026-08-25T16:24:23.390Z
---

The command-hub tablet (see [[device-architecture]]) runs the business on a **closed loop**: it only works with devices on the [[tailscale-mesh]], and every hour a scheduled task grades the whole setup against KPI standards.

- Home: `C:\Users\AIXMOS\CommandCenter\ClosedLoop\`
  - `KPI-STANDARDS.md` — the 8 KPI thresholds (mesh core online, latency <150ms, Ollama up, Mission Control intact, WorkSync armed, disk ≥15%, RAM ≥1.5GB, cycle <60s)
  - `closed-loop-check.ps1` — one cycle: sense → grade → report (Windows PowerShell 5.1-compatible; ASCII only, no em-dashes)
  - `SCOREBOARD.md` — latest graded scoreboard (GREEN/YELLOW/RED overall)
  - `logs\closed-loop.jsonl` — full cycle history
- Scheduled task `TMMT-ClosedLoop` runs hourly (created 2026-08-25 via schtasks; elevation was denied for Register-ScheduledTask, so no at-logon trigger — schtasks ONLOGON needs admin).
- Mesh core = `fleet` must be online + at least one of brainiac-7 / watchtower / tmmts-macbook-pro.
- Hard firewall lockdown (inbound Tailscale-only) is documented in KPI-STANDARDS.md but deliberately **not applied** — operator opt-in only.
- Anything RED on the scoreboard is the first item of the next work block; relates to [[fleet-watchtower]] and [[local-ai-ollama]].
