---
name: ugreen-nas
description: "The UGREEN NAS is the user's home hub for the brain/Obsidian vault and cross-device sync (tablet ↔ Brainiac ↔ Macs). Load whenever syncing the brain, mounting storage, or wiring devices together at home."
metadata: 
  node_type: memory
  type: project
  domain: system
  originSessionId: 5102c337-d5a6-4893-bf83-73d6c6f4e440
---

The user's chosen home for the AI brain + Obsidian vault is their **UGREEN NAS** (not cloud, not GitHub). It's private, always-on, on the home LAN — ideal for the home daily-driver tablet that stays at home, and reachable by **Brainiac** + the Macs on the same network. The TMMT ops package even ships a `sync-nas` script, so NAS sync is already part of the ecosystem. See [[device-architecture]], [[home-bot]].

## ✅ CONNECTED + SYNCING (2026-06-06)
- **Reachable via `192.168.1.236`** (main home LAN). Tablet connected to that Wi-Fi (`192.168.1.163`); SMB(445) on, login verified.
- **Login:** username **`MUHAMMAD TAHA`** (with the space — that exact string works). Password stored in Windows Credential Manager via `cmdkey` — NOT in this file.
- **Shares:** `personal_folder` (home), `ai-backups`, `ai-data`, `ai-ingest`, `ai-models`, `Photos`. Brain lives in the private `personal_folder`.
- **Brain master copy on NAS:** `N:\AIXMOS\AIXMOS-Brain` = `\\192.168.1.236\personal_folder\AIXMOS\AIXMOS-Brain` (drive `N:` mapped persistent). It's a full git working repo (readable Obsidian vault, cloud-backed via the NAS's OneDrive/GDrive sync).
- **Sync model:** tablet local `C:\Users\AIXMOS\AIXMOS-Brain` has git remote **`nas`** → push auto-updates the NAS working tree (`receive.denyCurrentBranch=updateInstead`). Verified: `git push nas main` lands files on the NAS. Use `git pull nas main` on other devices.
- **Git gotchas handled:** added `safe.directory` exceptions for the UNC path; set `core.autocrlf false` on the NAS repo; if push is rejected with "working directory has unstaged changes," run `git -C N:\AIXMOS\AIXMOS-Brain reset --hard HEAD` then push.

### ⚠️ Network caveat + the PREFERRED fix (Tailscale)
- Today, sync only works while the tablet is on the **`192.168.1.x`** Wi-Fi (the NAS's main LAN). On the usual **SATTAR (`192.168.68.x`)** Wi-Fi the NAS's `.59` interface exposes only UGOS 9999 (SMB blocked).
- **PREFERRED FIX = put the NAS on Tailscale** (see [[tailscale-mesh]]): install Tailscale in **UGOS App Center**, sign in as `AIXMOS537`. The NAS then gets a `100.x` address reachable from ANY Wi-Fi — sync works everywhere, no SMB-on-`.59` needed. Tablet + Brainiac are already on the tailnet.
- (Fallback only) Otherwise enable SMB on the `.59` interface + firewall-allow `192.168.68.0/24` and add a `nas68` remote.

## Why NAS over cloud/GitHub (decided 2026-06-06)
- User's GitHub account `AIXMOS537` is restricted (can't create repos); `Metavibez4L` is the **partner's** account — using it would expose the user's private family/personal lanes. So GitHub is out for the private brain.
- No cloud (OneDrive/Drive) is signed in on the tablet.
- NAS keeps everything **private + local**, and every home device can mount the same share.

## Connection (this tablet)
- Tablet IP: 192.168.68.63 (Wi-Fi). Gateway/router: 192.168.68.1. NAS is on the **192.168.68.x** subnet.
- NAS had **never been connected from this tablet** as of setup (no stored SMB creds, no mapping).
- **PENDING from user:** NAS IP/hostname · share/folder name · SMB username + password. Once provided: mount via SMB, create a `Brain/` (or AIXMOS-Brain) folder on the share, relocate the brain there + re-point the Claude memory junction, and store creds in Windows Credential Manager (not plaintext).

## Plan once connected
1. Mount NAS share (e.g. `\\<nas-ip>\<share>`), persist credential.
2. Move `C:\Users\AIXMOS\AIXMOS-Brain` → NAS share; junction `~/.claude/projects/C--/memory` → the NAS path so memory writes land on the NAS.
3. On **Brainiac** + Macs: mount the same share, open the brain folder as an **Obsidian vault**. Now one brain, synced across the home, no cloud.

## Discovery 2026-06-06 (from the tablet, confirmed live)
- **NAS = `192.168.68.59`**, UGOS web console on **port 9999** (http://192.168.68.59:9999 → HTTP 200 ✅).
- **Brainiac = `192.168.68.61`** (hostname `BRAINIAC-7`), SSH(22)+SMB(445) open — power machine on the same LAN.
- ⚠️ **SMB/NFS/FTP are NOT enabled on the NAS** — a full port scan found ONLY 9999 open (445, 2049, 21 all closed). So **the NAS can't be mounted yet**: file service must be turned on in UGOS first.
- ⚠️ The "`sync-nas` script ships with TMMT" note above was **not found on disk** — no such script exists. The real sync will be built once SMB is on.
- ⚠️ IPs are DHCP — set a **static IP / DHCP reservation** for the NAS (and Brainiac) so they don't move.

## Network topology RESOLVED (2026-06-06 traceroute)
- The NAS is **dual-homed** (two network ports): **`192.168.1.236`** on the main home LAN, and **`192.168.68.59`** on the **"SATTAR MANAGEMENT LLC"** Wi-Fi.
- **Tablet (`.63`) + Brainiac (`BRAINIAC-7`, `.61`) are BOTH on SATTAR (`192.168.68.x`)** — same network as the NAS's `.59` port. ✅ So all three can share one vault.
- `192.168.1.236` is on a **separate internet connection** — traceroute from the tablet goes 192.168.68.1 → `108.51.96.1` (public internet) → dead. The tablet/Brainiac **cannot** reach `.1.236`. Use **`192.168.68.59`** for everything on SATTAR.
- ⚠️ On the `.59` (SATTAR) port, **only UGOS web (9999) is exposed — SMB(445)/SSH(22) are off/blocked there.** Fix = in UGOS enable **SMB listening on ALL interfaces** + **firewall allow `192.168.68.0/24`**. Then tablet + Brainiac mount `\\192.168.68.59\Brain`.
- Bonus: NAS already syncs to the user's **OneDrive + Google Drive**, so the brain on the NAS gets cloud-backed automatically.

## DO-THIS-YOURSELF checklist (unblocks everything; needs your UGOS admin login)
1. Open **http://192.168.68.59:9999** → log in as admin.
2. **Enable SMB**: Control Panel / File Services → turn on **SMB** (a.k.a. Samba/Windows file sharing).
3. **Create a shared folder** named `Brain` (and optionally `Backups`, `TMMT`).
4. **Create a user** (e.g. `aixmos`) with read/write to `Brain`; set a password.
5. (Recommended) **Reserve a static IP** for the NAS in the router, or note its hostname.
6. Give me: **share path** (`\\192.168.68.59\Brain`), **username**, **password** → I mount it, move the brain onto it, re-point the memory junction, and wire Brainiac + the Macs to the same vault.
