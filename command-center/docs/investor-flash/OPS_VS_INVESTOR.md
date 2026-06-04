# Ops vs investor flash boundary (operator master only)

**Do not copy this file to investor USB drives.** Keep it on the Desktop `INVESTOR_FLASH_MASTER` folder and in `AIX_Command_Center` operator docs.

## Investor USB (clean, handoff-safe)

| Include | Notes |
|---------|--------|
| `AIX_AI_COMMAND_SYSTEM/` | Sanitized bundle; no committed secrets |
| `TMMT MANAGEMENT/` | Command center, AI_BRAIN, AUTOMATIONS (no operator-only ops trees) |
| `AIXMODE/` | Pointer to main bundle |
| `INSTALL.md`, `INVESTOR_README.md`, `INVESTOR_ONE_PAGER.md` | Mac + Windows install |
| `START_HERE.md`, `install.sh`, `install.bat` | Cross-platform entry at USB root |
| `docs/investor-flash/` | Architecture map, roadmap, flash brief |
| `INVESTOR_DRIVE.txt` | Optional label after clone (drive #) |

**Exclude:** API keys in `.env`, operator checklists, clone/wipe scripts, ops stacks, personal archives, staging dumps.

## Ops (Muhammad only — paid access gate)

| Exclude from investor USB | Why |
|---------------------------|-----|
| `AIXMOSXTMMT-OPS/`, `ops/`, `chummo-stack` | Operator automation & internal tooling |
| `taha1/`, `cyborg_staging/`, `MacMigrationBundle/` | Personal / migration |
| `CHUMMOCLAUDEOS/`, `MOOSECLAUDEOS/`, BROTHER I archives | Legacy cloud dumps |
| `OPERATOR_README.md`, `INVESTOR_INSTALL_CHECKLIST.md`, `SOLO_OPERATOR_WEEK.md` | Operator runbooks |
| `prepare-three-drives.sh`, `clone-to-flash.sh`, `refresh-investor-drives.sh`, `strip-secrets.sh` | Drive factory scripts |
| `OPS_VS_INVESTOR.md` | This boundary doc |
| Any `.env` / `.env.local` with real tokens | Secrets |

## Refresh workflow (operator Mac)

```bash
cd ~/Desktop/INVESTOR_FLASH_MASTER
./refresh-investor-drives.sh /Volumes/AIXMOS02 /Volumes/CYBORG
```

Or per drive: wipe → `SKIP_CONFIRM=1 ./clone-to-flash.sh /Volumes/NAME N`

## Access model

- **Investor / licensee:** clean USB + their own API keys in `.env` from `.env.example`.
- **Ops:** command center on Desktop, paid engagement, or explicit operator grant — never on clean investor drives.
