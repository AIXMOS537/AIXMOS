# AIX AI Command System Implementation

This implementation provides a local CLI for working with prompt templates and importing Airtable CSV templates.

## Files

- `aix_operator.py` - Loads structured prompt templates from `prompts/`, runs them with OpenAI, and imports Airtable CSV templates into a base.
- `IMPLEMENTATION.md` - Usage guide.

## Python On This Machine

If `python` is not available on PATH, use the bundled Codex runtime:

```powershell
& 'C:\Users\taha1\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' aix_operator.py list
```

## Usage

### Prompt operations

1. List available prompts:
   ```bash
   python aix_operator.py list
   ```

2. Show a prompt template:
   ```bash
   python aix_operator.py show morning
   ```

3. Run a prompt against OpenAI:
   ```bash
   OPENAI_API_KEY=your_key python aix_operator.py run morning
   ```

4. Add extra context or notes:
   ```bash
   python aix_operator.py run daily_money_check --data "Here is my current bill summary..."
   ```

5. Read extra context from a file:
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

### Airtable template operations

1. List available Airtable CSV templates:
   ```bash
   python aix_operator.py airtable list-templates
   ```

2. Preview a template:
   ```bash
   python aix_operator.py airtable show-template --template Bills
   ```

3. Import one CSV template into Airtable:
   ```bash
   AIRTABLE_API_KEY=your_key AIRTABLE_BASE_ID=your_base_id python aix_operator.py airtable import-template --template Bills
   ```

4. Sync all CSV templates into Airtable:
   ```bash
   AIRTABLE_API_KEY=your_key AIRTABLE_BASE_ID=your_base_id python aix_operator.py airtable sync-templates
   ```

5. Import into a different table name:
   ```bash
   python aix_operator.py airtable import-template --template Bills --table "Business Bills"
   ```

### Airtable live data fetch

1. Fetch rows from an Airtable table:
   ```bash
   AIRTABLE_API_KEY=your_key AIRTABLE_BASE_ID=your_base_id python aix_operator.py airtable get-table --table "Vehicles"
   ```

### Supabase live data

1. Fetch rows from a Supabase table:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co SUPABASE_KEY=your_key python aix_operator.py supabase fetch-table --table rentals
   ```

### Vercel endpoint calls

1. Call a Vercel endpoint:
   ```bash
   python aix_operator.py vercel call-endpoint --endpoint https://your-vercel-app.vercel.app/api/status
   ```

2. Call a Vercel endpoint with POST JSON:
   ```bash
   python aix_operator.py vercel call-endpoint --endpoint https://your-vercel-app.vercel.app/api/command --http-method POST --body '{"action":"status"}'
   ```

### Combined snapshot

1. Pull a current snapshot from Airtable, Supabase, and Vercel for TMMT:
   ```bash
   AIRTABLE_API_KEY=your_key AIRTABLE_BASE_ID=your_base_id \
   SUPABASE_URL=https://your-project.supabase.co SUPABASE_KEY=your_key \
   OPENAI_API_KEY=your_openai_key \
   python aix_operator.py snapshot \
   --airtable-tables "Vehicles,Bookings,Team_Tasks,Employees" \
   --supabase-tables "rentals,staff,vendors" \
   --vercel-endpoints "https://your-vercel-app.vercel.app/api/status" \
   --prompt-name tmmt_command_center_snapshot
   ```

2. Use the dedicated TMMT command center prompt:
   - `tmmt_command_center_snapshot`

This prints either a summary from OpenAI or the raw snapshot data when no OpenAI key is present.

### Notes

- `OPENAI_API_KEY` is used for prompt execution.
- `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` are used for Airtable import commands.
- The CLI is intentionally simple so it can support daily operating flow and money command center setup.
