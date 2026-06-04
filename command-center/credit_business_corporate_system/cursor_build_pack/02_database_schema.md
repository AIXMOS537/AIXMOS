# Database Schema Draft

## users

- id
- full_name
- email
- phone
- role
- brand_access
- status
- created_at

## leads

- id
- source
- brand
- first_name
- last_name
- email
- phone
- goal
- pipeline_stage
- assigned_to
- created_at
- updated_at

## readiness_scorecards

- id
- lead_id
- credit_score_range
- negative_items
- has_business_entity
- has_business_bank_account
- monthly_revenue_range
- has_bank_statements
- funding_goal
- vehicle_interest
- readiness_score
- recommended_path
- created_at

## clients

- id
- lead_id
- user_id
- program_type
- status
- onboarding_status
- credit_status
- funding_status
- rental_status
- start_date
- account_owner

## documents

- id
- client_id
- document_type
- file_url
- status
- reviewed_by
- reviewed_at
- notes

## tasks

- id
- title
- description
- assigned_to
- related_client_id
- related_lead_id
- status
- priority
- due_date

## pipeline_events

- id
- lead_id
- client_id
- from_stage
- to_stage
- changed_by
- notes
- created_at

## rental_applications

- id
- client_id
- lead_id
- driver_license_status
- insurance_status
- payment_status
- desired_vehicle_type
- rental_start_date
- status
- notes

## vehicles

- id
- unit_number
- year
- make
- model
- vin
- plate
- status
- daily_rate
- weekly_rate
- monthly_rate

## rentals

- id
- vehicle_id
- client_id
- start_date
- end_date
- payment_status
- contract_status
- return_status
- notes

## sop_documents

- id
- title
- department
- role
- content
- version
- status
- owner
- updated_at

## training_modules

- id
- title
- role
- department
- content
- quiz_required
- status

## training_progress

- id
- user_id
- training_module_id
- status
- completed_at
- score

## kpi_snapshots

- id
- week_start
- leads
- booked_calls
- showed_calls
- closed_deals
- revenue_collected
- refunds
- chargebacks
- funding_submissions
- funding_approvals
- rental_customers
- rental_revenue
- notes
