# How To Use This In Cursor

## Step 1: Create Or Open Your App Project

Open Cursor and create a new project folder, for example:

`D:\all_in_one_platform`

If you already have a code project, open that project folder instead.

## Step 2: Add This Build Pack To The Project

Copy or reference this folder:

`D:\credit_business_corporate_system\cursor_build_pack`

The most important file is:

`00_cursor_master_prompt.md`

## Step 3: Start Cursor With This Prompt

Paste this into Cursor chat:

```text
Read the build pack in D:\credit_business_corporate_system\cursor_build_pack.

Use 00_cursor_master_prompt.md as the master instruction.
Use the database schema, domain architecture, milestones, hiring/training infrastructure, vendor fulfillment interface, escalation playbook, and All In One integration layer as implementation requirements.
Also use 09_tmmt_management_aixmos_engine.md as the requirements for TMMT Management and Project AIXMOS.

First, inspect the current project. Identify any existing command center work, TMMT Rentals Vercel interface, routes, components, data models, and agent-related files. Do not delete or replace useful existing work.

Create an integration map, then implement Milestone 1: the static operating system with routes, navigation, dashboards, forms, placeholder data, and integration links into the existing command center/TMMT work.

Do not stop at a plan. Build the first working version.
```

```text
Implement Milestone 1C using 09_tmmt_management_aixmos_engine.md.

Build TMMT Management and Project AIXMOS as operating sections inside the All In One admin system.

Add:
- /admin/tmmt-management
- /admin/aixmos
- retail conversion board
- dealership partner pipeline
- mom-and-pop shop pipeline
- revenue recovery campaigns
- operator task queue
- agent activity panel
- command center widgets for AIXMOS

Project AIXMOS should act as the engine that routes retail customers into rentals, funding readiness, dealership referrals, fleet partner paths, and slow-month revenue campaigns for local shops.
It must also include credit repair guidance, funding resolution through partnerships, and available transportation inventory matching for business owners and individuals who need reliable transportation.
For retail customers, include a Second Chance Vehicle Pathway that helps people get reliable economy-friendly vehicles, receive credit cleanup guidance, learn payment discipline, and get a controlled education on vehicle-based revenue opportunities without guaranteeing passive income.

Use placeholder data first. Preserve existing TMMT Rentals work and connect it into this system.
```

## Step 4: Make Cursor Build In Order

Use these prompts one by one:

```text
Implement Milestone 1 from the build pack. Build the public All In One site, TMMT Rentals site, admin dashboard shell, portal shell, training portal shell, SOP library, CRM pipeline, and KPI dashboard using placeholder data.
```

```text
Implement Milestone 2 from the build pack. Add database models or local mock data structures for leads, clients, scorecards, rental applications, tasks, SOPs, and KPI snapshots. Add working forms for readiness scorecard, rental application, and partner intake.
```

```text
Implement Milestone 3. Build staff training portal pages, role-based training modules, script library, SOP pages, task assignment views, and training completion status.
```

```text
Implement Milestone 3B using 06_vendor_fulfillment_interface.md. Build the owner-facing vendor fulfillment command center with vendor directory, fulfillment order board, deal desk, vendor assignment workflow, QC queue, and vendor scorecards. Use placeholder data first.
```

```text
Implement Milestone 3C using 07_escalation_playbook.md. Build Heavy Mode as an owner-only escalation dashboard with priority cases, escalation level selector, owner-only notes, next 3 actions, vendor reassignment, client update plan, compliance review flag, and margin exception approval.
```

```text
Implement Milestone 4. Build client portal views for status, document checklist, appointments, required actions, and activity log.
```

## Step 5: Keep Cursor Focused

Do not ask Cursor to build everything at once after Milestone 1.

Use this pattern:

```text
Build only this module: [module name].
Use the existing style and data patterns.
After implementation, list files changed and how to test it.
```

## Step 6: Deployment

First launch:

- `allinonemanagementsolutions.com` as the main corporate site
- `tmmtrentals.com` as the rental site
- `.net` domains redirect to `.com`

Later:

- Move portal/admin/training to subdomains.
