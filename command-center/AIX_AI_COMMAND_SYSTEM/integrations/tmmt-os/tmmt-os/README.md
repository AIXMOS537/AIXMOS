# TMMT OS

The business operating system for TMMT Auto Services / TMMT Rentals / Project AIXMOS.

A Next.js 14 + Supabase workflow engine. Every customer request becomes a **case**.
Cases move through a typed pipeline (intake → review → vendor work → approval → close).
Three role-gated portals share one schema:

- `/internal/*` — Internal Team (admin + internal_team)
- `/vendor/*`   — Outside Vendor (vendor)
- `/investor/*` — Investor (investor)

## Stack

- Next.js 14 App Router (Server Components + Server Actions)
- Supabase (Postgres + Auth + Storage + RLS)
- Tailwind + shadcn-style UI primitives
- Zod for input validation
- Deploys clean on Vercel

## First-run checklist

1. **Install**
   ```bash
   cd tmmt-os
   npm install
   cp .env.example .env.local
   ```

2. **Create a Supabase project** at https://supabase.com, copy these into `.env.local`:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY` (Project Settings → API → service_role secret)
   - `INTAKE_WEBHOOK_SECRET` — any random string; used by `/api/intake`

3. **Apply the schema.** Either:
   - Paste `supabase/migrations/0001_init.sql` into the Supabase SQL Editor and run, **or**
   - Use the Supabase CLI: `supabase db push`

4. **Promote your first admin.** Sign up at `/login` (magic link or password), then in
   Supabase SQL Editor:
   ```sql
   update public.profiles set role = 'admin' where email = 'you@tmmt.com';
   ```

5. **Run the dev server**
   ```bash
   npm run dev
   ```

   Then visit:
   - http://localhost:3000/intake — public intake form
   - http://localhost:3000/internal/dashboard — internal portal (after admin promotion)
   - http://localhost:3000/vendor/dashboard — vendor portal (after creating a vendor)
   - http://localhost:3000/investor/dashboard — investor portal

## Onboarding a vendor

1. They sign up at `/login` like any user.
2. In Supabase:
   ```sql
   update public.profiles set role = 'vendor' where email = 'vendor@example.com';
   insert into public.vendors (profile_id, company_name, services, email)
   values ('<their profile id>', 'Ace Mobile Detail', '{detail,inspection}', 'vendor@example.com');
   ```
3. From the internal case detail page, assign them a job. They'll see it in `/vendor/dashboard`.

## External intake webhook

For Airtable / GoHighLevel / Zapier / n8n to file a case:

```bash
curl -X POST https://YOUR-APP/api/intake \
  -H "Content-Type: application/json" \
  -H "X-Intake-Secret: $INTAKE_WEBHOOK_SECRET" \
  -d '{
    "customer_name": "Jane Doe",
    "customer_email": "jane@example.com",
    "request_type": "tow",
    "subject": "Flat on the 405",
    "details": "Tire blew near La Cienega exit",
    "source": "ghl",
    "airtable_id": "recXXXXXX"
  }'
```

## Architecture map

```
src/
├── app/
│   ├── page.tsx                    Landing page
│   ├── intake/                     Public intake form
│   ├── api/intake/                 Public webhook for Airtable/GHL/Zapier
│   ├── login/                      Supabase magic-link + password
│   ├── auth/{callback,signout}/    Session lifecycle
│   ├── (internal)/internal/        Admin + internal_team portal
│   ├── (vendor)/vendor/            Vendor portal (RLS-scoped)
│   └── (investor)/investor/        Investor portal (RLS-scoped)
├── components/
│   ├── ui/                         shadcn-style primitives
│   ├── case-status-badge.tsx
│   ├── job-status-badge.tsx
│   └── portal-shell.tsx
├── lib/
│   ├── supabase/{server,client,middleware,service}.ts
│   ├── workflow/statuses.ts        Typed enums + transitions
│   ├── workflow/engine.ts          advanceCase / assignVendor / setJobStatus
│   ├── auth.ts                     getCurrentUser / requireRole
│   └── utils.ts
├── middleware.ts                   Role-gates /internal /vendor /investor
└── types/database.ts               Placeholder for generated types
```

## The workflow engine

`src/lib/workflow/statuses.ts` is the **single source of truth** for the pipeline
vocabulary — keep it in sync with `supabase/migrations/0001_init.sql`.

`src/lib/workflow/engine.ts` is intentionally thin. Each helper is a Server
Action that updates the DB, writes to `activity_logs`, optionally inserts a
`notifications` row, and revalidates the affected paths. Future automations
(SMS via GHL, ClickUp task creation, Slack pings) plug in here.

```ts
import { advanceCase, assignCaseToVendor, setVendorJobStatus } from "@/lib/workflow/engine";

await advanceCase(caseId, "internal_review", "ready for triage");
await assignCaseToVendor({ caseId, vendorId, title: "Brake inspection", offeredPrice: 250 });
await setVendorJobStatus(jobId, "accepted");
```

## RLS in plain English

| Role            | Can read                                              | Can write                                        |
|-----------------|-------------------------------------------------------|--------------------------------------------------|
| `admin`         | everything                                            | everything                                       |
| `internal_team` | everything (no destructive admin)                     | cases, tasks, vendor_jobs, approvals, vendors    |
| `vendor`        | only `vendor_jobs.vendor_id = me`; case/files for those | own job status, own job_updates, own files       |
| `investor`      | own `investor_account`; published updates in own org  | nothing                                          |
| `customer`      | nothing (no portal yet — they get email/SMS via GHL)  | inserts into `customer_intake_forms` (anonymous) |

All policies are in `0001_init.sql`. The DB enforces them — even if the Next layer
forgets a check, vendors cannot see other vendors' work.

## Storage

One private bucket: `vendor-files`. Path convention is `{vendor_job_id}/{filename}`.
Storage policies use the first path segment to match against the vendor's jobs.

## Where to go next

- Wire ClickUp: in `engine.ts → assignCaseToVendor`, POST to the ClickUp API
  and save the returned `task_id` / `url` into `cases.clickup_task_id` / `clickup_task_url`
  and `clickup_tasks`.
- Wire Airtable sync: read/write `cases.airtable_id`, and add a route
  `/api/airtable/sync` similar to `/api/intake`.
- Wire GoHighLevel: send SMS/email on case status transitions from the engine.
- Customer portal: add a `(customer)` route group and an RLS policy on `cases`
  matching `cases.customer_email = (select email from public.profiles where id = auth.uid())`.
- Generate types: `npm run db:types` after `supabase login && supabase link`.
