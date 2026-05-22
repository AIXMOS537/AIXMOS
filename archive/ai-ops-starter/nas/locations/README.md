# NAS — Locations & Operators

Per-site data for the Brainiac hierarchy. **Brainiac 7** owns `hot/` and master `knowledge/`. Each location syncs **up** to 7.

```
locations/
├── README.md
├── home/                    # tier 7 (owner)
│   └── operators/
│       └── brainiac-7/
├── hq/
│   ├── operators/
│   │   ├── brainiac-6-hq/
│   │   └── brainiac-4-jane/
│   ├── exports/             # daily recaps → 7 ingests
│   └── escalations/         # needs Brainiac 7
└── wh-east/
    ├── operators/
    │   └── brainiac-5-wh-east/
    ├── exports/
    └── escalations/
```

Each `operators/<id>/` folder:

```
inbox/
tasks/
comms/drafts/
journal/
```

Init all location folders:

```powershell
.\scripts\init-nas-layout.ps1
```

Registry: `setup/operators/registry.template.yaml`
