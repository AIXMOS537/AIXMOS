# Cursor Master Prompt

You are building the digital business infrastructure for a corporate credit readiness, business funding preparation, and car rental conversion company.

Business brands:

- All In One Management Solutions
  - Domains: `allinonemanagementsolutions.com`, `allinonemanagementsolutions.net`
  - Purpose: corporate parent brand for credit readiness, business funding preparation, client onboarding, partner intake, staff training, and internal operations.

- TMMT Rentals
  - Domains: `tmmtrentals.com`, `tmmtrentals.net`
  - Purpose: customer-facing vehicle rental and fleet partner brand.

- TMMT Management
  - Purpose: operating management company that manages TMMT Rentals, vehicle programs, partner accounts, operators, and revenue recovery plays.

- Project AIXMOS
  - Purpose: internal operating engine powering credit repair guidance, funding resolution through partnerships, transportation inventory matching, retail customer conversion, dealership/shop partnerships, slow-month revenue campaigns, agent workflows, and routing across TMMT Management.

Existing systems to preserve and connect:

- Existing command center work
- Existing TMMT Rentals Vercel interface
- Agent workflows already created by the owner
- Airtable hiring/background-check workflow

All In One Management Solutions should become the parent operating layer that connects these systems rather than replacing them.

Build a practical infrastructure that supports hiring, training, client intake, service delivery, CRM workflows, document collection, SOPs, compliance guardrails, and reporting.

Do not build a marketing-only landing page. Build the actual business operating system.

## First Build Target

Create a full-stack web app with:

1. Public website for All In One Management Solutions
2. Public website for TMMT Rentals
3. Shared admin dashboard
4. Staff training portal
5. SOP library
6. Client intake forms
7. Funding readiness scorecard
8. Rental candidate intake
9. CRM-style pipeline
10. KPI dashboard
11. Vendor fulfillment command center
12. Deal desk for tracking vendor cost, client price, and gross margin
13. Heavy Mode escalation dashboard for owner-controlled priority cases
14. Staff/operator hiring and training module
15. Airtable-ready background check module
16. Agent operations module
17. Integration layer for existing command center and TMMT Vercel interface
18. TMMT Management operating dashboard
19. Project AIXMOS engine dashboard
20. Retail-to-rental/dealership conversion board
21. Mom-and-pop shop slow-month revenue recovery pipeline
22. Credit/funding resolution board
23. Transportation inventory match board
24. Second Chance Vehicle Pathway for retail customers

## Recommended Technical Direction

Use a modern web stack:

- Next.js or React frontend
- Tailwind CSS or the existing repo styling system
- Supabase or PostgreSQL database
- Auth with role-based access
- Email/SMS integration placeholders
- File upload placeholders for documents

If no app exists yet, scaffold one cleanly.

## Required User Roles

- Founder / Admin
- Operations Manager
- Sales Rep
- Credit Specialist
- Funding Specialist
- Rental Coordinator
- Client
- Partner

## Required Modules

### Public Website: All In One Management Solutions

Pages:

- Home
- Credit Readiness
- Business Funding Prep
- Vehicle Monetization Pathway
- Partner Intake
- Book Consultation
- Client Login

Primary CTA:

- Complete Funding Readiness Scorecard

### Public Website: TMMT Rentals

Pages:

- Home
- Available Rentals
- Rental Requirements
- Apply to Rent
- Fleet Partner Program
- Contact
- Customer Login

Primary CTA:

- Start Rental Application

### Admin Dashboard

Views:

- Lead pipeline
- Client records
- Document status
- Credit readiness status
- Funding readiness status
- Rental candidate status
- Staff tasks
- KPI scorecard
- Compliance review queue
- Vendor directory
- Fulfillment order board
- Deal desk
- Vendor quality control queue
- Vendor scorecards

### Vendor Fulfillment Command Center

Purpose: let the owner route client work to outside vendor companies while keeping control of client communication, quality, cost, margin, and compliance.

Views:

- Vendor directory
- Vendor profiles
- Vendor document tracker
- Fulfillment orders
- Vendor assignment
- Deal desk
- Margin tracker
- QC queue
- Past-due fulfillment
- Vendor scorecards

### Heavy Mode Escalation

Purpose: give the owner a private command interface for high-value, urgent, stuck, or sensitive client cases.

Views:

- Priority client list
- Escalation case detail
- Escalation level selector
- Owner-only notes
- Next actions
- Vendor reassignment
- Client update plan
- Margin exception approval
- Compliance review flag

### TMMT Management / Project AIXMOS

Purpose: manage the full TMMT ecosystem through an internal engine that converts retail customers, dealership opportunities, and mom-and-pop shop relationships into rental, funding, partner, and revenue recovery outcomes.

Views:

- TMMT Management overview
- AIXMOS engine overview
- Retail conversion board
- Dealership partner pipeline
- Mom-and-pop shop pipeline
- Revenue recovery campaigns
- Operator task queue
- Agent activity
- Rental/funding/dealership routing
- Credit repair guidance routing
- Funding partner resolution routing
- Available transportation inventory matching
- Second chance vehicle pathway
- Revenue experience education without income guarantees

### Staff Training Portal

Views:

- Role-based onboarding
- SOP library
- Scripts
- Checklists
- Quizzes / sign-off status
- Training progress

### Client Portal

Views:

- Intake form
- Document checklist
- Status tracker
- Messages
- Appointments
- Required actions

## Compliance Rules

Do not include language that guarantees:

- Credit score increases
- Deletions
- Funding approvals
- Approval amounts
- Rental income

Use language like:

- Readiness
- Review
- Preparation
- Support
- Eligibility
- Candidate
- Pathway

## Build Style

The UI should feel corporate, operational, and trustworthy. Avoid hype-heavy pages. Prioritize dashboards, tables, forms, checklists, and task flows.

## First Milestone

First inspect the current project and identify existing command center and TMMT Rentals work. Preserve useful existing routes, components, and workflows.

Then build the information architecture, routes, database schema, and static UI screens. Use placeholder data where needed.

Do not delete existing command center or TMMT Rentals interface work unless explicitly instructed.

After the first milestone, build real form submission, role permissions, CRM pipeline movement, and KPI reporting.
