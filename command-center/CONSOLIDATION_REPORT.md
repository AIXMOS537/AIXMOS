# Consolidation report — 2026-05-16

## Source

- **BROTHER I:** `/Users/projectaixmos01/Desktop/BROTHER I` (4,224 files, 6.6 GB) — **unchanged** (copy-merge only)
- Upload log: `CLAUDE_COPY_LOG_20260516_211610.txt`

## Canonical working folder

**`~/Desktop/AIX_Command_Center`** (379 files, ~2 MB code/docs)

| Component | Status |
|-----------|--------|
| AIX_AI_COMMAND_SYSTEM | Merged (no secrets in investor paths) |
| TMMT MANAGEMENT | Merged — AI_BRAIN, AUTOMATIONS, tmmt-os |
| AIXMODE, AIXMOSXTMMT-OPS, all_in_one_platform | Included |
| agents/ | Root agent `.md` files |
| ops/moose-stack/ | brain.js, moose.js, start scripts |
| docs/ | Fleet + local AI guides |

Desktop symlinks: `~/Desktop/TMMT MANAGEMENT` → command center, `~/Desktop/AIXMODE` → command center.

## Investor master

**`~/Desktop/INVESTOR_FLASH_MASTER`** (285 files, sanitized)

- No `.env` / `.env.local` (secret scan clean)
- Clone tools: `prepare-three-drives.sh`, `clone-to-flash.sh`

## Not merged (personal / media — stay in BROTHER I)

AIRBNB, Photos, PICTURES, VIDEOS, CHUMMOCLAUDEOS, Dispute Letters, nested Desktop/Downloads duplicates, etc.

## Lexar

`/Volumes/LEXAR` — **not mounted**. When plugged in:

```bash
cd ~/Desktop/AIX_Command_Center/AIX_AI_COMMAND_SYSTEM
./scripts/sync-to-lexar.sh
```

## Investor USB clone

**Not run** — no 3 blank investor drives detected. Mounted: `AIXMOS02`, `CYBORG` (ops drives, excluded from auto-clone).

```bash
cd ~/Desktop/INVESTOR_FLASH_MASTER
./prepare-three-drives.sh
```
