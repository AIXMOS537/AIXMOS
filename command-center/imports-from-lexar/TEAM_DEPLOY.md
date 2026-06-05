# Team deployment — AIX AI Command System

Roll out the operating system (prompts, Airtable, CLI, optional API) so everyone works from the same playbook.

## What you are deploying

| Layer | What it is | Who needs it |
|-------|------------|--------------|
| **Docs & prompts** | `START_HERE.md`, `prompts/`, `00_COMMAND_CENTER/`, training | Everyone |
| **Airtable base** | Single source of truth for leads, tasks, money | Everyone (role-based views) |
| **CLI** (`aix_operator.py` / `./scripts/aix`) | Pull data, run prompts, snapshots | Leads + owner (optional for ICs) |
| **API** (`backend/api.py` on Vercel) | Shared read/snapshot endpoints | Optional — tech lead or automations |

## Phase 1 — Owner (you) — one time

### 1. Airtable command center

1. Create one Airtable base (or use your existing TMMT base).
2. Create a **personal access token** at [airtable.com/create/tokens](https://airtable.com/create/tokens) with read/write on that base only.
3. Copy the base ID from the URL (`appXXXXXXXX`).

### 2. Import templates

From this folder (with `.env` filled in):

```bash
chmod +x scripts/*.sh scripts/aix
./scripts/setup-mac.sh
# edit .env
./scripts/aix airtable sync-templates
```

Import order if doing manually: money tables first (`Bills`, cards, etc.), then TMMT (`Leads_Deals`, `Team_Tasks`, `Employees`, `Training_Progress`, `Decision_Log`). See `README.md`.

### 3. Assign coverage roles (if owner may be away)

Per `TMMT_MONTH_AWAY_PLAN.md` and `03_TRAINING_ACADEMY/role_index.md`:

- Acting Manager
- Sales Lead
- Operations Lead
- Money Lead
- Admin Recorder

Add each person to the **Employees** table with their role.

### 4. Secrets (never in git or chat)

| Secret | Who holds it |
|--------|----------------|
| `AIRTABLE_API_KEY` | Owner + Admin Recorder (+ API host env) |
| `AIRTABLE_BASE_ID` | Everyone (not secret — same base) |
| `OPENAI_API_KEY` | Owner + managers running AI prompts (optional per person) |
| `SUPABASE_*` | Only if you use Supabase live data |

Use a password manager or your host’s env vars — not Slack, not email.

---

## Phase 2 — Distribute the repo to the team

Pick **one** primary distribution method:

### Option A — Git (recommended for teams)

1. Initialize or push this folder to GitHub/GitLab (private repo).
2. Add `.env` to `.gitignore` (already listed).
3. Invite team with read access; managers with write if they maintain prompts.

### Option B — Flash drive / shared drive

1. Copy the whole `AIX_AI_COMMAND_SYSTEM` folder to the drive.
2. Each Mac: open the folder in Cursor → run `./scripts/setup-mac.sh`.
3. Re-sync when you update SOPs (weekly or after changes).

### Option C — Zip + onboarding doc

Zip the repo (no `.env`), send link, point people to **First 72 hours** below.

---

## Phase 3 — Each team member setup

### Mac (Cursor or Terminal)

```bash
cd /path/to/AIX_AI_COMMAND_SYSTEM
chmod +x scripts/*.sh scripts/aix
./scripts/setup-mac.sh
```

Edit `.env` only if they are approved to use the CLI with live keys (usually managers).

Daily:

```bash
./scripts/aix show morning
./scripts/aix run morning          # needs OPENAI_API_KEY
```

### Windows

```powershell
cd D:\AIX_AI_COMMAND_SYSTEM
.\scripts\setup-windows.ps1
# edit .env
python aix_operator.py show morning
```

### Phone (all roles)

Follow `DEVICE_SETUP_CHECKLIST.md`: pin ChatGPT/Claude, Airtable, bank apps; use voice notes and same-day Airtable entry for money/customer issues.

---

## Phase 4 — Role-based access

| Role | Airtable | AI (ChatGPT/Claude) | CLI / API keys |
|------|----------|---------------------|----------------|
| Acting Manager | Full base | Master operator + away prompts | Yes — morning/midday/weekly |
| Sales Lead | Leads, pipeline views | Sales + follow-up prompts | Optional |
| Operations Lead | Tasks, fulfillment | Operations prompts | Optional |
| Money Lead | Bills, cards, leaks | `daily_money_check`, weekly money | Yes for money snapshots |
| Admin Recorder | Edit all tables | Minimal — data entry focus | Airtable token only |
| Frontline IC | Their tasks view only | Role checklist in academy | No CLI keys |

**Paste once per person in ChatGPT/Claude:** `prompts/MASTER_OPERATOR_PROMPT.md`

**Away coverage:** `prompts/TMMT_MONTH_AWAY_PROMPTS.md` and `away_*` CLI prompts.

---

## Phase 5 — Optional: host the API (Vercel)

Shared API so automations (Zapier) or managers can hit one URL without local Python.

### Deploy

1. Install Vercel CLI: `npm i -g vercel`
2. From project root:

```bash
vercel login
vercel
```

3. In the Vercel project **Settings → Environment Variables**, add:

- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- `OPENAI_API_KEY` (optional, for `POST /snapshot` summaries)
- `SUPABASE_URL` / `SUPABASE_KEY` (optional)

4. Redeploy. Test:

```bash
curl https://YOUR_PROJECT.vercel.app/
curl https://YOUR_PROJECT.vercel.app/prompts
```

### Endpoints

- `GET /` — health
- `GET /prompts` — list prompt templates
- `GET /prompts/{name}` — fetch one prompt
- `GET /dealership/partners` — Airtable (needs env keys)
- `POST /snapshot` — JSON body: `airtable_tables`, `supabase_tables`, `vercel_endpoints`, `prompt_name`

Local API:

```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

---

## Phase 6 — First 72 hours (team)

Follow `FIRST_72_HOURS.md` as a team schedule:

| Day | Team focus |
|-----|------------|
| **Day 1** | Money visibility — everyone with money touch enters bills/cards/leaks |
| **Day 2** | Three AI check-ins (morning / midday / evening) using shared prompts |
| **Day 3** | Stale lead, unpaid, overdue task, bill-due views + one alert owner |

If preparing for owner absence: complete the extra checklist in `FIRST_72_HOURS.md` (acting roles, escalation rules, one dry-run day).

---

## Phase 7 — Ongoing rhythm

| Cadence | Action |
|---------|--------|
| Daily | Morning command → assign tasks → midday rescue → end-of-day closeout |
| Weekly | Weekly money routine (`sops/WEEKLY_MONEY_ROUTINE.md`) + owner update template |
| Monthly | Review `AUTOMATION_MAP.md`, fix leaks, update SOPs in `04_OPERATIONS_MANUAL/` |

Train using `03_TRAINING_ACADEMY/30_day_onboarding.md` per hire.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `python3 not found` | `brew install python` (Mac) or run `setup-windows.ps1` |
| Airtable 401/403 | Regenerate token; confirm base scope |
| Empty `get-table` | Table name must match Airtable exactly (e.g. `"Vehicles"`) |
| Snapshot returns raw JSON only | Set `OPENAI_API_KEY` in `.env` or Vercel env |
| Vercel 500 on `/snapshot` | Check env vars; confirm table names exist in base |

---

## Checklist — ready for team?

- [ ] Airtable base live with templates imported
- [ ] Roles assigned in Employees table
- [ ] Escalation rules reviewed (`00_COMMAND_CENTER/ESCALATION_RULES.md`)
- [ ] Repo or drive distributed; `.env` **not** in repo
- [ ] Managers ran `./scripts/aix list` successfully
- [ ] Everyone has phone + desktop checklist from `DEVICE_SETUP_CHECKLIST.md`
- [ ] (Optional) Vercel API deployed with env vars
- [ ] One full dry-run day without owner intervention (if month-away plan applies)
