# Offline Git History on Flash

The USB kit includes the **`.git`** folder so you have full version history without internet.

---

## What’s on the stick

| Included | Excluded |
|----------|----------|
| All kit files + **`.git/`** | **`.env`** (secrets) |
| `docs/DEPLOY-ORDER.md`, registry, agents | **`data/`** (runtime cache) |

Sync with:
```bash
FLASH_DRIVE=/Volumes/AI-OPS ./scripts/sync-to-flash.sh
```
```powershell
.\scripts\sync-to-flash.ps1 -FlashDrive E:
```

---

## On Windows (offline)

```powershell
cd E:\AI-OPS-STARTER
git log --oneline -10
git status
```

After copy to `C:\AI-OPS-STARTER`, history comes along:

```powershell
robocopy E:\AI-OPS-STARTER C:\AI-OPS-STARTER /E /XD data /XF .env
cd C:\AI-OPS-STARTER
git log --oneline -5
```

---

## On Mac (offline)

```bash
cd /Volumes/AI-OPS/AI-OPS-STARTER
git log --oneline -10
```

---

## Refresh history on the stick

After changes on Brainiac 7 or Mac, commit locally then re-sync:

```bash
cd ~/AI-OPS-STARTER
git add -A && git commit -m "Kit update"
FLASH_DRIVE=/Volumes/AI-OPS ./scripts/sync-to-flash.sh
```

---

## If `git` is missing on a PC

Install Git for Windows: https://git-scm.com/download/win  
History files are still on disk; `git log` works once Git is installed.
