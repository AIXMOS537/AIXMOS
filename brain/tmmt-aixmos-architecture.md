# AIXMOS + TMMT — how the two apps relate

> Verified against Supabase project `uapxakmlwnpfsftfeezx` on 2026-08-25.
> Two kinds of statement live here and they are labelled:
> **[VERIFIED]** = read out of the live database. **[INTENT]** = the target Taha
> stated as owner; not built yet.

This file is the answer to "separate TMMT and AIXMOS but keep them paired."
The short version: **the pairing already exists in the database. It is the app
code that has not caught up.** Nothing here needs inventing from scratch.

---

## 1. What is actually there right now

**[VERIFIED] One Supabase project holds both apps.**

| Fact | Value |
|---|---|
| Tables in `public` | 152 |
| Tables with RLS enabled | 152 (all of them) |
| Tables carrying an `org_id` column | 88 |
| Organizations | 9 |
| Operator profiles | 19 |
| Partners | 1 |
| Organization licenses | 4 |
| Auth users / profiles | 10 |
| GHL contacts synced | 1,637 |
| Portal clients | 0 |

**[VERIFIED] The multi-tenant scaffold is already built.** These helper
functions exist in the database and are callable today:

```
acting_org_id()              current_organization_id()      current_profile_email()
is_org_member(org uuid)      is_org_dispatcher(org uuid)    org_has_module(module text)
is_staff()                   is_admin()                     is_owner()
is_partner()                 is_super_admin()               is_internal_ops()
onboard_org_member(email, org, role)                        get_partner_fleet()
request_handoff(src_org, dest_org, contact, reason, …)      submit_customer_intake(…)
```

Alongside them: `organizations`, `org_roles`, `organization_licenses`,
`operator_profiles`, `operator_pipeline_tracker`, `operator_training_modules`,
`operator_training_progress`, `operator_rubric_scores`, `partners`,
`partner_fleet_access`, `partner_referrals`, `partner_app_endpoints`,
`portal_clients`, `profile_entitlement_grants`, `detail_memberships`,
`ghl_contacts`, `ghl_appointments`, `ghl_form_submissions`.

That is the operator/client/GHL platform. It is the **AIXMOS** half.

**[VERIFIED] TMMT Rentals is 20 of those 152 tables.** 18 of the 20 already
carry `org_id` and an org-scoped RLS policy. The two that do **not**:

```
incoming_leads   — no org_id   (the lead pipeline: 872 rows)
tasks            — no org_id   (added 2026-08-25)
```

---

## 2. The one thing that blocks onboarding a second operator

**[VERIFIED] Today, any staff user in any org can read every org's data.**

Every org-scoped table carries two *permissive* policies. Permissive policies
are OR'd together, so the weaker one wins:

```sql
-- fleet_org_all
  is_staff() OR (org_id IS NOT NULL AND is_org_member(org_id))
-- staff_all_fleet
  is_staff()
```

And `is_staff()` has no org dimension at all — it is global:

```sql
select role in ('admin','internal_team')
    or portal_role in ('team_member','manager','admin','super_admin')
from profiles where id = auth.uid()
```

So the org check is decorative. The moment operator #2 signs in as staff, they
see operator #1's fleet, leads, customers and payments.

With 9 organizations and 19 operator profiles already in the table, **this is
the thing to fix before anyone else is let in.** It is not a rebuild — it is
tightening the policy pair and giving `is_staff()` an org argument.

**[VERIFIED] The app writes nothing to `org_id`.** `src/lib/queries.ts` and
both server-action files never read or set it. Rows created through the app
land with `org_id = NULL`, which the org branch of the policy explicitly
excludes (`org_id IS NOT NULL AND …`). Those rows are reachable *only* through
the global `is_staff()` branch — which is why the app appears to work.

---

## 3. The target

**[INTENT] The two businesses are different shapes, and that is the point.**

- **AIXMOS** is membership and service, delivered entirely online. No physical
  product. Recurring relationship.
- **TMMT** is product *and* service, delivered through an app. Cars, contracts,
  inspections, physical handover.

They are joined by what happens when someone is turned down. **A customer who
cannot rent is not lost — they are routed into the credit pipeline**, where the
blockers on their profile get worked, and they come back to TMMT when their
profile is eligible. That routing is the hinge between the two businesses: TMMT
qualifies, AIXMOS repairs and guides, TMMT converts.

This makes the lead funnel a two-destination machine, not a single pipeline:

```
   intake  ──►  eligible?  ──yes──►  TMMT: waitlist → appointment → contract
                    │
                    └──no──►  AIXMOS: credit repair pipeline → guided work
                                        │
                                        └──► profile eligible ──► back to TMMT
```

Status: **not built.** `docs/ROADMAP.md` Tier 3 carries it as "Lead funnel:
auto-route non-qualifying leads into credit repair pipeline — ❌ Not done".
The database is readier than the app: `incoming_leads` already carries
`assigned_to`, `affiliate_operator_id`, `source_campaign`, `utm_*`,
`contacted_at`, `qualified_at`, `closed_at`, `lost_at` — a funnel with
attribution and stage timestamps, none of which the app writes yet.

**[INTENT] Two deployables, one spine.**

```
                    ┌───────────────────────────────┐
                    │  Supabase — one project        │
                    │  organizations · profiles      │
                    │  org_roles · licenses          │
                    │  GHL sync · entitlements       │
                    └───────┬───────────────┬────────┘
                            │               │
            ┌───────────────┴────┐     ┌────┴──────────────────┐
            │  AIXMOS (platform) │     │  TMMT Rentals (app)   │
            │  operator onboard  │     │  fleet · leads        │
            │  training · rubric │     │  contracts · payments │
            │  partners · portal │     │  inspections · tickets│
            │  licensing · GHL   │     │  one org's operation  │
            └────────────────────┘     └───────────────────────┘
```

- **Separate**: two repos, two Vercel projects, two domains, deployed and
  versioned independently. TMMT can ship without touching AIXMOS.
- **Paired**: one database, one identity (`profiles`), one org model, one set of
  RLS helpers. A person signs in once and is the same person in both.

**[INTENT] Three audiences, three doors.**

| Who | Door | Sees |
|---|---|---|
| Internal ops (you, the team) | AIXMOS admin | every org, platform-wide |
| Operator | TMMT app, scoped to their org | their own fleet/leads/customers, plus everything AIXMOS has published to them |
| Client / renter | client portal | their own records only — contract, payments, inspections, tickets |

**[INTENT] Operator onboarding runs off their own GHL account.** An operator
arrives with their own GHL sub-account; AIXMOS creates the org, links the GHL
location, grants the license, and from then on that operator's leads flow into
*their* `org_id` rather than the shared pool. `onboard_org_member(email, org,
role)` and `organization_licenses` are the hooks that already exist for this.
`ghl_contacts` (1,637 rows) is currently org-less and would need the same
`org_id` treatment as everything else.

---

## 4. Rebuild rules

Anything rebuilding this — Cursor, Cowork, a subagent — follows these:

1. **Do not redesign the tenancy model.** It exists. Finish wiring it.
2. **`org_id` is not optional.** Every business table carries it, every write
   sets it from `acting_org_id()`, every read is filtered by RLS, not by a
   `.eq('org_id', …)` in application code that someone can forget.
3. **`is_staff()` alone must never be a read path for org data.** Replace the
   bare `is_staff()` policy with `is_internal_ops()` (platform staff, all orgs,
   deliberately) or `is_staff_of(org_id)`. Keep the two intents distinct.
4. **One identity table.** `profiles` is it. Do not add a parallel user table
   for operators or clients — use `role` / `portal_role` / `org_roles`.
5. **Backfill before enforcing.** Rows with `org_id = NULL` become invisible the
   moment the global staff branch is removed. Assign them to the TMMT house org
   first, then tighten the policy, in that order.
6. **The database is shared with `tmmt-os`.** Every migration lands on both
   apps. Nothing here is a private schema change.
7. **Two tables still need `org_id`:** `incoming_leads`, `tasks`. Also
   `ghl_contacts`, `ghl_appointments`, `ghl_form_submissions` if operators bring
   their own GHL accounts.

---

## 5. Open questions for Taha

These change the build and only you can answer them:

- Is AIXMOS a separate Next app, or a route group inside the existing one? (Two
  repos is cleaner for licensing; one repo is cheaper to run.)
- Does an operator get the TMMT app white-labelled on their own domain, or a
  shared domain with org switching?
- Does a client portal client ever belong to more than one org?
- What does an `organization_license` actually unlock — modules
  (`org_has_module`), seat count, or both?

Related: [[closed-loop-ops]] · [[command-center-dashboards]] · [[fleet-watchtower]]
