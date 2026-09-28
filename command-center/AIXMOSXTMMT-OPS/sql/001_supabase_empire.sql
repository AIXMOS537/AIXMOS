-- AIXMOSXTMMT Empire — run once in Supabase SQL Editor

-- === CORE AGENT TABLES ===
create table if not exists autonomy_rules (
  id uuid primary key default gen_random_uuid(),
  level text not null default 'A',
  rules jsonb not null default '{}',
  updated_at timestamptz default now()
);

create table if not exists decisions (
  id uuid primary key default gen_random_uuid(),
  topic text not null,
  decision text not null,
  context text,
  made_at timestamptz default now(),
  superseded_by uuid references decisions(id)
);

create table if not exists faq_snippets (
  id uuid primary key default gen_random_uuid(),
  trigger_phrases text[] not null default '{}',
  approved_answer text not null,
  channel text check (channel in ('email','sms','clickup','any')),
  auto_send_allowed boolean not null default false,
  use_count int default 0,
  created_at timestamptz default now()
);

create table if not exists action_queue (
  id uuid primary key default gen_random_uuid(),
  tier text not null check (tier in ('yellow','red')),
  source text not null,
  engine text check (engine in ('rental','dealership','b2b')),
  summary text not null,
  draft_body text,
  payload jsonb default '{}',
  assigned_to uuid,
  escalation_owner boolean default false,
  status text not null default 'pending'
    check (status in ('pending','approved','rejected','sent','expired')),
  created_at timestamptz default now(),
  approved_at timestamptz,
  sent_at timestamptz
);

create table if not exists audit_log (
  id uuid primary key default gen_random_uuid(),
  agent text not null,
  action text not null,
  tier text not null check (tier in ('green','yellow','red')),
  target text,
  payload jsonb,
  result text,
  created_at timestamptz default now()
);

create table if not exists contacts_context (
  id uuid primary key default gen_random_uuid(),
  external_id text,
  source text,
  display_name text,
  notes text,
  do_not_auto_contact boolean default true,
  updated_at timestamptz default now()
);

-- === WORKFORCE / LIVE SCHEDULING ===
create table if not exists team_members (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  email text unique,
  role text not null check (role in ('owner','operator','va')),
  office text check (office in ('A','C','remote','home')),
  timezone text not null default 'UTC',
  skills text[] default '{}',
  clickup_user_id text,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table if not exists shifts (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references team_members(id),
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  office text,
  engine text check (engine in ('rental','dealership','b2b','any')),
  notes text,
  created_by uuid references team_members(id),
  created_at timestamptz default now()
);

create table if not exists availability_live (
  member_id uuid primary key references team_members(id),
  status text not null default 'off'
    check (status in ('available','busy','break','off','pto')),
  until timestamptz,
  current_task text,
  updated_at timestamptz default now(),
  heartbeat_at timestamptz default now()
);

create table if not exists time_events (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references team_members(id),
  event text not null check (event in ('clock_in','clock_out','break_start','break_end','status_change')),
  meta jsonb default '{}',
  created_at timestamptz default now()
);

-- === EMPIRE CRM MEMORY ===
create table if not exists empire_entities (
  id uuid primary key default gen_random_uuid(),
  type text not null check (type in ('applicant','partner','rental_customer','vehicle')),
  external_crm_id text,
  display_name text not null,
  meta jsonb default '{}',
  created_at timestamptz default now()
);

create table if not exists empire_deals (
  id uuid primary key default gen_random_uuid(),
  entity_id uuid references empire_entities(id),
  engine text check (engine in ('rental','dealership','b2b')),
  stage text not null,
  value_estimate numeric,
  owner_operator text,
  next_action_at timestamptz,
  updated_at timestamptz default now()
);

create index if not exists idx_action_queue_status on action_queue(status);
create index if not exists idx_shifts_range on shifts(starts_at, ends_at);
create index if not exists idx_availability_status on availability_live(status);
create index if not exists idx_audit_log_created on audit_log(created_at desc);

insert into autonomy_rules (level, rules)
values ('A', '{"auto_send_external": false}'::jsonb);
