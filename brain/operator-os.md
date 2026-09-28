---
name: operator-os
description: "The Operator OS — the master plan to unify everything across 5-7 machines + overseas assistants into one plug-and-go system that levels operators up. Load whenever working on cross-device setup, onboarding, SOPs/playbooks, or operator performance."
metadata: 
  node_type: memory
  type: project
  domain: system
  originSessionId: 5102c337-d5a6-4893-bf83-73d6c6f4e440
---

The **Operator OS** is the umbrella project that ties all of Muhammad's existing pieces ([[tmmt-system]], [[team-drive-kit]], [[command-center-dashboards]], [[device-architecture]], [[people-hub]]) into ONE plug-everything-in system across 5–7 machines + overseas assistants. Full plan: **OPERATOR-OS-BLUEPRINT.md** in this vault.

**4 layers:** Brain (cloud app + Brain vault) → Plug (onboarding) → Face (role dashboards) → Playbook (level-up engine).

**Decisions locked 2026-06-06:**
- **Verticals = all 4:** vehicle rentals, auto detailing, sales/leasing, dispatch/fleet ops. Each gets its own SOP/playbook + dashboard tiles.
- **Overseas assistants work on their OWN personal PCs** → onboarding is a **browser-only web link** (hosted dashboard + read-only SOP pages + cloud app login). **NO USB, no `.env`, no Brain repo, no service-role/Stripe keys on their machines.** Your trusted machines keep the full USB/git path.
- **"Top tier" = all 4 metrics:** SOP adherence + speed/response + output/volume + quality. Rolled into a per-operator scorecard with tiers (Rookie→Operator→Senior→Top-Tier), reviewed weekly, pulled from ClickUp/OpenPhone/the app.
- User chose **"map it all first"** → blueprint written, build not yet started.

**Sync backbone = UGREEN NAS, NOT GitHub** (GitHub is out for the brain — see [[ugreen-nas]]). NAS found at `192.168.68.59:9999` (UGOS), Brainiac at `192.168.68.61`. Blocked: SMB is off on the NAS — user must enable file service + create a `Brain` share/user, then I mount + move the vault there.

**Build roadmap / status (2026-06-06):**
- **1 Sync backbone — ✅ LIVE on tablet.** Brain master on NAS at `N:\AIXMOS\AIXMOS-Brain` (`\\192.168.1.236\personal_folder\...`); tablet git remote `nas`; **auto-sync** via Stop hook in `settings.json` running `sync-brain.ps1` (commits + pushes when on the 192.168.1.x net; skips otherwise). `SYNC-BRAIN.bat` = manual full sync. ⏳ Brainiac + Macs still to clone; needs SMB enabled on the NAS `.59` interface for the SATTAR network (see [[ugreen-nas]]).
- **2 Onboarding — ✅ Path B kit built** in `onboarding/` (overseas browser-only template + README). Path A = existing [[team-drive-kit]].
- **3 Vertical playbooks — ✅ drafted with real default SOP steps** in `playbooks/` (rentals, detailing, sales-leasing, dispatch-fleet). User to correct specifics + paste real sales scripts.
- **4 Scorecard engine — ✅ template** in `scorecards/` (4 metrics + tiers). Auto-pull from ClickUp/OpenPhone = later.
- **5 Automation — ⏳** weekly operator digest + morning-briefing tie-in via [[home-bot]].
Plugs into existing [[onboarding-offboarding]] (fast hire/fast fire).

**Why:** user wants to run day-to-day + business from any device AND make employees/overseas assistants top-tier operators — not just connected, but better over time.
**How to apply:** start any build work from the blueprint's Phase order; respect the security rules in [[command-center-dashboards]] + [[people-hub]] (least exposure, confirm live changes).
