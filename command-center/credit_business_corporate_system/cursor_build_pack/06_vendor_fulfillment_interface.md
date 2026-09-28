# Vendor Fulfillment Interface

## Purpose

Build an owner-facing fulfillment backend that lets the company sell under its own brands while routing work to approved vendor companies, contractors, lenders, processors, vehicle partners, document providers, credit specialists, and other fulfillment partners.

The owner should be able to see:

- Which client needs what service
- Which vendor is assigned
- What the vendor owes
- What the client has paid
- What the company margin is
- Whether fulfillment is on track
- Whether the vendor is compliant
- Whether the client needs an update

This should feel like a command center, not a basic contact list.

## Core Concept

The company owns:

- Brand
- Client relationship
- Intake
- Payment collection
- Quality control
- Client communication
- Vendor assignment
- Compliance oversight

Vendors fulfill specific service components.

## Required Modules

### Vendor Directory

Fields:

- Vendor company name
- Contact person
- Email
- Phone
- Service categories
- Status: active, paused, probation, terminated
- Contract status
- W9 status
- Insurance/license documents
- Compliance notes
- Payment terms
- Standard pricing
- Internal rating
- Notes

Service categories:

- Credit analysis
- Dispute preparation
- Business funding packaging
- Lender/broker partner
- Document preparation
- Tax/bookkeeping partner
- Business setup partner
- Insurance partner
- Vehicle rental fulfillment
- Fleet maintenance
- Vehicle sourcing
- Legal review
- Marketing/ads
- Call center/sales support

### Fulfillment Orders

Each client service request should become a fulfillment order.

Fields:

- Order ID
- Client
- Brand: All In One or TMMT
- Service type
- Internal owner
- Assigned vendor
- Client price
- Vendor cost
- Gross margin
- Status
- Due date
- Priority
- Documents needed
- Documents received
- Vendor notes
- Client update status
- Quality control status

Statuses:

- New
- Needs Assignment
- Assigned
- Waiting on Client Docs
- Waiting on Vendor
- In Progress
- Vendor Submitted
- Internal Review
- Client Update Needed
- Completed
- Rework Required
- Cancelled
- Disputed

### Deal Desk

Purpose: owner view of revenue, vendor cost, and margin.

Views:

- Open fulfillment orders
- Vendor cost by week
- Revenue collected
- Gross margin
- Unpaid vendor invoices
- Client balances
- Refund risk
- Deals needing owner approval

Required calculations:

- Gross margin = client price - vendor cost
- Margin percent = gross margin / client price
- Vendor payable total
- Client receivable total
- Net projected profit

### Vendor Assignment Workflow

Flow:

1. Client pays or qualifies for service.
2. System creates fulfillment order.
3. Owner or Ops Manager reviews order.
4. System recommends eligible vendors by service category.
5. Owner assigns vendor.
6. Vendor receives task or internal staff sends work packet.
7. Vendor updates status or staff updates on vendor's behalf.
8. Internal team reviews vendor output.
9. Client receives approved update.
10. Order is marked complete.

### Vendor Portal

Optional first version:

Instead of full vendor login, build internal vendor management first.

Later version:

- Vendor login
- Assigned orders
- Upload deliverables
- Update statuses
- Secure message thread
- Invoice submission

### Quality Control Queue

Every vendor deliverable should pass internal review before client delivery.

Fields:

- Fulfillment order
- Vendor
- Deliverable type
- Submitted date
- Reviewer
- QC status
- Issues found
- Rework notes
- Approved date

QC statuses:

- Not Submitted
- Pending Review
- Approved
- Rework Requested
- Rejected

### Vendor Scorecard

Track:

- Orders assigned
- Orders completed
- Average turnaround time
- Rework rate
- Client complaint count
- On-time percentage
- Average margin
- Revenue fulfilled
- Internal rating

### Contract And Compliance Vault

Track vendor documents:

- Service agreement
- NDA
- W9
- Insurance
- Licenses
- Data handling agreement
- Payment terms
- Compliance acknowledgement

Warnings:

- Missing agreement
- Expired insurance
- Missing W9
- Vendor on probation
- Vendor has high complaint rate

## Owner Dashboard

The owner needs a single dashboard with:

- Today's new fulfillment orders
- Orders waiting for vendor assignment
- Orders past due
- Orders needing client update
- Vendor deliverables needing QC
- Revenue collected this week
- Vendor costs this week
- Projected gross margin
- Top vendors by volume
- Vendors with issues
- High-value clients in progress

## Database Additions

### vendors

- id
- company_name
- contact_name
- email
- phone
- service_categories
- status
- payment_terms
- standard_pricing_notes
- rating
- notes
- created_at
- updated_at

### vendor_documents

- id
- vendor_id
- document_type
- file_url
- status
- expiration_date
- reviewed_by
- notes

### fulfillment_orders

- id
- client_id
- lead_id
- brand
- service_type
- internal_owner_id
- vendor_id
- client_price
- vendor_cost
- gross_margin
- margin_percent
- status
- priority
- due_date
- client_update_status
- qc_status
- notes
- created_at
- updated_at

### fulfillment_events

- id
- fulfillment_order_id
- event_type
- previous_status
- new_status
- actor_id
- notes
- created_at

### vendor_invoices

- id
- vendor_id
- fulfillment_order_id
- amount
- status
- due_date
- paid_date
- notes

### qc_reviews

- id
- fulfillment_order_id
- vendor_id
- reviewer_id
- status
- issues_found
- rework_notes
- approved_at
- created_at

## Cursor Build Instruction

Add a new `/admin/vendors` section with:

- Vendor directory
- Vendor profile page
- Add/edit vendor form
- Vendor document tracker
- Vendor scorecard

Add a new `/admin/fulfillment` section with:

- Fulfillment order board
- Fulfillment order detail page
- Vendor assignment action
- Deal desk margin view
- QC queue
- Past-due order view

Add dashboard widgets to `/admin`:

- Needs vendor assignment
- Past-due fulfillment
- QC pending
- Vendor costs
- Projected margin

## First Version Requirements

Use placeholder vendors and orders first.

Do not build external vendor login in version one unless the rest of admin is already working.

Priority is owner visibility and operational control.
