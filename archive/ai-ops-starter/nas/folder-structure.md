# NAS Folder Structure

Root SMB share: `\\UGREEN-NAS\AI-OPS` (Windows `Z:\`)

```
AI-OPS/
├── README.md
├── knowledge/
│   ├── README.md
│   ├── products/
│   ├── policies/
│   └── faq/
├── sops/
│   ├── README.md
│   ├── onboarding/
│   ├── support/
│   └── engineering/
├── clients/
│   ├── README.md
│   └── <client-slug>/
│       ├── notes/
│       └── deliverables/
├── meetings/
│   ├── README.md
│   ├── transcripts/
│   └── recordings/          # optional — large files
├── tasks/
│   ├── README.md
│   ├── inbox/
│   └── archive/
├── incidents/
│   └── YYYY-MM-DD-<slug>.md
├── backups/
│   └── ai-ops/
│       └── YYYY-MM-DD/
├── exports/
│   ├── open-webui/
│   └── n8n/
└── templates/
    ├── sop-template.md
    ├── meeting-notes-template.md
    └── incident-template.md
```

## README template (per folder)

```markdown
# <Folder Name>
Purpose: ...
Owner: ...
Update cadence: weekly | on change
Sources: Open WebUI RAG; Counsel for comms/SOP context
```

## Mapping to executives (Brainiac 7)

| Folder | Primary executive |
|--------|-------------------|
| sops/, knowledge/ | Counsel |
| clients/, meetings/ | Counsel / Operator |
| incidents/ | Oracle (review) + human |
| tasks/ | Operator |
| templates/ | Operator (filing) |

## Windows sync script

`scripts/sync-nas-knowledge.ps1` mirrors `Z:\knowledge` and `Z:\sops` to local ingest folder.
