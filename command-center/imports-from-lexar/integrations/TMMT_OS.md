# TMMT OS ↔ AIX AI Command System

**TMMT OS** is the operational web app you deploy to Vercel (`https://tmmt-c919-two.vercel.app`).  
**AIX AI Command System** is the daily operator layer (prompts, CLI, snapshots, money/TMMT playbooks).

They share the same backends but serve different jobs.

| Layer | Repo / path | Role |
|-------|-------------|------|
| **TMMT OS** | `integrations/tmmt-os/tmmt-os/` (from `tmmt-os.zip`) | Run the business: cases, vendors, intake, portals |
| **Command system** | `/Volumes/LEXAR/AIX_AI_COMMAND_SYSTEM` | AI check-ins, cross-system snapshots, team SOPs |

---

## What TMMT OS is

Next.js 14 **workflow engine** for TMMT Auto Services / TMMT Rentals / Project AIXMOS.

- Every customer request becomes a **case** with a typed pipeline (intake → review → vendor work → approval → close).
- **Supabase** is the system of record (Postgres + Auth + RLS + Storage).
- **Airtable** is linked via `airtable_id` fields and planned sync (webhook + pull script — not fully built yet).
- **Three role-gated portals** + public intake:
  - `/internal/*` — admin + internal team
  - `/vendor/*` — vendors (RLS-scoped jobs)
  - `/investor/*` — investors
  - `/intake` — public form
  - `/login` — Supabase auth (matches your Vercel URL)

### Tech stack

- Next.js 14 App Router, TypeScript, Server Components + Server Actions
- `@supabase/ssr` + `@supabase/supabase-js`
- Tailwind + shadcn-style UI, Zod
- Deploy: Vercel

### Supabase tables (from `0001_init.sql`)

Use these names in command-system snapshots — **not** the old guessed list (`rentals`, `staff`, etc.):

| Table | Purpose |
|-------|---------|
| `organizations` | TMMT / investor / vendor orgs |
| `profiles` | Users + roles (`admin`, `internal_team`, `vendor`, `investor`, `customer`) |
| `vendors` | Vendor companies |
| `customer_intake_forms` | Raw intake (web, Airtable, GHL, Zapier) |
| `cases` | Main workflow records |
| `tasks` | Internal tasks on cases |
| `vendor_jobs` | Work assigned to vendors |
| `approvals` | Approval queue |
| `activity_log` | Audit trail |
| `notifications` | In-app notifications |
| `clickup_tasks` | ClickUp linkage (placeholder) |
| `files` / storage | Vendor uploads |

Many rows store `airtable_id` for future bidirectional sync.

### API routes (today)

| Route | Auth | Purpose |
|-------|------|---------|
| `POST /api/intake` | `X-Intake-Secret` header | Webhook: Airtable / GHL / Zapier → creates intake + case |
| `/auth/callback`, `/auth/signout` | Session | Supabase auth |
| *(planned)* `/api/airtable/sync`, `/api/clickup/webhook` | — | Mentioned in `CURSOR_BOOTSTRAP.md`, not in zip yet |

**`GET /api/status`** returns JSON (`{ ok, service, timestamp }`) — used by command-system snapshots. Redeploy TMMT OS after pulling this change.

---

## How it connects to your stack

```
┌─────────────────────┐     webhook      ┌──────────────────┐
│  Airtable (TMMT)    │ ───────────────► │  TMMT OS         │
│  appcenWUju039rD7b  │   POST /api/intake│  Vercel app      │
└─────────────────────┘                   │  tmmt-c919-two   │
         ▲                                └────────┬─────────┘
         │  (planned sync)                          │
         │                                          │ service role
┌────────┴────────────┐                   ┌─────────▼─────────┐
│  AIX Command CLI/API │ ◄── snapshots ────│  Supabase         │
│  prompts, morning    │                   │  uapxakmlwnpfsft…  │
└─────────────────────┘                   └───────────────────┘
```

### Env alignment

| TMMT OS (`.env.local`) | Command system (`.env`) |
|------------------------|-------------------------|
| `NEXT_PUBLIC_SUPABASE_URL` | `SUPABASE_URL` (same URL) |
| `SUPABASE_SERVICE_ROLE_KEY` | `SUPABASE_KEY` (service role for snapshots) |
| `AIRTABLE_API_KEY` | `AIRTABLE_API_KEY` |
| `AIRTABLE_BASE_ID` | `AIRTABLE_BASE_ID` (`appcenWUju039rD7b`) |
| `INTAKE_WEBHOOK_SECRET` | Use in Zapier when calling TMMT OS |

Command system does **not** need `NEXT_PUBLIC_*` unless you embed the Next app.

---

## Recommended merge path

### 1. Treat TMMT OS as the Vercel source of truth

- Develop in `integrations/tmmt-os/tmmt-os/` or move the folder to its own git repo linked to `tmmt-c919-two.vercel.app`.
- Apply `supabase/migrations/0001_init.sql` to project `uapxakmlwnpfsftfeezx` if not already applied.

### 2. Fix command-system Supabase snapshot tables

Update `config/tmmt_integration.json` → `supabase.snapshot_tables` to real TMMT OS tables, e.g.:

```json
"cases", "vendor_jobs", "vendors", "customer_intake_forms", "tasks"
```

Then with `SUPABASE_KEY` set:

```bash
./scripts/aix integrate status --probe
./scripts/aix integrate tmmt-snapshot
```

### 3. Wire Airtable → TMMT OS intake

Zapier / Airtable automation:

- **POST** `https://tmmt-c919-two.vercel.app/api/intake`
- Header: `X-Intake-Secret: <INTAKE_WEBHOOK_SECRET from Vercel>`
- Body: `customer_name`, `subject`, `request_type`, `airtable_id`, `source: "airtable"`

Command system can **read** Airtable for morning briefings; TMMT OS **writes** operational cases into Supabase.

### 4. Add a JSON health route (optional, for snapshots)

In TMMT OS, add e.g. `src/app/api/status/route.ts`:

```ts
export async function GET() {
  return Response.json({ ok: true, service: "tmmt-os" });
}
```

Then in command system `.env`:

```bash
VERCEL_SNAPSHOT_PATHS=/api/status
```

### 5. Single Vercel project vs two

| Approach | When |
|----------|------|
| **One project** | TMMT OS repo root = Vercel root; add Python `api/` from command system only if you need shared deployment |
| **Two projects** | TMMT OS on `tmmt-c919-two`; command API on a subdomain; Next.js proxy via `integrations/nextjs-command-proxy.example.ts` |

Default: keep **TMMT OS** as the main app; run command API locally or on a small second Vercel project for AI/cron.

---

## Source location

Portable source: `TMMT MANAGEMENT/tmmt-os.zip` on this drive (Lexar root)  
Workspace copy: `integrations/tmmt-os/tmmt-os/` (relative to `AIX_AI_COMMAND_SYSTEM/`)

Do not commit `.env.local` from TMMT OS. Re-copy the zip to refresh the integration folder if the app is updated elsewhere.

---

## Next build items (from TMMT OS docs)

1. Airtable bidirectional sync (`/api/airtable/webhook` + pull script)
2. ClickUp on vendor assignment
3. GHL notifications on status change
4. Customer portal `(customer)` route group

Command system prompts (`tmmt_command_center_snapshot`, `away_*`, money checks) stay in `prompts/` and pull live data from Airtable + Supabase once keys are set.
