# NAS Folder Structure (60TB)

Root: `\\UGREEN-NAS\AI-OPS` · Windows: `W:\` · Mac: `~/NAS/AI-OPS`

```
AI-OPS/
├── README.md
│
├── hot/                          # HOT — RAG + active (sync to Brainiac 7 ingest)
│   ├── brainiac-7/               # optional — session exports from Windows brain
│   │   ├── sessions/
│   │   └── recaps/
│   ├── knowledge/
│   ├── projects/
│   └── voice-notes/              # last 30 days raw audio (optional)
│
├── life/                         # WARM — personal executive data
│   ├── inbox/                    # unprocessed voice/text dumps
│   │   └── processed/
│   ├── tasks/
│   ├── journal/
│   │   └── recaps/               # Operator daily recaps
│   ├── decisions/                # Oracle decision log
│   ├── meetings/
│   │   ├── transcripts/
│   │   └── actions/
│   ├── comms/
│   │   └── drafts/               # Counsel drafts
│   ├── relationships/
│   └── health-finances/          # optional — restrict ACL
│
├── work/                         # WARM — business
│   ├── strategy/                 # Oracle
│   ├── tasks/                    # Operator
│   ├── clients/
│   ├── meetings/
│   └── projects/
│
├── knowledge/                    # WARM — shared reference
│   ├── sops/
│   ├── policies/
│   ├── templates/
│   │   └── comms/
│   └── faq/
│
├── archive/                      # COLD — bulk / old
│   ├── life/
│   ├── work/
│   ├── media/                    # video, photos, large files
│   └── year/YYYY/
│
├── vault/                        # restricted
│   ├── exports/
│   └── legal/
│
├── backups/
│   └── ai-ops/
│       └── YYYY-MM-DD/           # Docker volume exports
│
├── models/                       # optional
│   └── ollama/
│
└── exports/
    ├── open-webui/
    └── n8n/
```

## Size guidance

| Area | Guidance |
|------|----------|
| `hot/` | Keep under ~2 TB — prune monthly to `archive/` |
| `life/` + `work/` | Grow freely; snapshot weekly |
| `archive/` | Majority of 60TB over years |
| `backups/` | Retention policy in `backup-checklist.md` |

## Init

**Windows:** `.\scripts\init-nas-layout.ps1`  
**Mac:** `./scripts/init-nas-layout.sh`
