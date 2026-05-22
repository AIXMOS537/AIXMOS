# Backup Checklist

## What to back up

| Asset | Location | Frequency |
|-------|----------|-----------|
| Open WebUI data | Docker volume `open-webui-data` | Daily |
| n8n workflows + DB | Volume `n8n-data`, Postgres `postgres-data` | Daily |
| Qdrant vectors | Volume `qdrant-data` | Weekly |
| Agent prompts & kit | `C:\AI-OPS-STARTER`, git/flash | On change |
| Company knowledge | NAS `AI-OPS/knowledge`, `sops` | Continuous (NAS RAID) |
| `.env` | Password manager + offline secure store | On change |

## Windows backup commands

```powershell
cd C:\AI-OPS-STARTER
.\scripts\backup-windows.ps1
```

Target: `Z:\backups\ai-ops\YYYY-MM-DD\`

## Mac (sync kit only)

```bash
~/AI-OPS-STARTER/scripts/backup-mac.sh
```

## Restore test (monthly)

- [ ] Restore Open WebUI volume to test folder
- [ ] Import one n8n workflow from backup JSON
- [ ] Verify Qdrant collection count matches pre-backup notes

## Retention

- Daily: 7 days
- Weekly: 4 weeks
- Monthly: 12 months (NAS)

## Flash drive

- [ ] Flash holds **kit source**, not primary backups
- [ ] Refresh flash after material doc/agent changes
