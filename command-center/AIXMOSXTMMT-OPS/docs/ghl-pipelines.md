# GHL Pipelines

## Applicants – Dealership

Stages: `New lead` → `Contacted` → `Qualified` → `Appointment set` → `Showed` → `Application in` → `Approved / conditional` → `Sold / placed` → `Lost`

Fields: `source`, `vehicle_interest`, `budget`, `timeline`, `rental_customer_yn`, `compliance_flags`

SLA: New lead → Contacted in 15 minutes (business hours).

## Partners – Empire

Stages: `Target list` → `First touch` → `Meeting set` → `Pilot deal` → `Active partner` → `Scaling` → `Dormant`

Fields: `business_name`, `owner_name`, `niche`, `geography`, `they_want`, `we_offer`, `next_action_date`

## Level A

- n8n may update internal systems (green).
- SMS/email to humans only via `webhook_approve_send` (yellow).
