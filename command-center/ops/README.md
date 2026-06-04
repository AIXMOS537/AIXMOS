# Ops stacks (Command Center)

| Folder | Purpose | Start |
|--------|---------|--------|
| `moose-stack/` | Multi-agent brain (`brain.js`, `moose.js`) | `./start-moose-mac.sh` |
| `chummo-stack/` | CHUMMO messaging + local portal | `bash start-mac.sh` or `node serve.js` |

## CHUMMO stack

```bash
cd ~/Desktop/AIX_Command_Center/ops/chummo-stack
npm install
bash start-mac.sh          # terminal CHUMMO agent (one lead at a time)
node chummo-run.js --source data/leads.example.csv --dry-run   # batch: all pipelines
node chummo-run.js --source /path/to/Leads_Deals.csv --limit 50  # batch: your export
node serve.js              # http://localhost:3000 + /portal
```

**Batch pipelines:** see `ops/chummo-stack/CHUMMO_PIPELINE.md`

Portal is a **placeholder** (no login). Add Supabase Auth before distributing.

**Docs:** `project_aixmos_chummo.md` in `../docs/AIXMOS/`

## MOOSE stack

```bash
cd ~/Desktop/AIX_Command_Center/ops/moose-stack
node brain.js
```
