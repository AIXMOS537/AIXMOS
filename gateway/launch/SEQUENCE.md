# TMMT Rentals — YES-Reply Close Sequence (SOP)

When a lead replies YES, run this exact sequence so every customer closes the same way.
Maps to your Airtable: Incoming Leads → Background Checks → Waitlist/Appointments → Active Customers
(Status "Contracting" moves them) → Contracts → Vehicle Handover.

## Step 0 — Reply fast (within 5 min beats everything)
> "Awesome {name}! Two quick things and I'll lock in your car:
> 1) What city/when do you need it? 2) I'll text you a 2-min verification link."
Set Incoming Leads **Status = Contacting**, add Notes ("YES — wants {car}, {date}").

## Step 1 — Verification / Background Check
- Send the verification form (collects license, insurance, paystub → **Background Checks** table).
- Wait for **Eligibility Status = Eligible** (and check **Do Not Rent List**).
- ❌ Not eligible / on DNR → polite decline, log reason. ✅ Eligible → continue.

## Step 2 — Match the car + book the viewing
- Match to an **Available** vehicle (Fleet). Confirm weekly price.
- Create an **Appointment** (Appointment Type = viewing/pickup, date/time, location, assigned staff).
- Text confirmation: "You're set for {day/time} at {location} to see the {car}. Bring your license + proof of insurance."

## Step 3 — Contract
- Generate a **Contract** (vehicle, start/end, base price, taxes/fees, insurance fee, total).
- Send for e-signature → set **Contract Status = Sent**, then **Signed** on signature.
- Collect first payment (Customer Payments: method, amount, next due date).

## Step 4 — Handover
- Complete **Vehicle Handover**: required docs (license, insurance, inspection, registration) checked.
- **Customer Inspection Photos** (condition before leaving) + odometer.
- Flip **Incoming Leads Status = Contracting** → they auto-move to **Active Customers**.
- Set Fleet vehicle status = Rented; link customer.

## Step 5 — First-week follow-up (retention)
- Day 2: "How's the {car} treating you?" Day 6: payment reminder before due date.
- Log payment reliability; flag any ticket/maintenance early.

## Credit-to-keys upsell (if applicable)
- For customers on the credit path: track in the program tables, surface the "rent → own" milestone.
- ⚠️ Compliance: don't promise specific credit-score outcomes; keep credit-repair claims clean (CROA).

## Texting
- Use the Incoming Leads **SMS Number (auto)** field (E.164) with your Quo/AI texting system.
- Once Quo SMS is wired, AIXMOS can auto-send Steps 0–2 and only escalate to a human on YES.
