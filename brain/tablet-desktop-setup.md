---
name: tablet-desktop-setup
description: "Windows tablet desktop/launcher state after 2026-06-06 cleanup — what's intentional and what not to undo"
metadata: 
  node_type: memory
  type: project
  originSessionId: 83a6dac9-8f84-46e6-a0cd-d42c207205ae
---

State of the Windows 10 tablet (DESKTOP-1IT6EL5\AIXMOS) after the 2026-06-06 desktop cleanup. See [[device-architecture]] and [[tmmt-system]].

**Business runs in the cloud** — `https://tmmt-ops.vercel.app` is always-on and needs no local install for day-to-day. The USB drives (E:/F:) are backup/project library only (their `START-HERE.txt` says so).

**Desktop launchers (keep these):**
- `START-TMMT-APP.bat` — daily, low-power: just opens the cloud site.
- `START-TMMT-OFFLINE-DEV.bat` — boots the LOCAL dev server (heavier); use only when offline.
- `START-CEO-COMMAND-CENTER.bat` and `CEO Command Center.url` — now open **`CommandCenter\Home-Command-Center.html`** (the whole-life home screen: Family · Friends · Work zones + "talk to your bot" hero). Old work-only `CEO-Dashboard.html` kept as fallback.
- `Cursor.lnk`.

**Home daily-driver screen:** `CommandCenter\Home-Command-Center.html` is the unified home dashboard and auto-opens on login (via `AutoStart-DailyDriver.bat`, which no longer force-opens the cloud briefing tab). It pairs with [[household-and-team-schedules]] + [[people-hub]] — Family/Friends zones show empty-state prompts until the user feeds the bot people.

**Offline dev install:** the real deployable app (`tmmt-os`, Next.js 14 + Supabase + Stripe) is installed locally at `C:\Users\AIXMOS\CommandCenter\tmmt-os` (~388 MB, `npm ci` done, smoke-tested OK). Source of truth on USB is `E:\AIXMOS\02_BUSINESS_TMMT\TMMT_MANAGEMENT\tmmt-os`. The offline launcher auto-detects `node_modules\next` there.

**Scheduled task `USB-SetupKit-AutoRun` is now FULLY REMOVED** (user ran `Unregister-ScheduledTask` elevated, later on 2026-06-06). It had come back as state "Ready" (re-created after the earlier disable), and on every USB insert (PnP event 410) re-deployed setup-kit clutter (`INSTALL-NOW-USB-IN.bat`, `CLICK-ME-NOW.txt`, `DO-IT-ALL.bat`, `CEO-ASK-ME.txt`, etc.) onto the desktop. Its target script `D:\install\Invoke-OnVolumeAttach.ps1` was missing. **Do NOT recreate** unless the user wants plug-and-play USB auto-setup back.

**Desktop/drive clutter regenerator = a separate Cursor Agent session** (confirmed: the generator strings live only in `AppData\Roaming\Cursor\...\anysphere.cursor-retrieval\checkpoints\...`). Cleaning the desktop won't hold while that agent is mid-task — stop it first.

**2026-06-06 deep cleanup (this session):** Both USB roots reduced to just `AIXMOS\` + `START-HERE.txt` (+ intentional `TMMT-SETUP\` team kit). Removed items quarantined to `_QUARANTINE-2026-06-06\` on desktop + each drive (reversible, nothing deleted). Deleted macOS junk: 32 files on E:, 22,485 on F:. Loose `TMMT-SECRETS.enc`/`TMMT-KEY` folded into `AIXMOS\05_SECRETS_AND_KEYS\_mac_encrypted_vault\`. See [[tmmt-cleanup-prefs]].

**Left untouched per user (2026-06-06):** Perfect Memory (autostarts, ~314 MB), AnyDesk + Tailscale (remote access between tablet and Macs). RAM was healthy (~7.8 GB free of 15.9).
