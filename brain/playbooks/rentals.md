# 🚗 Vehicle Rentals — Playbook
_Part of the [[operator-os]] vertical playbooks. Pairs with [[tmmt-system]], [[people-hub]], [[onboarding-offboarding]]._
_Steps below are **DRAFT defaults** — correct anything that doesn't match how TMMT actually runs._

## What this vertical does
Bookings, fleet availability, customer handling, and operator/agency partners for the rental side of TMMT.

## Systems it touches
TMMT app (`active_customers`, `incoming_leads`, `operator_profiles`, `do_not_rent_list`) · OpenPhone (customer SMS/calls) · ClickUp (tasks) · Google Calendar (booking/handover times) · GHL (`ghl_contacts`).

## Roles
operator · dispatch · manager.

## SOP 1 — New booking (lead → confirmed)
- [ ] Capture the lead → log in `incoming_leads` (source, name, dates wanted, vehicle type)
- [ ] Respond within target time (see KPIs) via OpenPhone
- [ ] **Screen the renter:** valid driver's license, minimum age, proof of insurance; **check `do_not_rent_list`** before anything else
- [ ] Confirm a specific vehicle + dates are available (no double-book)
- [ ] Quote rate + deposit per current policy; confirm the renter agrees
- [ ] Send + get the signed rental agreement
- [ ] Collect deposit/payment hold
- [ ] Move record `incoming_leads` → `active_customers`; put handover on the calendar
- [ ] Send confirmation (date, time, location, what to bring) via OpenPhone

## SOP 2 — Handover (giving the vehicle)
- [ ] Verify ID matches the agreement
- [ ] Walk-around inspection **with photos/video** (all sides, existing damage, interior, dash)
- [ ] Record fuel level + odometer
- [ ] Confirm return date/time + late policy with the renter
- [ ] Hand over keys; log "out" status in the app

## SOP 3 — Return
- [ ] Walk-around inspection **with photos** + compare to handover
- [ ] Record fuel + odometer; apply fuel/mileage charges if any
- [ ] Note any new damage → start claim/charge process
- [ ] Release or deduct deposit per condition
- [ ] Mark vehicle returned; flag for cleaning/detail before next rental
- [ ] Thank-you + review request via OpenPhone

## SOP 4 — Daily
- [ ] Review today's pickups + returns on the calendar
- [ ] Chase overdue returns
- [ ] Update fleet availability; flag vehicles needing service/clean

## The 4 KPIs (-> [[operator-scorecard-template]])
- 📋 **SOP adherence:** booking + handover/return checklists fully completed, photos attached, do-not-rent checked
- ⚡ **Speed:** lead -> first response time; booking turnaround
- 📦 **Output:** bookings handled / week
- ✅ **Quality:** dispute/complaint rate, accurate records, deposits handled clean

## Training path
Read this playbook -> shadow 3 bookings -> 5 supervised bookings -> cleared solo on standard bookings -> handles exceptions/disputes = Senior.
