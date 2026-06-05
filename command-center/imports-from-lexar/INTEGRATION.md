# TMMT integration — Airtable + Supabase + your Vercel app

Connect the command system to **your existing TMMT Airtable base**, **Supabase project**, and **hosted Vercel app** without importing CSV templates into a new base.

## Your TMMT Airtable base (configured)

| Item | Value |
|------|--------|
| Base ID | `appcenWUju039rD7b` |
| Base URL | https://airtable.com/appcenWUju039rD7b |
| Table you linked | `tbl4gndUYeiOUWYRR` (first in snapshot list) |
| View | `viwuJ5HJDh6RoplEb` |

Airtable’s API accepts **table IDs** (like `tbl4gndUYeiOUWYRR`) or table names. After you add `AIRTABLE_API_KEY`, run `./scripts/aix integrate discover-airtable` to see human-readable names and fix `config/tmmt_integration.json` if any guessed names are wrong.

See also `config/AIRTABLE_BASE.md` and **`integrations/TMMT_OS.md`** (your Next.js app from `tmmt-os.zip`).

## Your Supabase project (configured)

| Item | Value |
|------|--------|
| Project URL | `https://uapxakmlwnpfsftfeezx.supabase.co` |
| Dashboard | https://supabase.com/dashboard/project/uapxakmlwnpfsftfeezx |

Add `SUPABASE_KEY` (service role) in `.env` only — never commit it. Get it from **Project Settings → API → service_role**.

## Your Vercel app (configured)

| Item | Value |
|------|--------|
| App URL | https://tmmt-c919-two.vercel.app |
| Login | https://tmmt-c919-two.vercel.app/login |

**API probe (May 2026):** `/api/status`, `/api/health`, `/api/command`, and similar paths return **HTTP 200 HTML** (SPA shell), not JSON. `VERCEL_SNAPSHOT_PATHS` is **empty** until you add real JSON API routes in the TMMT app. Snapshots use **Airtable + Supabase** until then.

When you add a JSON endpoint (e.g. `/api/status` returning `{ "ok": true }`):

```bash
VERCEL_SNAPSHOT_PATHS=/api/status
```

Quick check:

```bash
curl -sI https://tmmt-c919-two.vercel.app/login
curl -s https://tmmt-c919-two.vercel.app/api/status | head -c 200
```

## 1. Copy config and env

```bash
cp config/tmmt_integration.example.json config/tmmt_integration.json
cp .env.example .env
```

Edit `.env`:

| Variable | Purpose |
|----------|---------|
| `AIRTABLE_API_KEY` | Personal access token scoped to your TMMT base |
| `AIRTABLE_BASE_ID` | `appcenWUju039rD7b` (already set) |
| `SUPABASE_URL` | `https://uapxakmlwnpfsftfeezx.supabase.co` (already set) |
| `SUPABASE_KEY` | **Service role** — you add from Supabase dashboard |
| `OPENAI_API_KEY` | Morning/snapshot AI summaries |
| `VERCEL_APP_URL` | `https://tmmt-c919-two.vercel.app` (already set) |
| `VERCEL_SNAPSHOT_PATHS` | Only JSON API paths (optional until you add routes) |
| `COMMAND_API_SECRET` | Optional — required header for production API |

Optional overrides (skip editing JSON if you prefer env only):

```bash
AIRTABLE_SNAPSHOT_TABLES=Leads Deals,Team Tasks,Employees,Vehicles,Bookings
SUPABASE_SNAPSHOT_TABLES=rentals,staff,vendors,bookings
```

## 2. Match your real table names

List tables in your TMMT Airtable base:

```bash
./scripts/aix integrate discover-airtable
```

Update `config/tmmt_integration.json` → `airtable.snapshot_tables` so names match **exactly** (spaces and casing matter).

Probe connectivity:

```bash
./scripts/aix integrate status --probe
```

## 3. Local command center snapshot

Raw data from all three systems:

```bash
./scripts/aix integrate tmmt-snapshot
```

With AI briefing:

```bash
# OPENAI_API_KEY in .env
./scripts/aix integrate tmmt-snapshot --prompt-name tmmt_command_center_snapshot
```

Morning check with live data:

```bash
curl -s -X POST http://localhost:8000/command/run \
  -H "Content-Type: application/json" \
  -H "X-Command-Secret: $COMMAND_API_SECRET" \
  -d '{"prompt_name":"morning_command","include_snapshot":true}'
```

## 4. API (local or Vercel)

```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --reload --port 8000
```

| Endpoint | Description |
|----------|-------------|
| `GET /integrations/status` | Config + credential flags (+ `?probe=true`) |
| `GET /integrations/discover/airtable` | Table names in your base |
| `GET /airtable/{table}` | Live Airtable rows |
| `GET /supabase/{table}` | Live Supabase rows |
| `POST /command/tmmt-snapshot` | Unified snapshot + optional AI summary |
| `POST /command/run` | Run morning/midday prompt with live data |

Deploy this repo to Vercel (Python `api/index.py`) **or** merge env vars into your existing project.

### Option A — Same Vercel project (Python routes alongside your app)

If your app is already on Vercel, add this repo’s `api/index.py` and `vercel.json` routes, or copy `backend/` + `aix_operator.py` + `prompts/` into the project root and set the same environment variables in the Vercel dashboard.

### Option B — Keep your Next.js app; proxy to the command API

Deploy this command API (subdomain or `/api/command` on a second Vercel project). In your existing app, add a server route that forwards requests — see `integrations/nextjs-command-proxy.example.ts`.

Set in your Next.js app:

```bash
AIX_COMMAND_API_URL=https://your-command-api.vercel.app
COMMAND_API_SECRET=same-secret-on-both-sides
```

Call from your dashboard:

```ts
const res = await fetch("/api/command/tmmt-snapshot", { method: "POST" });
const { summary, snapshot } = await res.json();
```

### Option C — Call from Zapier / cron

`POST https://YOUR_COMMAND_API.vercel.app/command/tmmt-snapshot`  
Header: `X-Command-Secret: …`  
Body: `{}` or override tables:

```json
{
  "airtable_tables": ["Leads Deals", "Team Tasks"],
  "supabase_tables": ["rentals"],
  "summarize": true
}
```

## 5. Vercel environment checklist

In **your existing Vercel project** (or the command API project), set:

- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY` (service role)
- `OPENAI_API_KEY`
- `VERCEL_APP_URL` → `https://tmmt-c919-two.vercel.app`
- `VERCEL_SNAPSHOT_PATHS` → only if you have JSON API routes (see probe note above)
- `COMMAND_API_SECRET` (recommended)

Redeploy after saving env vars.

## 6. Supabase notes

- Server-side snapshots should use the **service role** key in Vercel only.
- If a table returns empty or 401, check RLS policies — the service role bypasses RLS; anon keys may not.
- Align `supabase.snapshot_tables` in config with your real public table names.

## 7. Do not sync CSV templates to TMMT

With an existing base, **do not** run `airtable sync-templates` unless you intend to add new tables. Use `discover-airtable` and config only.
