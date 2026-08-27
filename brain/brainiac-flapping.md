---
name: brainiac-flapping
description: "brainiac-7 drops off the Tailscale mesh repeatedly - diagnosis, the fix script, and how it is monitored"
metadata: 
  node_type: memory
  type: project
  originSessionId: c0397b4e-80db-436d-88b3-41c8643364a1
  modified: 2026-08-25T20:14:19.304Z
---

`brainiac-7` (100.64.0.1, Windows) keeps dropping off the [[tailscale-mesh]]. Investigated 2026-08-25.

**Observed pattern** (from ClosedLoop logs): offline ~17h overnight, online 12:51-14:50, offline 14:50-16:06, back online. Long offline stretches with online windows of 1-2h.

**Ruled out:** node key is valid until 2026-11-18, so key expiry is NOT the cause. It relays via DERP `iad` and never gets a direct handshake - consistent with the tablet sitting on a guest WiFi network.

**Fix script:** `CommandCenter\ops\fix-brainiac-flapping.ps1` - must run ON the flapping machine, as Administrator. `-Report` mode inspects without changing anything. Covers the five real causes: Tailscale unattended mode (biggest one - Windows disconnects Tailscale at logout without it), sleep/hibernate on AC, WiFi adapter power management, Tailscale service start mode, and Fast Startup.
- Delivered to brainiac-7 via **Taildrop** (`tailscale file cp <script> brainiac-7:`) - lands in Downloads. `ops fix-flapping` re-sends it whenever the target is online.
- **APPLIED on the tablet (DESKTOP-1IT6EL5) 2026-08-25** - all 5 checks now green: Tailscale unattended ON (`tailscale set --unattended` -> `ForceDaemon: true`), Fast Startup OFF (`HiberbootEnabled=0`), WiFi power saving OFF (`PnPCapabilities=24`). Needs a reboot for the WiFi change to bite. Applied via `Start-Process -Verb RunAs` (UAC); the Claude session itself is NOT elevated.
- Original report found **3 real problems** - Tailscale unattended OFF, WiFi adapter power-down allowed, Fast Startup ON. Tailscale service is fine.
- **Sleep is NOT a problem on the tablet**: `powercfg /a` reports `Standby (S0 Low Power Idle) Network Connected`, i.e. Modern Standby that keeps the network up while asleep. It sleeps after 300 min AC but stays connected. The script now detects S0-network-connected and deliberately leaves the sleep timeout alone - only classic S3 machines get the never-sleep change. Check which type brainiac-7 is before assuming sleep is its cause.
- `Get-NetAdapterPowerManagement` fails on this tablet's Marvell AVASTAR adapter ("device not functioning"), so the script falls back to the registry: `PnPCapabilities` bit `0x18` under the net class GUID `{4d36e972-e325-11ce-bfc1-08002be10318}`.

**Monitoring:** `flapwatch.ps1` + scheduled task `TMMT-FlapWatch` (every 5 min) logs only state *changes* to `ClosedLoop\logs\flaps.jsonl`. View with `ops flaps` (see [[ops-command]]) - shows current state, recent transitions, and drops-per-device with average uptime.

**Access limits:** brainiac-7 has SSH (22) and SMB (445) open but WinRM/RDP closed. SSH needs credentials that were not available, and Tailscale SSH is not enabled on it (no host keys). So remote execution was not possible - only file delivery via Taildrop.

**Honest caveat:** these settings fix sleep/logout/power-saving drops. If the machine is physically powered off (the 17h overnight gap suggests it may be), no software setting keeps it online - that needs it left running, or Wake-on-LAN.

- **Trap:** `Set-NetAdapterPowerManagement` can report success on drivers that silently ignore it, which made the first elevated run skip the registry fallback and leave WiFi unchanged. The script now writes the registry FIRST and reads the value back to confirm - it never claims a fix it has not verified.
