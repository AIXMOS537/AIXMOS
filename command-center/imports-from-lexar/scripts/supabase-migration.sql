-- TMMT Supabase Migration
-- Run this in Supabase SQL Editor before running airtable-to-supabase-sync.py

create table if not exists leads (
  id              bigserial primary key,
  airtable_id     text unique,
  name            text,
  phone           text,
  email           text,
  notes           text,
  source          text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

create table if not exists customers (
  id              bigserial primary key,
  airtable_id     text unique,
  name            text,
  phone           text,
  vehicle         text,
  weekly_payment  numeric,
  start_date      date,
  status          text,
  notes           text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

create table if not exists payments (
  id                  bigserial primary key,
  airtable_id         text unique,
  customer_name       text,
  amount              numeric,
  status              text,
  last_payment_date   date,
  next_due_date       date,
  past_due            text,
  method              text,
  notes               text,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

create table if not exists fleet (
  id              bigserial primary key,
  airtable_id     text unique,
  name            text,
  year            text,
  plate           text,
  status          text,
  partner         text,
  weekly_price    numeric,
  notes           text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- Auto-update updated_at on every row change
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create or replace trigger leads_updated_at
  before update on leads for each row execute function update_updated_at();
create or replace trigger customers_updated_at
  before update on customers for each row execute function update_updated_at();
create or replace trigger payments_updated_at
  before update on payments for each row execute function update_updated_at();
create or replace trigger fleet_updated_at
  before update on fleet for each row execute function update_updated_at();
