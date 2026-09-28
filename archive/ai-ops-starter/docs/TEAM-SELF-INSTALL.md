# Team Self-Install Guide

**Distribution priority (use in this order):**

1. **Flash drive** — primary handoff  
2. **NAS** — office / Tailscale LAN updates  
3. **GitLab or GitHub** — versioned zip for remote staff  
4. **Google Drive** — convenience copy of the **same** zip (never the only source)

**Kit version:** see `VERSION` in the project root.

---

## Who installs what

| Tier | Examples | Install |
|------|----------|---------|
| **7** | Muhammad Taha (Brainiac 7) | Full stack — `scripts\installers\install-brainiac-7.ps1` |
| **5–4** | Dominique, Michael, Claryn, Nathan, … | Personal `install-*.ps1` + Docker/Ollama/Tailscale |
| **3** | Dyson, Nathan | Same as tier 4–5 |
| **2–1** | Shared tablet, viewers | **No full kit** — Tailscale + `http://brainiac-7:3000` only |

Thin-client guide: `scripts\installers\install-shared-thin.ps1` (if generated).

---

## Channel 1 — Flash drive (primary)

### Admin (you) — refresh the stick

**Mac:**

```bash
cd ~/AI-OPS-STARTER
./scripts/publish-release.sh
# or step by step:
./scripts/build-release-zip.sh
FLASH_DRIVE=/Volumes/AI-OPS ./scripts/sync-to-flash.sh
cp dist/AI-OPS-STARTER-v*.zip /Volumes/AI-OPS/AI-OPS-RELEASES/
```

**Windows (Brainiac 7):**

```powershell
cd C:\AI-OPS-STARTER
.\scripts\publish-release.ps1 -FlashDrive E:
```

USB layout:

```text
E:\AI-OPS-STARTER\          ← full kit (open START-HERE-FLASH.md)
E:\AI-OPS-RELEASES\         ← versioned zip for copy to PC
```

### Each operator — from flash

1. Insert USB → copy to `C:\AI-OPS-STARTER` (or run from flash, then copy):

```powershell
robocopy E:\AI-OPS-STARTER C:\AI-OPS-STARTER /E /XD data /XF .env
```

2. Open **`docs\install-guides\INSTALL-<yourname>.md`** or find your script in **`scripts\installers\`**.

3. Optional prerequisites (Admin PowerShell once):

```powershell
cd C:\AI-OPS-STARTER
.\scripts\install-prerequisites.ps1
```

4. Run **your** installer:

```powershell
cd C:\AI-OPS-STARTER
.\scripts\installers\install-dominique.ps1
# or: .\scripts\installers\install-dominique.ps1 -InstallPrerequisites
```

5. Open http://127.0.0.1:3000 — paste `prompts\tier-preamble.md` + your executive from `agents\`.

**Never** copy `.env` from the USB.

---

## Channel 2 — NAS (secondary)

After Brainiac 7 has NAS mapped:

```powershell
cd C:\AI-OPS-STARTER
.\scripts\build-release-zip.ps1
.\scripts\publish-to-nas.ps1
# default: \\UGREEN-NAS\AI-OPS\releases\v1.0.0\
```

Operators on LAN or Tailscale:

1. Download `\\UGREEN-NAS\AI-OPS\releases\v1.0.0\AI-OPS-STARTER-v1.0.0.zip`
2. Extract to `C:\AI-OPS-STARTER`
3. Run their `scripts\installers\install-*.ps1`

Per-person one-pagers are copied to the same NAS folder (`INSTALL-*.md`).

---

## Channel 3 — GitLab / GitHub (remote backup)

1. Create a **private** project and push this repo (no `.env` in git — already in `.gitignore`).
2. Tag a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

3. Build zip locally: `.\scripts\build-release-zip.ps1` or `./scripts/build-release-zip.sh`
4. Attach `dist/AI-OPS-STARTER-v1.0.0.zip` to **Releases** for that tag.
5. Send operators the release URL — **Download zip** → extract → run their `install-*.ps1`.

Updates: email/Slack *"v1.0.1 is out — re-download the release zip."*

---

## Channel 4 — Google Drive (convenience)

Use the **identical** zip from `dist\` — do not zip ad-hoc folders.

1. Upload `AI-OPS-STARTER-v1.0.0.zip` to a **Shared drive** (workspace) or folder shared to work emails only.
2. Pin a Doc with:
   - Link to the zip
   - Link to `docs/TEAM-SELF-INSTALL.md` (or paste the operator’s `INSTALL-*.md`)
   - Prerequisites: Docker, Ollama, Tailscale
3. Filename must include version: `AI-OPS-STARTER-v1.0.0.zip`

**Do not** set link to "Anyone on the internet."

---

## Prerequisites (all full-stack tiers)

| Tool | Install |
|------|---------|
| Docker Desktop | `winget install Docker.DockerDesktop` or https://www.docker.com/products/docker-desktop/ |
| Ollama | `winget install Ollama.Ollama` or https://ollama.com/download |
| Tailscale | `winget install Tailscale.Tailscale` or https://tailscale.com/download |

One-shot script: `.\scripts\install-prerequisites.ps1` (Admin).

Or pass `-InstallPrerequisites` to your personal `install-*.ps1`.

---

## Thin client (tier 2–1)

No Docker. No Ollama. No full kit required.

1. Install Tailscale and join the tailnet.
2. Browser → **http://brainiac-7:3000**
3. Use Open WebUI on Brainiac 7; optional: paste `prompts\tier-preamble.md` (tier 2).

---

## Message template

Send each person **only their section**:

> **Brainiac install (v1.0.0)**  
>  
> 1. Get the kit: **USB** from Taha *or* NAS zip *or* GitLab release link *or* Google Drive (same file).  
> 2. Extract/copy to `C:\AI-OPS-STARTER`.  
> 3. Install Docker, Ollama, Tailscale if you don’t have them (links in TEAM-SELF-INSTALL).  
> 4. PowerShell: `cd C:\AI-OPS-STARTER` then run:  
>    `.\scripts\installers\install-YOURNAME.ps1`  
> 5. Open http://127.0.0.1:3000 when done.  
>  
> Do **not** use a `.env` file from email/USB/Drive — the script creates one locally.

Replace `YOURNAME` with: `dominique`, `michael`, `dyson`, `nathan`, `claryn`, `brainiac-7` (Taha), etc.

---

## Admin checklist

- [ ] Brainiac 7 Phase 1 complete before rolling operators
- [ ] Run `.\scripts\generate-installers.ps1` after registry edits
- [ ] `VERSION` bumped for each rollout wave
- [ ] Flash refreshed (`publish-release`)
- [ ] NAS `releases\vX.Y.Z\` updated
- [ ] GitLab/GitHub release attached (optional)
- [ ] Drive copy matches version in filename (optional)
- [ ] Kayleigh installer left blocked until hired (`-Force` only when ready)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Docker missing" | Run `install-prerequisites.ps1` as Admin, reboot |
| Wrong node / hostname | Re-run your `install-*.ps1` (re-provisions `.env`) |
| Stale kit | Check `VERSION` file; re-copy flash or re-download zip |
| Can't reach Brainiac 7 | Tailscale on; ping `brainiac-7` |

See `troubleshooting.md` and `docs\DEPLOY-ORDER.md`.
