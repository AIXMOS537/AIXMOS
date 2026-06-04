# Standard And Heavy Escalation Playbook

## Philosophy

The company should not show every internal strategy to clients, vendors, or outside parties too early. Public messaging stays clean and simple. Internal operations stay fully documented, strategic, and ready to escalate when a client needs stronger support.

Core rule:

> We do not cheat the law. We outwork, out-document, out-coordinate, and out-negotiate.

## Two Fulfillment Modes

### Standard Fulfillment

Used for normal clients and routine service delivery.

Includes:

- Intake
- Readiness scorecard
- Document checklist
- Credit/funding/rental review
- Vendor assignment if needed
- Scheduled client updates
- Standard turnaround times
- Normal QC review

### Heavy Escalation

Used for high-value clients, urgent deadlines, stuck files, vendor delays, complex funding opportunities, complaint risk, or owner-priority cases.

Heavy escalation should be owner-controlled or manager-approved.

Includes:

- Owner or senior manager review
- Priority vendor assignment
- Multi-vendor comparison
- Deeper document review
- Additional funding route review
- Direct partner outreach
- Faster client update cadence
- Stronger QC requirements
- Escalation notes locked to internal users only

## Escalation Triggers

Automatically flag a client/order for review when:

- Client paid above a high-value threshold
- Client has urgent funding deadline
- Client is at refund or chargeback risk
- Vendor is past due
- Client has complained
- Funding denial occurred
- Documents are incomplete for more than 7 days
- Rental handoff is blocked
- Client has strong funding potential
- Owner manually marks as priority

## Escalation Levels

### Level 1: Manager Review

Use when:

- Client is confused
- Documents are delayed
- Normal workflow is stuck
- Staff needs decision support

Actions:

- Review account
- Update task owner
- Send client update
- Adjust due dates
- Add notes

### Level 2: Vendor Pressure / Reassignment

Use when:

- Vendor misses deadline
- Vendor quality is weak
- Client needs faster turnaround

Actions:

- Message vendor
- Set new deadline
- Request deliverable
- Reassign to backup vendor
- Mark vendor scorecard
- Hold payment if contract allows

### Level 3: Owner Heavy Mode

Use when:

- High-value client
- Complex funding route
- Major complaint risk
- Major revenue opportunity
- Strategic relationship

Actions:

- Owner review
- Senior vendor assignment
- Partner/lender direct outreach
- Deal desk review
- Margin exception approval
- Custom client plan
- Increased update cadence

### Level 4: Legal / Compliance Review

Use when:

- Client threatens legal action
- Chargeback filed
- Vendor compliance issue
- Disputed claim
- Sensitive document issue
- Potential advertising/sales claim concern

Actions:

- Freeze risky communication
- Pull client file
- Review contracts and disclosures
- Document timeline
- Prepare response
- Escalate to attorney if needed

## Internal Visibility Rules

Client-facing users should see:

- Current status
- Required client actions
- Appointment dates
- Approved updates
- Completed milestones

Internal staff should see:

- Notes
- Vendor assignments
- Tasks
- Client risk flags
- Operational bottlenecks

Owner/admin only should see:

- Vendor costs
- Margin
- Sensitive escalation notes
- Vendor performance issues
- Refund/chargeback risk
- Heavy mode strategy
- Partner/lender route notes

## Heavy Mode Dashboard

Build a dashboard section called:

`/admin/heavy-mode`

Widgets:

- Priority clients
- High-value deals
- Stuck fulfillment orders
- Vendor past due
- Funding rework cases
- Complaint/chargeback risk
- Owner approval needed
- Margin exceptions
- Legal/compliance review

## Heavy Mode Case File

Each heavy mode case should include:

- Client
- Reason for escalation
- Current service path
- Revenue collected
- Vendor cost
- Margin
- Assigned senior owner
- Open blockers
- Next 3 actions
- Client update plan
- Vendor pressure plan
- Compliance notes
- Final resolution

## Approved Heavy Mode Tactics

Allowed:

- Faster turnaround
- More detailed review
- Better vendor
- Backup vendor
- Direct partner outreach
- Additional document cleanup
- Better client education
- More frequent updates
- Internal margin exception
- Custom payment arrangement
- Rework after denial
- Escalated quality control

Not allowed:

- Fake documents
- False disputes
- Misrepresenting income or revenue
- Misleading lender applications
- Guaranteeing outcomes
- Hiding required terms from clients
- Making claims the company cannot prove
- Using vendor work without QC

## Cursor Build Instruction

Add Heavy Mode to the admin dashboard.

Required screens:

- `/admin/heavy-mode`
- Heavy mode case list
- Heavy mode case detail
- Escalation level selector
- Owner-only notes
- Next 3 actions panel
- Vendor pressure/reassignment panel
- Client update plan
- Compliance review flag
- Margin exception approval

Required permissions:

- Admin can see all heavy mode data.
- Operations Manager can see operational escalation data.
- Staff can see assigned tasks only.
- Clients never see heavy mode notes.
- Vendors never see internal heavy mode notes.

Use placeholder data first.
