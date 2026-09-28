---
name: worksync-usb
description: "Auto-mirror of the tablet's content (Work + Brain + Personal lanes) to any removable drive on plug-in. Load when touching USB sync, scheduled tasks, or carrying work to the work Mac."
metadata:
  node_type: memory
  type: project
  domain: system
  originSessionId: d6fe3dbf-f52c-4ccb-9c4b-c394bbf3a955
---

On the Windows tablet, **every removable drive plugged in gets the tablet's content auto-mirrored onto it** so the user can carry it to the work Mac. Set up 2026-06-06 ("everything done on this tablet copied to my flashdrives as soon as I plug them in").

**Choices:** ANY removable drive · incremental MIRROR. Scope **started work-only but the user upgraded it to FULL (everything incl. the private brain) on 2026-06-06** ("put everything ive done into the flashdrives" → chose "literally everything incl. brain"). This is a deliberate operator override of the [[home-bot]] domain-separation rule — the drives now carry private family/personal data, so they must stay with the user (the `_TABLET-SYNC-INFO.txt` on each drive warns "do not leave it at the shop").

## How it works
- Automation lives in `C:\Users\AIXMOS\Automation\WorkSync\` (kept OUT of the mirror set):
  - `Watch-USB.ps1` — polls every 4s for new removable drives (DriveType=2, Size>0); single-instance mutex `Global\TMMT-WorkSync-USB`. Syncs drives present at startup too (so already-plugged drives sync on login).
  - `Sync-WorkToUSB.ps1 -Drive X:` — `robocopy /MIR` each source into a labeled LANE on the drive (see below); writes `X:\_TABLET-SYNC-INFO.txt`; best-effort toast. Logs in `…\WorkSync\logs\` (sync_*.log = my status, robocopy_*.log = robocopy's own — kept separate to avoid an encoding-garble bug).
  - `Start-WorkSync.vbs` — launches the watcher fully hidden.
- **Scheduled task `TMMT-WorkSync-USB`** runs the vbs `-AtLogOn` (user AIXMOS, Limited). CLEAN, single-purpose — **NOT** the removed clutter task `USB-SetupKit-AutoRun` (see [[tablet-desktop-setup]]); do not confuse them.

## Lanes on each drive (3 robocopy mirrors)
- `<Drive>\TMMT-WORK\`    ← CommandCenter, TMMT, TMMT-TEAM-DRIVE   (~6.4 MB)
- `<Drive>\AIXMOS-BRAIN\` ← AIXMOS-Brain (private Obsidian vault)   (~0.2 MB) — also syncs to [[ugreen-nas]] separately
- `<Drive>\PERSONAL\`     ← Downloads, Documents, Desktop           (~330 MB, almost all Downloads)
- **Excluded dirs (all lanes):** node_modules, .next, .turbo, .cache, .vercel, dist, build → run `npm ci` on the work Mac to restore. Cut ~937 MB of junk.
- Each mirror is scoped to its own lane subfolder, so syncing to "any" drive never touches the rest of that drive (e.g. the existing `E:\AIXMOS\` source-of-truth tree).

## Verified
- 2026-06-06: work-only mirror live-tested on E: (CYBORG) + F: (AIXMOS02).
- 2026-06-06: full 3-lane mirror live-tested on both — each holds TMMT-WORK + AIXMOS-BRAIN + PERSONAL (~336 MB), robocopy exits 0/1 (success). Watcher handles multiple drives sequentially.

**To narrow back to work-only:** edit `$lanes` in `Sync-WorkToUSB.ps1` to keep only the TMMT-WORK rows.
**To remove entirely:** `Unregister-ScheduledTask -TaskName TMMT-WorkSync-USB -Confirm:$false`, kill the Watch-USB.ps1 powershell process, delete the WorkSync folder.
