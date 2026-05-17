-- Clock app RLS — run after 001 and after Supabase Auth is configured
-- Map auth.users.email to team_members.email

alter table availability_live enable row level security;
alter table time_events enable row level security;
alter table team_members enable row level security;

-- Operators/owner: extend with custom claims or service role in admin tools only

create or replace function public.current_member_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select id from team_members
  where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  limit 1;
$$;

create policy "members read own row"
  on team_members for select
  using (id = public.current_member_id());

create policy "va update own availability"
  on availability_live for all
  using (member_id = public.current_member_id())
  with check (member_id = public.current_member_id());

create policy "va insert own time_events"
  on time_events for insert
  with check (member_id = public.current_member_id());

create policy "va read own time_events"
  on time_events for select
  using (member_id = public.current_member_id());

-- TODO: add operator policies (read all) via role claim or separate operator role table
