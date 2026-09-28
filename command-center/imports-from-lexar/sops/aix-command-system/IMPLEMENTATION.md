# AIX AI Command System

Local CLI for working with prompt templates and importing Airtable CSV templates.

## Files

- `aix_operator.py` — Loads structured prompt templates from `prompts/`, runs them with OpenAI, and imports Airtable CSV templates into a base.
- `IMPLEMENTATION.md` — This usage guide.

## Python On This Machine

If `python` is not available on PATH, use the bundled Codex runtime:

```powershell
& 'C:\Users\taha1\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' aix_operator.py list
```

## Prompt operations

List available prompts:

```bash
python aix_operator.py list
```

Show a prompt template:

```bash
python aix_operator.py show morning
```

Run a prompt against OpenAI:

```bash
# PowerShell
$env:OPENAI_API_KEY="your_key"; python aix_operator.py run morning
```

Add extra context or notes:

```bash
python aix_operator.py run daily_money_check --data "Here is my current bill summary..."
```

Read extra context from a file:

```bash
python aix_operator.py run team_delegation --data-file ./notes.txt
```

Useful TMMT month-away prompts:

```bash
python aix_operator.py show away_morning_manager
python aix_operator.py show away_midday_rescue
python aix_operator.py show away_weekly_owner_report
python aix_operator.py show sop_builder
python aix_operator.py show employee_correction
```

## Airtable template operations

List available Airtable CSV templates:

```bash
python aix_operator.py airtable list-templates
```

Preview a template:

```bash
python aix_operator.py airtable show-template --template Bills
```

Import one CSV template into Airtable:

```bash
$env:AIRTABLE_API_KEY="your_key"
$env:AIRTABLE_BASE_ID="your_base_id"
python aix_operator.py airtable import-template --template Bills
```

Sync all CSV templates into Airtable:

```bash
python aix_operator.py airtable sync-templates
```

Import into a different table name:

```bash
python aix_operator.py airtable import-template --template Bills --table "Business Bills"
```

## Airtable live data fetch

Fetch rows from an Airtable table:

```bash
python aix_operator.py airtable get-table --table "Vehicles"
```

## Supabase live data

Fetch rows from a Supabase table:

```bash
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your_key"
python aix_operator.py supabase fetch-table --table rentals
```

## Vercel endpoint calls

Call a Vercel endpoint:

```bash
python aix_operator.py vercel call-endpoint --endpoint https://your-vercel-app.vercel.app/api/status
```

Call a Vercel endpoint with POST JSON:

```bash
python aix_operator.py vercel call-endpoint --endpoint https://your-vercel-app.vercel.app/api/command --http-method POST --body '{"action":"status"}'
```

## Combined snapshot

Pull a current snapshot from Airtable, Supabase, and Vercel for TMMT:

```bash
$env:AIRTABLE_API_KEY="your_key"
$env:AIRTABLE_BASE_ID="your_base_id"
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your_key"
$env:OPENAI_API_KEY="your_openai_key"
python aix_operator.py snapshot `
  --airtable-tables "Vehicles,Bookings,Team_Tasks,Employees" `
  --supabase-tables "rentals,staff,vendors" `
  --vercel-endpoints "https://your-vercel-app.vercel.app/api/status" `
  --prompt-name tmmt_command_center_snapshot
```

Use the dedicated TMMT command center prompt: `tmmt_command_center_snapshot`

This prints either a summary from OpenAI or the raw snapshot data when no OpenAI key is present.

## Notes

- `OPENAI_API_KEY` is used for prompt execution.
- `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` are used for Airtable import and fetch commands.
- `SUPABASE_URL` and `SUPABASE_KEY` are used for Supabase fetch commands.
- Prompt templates live in `prompts/*.json` with `system`, `user`, and optional `model` / `temperature`.
- CSV templates live in `airtable_templates/*.csv`.
- The CLI uses only the Python standard library (no pip install required).
