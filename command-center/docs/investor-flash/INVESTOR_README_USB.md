# AIX Command Center — Investor Flash Drive

This drive contains a **sanitized** offline copy of the AIX AI Command System and TMMT Management stack. **No API keys are included.** Add your own credentials before running automations.

## What is on this drive

| Path | Purpose |
|------|---------|
| `AIX_AI_COMMAND_SYSTEM/` | Prompts, SOPs, Python CLI/API, backend, setup scripts |
| `TMMT MANAGEMENT/` | Command center, **AI_BRAIN**, **AUTOMATIONS**, `tmmt-os` |
| `AIXMODE/` | Pointer to the main bundle |
| `INSTALL.md` | Full install guide (Mac + Windows) |
| `INVESTOR_ONE_PAGER.md` | What they're buying into, unit economics placeholders, ops gates |
| `docs/investor-flash/` | One-page flash, architecture map, AIXMOS brief, 30/60/90 roadmap |

## 5-minute install — Mac

```bash
cd "/Volumes/YOUR_DRIVE/AIX_AI_COMMAND_SYSTEM"
chmod +x scripts/*.sh scripts/aix 2>/dev/null || true
./scripts/setup-mac.sh
cp .env.example .env
open -e .env
```

Read `START_HERE.md`, then `TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md`.

## 5-minute install — Windows

```powershell
cd E:\AIX_AI_COMMAND_SYSTEM
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
Copy-Item .env.example .env
notepad .env
```

## API keys

Copy from `.env.example` and fill in your own Airtable, Supabase, and optional OpenAI values. Never share `.env`.

## Optional: Cursor

Open `AIX_AI_COMMAND_SYSTEM` in [Cursor](https://cursor.com) after setup.

## Ops vs investor (what is not on this USB)

This is a **clean investor** copy. It does not include operator-only ops (internal ops folders, drive-factory scripts, migration archives, or `OPERATOR_README` / solo-operator week plans). The operator maintains those on a separate master — not on handout drives.

Use **Mac** (`install.sh` or `AIX_AI_COMMAND_SYSTEM/scripts/setup-mac.sh`) or **Windows** (`install.bat` or `scripts/setup-windows.ps1`). Start at `START_HERE.md` on the USB root.
