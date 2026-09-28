-- Optional example rows — change emails before running

insert into team_members (display_name, email, role, office, timezone, skills)
values
  ('CEO', 'ceo@example.com', 'owner', 'home', 'America/Chicago', '{}'),
  ('Operator One', 'ops1@example.com', 'operator', 'C', 'America/Chicago', '{ghl_applicant,rental_ops}'),
  ('Operator Two', 'ops2@example.com', 'operator', 'C', 'America/Chicago', '{ghl_applicant,b2b_research}'),
  ('Operator Three', 'ops3@example.com', 'operator', 'A', 'America/Chicago', '{b2b_research}'),
  ('VA Example', 'va1@example.com', 'va', 'remote', 'Asia/Manila', '{rental_ops,english}')
on conflict (email) do nothing;
