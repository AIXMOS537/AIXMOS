---
name: go-kit
description: "The TMMT Go-Kit — a carry-anywhere flashdrive that plugs into any machine to run a live 'All Systems Go' health check + launch the operation. Mobile demo / portable work unit. Load when working on the demo drive, health checks, or portable launch."
metadata: 
  node_type: memory
  type: project
  domain: work
  originSessionId: 5102c337-d5a6-4893-bf83-73d6c6f4e440
---

The **Go-Kit** is Muhammad's carry-anywhere mobile operation unit (a flashdrive) — plug into ANY machine, double-click, see the whole operation is healthy, and launch it. "Little but big impact." Distinct from the [[team-drive-kit]] (which installs/onboards a machine): the Go-Kit installs NOTHING — it's browser-only demo + ops check. Fits the [[worksync-usb]] work-only rule.

- **Master folder:** `C:\Users\AIXMOS\TMMT-GOKIT` (on the tablet). Copy to any flashdrive to make a Go-Kit.
- **Also synced in the brain at `gokit/`** (GO.html + START-HERE.txt + MAKE-A-DRIVE.md) so it reaches every device (incl. the Mac) automatically. ⚠️ Copy ONLY the `gokit` folder's files to a flashdrive — NEVER the whole brain (it has private lanes). To make a drive from the Mac: plug in → drag `gokit/GO.html` (+ START-HERE.txt) onto the drive.
- **`GO.html`** — self-contained launcher (no install, works Win/Mac in any browser). On open it runs a live reachability **health check** of: Internet, TMMT App (`tmmt-ops.vercel.app`), ClickUp, Slack, OpenPhone, Google → "ALL SYSTEMS GO" banner. Then big launch tiles (TMMT app + work tools).
- **`START-HERE.txt`** — plain instructions.

**Security (built in):** WORK-ONLY. **No private brain, no family/personal, no secret keys** on this drive — safe to plug into a demo/client machine. Logins happen in the browser, nothing stored on the drive. (Carries the [[command-center-dashboards]] least-exposure + [[home-bot]] domain-separation rules.)

**Status 2026-06-06:** master folder built (GO.html + START-HERE.txt). No flashdrive was plugged in at build time → user copies the folder to a drive, OR plug a drive in and have Claude deploy it. Deliberately did NOT bundle `Home-Command-Center.html` or `CEO-Dashboard.html` (they contain family/friends zones or owner-only sensitive tiles).

**Deployed 2026-06-06:** Go-Kit (`GO.html` + `GO-KIT-START-HERE.txt`) copied to the ROOT of both USB drives **E: "CYBORG"** and **F: "AIXMOS02"**. Plug in → double-click `GO.html`.

**⚠️ Drive privacy boundary (user decision 2026-06-06):** E: and F: ALSO carry private data — `AIXMOS-BRAIN\` (the private brain), `PERSONAL\` (Desktop/Documents/Downloads), and `TMMT-SECRETS.enc` + `.__KEYS-canonical` + `UNLOCK-SECRETS-MAC.command`. User chose to **LEAVE AS-IS** because these drives are **MY-MACHINES-ONLY** — never plugged into clients'/others' computers. So they are NOT demo-safe despite the pitch/sales kits on them. **If the user ever wants to hand a drive to someone or demo on a foreign machine, FIRST make a clean work-only copy** (just the `gokit` files + work assets, no brain/PERSONAL/secrets) — do not hand out E:/F: as-is.

**Possible next adds:** a clean demo dashboard (operator role, no sensitive tiles); a Mac `GO.command`; auto-open on insert (the user previously REMOVED USB auto-run — do NOT re-add without asking, see [[tablet-desktop-setup]]).
