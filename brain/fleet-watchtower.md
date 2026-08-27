---
name: fleet-watchtower
description: "The Fleet Watchtower — the tablet's 'Big Brother' board that watches every computer (home + office) over Tailscale. Load when working on monitoring machines, the watchtower, or deep agents."
metadata: 
  node_type: memory
  type: project
  domain: system
  originSessionId: f896922d-5795-49d2-b8ad-f08910a1713e
---

User wanted the home tablet to become a "Big Brother" that watches all their computers at home and the office. Built on top of the existing [[tailscale-mesh]] (the transport) and lives in `C:\Users\AIXMOS\CommandCenter\` next to [[command-center-dashboards]].

## What it is (built 2026-06-07)
- **Watchtower server** = `C:\Users\AIXMOS\CommandCenter\Watchtower\fleet-watchtower.ps1` — a self-contained PowerShell HTTP server (no Docker, no cloud). Reads `tailscale status --json` for up/down of every machine, and ingests deep stats from agents via `POST /api/report`. Serves a dark dashboard on port **8787**.
  - `-Bind 127.0.0.1` (default) = viewer mode (tablet). `-Bind +` = hub mode (needs urlacl + firewall, run elevated).
- **Tablet board (up/down)** = auto-starts at login (Startup shortcut `Fleet Watchtower.lnk` → `SILENT-START.vbs`). Tile on CEO-Dashboard.html: **🛰️ Fleet Watchtower → Watchtower** (`http://127.0.0.1:8787`). Owner-only (`roles:[]`).
- **Deep agent** = `DeployKit\aixmos-agent.ps1` (Windows) + `DeployKit\aixmos-agent-mac.sh` (macOS) — report CPU/RAM/disk/uptime + logged-in user + active app + idle, posting to the hub every 20s. Must run in the user's interactive session (Win = Startup shortcut; Mac = LaunchAgent) to read the active window. **Pipeline validated locally** (real Windows agent → board showed live stats). Hub matches report name to Tailscale HostName via a normalized key (uppercase, strip spaces/`-`/`_`) so "MacBook Pro" lines up.
- **Phone alerts** = `DeployKit\aixmos-alerts.ps1` runs on the hub, polls `/api/fleet`, and pushes via **ntfy** (free app) on machine down / back / disk ≥92% / sustained CPU ≥90% (3 consecutive polls). Topic auto-generated into `alerts-topic.txt` by the installer; user subscribes in the ntfy app. ⚠️ ntfy **headers must be ASCII** — titles are plain text, emoji comes from ntfy `Tags` shortcodes (validated end-to-end: push delivered with title+tags+priority).
- **Worklog** = hub appends every agent report to a daily CSV in `worklog\YYYY-MM-DD.csv`; `/api/worklog?date=` summarizes per machine+user (active minutes = summed gaps where idle<300s, gap≤120s); `/worklog` page + CEO tile **🕒 Worklog**. Validated (logging + summary + page serve). Active minutes need a full day of data to read meaningfully.
- **Hub design** = lives on **Brainiac** (`100.64.0.1`, always-on), NOT the tablet (which sleeps/roams). Agents post to Brainiac; tablet views it via the **🔭 Deep Hub** tile (`http://100.64.0.1:8787`). Local tablet board is the always-available up/down fallback.
- **Live screens** = RustDesk, peer-to-peer over Tailscale (installed by the agent/hub installers; needs a one-time permanent password per machine).

## DeployKit (`Watchtower\DeployKit\`) — run as admin
1. `1-JOIN-MESH.bat` — office PCs: winget Tailscale + sign in as AIXMOS537.
2. `2-INSTALL-HUB.bat` — **Brainiac only**: urlacl + firewall (mesh-only 100.64.0.1/10), schedules watchtower as SYSTEM onstart, installs RustDesk.
3. `3-INSTALL-AGENT.bat` (Windows) / `INSTALL-AGENT-MAC.command` (Mac) — **every** machine: agent auto-start + RustDesk.
4. `4-INSTALL-ALERTS.bat` — **Brainiac only**: ntfy phone alerts (down/back/disk).
`README.md` has the full ordered rollout.

## Fleet seen 2026-06-07 (6 nodes; more than [[device-architecture]] listed)
tablet `DESKTOP-1IT6EL5` 100.64.0.1 · `BRAINIAC-7` 100.64.0.1 · `FLEET` 100.64.0.1 · `iphone171` (iOS) · `MacBook Pro` 100.64.0.1 · `DESKTOP-V9GQHHJ` 100.64.0.1.

## Status / open
- ✅ Tablet up/down board: live + auto-start. ⏳ User to run the 3 DeployKit installers (hub on Brainiac, then agents everywhere, office boxes join mesh first). User chose the "make me an installer" path (no creds shared) over giving Brainiac SSH login.
- Phones show up/down only (all they expose); Win + Mac do full health/activity. Hub IP is hard-coded to Brainiac's 100.x in the agents — change `$Hub`/`HUB` if it moves (or switch to MagicDNS `brainiac-7`).

**Why:** single glanceable command screen for the whole fleet, matching the [[operator-os]] "run everything from any device" goal.
**How to apply:** new machine → join mesh, run agent installer. Edit tiles in CEO-Dashboard.html (owner-only). Keep the hub on an always-on box, not the tablet.
