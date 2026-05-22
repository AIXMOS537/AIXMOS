# Flash Drive Guide

## Purpose

The flash drive is a **portable copy** of `AI-OPS-STARTER`: agents, scripts, compose file, docs, n8n workflows — **not** running databases or `.env` secrets.

---

## Recommended setup

| Item | Value |
|------|-------|
| Label | `AI-OPS` (helps Mac `FLASH_DRIVE` path) |
| Format | exFAT (Mac + Windows) or NTFS (Windows-primary) |
| Size | 8 GB+ (models are NOT on flash — pulled on Windows) |

---

## Copy to flash (full install kit) — **primary distribution channel**

Includes per-person **`scripts/installers/install-*.ps1`**, **`docs/TEAM-SELF-INSTALL.md`**, deploy order, registry.

### One command (recommended)

**Mac:**

```bash
cd ~/AI-OPS-STARTER
./scripts/publish-release.sh
```

**Windows:**

```powershell
cd C:\AI-OPS-STARTER
.\scripts\publish-release.ps1 -FlashDrive E:
```

This refreshes installers, syncs `AI-OPS-STARTER\` to the stick, and copies `AI-OPS-RELEASES\AI-OPS-STARTER-v*.zip`.

### Manual sync

**Mac:**

```bash
FLASH_DRIVE=/Volumes/AI-OPS ~/AI-OPS-STARTER/scripts/sync-to-flash.sh
```

**Windows:**

```powershell
cd C:\AI-OPS-STARTER
.\scripts\sync-to-flash.ps1 -FlashDrive E:
```

### Verify

```bash
./scripts/verify-flash-drive.sh /Volumes/AI-OPS/AI-OPS-STARTER
```

On the USB, open **`START-HERE-FLASH.md`** first.

---

## Deploy from flash → Windows brain

1. Insert flash (e.g. drive `E:`)
2. Read **`START-HERE-FLASH.md`** or **`docs\DEPLOY-ORDER.md`**
3. Copy to permanent location:

```powershell
robocopy E:\AI-OPS-STARTER C:\AI-OPS-STARTER /E /XD data /XF .env
cd C:\AI-OPS-STARTER
# Phase 1 (Taha / Brainiac 7) — see docs\DEPLOY-ORDER.md
.\scripts\phase1-windows-bootstrap.ps1
```

4. Each operator: `.\scripts\installers\install-<name>.ps1` (see **`docs\install-guides\`**)
5. Models download via Ollama on Windows (not from flash)

---

## Offline git history

The flash copy **includes `.git/`** so `git log` works without internet. See `docs/offline-git-history.md`.

After kit changes on your Mac or Brainiac 7:
```bash
git add -A && git commit -m "Kit update"
FLASH_DRIVE=/Volumes/AI-OPS ./scripts/sync-to-flash.sh
```

## What NOT to put on flash

- `.env` (secrets)
- `data/` (runtime cache)
- Docker volumes / databases
- Full Ollama model blobs (use `ollama pull` on Windows)
- Client PII exports unless encrypted

---

## Refresh cycle

After editing on Mac:

```bash
FLASH_DRIVE=/Volumes/AI-OPS ./start-mac.sh
```

Or re-run `install-mac.sh`.

---

## Offline readme

A `README.txt` is generated on verify — points to `README.md` on Windows after copy.
