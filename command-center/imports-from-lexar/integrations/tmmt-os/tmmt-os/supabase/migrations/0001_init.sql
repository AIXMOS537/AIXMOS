-- =============================================================================
-- TMMT OS — Initial schema
-- Workflow engine: intake -> case -> tasks -> vendor jobs -> approvals -> close
-- =============================================================================
-- This file is idempotent enough for fresh projects. For an existing DB,
-- review before applying.

create extension if not exists "pgcrypto";

-- -----------------------------------------------------------------------------
-- ENUMS
-- -----------------------------------------------------------------------------
do $$ begin
  create type public.user_role as enum (
    'admin', 'internal_team', 'investor', 'vendor', 'customer'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.case_status as enum (
    'intake_submitted',
    'initial_contact_needed',
    'initial_contact_complete',
    'internal_review',
    'task_assignment',
    'vendor_needed',
    'vendor_assigned',
    'vendor_in_progress',
    'vendor_completed',
    'internal_quality_check',
    'customer_follow_up',
    'awaiting_approval',
    'completed',
    'closed',
    'blocked'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.vendor_job_status as enum (
    'offered','accepted','declined','scheduled','in_progress',
    'pending_review','completed','rejected','paid','cancelled'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type public.request_type as enum (
    'rental_booking','rental_support','maintenance','repair','detail',
    'tow','inspection','delivery','content','consulting','other'
  );
exception when duplicate_object then null; end $$;

-- -----------------------------------------------------------------------------
-- ORGANIZATIONS
-- -----------------------------------------------------------------------------
create table if not exists public.organizations (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  kind        text not null default 'tmmt',   -- 'tmmt' | 'investor_group' | 'vendor_company'
  airtable_id text,
  created_at  timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- PROFILES — 1:1 with auth.users
-- -----------------------------------------------------------------------------
create table if not exists public.profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  email           text unique,
  full_name       text,
  phone           text,
  role            public.user_role not null default 'customer',
  organization_id uuid references public.organizations(id) on delete set null,
  airtable_id     text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- Auto-create a profile row whenever a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.email)
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- -----------------------------------------------------------------------------
-- VENDORS — a business entity that performs jobs (linked to a profile)
-- -----------------------------------------------------------------------------
create table if not exists public.vendors (
  id            uuid primary key default gen_random_uuid(),
  profile_id    uuid unique references public.profiles(id) on delete set null,
  company_name  text not null,
  contact_name  text,
  email         text,
  phone         text,
  services      text[] not null default '{}',   -- ['mechanic','detail','tow', ...]
  active        boolean not null default true,
  airtable_id   text,
  notes         text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists vendors_profile_idx on public.vendors(profile_id);

-- -----------------------------------------------------------------------------
-- CUSTOMER INTAKE FORMS — raw submissions
-- -----------------------------------------------------------------------------
create table if not exists public.customer_intake_forms (
  id             uuid primary key default gen_random_uuid(),
  submitted_by   uuid references public.profiles(id) on delete set null,
  customer_name  text not null,
  customer_email text,
  customer_phone text,
  request_type   public.request_type not null default 'other',
  subject        text not null,
  details        text,
  payload        jsonb not null default '{}'::jsonb,
  source         text not null default 'web',    -- 'web' | 'airtable' | 'ghl' | 'zapier' | 'api'
  airtable_id    text,
  created_at     timestamptz not null default now()
);
create index if not exists intake_created_idx on public.customer_intake_forms(created_at desc);

-- -----------------------------------------------------------------------------
-- CASES — the workflow record
-- -----------------------------------------------------------------------------
create table if not exists public.cases (
  id               uuid primary key default gen_random_uuid(),
  ref_code         text unique not null default ('C-' || upper(substr(replace(gen_random_uuid()::text,'-',''),1,8))),
  intake_id        uuid references public.customer_intake_forms(id) on delete set null,
  customer_name    text not null,
  customer_email   text,
  customer_phone   text,
  request_type     public.request_type not null default 'other',
  subject          text not null,
  description      text,
  status           public.case_status not null default 'intake_submitted',
  priority         smallint not null default 3,    -- 1=urgent 5=low
  owner_id         uuid references public.profiles(id) on delete set null,
  organization_id  uuid references public.organizations(id) on delete set null,
  airtable_id      text,
  clickup_task_id  text,
  clickup_task_url text,
  metadata         jsonb not null default '{}'::jsonb,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  closed_at        timestamptz
);
create index if not exists cases_status_idx on public.cases(status);
create index if not exists cases_owner_idx on public.cases(owner_id);
create index if not exists cases_created_idx on public.cases(created_at desc);

-- -----------------------------------------------------------------------------
-- CASE STATUS HISTORY
-- -----------------------------------------------------------------------------
create table if not exists public.case_status_history (
  id          uuid primary key default gen_random_uuid(),
  case_id     uuid not null references public.cases(id) on delete cascade,
  from_status public.case_status,
  to_status   public.case_status not null,
  changed_by  uuid references public.profiles(id) on delete set null,
  note        text,
  created_at  timestamptz not null default now()
);
create index if not exists csh_case_idx on public.case_status_history(case_id, created_at desc);

create or replace function public.log_case_status_change()
returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    insert into public.case_status_history (case_id, from_status, to_status, changed_by)
    values (new.id, null, new.status, auth.uid());
  elsif new.status is distinct from old.status then
    insert into public.case_status_history (case_id, from_status, to_status, changed_by)
    values (new.id, old.status, new.status, auth.uid());
    if new.status in ('completed','closed') and new.closed_at is null then
      new.closed_at := now();
    end if;
  end if;
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists cases_status_change on public.cases;
create trigger cases_status_change
  before insert or update on public.cases
  for each row execute function public.log_case_status_change();

-- -----------------------------------------------------------------------------
-- TASKS (internal) + CLICKUP TASKS (mirror)
-- -----------------------------------------------------------------------------
create table if not exists public.tasks (
  id           uuid primary key default gen_random_uuid(),
  case_id      uuid references public.cases(id) on delete cascade,
  title        text not null,
  description  text,
  status       text not null default 'open',   -- open | in_progress | done | blocked
  assignee_id  uuid references public.profiles(id) on delete set null,
  due_at       timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists tasks_case_idx on public.tasks(case_id);

create table if not exists public.clickup_tasks (
  id              uuid primary key default gen_random_uuid(),
  case_id         uuid references public.cases(id) on delete cascade,
  task_id         uuid references public.tasks(id) on delete set null,
  clickup_task_id text not null,
  clickup_url     text,
  list_id         text,
  status          text,
  raw             jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create unique index if not exists clickup_tasks_remote_idx on public.clickup_tasks(clickup_task_id);

-- -----------------------------------------------------------------------------
-- VENDOR JOBS
-- -----------------------------------------------------------------------------
create table if not exists public.vendor_jobs (
  id              uuid primary key default gen_random_uuid(),
  case_id         uuid not null references public.cases(id) on delete cascade,
  vendor_id       uuid not null references public.vendors(id) on delete restrict,
  title           text not null,
  description     text,
  location        text,
  status          public.vendor_job_status not null default 'offered',
  offered_price   numeric(10,2),
  agreed_price    numeric(10,2),
  scheduled_for   timestamptz,
  due_at          timestamptz,
  clickup_task_id text,
  airtable_id     text,
  created_by      uuid references public.profiles(id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  completed_at    timestamptz
);
create index if not exists vj_vendor_idx on public.vendor_jobs(vendor_id, status);
create index if not exists vj_case_idx on public.vendor_jobs(case_id);

create or replace function public.touch_vendor_job()
returns trigger language plpgsql as $$
begin
  if new.status is distinct from old.status and new.status in ('completed','cancelled','rejected') and new.completed_at is null then
    new.completed_at := now();
  end if;
  new.updated_at := now();
  return new;
end;
$$;
drop trigger if exists vendor_jobs_touch on public.vendor_jobs;
create trigger vendor_jobs_touch
  before update on public.vendor_jobs
  for each row execute function public.touch_vendor_job();

-- -----------------------------------------------------------------------------
-- VENDOR JOB UPDATES (timeline) + VENDOR FILES
-- -----------------------------------------------------------------------------
create table if not exists public.vendor_job_updates (
  id            uuid primary key default gen_random_uuid(),
  vendor_job_id uuid not null references public.vendor_jobs(id) on delete cascade,
  author_id     uuid references public.profiles(id) on delete set null,
  kind          text not null default 'note',  -- note | status_change | invoice | photo
  body          text,
  metadata      jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now()
);
create index if not exists vju_job_idx on public.vendor_job_updates(vendor_job_id, created_at desc);

create table if not exists public.vendor_files (
  id            uuid primary key default gen_random_uuid(),
  vendor_job_id uuid not null references public.vendor_jobs(id) on delete cascade,
  uploaded_by   uuid references public.profiles(id) on delete set null,
  kind          text not null default 'photo',  -- photo | invoice | document
  storage_path  text not null,                  -- path inside the 'vendor-files' bucket
  filename      text,
  mime_type     text,
  size_bytes    bigint,
  created_at    timestamptz not null default now()
);
create index if not exists vf_job_idx on public.vendor_files(vendor_job_id);

-- -----------------------------------------------------------------------------
-- INVESTORS
-- -----------------------------------------------------------------------------
create table if not exists public.investor_accounts (
  id              uuid primary key default gen_random_uuid(),
  profile_id      uuid not null references public.profiles(id) on delete cascade,
  organization_id uuid references public.organizations(id) on delete set null,
  display_name    text,
  position_value  numeric(14,2),
  created_at      timestamptz not null default now()
);
create index if not exists ia_profile_idx on public.investor_accounts(profile_id);

create table if not exists public.investor_updates (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid references public.organizations(id) on delete cascade,
  title           text not null,
  body            text,
  period_start    date,
  period_end      date,
  published       boolean not null default false,
  published_at    timestamptz,
  created_by      uuid references public.profiles(id) on delete set null,
  created_at      timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- APPROVALS, NOTIFICATIONS, DOCUMENTS, ACTIVITY LOG
-- -----------------------------------------------------------------------------
create table if not exists public.approvals (
  id          uuid primary key default gen_random_uuid(),
  case_id     uuid references public.cases(id) on delete cascade,
  requested_by uuid references public.profiles(id) on delete set null,
  requested_of uuid references public.profiles(id) on delete set null,
  reason      text,
  decision    text not null default 'pending',  -- pending | approved | rejected
  decided_at  timestamptz,
  decision_note text,
  created_at  timestamptz not null default now()
);

create table if not exists public.notifications (
  id         uuid primary key default gen_random_uuid(),
  recipient  uuid not null references public.profiles(id) on delete cascade,
  case_id    uuid references public.cases(id) on delete set null,
  kind       text not null,                 -- 'case_assigned','vendor_job_offered','status_change', ...
  title      text not null,
  body       text,
  read_at    timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists notifications_recipient_idx on public.notifications(recipient, read_at, created_at desc);

create table if not exists public.documents (
  id          uuid primary key default gen_random_uuid(),
  case_id     uuid references public.cases(id) on delete cascade,
  kind        text not null default 'general', -- contract | invoice | photo | other
  title       text,
  storage_path text not null,
  visibility  text not null default 'internal', -- internal | vendor | investor | customer | public
  uploaded_by uuid references public.profiles(id) on delete set null,
  created_at  timestamptz not null default now()
);

create table if not exists public.activity_logs (
  id          uuid primary key default gen_random_uuid(),
  actor_id    uuid references public.profiles(id) on delete set null,
  entity      text not null,                  -- 'case','vendor_job','approval', ...
  entity_id   uuid,
  action      text not null,                  -- 'created','updated','status_changed', ...
  data        jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists activity_entity_idx on public.activity_logs(entity, entity_id, created_at desc);

-- -----------------------------------------------------------------------------
-- ROLE HELPERS — used by RLS policies
-- -----------------------------------------------------------------------------
create or replace function public.current_role()
returns public.user_role
language sql stable
security definer
set search_path = public
as $$
  select role from public.profiles where id = auth.uid()
$$;

create or replace function public.is_staff()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((select role in ('admin','internal_team') from public.profiles where id = auth.uid()), false)
$$;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((select role = 'admin' from public.profiles where id = auth.uid()), false)
$$;

create or replace function public.current_vendor_id()
returns uuid language sql stable security definer set search_path = public as $$
  select id from public.vendors where profile_id = auth.uid() limit 1
$$;

-- -----------------------------------------------------------------------------
-- RLS — enable on every user-facing table
-- -----------------------------------------------------------------------------
alter table public.profiles            enable row level security;
alter table public.organizations       enable row level security;
alter table public.customer_intake_forms enable row level security;
alter table public.cases               enable row level security;
alter table public.case_status_history enable row level security;
alter table public.tasks               enable row level security;
alter table public.clickup_tasks       enable row level security;
alter table public.vendors             enable row level security;
alter table public.vendor_jobs         enable row level security;
alter table public.vendor_job_updates  enable row level security;
alter table public.vendor_files        enable row level security;
alter table public.investor_accounts   enable row level security;
alter table public.investor_updates    enable row level security;
alter table public.approvals           enable row level security;
alter table public.notifications       enable row level security;
alter table public.documents           enable row level security;
alter table public.activity_logs       enable row level security;

-- profiles: user reads/updates self; staff read all; admin writes all
drop policy if exists profiles_self_read on public.profiles;
create policy profiles_self_read on public.profiles for select
  using (id = auth.uid() or public.is_staff());
drop policy if exists profiles_self_update on public.profiles;
create policy profiles_self_update on public.profiles for update
  using (id = auth.uid() or public.is_admin())
  with check (id = auth.uid() or public.is_admin());

-- organizations: staff read all; investors read their own
drop policy if exists orgs_read on public.organizations;
create policy orgs_read on public.organizations for select
  using (
    public.is_staff()
    or id in (select organization_id from public.profiles where id = auth.uid())
  );

-- customer_intake_forms: public can INSERT (anonymous web intake);
-- only staff can SELECT.  Anonymous inserts are also gated by the app-layer
-- INTAKE_WEBHOOK_SECRET when coming through /api/intake.
drop policy if exists intake_insert_anyone on public.customer_intake_forms;
create policy intake_insert_anyone on public.customer_intake_forms for insert
  with check (true);
drop policy if exists intake_select_staff on public.customer_intake_forms;
create policy intake_select_staff on public.customer_intake_forms for select
  using (public.is_staff());

-- cases: staff full access; vendor sees cases with one of their jobs;
-- investor sees cases in their org; customer-by-email is out of scope for v1.
drop policy if exists cases_staff_all on public.cases;
create policy cases_staff_all on public.cases for all
  using (public.is_staff()) with check (public.is_staff());

drop policy if exists cases_vendor_read on public.cases;
create policy cases_vendor_read on public.cases for select
  using (
    exists (
      select 1 from public.vendor_jobs vj
      where vj.case_id = cases.id and vj.vendor_id = public.current_vendor_id()
    )
  );

drop policy if exists cases_investor_read on public.cases;
create policy cases_investor_read on public.cases for select
  using (
    public.current_role() = 'investor'
    and organization_id in (select organization_id from public.profiles where id = auth.uid())
  );

-- case_status_history: same access surface as cases
drop policy if exists csh_staff on public.case_status_history;
create policy csh_staff on public.case_status_history for select using (public.is_staff());
drop policy if exists csh_vendor on public.case_status_history;
create policy csh_vendor on public.case_status_history for select using (
  exists (select 1 from public.vendor_jobs vj where vj.case_id = case_status_history.case_id and vj.vendor_id = public.current_vendor_id())
);

-- tasks: staff full; vendors don't see internal tasks
drop policy if exists tasks_staff_all on public.tasks;
create policy tasks_staff_all on public.tasks for all using (public.is_staff()) with check (public.is_staff());

-- clickup_tasks: staff only
drop policy if exists clickup_staff on public.clickup_tasks;
create policy clickup_staff on public.clickup_tasks for all using (public.is_staff()) with check (public.is_staff());

-- vendors: staff full; vendor reads own row
drop policy if exists vendors_staff_all on public.vendors;
create policy vendors_staff_all on public.vendors for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists vendors_self_read on public.vendors;
create policy vendors_self_read on public.vendors for select using (profile_id = auth.uid());

-- vendor_jobs: staff full; vendor reads + updates own
drop policy if exists vj_staff_all on public.vendor_jobs;
create policy vj_staff_all on public.vendor_jobs for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists vj_vendor_read on public.vendor_jobs;
create policy vj_vendor_read on public.vendor_jobs for select using (vendor_id = public.current_vendor_id());
drop policy if exists vj_vendor_update on public.vendor_jobs;
create policy vj_vendor_update on public.vendor_jobs for update
  using (vendor_id = public.current_vendor_id())
  with check (vendor_id = public.current_vendor_id());

-- vendor_job_updates: staff full; vendor can read + insert for own jobs
drop policy if exists vju_staff_all on public.vendor_job_updates;
create policy vju_staff_all on public.vendor_job_updates for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists vju_vendor_read on public.vendor_job_updates;
create policy vju_vendor_read on public.vendor_job_updates for select using (
  exists (select 1 from public.vendor_jobs vj where vj.id = vendor_job_updates.vendor_job_id and vj.vendor_id = public.current_vendor_id())
);
drop policy if exists vju_vendor_insert on public.vendor_job_updates;
create policy vju_vendor_insert on public.vendor_job_updates for insert with check (
  exists (select 1 from public.vendor_jobs vj where vj.id = vendor_job_updates.vendor_job_id and vj.vendor_id = public.current_vendor_id())
);

-- vendor_files: same access pattern
drop policy if exists vf_staff_all on public.vendor_files;
create policy vf_staff_all on public.vendor_files for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists vf_vendor_read on public.vendor_files;
create policy vf_vendor_read on public.vendor_files for select using (
  exists (select 1 from public.vendor_jobs vj where vj.id = vendor_files.vendor_job_id and vj.vendor_id = public.current_vendor_id())
);
drop policy if exists vf_vendor_insert on public.vendor_files;
create policy vf_vendor_insert on public.vendor_files for insert with check (
  exists (select 1 from public.vendor_jobs vj where vj.id = vendor_files.vendor_job_id and vj.vendor_id = public.current_vendor_id())
);

-- investor_accounts: staff full; investor reads self
drop policy if exists ia_staff_all on public.investor_accounts;
create policy ia_staff_all on public.investor_accounts for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists ia_self_read on public.investor_accounts;
create policy ia_self_read on public.investor_accounts for select using (profile_id = auth.uid());

-- investor_updates: staff full; investor reads published updates for their org
drop policy if exists iu_staff_all on public.investor_updates;
create policy iu_staff_all on public.investor_updates for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists iu_investor_read on public.investor_updates;
create policy iu_investor_read on public.investor_updates for select using (
  published = true
  and public.current_role() = 'investor'
  and organization_id in (select organization_id from public.profiles where id = auth.uid())
);

-- approvals: staff full; requested_of can read + decide
drop policy if exists approvals_staff_all on public.approvals;
create policy approvals_staff_all on public.approvals for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists approvals_target on public.approvals;
create policy approvals_target on public.approvals for update
  using (requested_of = auth.uid()) with check (requested_of = auth.uid());

-- notifications: recipient only
drop policy if exists notifications_self on public.notifications;
create policy notifications_self on public.notifications for select using (recipient = auth.uid() or public.is_staff());
drop policy if exists notifications_update_self on public.notifications;
create policy notifications_update_self on public.notifications for update using (recipient = auth.uid()) with check (recipient = auth.uid());

-- documents: staff full; visibility-based read for non-staff (vendor / investor / customer)
drop policy if exists documents_staff_all on public.documents;
create policy documents_staff_all on public.documents for all using (public.is_staff()) with check (public.is_staff());
drop policy if exists documents_vendor on public.documents;
create policy documents_vendor on public.documents for select using (
  visibility = 'vendor' and exists (
    select 1 from public.vendor_jobs vj where vj.case_id = documents.case_id and vj.vendor_id = public.current_vendor_id()
  )
);
drop policy if exists documents_investor on public.documents;
create policy documents_investor on public.documents for select using (
  visibility = 'investor' and public.current_role() = 'investor'
);

-- activity_logs: staff full read; everyone can insert their own
drop policy if exists activity_staff_read on public.activity_logs;
create policy activity_staff_read on public.activity_logs for select using (public.is_staff() or actor_id = auth.uid());
drop policy if exists activity_self_insert on public.activity_logs;
create policy activity_self_insert on public.activity_logs for insert with check (actor_id = auth.uid() or actor_id is null);

-- -----------------------------------------------------------------------------
-- STORAGE — vendor-files bucket (private) + policies
-- Path convention: {vendor_job_id}/{filename}
-- -----------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('vendor-files', 'vendor-files', false)
on conflict (id) do nothing;

-- Staff: full
drop policy if exists "vendor-files staff read" on storage.objects;
create policy "vendor-files staff read" on storage.objects for select
  using (bucket_id = 'vendor-files' and public.is_staff());
drop policy if exists "vendor-files staff write" on storage.objects;
create policy "vendor-files staff write" on storage.objects for insert
  with check (bucket_id = 'vendor-files' and public.is_staff());

-- Vendor: read + insert only inside folders for their own jobs.
-- Folder is the first path segment = vendor_job_id.
drop policy if exists "vendor-files vendor read" on storage.objects;
create policy "vendor-files vendor read" on storage.objects for select
  using (
    bucket_id = 'vendor-files'
    and exists (
      select 1 from public.vendor_jobs vj
      where vj.id::text = split_part(name, '/', 1)
        and vj.vendor_id = public.current_vendor_id()
    )
  );

drop policy if exists "vendor-files vendor write" on storage.objects;
create policy "vendor-files vendor write" on storage.objects for insert
  with check (
    bucket_id = 'vendor-files'
    and exists (
      select 1 from public.vendor_jobs vj
      where vj.id::text = split_part(name, '/', 1)
        and vj.vendor_id = public.current_vendor_id()
    )
  );
