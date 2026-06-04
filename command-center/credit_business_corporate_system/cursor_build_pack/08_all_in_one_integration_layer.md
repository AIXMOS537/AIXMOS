# All In One Integration Layer

## Purpose

All In One Management Solutions should become the parent command layer that connects every operating piece:

- Existing command center
- Existing TMMT Rentals Vercel interface
- TMMT Rentals public/customer system
- Credit readiness operations
- Business funding operations
- Vendor fulfillment backend
- Agent workflows
- Team/operator hiring and training
- Airtable background check and staff qualification workflow
- Client, vendor, and partner records

The goal is not to rebuild everything from scratch if a useful system already exists. The goal is to connect, standardize, and control everything from All In One.

## Existing Assets To Preserve

Cursor should first inspect the project and identify any existing:

- Command center routes
- Admin dashboards
- TMMT Rentals interface
- Vercel deployment configuration
- Agent files
- CRM or pipeline logic
- Existing forms
- Existing data models
- Existing API routes
- Existing UI components

Do not delete or replace existing work unless it is broken and the replacement is clearly better.

## Parent Architecture

All In One should become the central operator layer.

TMMT Rentals should remain a distinct rental brand connected to the same backend.

Recommended structure:

- All In One = corporate HQ, staff, vendors, clients, funding, compliance, training, reporting
- TMMT Rentals = rental applications, fleet operations, renter/customer journey
- Command Center = owner/operator control room
- Airtable = hiring/background-check workflow until a native module replaces it
- Agents = task execution helpers for operations, documents, media, vendor follow-up, and training

## Unified Navigation

The owner/admin interface should include:

- Command Center
- Leads
- Clients
- Credit Readiness
- Funding Readiness
- TMMT Rentals
- Vendors
- Fulfillment Orders
- Heavy Mode
- Staff / Operators
- Training
- Background Checks
- SOPs
- Agents
- KPI Dashboard
- Settings

## Staff And Operator System

The system must support hiring and training operators quickly.

Staff/operator records should include:

- Full name
- Email
- Phone
- Role applied for
- Current role
- Status
- Background check status
- Training status
- SOP sign-offs
- Assigned department
- Assigned manager
- Start date
- Notes

Operator statuses:

- Applicant
- Pre-Screen
- Background Check Pending
- Background Check Passed
- Background Check Failed
- Training Assigned
- Training In Progress
- Training Complete
- Active
- Paused
- Terminated

## Airtable Background Check Integration

First version can use Airtable as the source of truth for hiring and background check tracking.

Build an integration-ready interface with:

- Airtable base ID placeholder
- Airtable table name placeholder
- API key/env var placeholder
- Sync status
- Last synced time
- Import candidates button placeholder
- Candidate list
- Background check status mapping

Environment variables:

- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- `AIRTABLE_CANDIDATES_TABLE`

Status mapping:

- Airtable `New Applicant` -> App `Applicant`
- Airtable `Pre Screen` -> App `Pre-Screen`
- Airtable `BG Pending` -> App `Background Check Pending`
- Airtable `BG Passed` -> App `Background Check Passed`
- Airtable `BG Failed` -> App `Background Check Failed`
- Airtable `Training` -> App `Training In Progress`
- Airtable `Approved` -> App `Active`

## Agent Operations Layer

Agents should be represented as operational helpers inside All In One.

Agent records should include:

- Agent name
- Purpose
- Department
- Allowed tasks
- Required approval level
- Status
- Last run
- Output location
- Notes

Agent categories:

- Credit Operations Agent
- Funding Prep Agent
- Vendor Follow-Up Agent
- Document Drafting Agent
- Media/Marketing Agent
- Rental Operations Agent
- Training/SOP Agent
- Heavy Mode Support Agent

Approval levels:

- Auto allowed
- Manager approval required
- Owner approval required
- Compliance review required

## Existing TMMT Vercel Interface

If a TMMT Rentals Vercel app or interface already exists, connect it into the All In One command layer.

Cursor should:

1. Inspect current routes and components.
2. Identify the existing TMMT interface.
3. Preserve useful UI and workflows.
4. Add admin links from All In One to TMMT operations.
5. Add shared data models or adapters for:
   - rental applications
   - renters
   - vehicles
   - fleet partners
   - payments
   - rental status
6. Add placeholders for Vercel deployment notes and env vars.

## Command Center Integration

The existing command center should become the owner home screen if it is usable.

It should show:

- Today's leads
- Active clients
- Funding cases
- Rental applications
- Vendor fulfillment
- Heavy Mode cases
- Staff/operator status
- Background check queue
- Training progress
- KPI summary
- Agent activity

## Cursor Build Instruction

Before building new screens, inspect the existing project.

Create an integration map:

- Existing routes
- Existing components
- Existing data models
- Existing command center features
- Existing TMMT Rentals features
- Missing modules
- Recommended merge plan

Then implement the All In One integration layer:

- Unified owner/admin navigation
- Staff/operators module
- Background checks module with Airtable-ready placeholders
- Agents module
- Command center widgets connecting existing systems
- TMMT Rentals integration links/adapters

Use placeholder data first.

Do not remove existing command center or TMMT interface work.
