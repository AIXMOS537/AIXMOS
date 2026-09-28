# CHUMMO Pipeline Runner

Batch-process leads across pipelines: CHUMMO writes messages, MOOSE/BRAIN handle heavy cases.

## Quick start

```bash
cd ops/chummo-stack
export AI_PROVIDER=auto OLLAMA_BASE_URL=http://127.0.0.1:11434

# Plan only (no AI)
node chummo-run.js --source data/leads.example.csv --dry-run

# Run (demo file — 3 leads)
npm run run:demo

# Your export
node chummo-run.js --source /path/to/Leads_Deals.csv --limit 50
```

Outputs land in `output/runs/` as JSON + `*-review.md` for copy/paste into GHL.

## Lead sources

| Source | How |
|--------|-----|
| **CSV** | Airtable/GHL export — columns like `Leads_Deals.csv` template |
| **JSON** | `{ "leads": [ { "name", "status", "pipeline", ... } ] }` |
| **Folder** | All `.csv` / `.json` in one directory |
| **GHL API** | `--source ghl` + `GHL_API_KEY` + `GHL_LOCATION_ID` in env |

Template: `AIX_AI_COMMAND_SYSTEM/airtable_templates/Leads_Deals.csv`

## Stage → message mapping

Stages map to CHUMMO message types (SMS/email). See `lib/stage-map.js`.

Examples:
- New Lead → first outreach SMS
- Proposal Sent / Negotiation → upgrade email + **MOOSE**
- Closed Lost → re-engagement SMS
- Paid / Onboarded → welcome message

## Agent delegation

| Agent | When |
|-------|------|
| **CHUMMO** | Every processed lead |
| **MOOSE** | High value ($3,750+), proposal/negotiation stages, overdue next action, flagged notes |
| **BRAIN** | Escalations, enterprise value ($15k+), complex notes |

Disable: `--no-delegate`

## Options

```
--limit N           Max leads to process
--pipeline credit   Filter by pipeline / business line
--skip-closed       Skip closed won/lost/inactive
--dry-run           Show plan without AI
--delay 2000        Ms between calls (large models)
--no-delegate       CHUMMO only
```

## GHL live pull

```bash
export GHL_API_KEY=...
export GHL_LOCATION_ID=...
node chummo-run.js --source ghl --limit 25
```

Level A safety: review `*-review.md` before sending — nothing auto-sends to contacts.
