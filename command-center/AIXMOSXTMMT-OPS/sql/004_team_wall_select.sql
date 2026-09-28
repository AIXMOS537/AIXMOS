-- Clock app: allow authenticated team members to read the live wall
-- Run after 002_rls_clock.sql

create policy "team read availability wall"
  on availability_live for select
  to authenticated
  using (true);

create policy "team read member names for wall"
  on team_members for select
  to authenticated
  using (true);
