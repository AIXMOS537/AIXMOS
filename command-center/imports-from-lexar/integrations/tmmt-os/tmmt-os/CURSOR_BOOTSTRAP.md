# Cursor bootstrap prompt — paste into Cursor's chat after opening this folder

Copy the block below into Cursor (Cmd+L) as your first message. It gives Cursor
the full mental model so it stops re-deriving the design every turn.

---

You're working on **TMMT OS**, a Next.js 14 + Supabase business operating system
for TMMT Auto Services. The project is already scaffolded — your job is to
extend it, not rebuild it. Read `README.md` and `src/lib/workflow/statuses.ts`
before suggesting anything.

## Stack (already wired)
- Next.js 14 App Router, TypeScript, Server Components + Server Actions
- Supabase (Postgres + Auth + Storage + RLS) via `@supabase/ssr`
- Tailwind + shadcn-style primitives in `src/components/ui/`
- Zod for input validation

## What exists
- **Schema**: `supabase/migrations/0001_init.sql` — every table, enum, RLS policy,
  trigger, and storage bucket for the workflow engine.
- **Workflow engine**: `src/lib/workflow/{statuses,engine}.ts` — typed enums,
  forward transitions, and the server-side `advanceCase` / `assignCaseToVendor` /
  `setVendorJobStatus` / `recordVendorFile` helpers.
- **Three portals** (route groups, role-gated by `middleware.ts`):
  - `(internal)` → `/internal/{dashboard,cases,cases/[id],vendors}`
  - `(vendor)`   → `/vendor/{dashboard,jobs/[id]}`
  - `(investor)` → `/investor/dashboard`
- **Public intake**: `/intake` form + `/api/intake` webhook (Airtable / GHL / Zapier).

## Rules of the road
1. **Vocabulary lives in `statuses.ts`.** Never hard-code a case_status or
   vendor_job_status string anywhere else. If you need a new state, add it
   there *and* to the matching enum in `supabase/migrations/0001_init.sql` via
   a new `000N_*.sql` migration — never edit `0001_init.sql` after it's been
   applied.
2. **All mutations go through `src/lib/workflow/engine.ts`** so we get the
   activity_log + notification + revalidatePath behavior for free.
3. **Server-side data fetching uses `createSupabaseServerClient()`** from
   `src/lib/supabase/server.ts`. It honors RLS. Only `service.ts` bypasses
   RLS and that's reserved for anonymous intake + admin scripts.
4. **Vendors can only see their own jobs.** This is enforced by RLS using
   `public.current_vendor_id()`. Don't write app-layer filters as the
   primary guard — they'd be a bypass risk if forgotten.
5. **Status changes ripple.** When `vendor_jobs.status` moves to
   `in_progress` / `pending_review` / `completed`, the engine mirrors that
   into `cases.status` via `caseStatusForVendorJob()`. Keep this mapping
   consistent if you add states.
6. **Storage path convention**: `vendor-files/{vendor_job_id}/{filename}`.
   Storage policies use the first path segment for vendor ownership checks
   — never break that convention.

## Suggested next deliverables (pick whichever the user asks for)
- ClickUp integration: in `engine.ts → assignCaseToVendor`, POST a task,
  store `task_id`/`url` on `cases` + `clickup_tasks`. Add a webhook
  `/api/clickup/webhook` that flips `tasks.status` on remote changes.
- Airtable sync: bidirectional via `/api/airtable/webhook` POST + a
  nightly `node scripts/airtable-pull.ts` script.
- GoHighLevel SMS/email on status transitions (subscribe inside engine
  helpers — keep them async/best-effort, never block the response).
- Customer portal `(customer)` route group with a magic-link login that
  matches `cases.customer_email`.
- Approvals UI: `/internal/approvals` listing pending rows from
  `public.approvals`; investor sees a read-only digest in their portal.
- Real-time updates: swap server-only reads for a `useEffect` that subscribes
  to `cases` and `vendor_jobs` via `supabase.channel('cases')`.
- Generated types: `supabase gen types typescript --project-id <REF> > src/types/database.ts`,
  then thread `<Database>` into the helpers in `src/lib/supabase/*`.

## Don't do
- Don't import `src/lib/supabase/service.ts` from a Client Component.
- Don't disable RLS on a table — fix the policy instead.
- Don't add columns without a new migration file.
- Don't use a default `select('*')` from a Client Component — pick columns.
