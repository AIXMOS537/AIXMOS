# 🚦 Dispatch / Fleet Ops — Playbook
_Part of the [[operator-os]] vertical playbooks. Pairs with [[tmmt-system]], [[people-hub]], [[onboarding-offboarding]]._
_Steps below are **DRAFT defaults** — correct anything that doesn't match how TMMT actually runs._

## What this vertical does
Day-to-day vehicle movement, maintenance coordination with mechanics/shops, and vendor coordination so the fleet stays available.

## Systems it touches
TMMT app (fleet status, `vendors`, `shops_mechanics_cleaning`) · ClickUp (job assignment) · Calendar (service/move times) · OpenPhone (driver/vendor contact).

## Roles
dispatch · operator.

## SOP 1 — Vehicle movement (pickup / drop / swap / to-shop)
- [ ] Need identified -> create ClickUp task (which vehicle, from, to, by when)
- [ ] Assign a driver/operator + time; confirm via OpenPhone
- [ ] Pre-move check: keys, fuel, condition photos, plates/docs in vehicle
- [ ] Driver confirms completion (photo at destination)
- [ ] Update vehicle location + status in the app

## SOP 2 — Maintenance / shop
- [ ] Issue logged (what's wrong, urgency) -> choose mechanic/shop from `shops_mechanics_cleaning`
- [ ] Get estimate; if over the approval cap, get owner/manager sign-off first
- [ ] Send vehicle in; mark it **unavailable** so it can't be booked
- [ ] Track status in/out of shop; keep ClickUp updated
- [ ] On return: verify the fix, update status to **available**

## SOP 3 — Vendor jobs
- [ ] Assign job to the right vendor (cleaning/moving/repair)
- [ ] Confirm scope + cost; track to completion; close the task

## Daily
- [ ] Review fleet board: what's out, due back, in shop, available
- [ ] Today's moves assigned + confirmed
- [ ] Flag availability gaps before they bite a booking

## The 4 KPIs (-> [[operator-scorecard-template]])
- 📋 **SOP adherence:** every move/job logged + status kept current
- ⚡ **Speed:** time-to-dispatch; minimize vehicle downtime
- 📦 **Output:** moves/jobs handled / week
- ✅ **Quality:** fewer errors (wrong vehicle/time), max fleet availability

## Training path
Read playbook -> shadow dispatcher 1 day -> handle moves supervised -> run a full day solo with check-ins -> cleared.
