# Lexar portable install — Command Center (Windows + Mac)

This drive contains a complete offline copy of the **AIX AI Command System** and **TMMT Management** stack. Use forward slashes in docs; on Windows, the same paths work in PowerShell and most tools (e.g. `E:/AIX_AI_COMMAND_SYSTEM`).

## What is on this drive

| Path | Purpose |
|------|---------|
| `AIX_AI_COMMAND_SYSTEM/` | Main bundle: prompts, SOPs, Python CLI/API, backend, scripts, Airtable templates, TMMT integration |
| `TMMT MANAGEMENT/` | TMMT command center, **AI_BRAIN**, **AUTOMATIONS** (agents/scripts), fleet, finance, `tmmt-os` app source |
| `AIXMODE/` | Pointer to the main bundle (legacy folder name) |
| `INSTALL.md` | This file |

**Other flash drives:** Only `LEXAR` was mounted during the last sync. Plug in any other drives and re-run `AIX_AI_COMMAND_SYSTEM/scripts/sync-to-lexar.sh` (Mac) or `sync-to-lexar.ps1` (Windows) from a machine that can see all volumes.

## Quick start — Mac

1. Insert the Lexar drive. Note the volume name (e.g. `/Volumes/LEXAR`).
2. Open Terminal:
   ```bash
   cd "/Volumes/LEXAR/AIX_AI_COMMAND_SYSTEM"
   chmod +x scripts/*.sh scripts/aix 2>/dev/null || true
   ./scripts/setup-mac.sh
   ```
3. Copy secrets locally (never commit):
   ```bash
   cp .env.example .env
   # Edit .env with your Airtable token, base ID, Supabase URL, etc.
   ```
4. Read `START_HERE.md`, then `ONE_PAGE_START.md` or `TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md`.
5. Optional TMMT web app:
   ```bash
   cd "/Volumes/LEXAR/TMMT MANAGEMENT/tmmt-os"
   cp .env.example .env.local
   npm install
   npm run dev
   ```

**Python:** Use `python3` (macOS). The setup script creates `.venv` and installs `requirements.txt`.

## Quick start — Windows

1. Open PowerShell (drive letter may be `E:` or `F:`):
   ```powershell
   cd E:\AIX_AI_COMMAND_SYSTEM
   Set-ExecutionPolicy -Scope Process Bypass
   .\scripts\setup-windows.ps1
   ```
2. Copy secrets:
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
3. Read `START_HERE.md` and `TEAM_DEPLOY.md`.
4. Optional TMMT OS:
   ```powershell
   cd "E:\TMMT MANAGEMENT\tmmt-os"
   Copy-Item .env.example .env.local
   npm install
   npm run dev
   ```

**Python:** Use `python` (Windows installer). If both exist, prefer `py -3`.

## Cross-platform scripts

| Task | Mac / Linux | Windows |
|------|-------------|---------|
| First-time setup | `scripts/setup-mac.sh` | `scripts/setup-windows.ps1` |
| Load env vars | `scripts/load-env.sh` | Set variables in `.env` or use `$env:VAR = "..."` |
| CLI wrapper | `./scripts/aix` | `python aix_operator.py` |
| Sync Mac → Lexar | `scripts/sync-to-lexar.sh` | `scripts/sync-to-lexar.ps1` |

Shell scripts (`.sh`) are not native on Windows; use PowerShell setup and `python aix_operator.py` for CLI tasks.

## Security — `.env` files

- **Do not** share API keys on this flash drive in plain text for team handoff.
- If `.env` exists on the drive with real tokens, treat the drive as **sensitive** or delete `.env` and use only `.env.example` when copying to a new machine.
- Never copy `.env.local` from TMMT OS; use `.env.example` / `.env.tmmt-os.example`.

## TMMT brain and agents

| Location | Contents |
|----------|----------|
| `TMMT MANAGEMENT/AI_BRAIN/` | Memory index, workflow memory, agent prompts (e.g. Captain America, Wonder Woman) |
| `TMMT MANAGEMENT/AUTOMATIONS/` | Command agent plan, n8n blueprint, Python scripts, JSON configs, prompts |
| `TMMT MANAGEMENT/DATA/SCHEMAS/` | Agent task schema |
| `AIX_AI_COMMAND_SYSTEM/prompts/` | Daily command, money, TMMT snapshot prompts |

## Verify install (optional)

From a Mac with both Desktop and Lexar connected:

```bash
diff -rq ~/Desktop/TMMT\ MANAGEMENT /Volumes/LEXAR/TMMT\ MANAGEMENT \
  --exclude=node_modules --exclude=.git --exclude='._*' --exclude=.DS_Store
```

No output means TMMT tree matches. AIX bundle on Lexar is a **superset** of the small `Desktop/AIXMODE` subset.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `python` not found (Windows) | Install from https://www.python.org/downloads/ and check "Add to PATH" |
| `python3` not found (Mac) | `brew install python` or python.org installer |
| Permission denied on `.sh` | `chmod +x scripts/*.sh` |
| exFAT/FAT timestamp errors on sync | Use `rsync --no-times` or run sync from Terminal.app |
| Hardcoded Mac paths in old copies | Prefer this drive’s `build_execution_workbook.mjs` (uses relative paths) |

## Primary docs (read order)

1. `AIX_AI_COMMAND_SYSTEM/START_HERE.md`
2. `AIX_AI_COMMAND_SYSTEM/README.md`
3. `AIX_AI_COMMAND_SYSTEM/FIRST_72_HOURS.md`
4. `TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md`
5. `AIX_AI_COMMAND_SYSTEM/TEAM_DEPLOY.md`
