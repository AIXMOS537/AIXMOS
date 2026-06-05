# AIX AI Command System

**Deploying for a team?** Start with `TEAM_DEPLOY.md`.

Open these in order:

1. `START_HERE.md`
2. `FIRST_72_HOURS.md`
3. `TMMT_MONTH_AWAY_PLAN.md`
4. `MONEY_COMMAND_CENTER.md`
5. `TMMT_OPERATING_SYSTEM.md`
6. `DEVICE_SETUP_CHECKLIST.md`
7. `prompts/MASTER_OPERATOR_PROMPT.md`

**Already have TMMT on Airtable + Supabase + Vercel?** See `INTEGRATION.md` — connect your existing base (no CSV import required).

**TMMT Rentals app** (Next.js, deployed on Vercel): lives in the private repo `AIXMOS537/TMMT`. The earlier `tmmt-os` prototype was removed — see `../archive/TMMT_OS_ARCHIVE_NOTE.md`.

**Daily routine:** `ONE_PAGE_START.md` → run `./scripts/tmmt-day` each morning.

Import the CSV files in `airtable_templates` into Airtable only if you are creating a **new** money command center base.

For TMMT coverage while you are away, import:

- `Leads_Deals.csv`
- `Team_Tasks.csv`
- `Employees.csv`
- `Training_Progress.csv`
- `Decision_Log.csv`

Use the prompts daily with ChatGPT or Claude.

## Local CLI

A local helper script is available to run prompt templates, import Airtable CSV templates, and connect live data from Airtable, Supabase, and Vercel.

- `python aix_operator.py list`
- `python aix_operator.py show morning`
- `OPENAI_API_KEY=... python aix_operator.py run master`
- `AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... python aix_operator.py airtable sync-templates`
- `AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... python aix_operator.py airtable get-table --table "Vehicles"`
- `SUPABASE_URL=... SUPABASE_KEY=... python aix_operator.py supabase fetch-table --table rentals`
- `python aix_operator.py vercel call-endpoint --endpoint https://your-vercel-app.vercel.app/api/status`
- `OPENAI_API_KEY=... python aix_operator.py snapshot --airtable-tables "Vehicles,Bookings" --supabase-tables "rentals,staff" --vercel-endpoints "https://your-vercel-app.vercel.app/api/status" --prompt-name car_rental_snapshot`
- `OPENAI_API_KEY=... python aix_operator.py snapshot --airtable-tables "Vehicles,Bookings,Team_Tasks,Employees" --supabase-tables "rentals,staff,vendors" --vercel-endpoints "https://your-vercel-app.vercel.app/api/status" --prompt-name tmmt_command_center_snapshot`
- `AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... python aix_operator.py dealership get-partners`
- `AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... python aix_operator.py dealership get-shared-lot`
- `AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... python aix_operator.py dealership get-fleet --table "Dealership Fleets"`
- `OPENAI_API_KEY=... AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... python aix_operator.py dealership snapshot --airtable-tables "Dealership Partners,Shared Lot Inventory,Dealership Fleets" --prompt-name dealership_daily_snapshot`

## Backend API Skeleton

A basic FastAPI backend has been added at `backend/api.py`. It exposes endpoints for:

- `GET /` — status check
- `GET /prompts` — list available prompts
- `GET /prompts/{prompt_name}` — retrieve a prompt template
- `GET /dealership/partners` — fetch Airtable Dealership Partners
- `GET /dealership/shared-lot` — fetch Airtable Shared Lot Inventory
- `GET /dealership/fleet?table=...` — fetch a fleet or related table
- `POST /snapshot` — run a snapshot summary from provided sources

## MacBook / Cursor / Deploy

**Quick setup (Mac):**

```bash
chmod +x scripts/*.sh scripts/aix
./scripts/setup-mac.sh
# edit .env, then:
./scripts/aix list
./scripts/aix airtable sync-templates
```

**Windows:** run `scripts/setup-windows.ps1`, then `python aix_operator.py list`.

**Team rollout:** see `TEAM_DEPLOY.md`.

**Local API:**

```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

**Vercel (shared API for the team):**

```bash
vercel login
vercel
```

Set `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `SUPABASE_URL`, `SUPABASE_KEY`, `VERCEL_APP_URL`, and optional `OPENAI_API_KEY` / `COMMAND_API_SECRET` in the Vercel project environment. Entrypoint: `api/index.py`. See `INTEGRATION.md` for wiring into your existing app.
