# AI-OPS-STARTER

Plug-and-play **local-first AI operations** kit for:

| Machine | Role |
|---------|------|
| **Brainiac 7** (Windows 11 Pro) | Primary intellect node — Ollama + Docker stack |
| **MacBook** | Admin / edit / deploy / sync flash drive |
| **UGREEN NAS (60TB)** | System of record (SMB) |
| **Flash drive** | **Primary** handoff — full kit + per-person installers |

**Team self-install (flash → NAS → GitLab → Drive):** `docs/TEAM-SELF-INSTALL.md`

**Brainiac 7** is your Windows AI brain — the **supreme tier**. Other locations and operators use **Brainiac 6 → 1** (lower intellect / scope), all escalating to **7**. See `docs/brainiac-hierarchy.md` and `docs/brainiac-7.md`.

**Stack:** Docker Desktop, Ollama, Open WebUI, n8n, Qdrant, Tailscale (+ optional Faster-Whisper, PostgreSQL, Redis)

**Models:** `qwen2.5:7b`, `llama3.2`, `nomic-embed-text`

**Executives:** **Oracle** (strategy), **Operator** (daily processing), **Counsel** (communication) — see `agents/`

**Deploy order (phases 1→5 + heroes):** `docs/DEPLOY-ORDER.md` — *Ryn = Claryn (Mystique), Phase 4 with Nathan.*

---

## WINDOWS FIRST COMMAND (Phase 1)

Run in **PowerShell as your normal user** (Admin only if Docker install requires it). Creates folder, checks tools, pulls models, starts stack:

```powershell
$root = "C:\AI-OPS-STARTER"
New-Item -ItemType Directory -Force -Path $root | Out-Null
# If copying from flash drive E: adjust source:
# Copy-Item -Recurse -Force "E:\AI-OPS-STARTER\*" $root
Set-Location $root
@(
  @{ Name = "docker"; Cmd = { docker version } },
  @{ Name = "ollama"; Cmd = { ollama --version } },
  @{ Name = "tailscale"; Cmd = { tailscale status } }
) | ForEach-Object {
  try { & $_.Cmd | Out-Null; Write-Host "[OK] $($_.Name)" -ForegroundColor Green }
  catch { Write-Host "[MISSING] $($_.Name) - install before continuing" -ForegroundColor Red }
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
ollama pull qwen2.5:7b; ollama pull llama3.2; ollama pull nomic-embed-text
docker compose pull; docker compose up -d
Write-Host "`nOpen http://127.0.0.1:3000 (WebUI) and http://127.0.0.1:5678 (n8n)`n" -ForegroundColor Cyan
```

**Or** use the installer script after files are on disk:

```powershell
cd C:\AI-OPS-STARTER
Set-ExecutionPolicy -Scope Process Bypass
.\install-windows.ps1
```

---

## MACBOOK SETUP (M1 — admin / control)

**Full guide:** `setup/mac/MACBOOK-SETUP.md` — Tailscale, flash sync, NAS, remote Brainiac 7.

Quick start:

```bash
cd ~/AI-OPS-STARTER && ./install-mac.sh
# Tailscale on → Safari http://brainiac-7:3000
```

---

## MAC FIRST COMMAND (prepare / sync flash)

Run in **Terminal** on MacBook:

```bash
export KIT="$HOME/AI-OPS-STARTER"
export FLASH="/Volumes/AI-OPS"   # change to your USB volume name
mkdir -p "$KIT"
# If kit is on flash already:
# rsync -av "/Volumes/AI-OPS/AI-OPS-STARTER/" "$KIT/"
chmod +x "$KIT"/*.sh "$KIT"/scripts/*.sh 2>/dev/null
[[ -d "$FLASH" ]] && rsync -av --exclude .env "$KIT/" "$FLASH/AI-OPS-STARTER/"
tailscale status 2>/dev/null || echo "Install Tailscale: https://tailscale.com/download"
echo "Edit kit at $KIT — sync to flash at $FLASH/AI-OPS-STARTER"
```

**Or:**

```bash
cd ~/AI-OPS-STARTER && ./install-mac.sh
```

---

## FLASH DRIVE — copy & run on Windows

Full kit on USB includes **`START-HERE-FLASH.md`**, **`docs/DEPLOY-ORDER.md`**, and **`setup/operators/registry.yaml`**.

### 1. Copy kit to flash (Mac or Windows)

**Mac:**
```bash
FLASH_DRIVE=/Volumes/AI-OPS ~/AI-OPS-STARTER/scripts/sync-to-flash.sh
```

**Windows (PowerShell):**
```powershell
cd C:\AI-OPS-STARTER
.\scripts\sync-to-flash.ps1 -FlashDrive E:
```

### 2. On Windows AI machine (from flash `E:`)

Open **`START-HERE-FLASH.md`** on the USB, then:

```powershell
robocopy E:\AI-OPS-STARTER C:\AI-OPS-STARTER /E /XD data /XF .env
cd C:\AI-OPS-STARTER
# Follow docs\DEPLOY-ORDER.md for your phase
.\scripts\phase1-windows-bootstrap.ps1
```

Full details: `docs/flash-drive-guide.md`

---

## Architecture

```
┌─────────────┐     Tailscale      ┌──────────────────────┐
│   MacBook   │◄──────────────────►│  Brainiac 7          │
│ admin/edit  │                    │ Windows 11 Pro brain │
└──────┬──────┘                    │ Ollama + Docker stack│
       │ rsync flash               └──────────┬───────────┘
       ▼                                      │ SMB (60TB)
┌─────────────┐                    ┌──────────────────────┐
│ Flash drive │                    │   UGREEN NAS         │
│ portable kit│                    │ system of record     │
└─────────────┘                    └──────────────────────┘
```

- **Executives** run on Brainiac 7 via Open WebUI + Ollama
- **No public ports** — localhost + Tailscale
- **Paid APIs disabled** in `.env.example`

---

## Services (localhost on Windows)

| Service | URL |
|---------|-----|
| Open WebUI | http://127.0.0.1:3000 |
| n8n | http://127.0.0.1:5678 |
| Qdrant | http://127.0.0.1:6333/dashboard |
| Ollama | http://127.0.0.1:11434 |

From Mac (Tailscale): `http://brainiac-7:3000` or `http://<tailscale-ip>:3000`

---

## Daily commands

**Windows — start stack:**
```powershell
cd C:\AI-OPS-STARTER
.\start-windows.ps1
```

**Mac — sync flash + show Tailscale URLs:**
```bash
FLASH_DRIVE=/Volumes/AI-OPS ~/AI-OPS-STARTER/start-mac.sh
```

**Stop stack (Windows):**
```powershell
cd C:\AI-OPS-STARTER
docker compose down
```

---

## First-run order

1. `first-run-checklist.md`
2. `docs/nas-mount-guide.md`
3. `docs/open-webui-import.md`
4. Import `n8n/*.json` workflows
5. `security-checklist.md`
6. `backup-checklist.md`

---

## Executive roster (Brainiac 7)

| Executive | Role |
|-----------|------|
| **Oracle** | Chief strategic intellect — decisions, priorities, risk |
| **Operator** | Executive processor of reality — tasks, time, follow-ups |
| **Counsel** | Interpreter of human systems — messages, people, research |

Legacy 12-agent pack archived in `agents/archive/legacy-12/` — not for daily use.

---

## n8n example workflows

| File | Purpose |
|------|---------|
| `n8n/team-question-sop-answer.json` | Team question → SOP answer |
| `n8n/chat-to-task-assignment.json` | Chat → task assignment |
| `n8n/meeting-transcript-action-items.json` | Transcript → action items |
| `n8n/unanswered-escalate-taha.json` | Unanswered → escalate Taha |
| `n8n/daily-recap.json` | Daily recap |

Import: n8n UI → Workflows → Import from File

---

## Optional profiles

```powershell
# Redis + Faster-Whisper
docker compose --profile optional up -d
```

---

## Documentation index

- `docs/brainiac-7.md` — Brainiac 7 identity, voice, daily rituals
- `docs/nas-mount-guide.md` — UGREEN NAS SMB
- `docs/open-webui-import.md` — Executives & models
- `docs/flash-drive-guide.md` — Portable kit
- `docs/tailscale-remote-access.md` — Mac → Windows
- `nas/folder-structure.md` — NAS layout
- `troubleshooting.md` — Common fixes

---

## License & safety

This kit provides **legitimate local AI operations** tooling only. Do not use it to bypass security, credentials, or platform safety policies.
