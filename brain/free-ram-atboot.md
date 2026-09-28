---
name: free-ram-atboot
description: Boot-time RAM cleanup scheduled task on the command-hub tablet (DESKTOP-1IT6EL5)
metadata: 
  node_type: memory
  type: project
  originSessionId: fa64a7db-9a61-4999-8854-1c74b83dbde4
  modified: 2026-08-20T17:30:42.993Z
---

On the Windows command-hub tablet (DESKTOP-1IT6EL5, 2-core i7-6650U / 16GB), a scheduled task **FreeRAM-AtBoot** runs at every logon (+60s delay) **and every 3 hours** to trim the working set of all processes and free RAM. Set up 2026-08-20.

- Script: `C:\Users\AIXMOS\Automation\Free-RAM-AtBoot.ps1` (uses built-in `EmptyWorkingSet` API — nothing killed/uninstalled).
- Log: `C:\Users\AIXMOS\Automation\free-ram.log` (before/after free MB, keeps last 200 runs). First run freed ~1.8 GB.
- Runs in the user context, no admin/UAC needed. Manage with `Get-ScheduledTask FreeRAM-AtBoot` / `Start-ScheduledTask` / `Unregister-ScheduledTask`.

Context: same 2026-08-20 cleanup pass uninstalled AnyDesk, both Copilots, Bonjour + Apple Software Update, and disabled OneDrive autostart. **Perfect Memory** is the tablet's top CPU consumer (always-on capture) but the user chose to keep it running untouched. See [[tablet-desktop-setup]], [[device-architecture]], [[fleet-watchtower]].
