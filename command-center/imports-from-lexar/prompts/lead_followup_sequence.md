# TMMT Lead Follow-Up Sequence

## How to use this
Identify which stage the lead is in from their Airtable notes, then send the matching message.
Personalize [NAME] and [CAR TYPE] before sending. Send via text/WhatsApp.

---

## STAGE 1 — First contact (new lead, no notes yet)
**Trigger:** Lead just came in, never been contacted.

**Text:**
> Hey [NAME], this is [YOUR NAME] from TMMT Rentals.
> I saw you were interested in renting a car for Uber/Lyft.
> We have vehicles available starting this week — weekly rates from $300.
> Want me to send over the quick rental form to get you started?

**Airtable note to add:** `Day 1 - first text sent`

---

## STAGE 2 — Form sent, no response (1-3 days)
**Trigger:** Notes say "form sent" or "form sent, no response"

**Text:**
> Hey [NAME], just checking in — did you get the form I sent?
> Takes about 2 minutes to fill out and we can have you in a car by [DAY].
> Let me know if you have any questions or if the link didn't come through.

**Airtable note to add:** `Day 3 - follow-up sent`

---

## STAGE 3 — No response after follow-up (3-5 days)
**Trigger:** Notes say "3 days no response" or "reached multiple times"

**Text:**
> Hey [NAME], last check-in from me.
> I have a [CAR TYPE] available right now at $[PRICE]/week — this is perfect for Uber/Lyft drivers.
> If timing isn't right, no worries. Just reply STOP and I won't reach out again.
> If you're still interested, reply YES and I'll hold a spot for you today.

**Airtable note to add:** `Day 5 - final follow-up sent`

---

## STAGE 4 — Unavailable / busy
**Trigger:** Notes say "unavailable" or "call declined"

**Text:**
> Hey [NAME], I know you've been busy — no pressure.
> When you're ready to get on the road with Uber/Lyft, we're here.
> We usually have cars available same week. Just reply anytime and I'll get you set up fast.

**Airtable note to add:** `Soft hold - replied when ready`

---

## STAGE 5 — On waitlist
**Trigger:** Notes say "on wait list"

**Text:**
> Good news [NAME] — a spot just opened up on our fleet.
> You were on our waitlist so I wanted to reach out first before we post it.
> Can you come in this week? Reply YES and I'll hold it for 24 hours.

**Airtable note to add:** `Waitlist - spot offered [DATE]`

---

## STAGE 6 — Not eligible (re-engage later)
**Trigger:** Notes say "not eligible" or "12 criminal records" or "not eligible SS"

**Text:**
> Hey [NAME], we weren't able to approve your application at this time.
> Requirements do change — if your situation has updated, feel free to reach back out.
> We'd love to get you on the road when the time is right.

**Airtable note to add:** `Not eligible - soft close [DATE]`

---

## STAGE 7 — Not interested (close it out)
**Trigger:** Notes say "not interested" or "DND"

> DO NOT contact. Mark as closed in Airtable.

**Airtable note to add:** `Closed - not interested [DATE]`

---

## STAGE 8 — Re-engage cold leads (90+ days old)
**Trigger:** Lead went cold 3+ months ago with no hard "not interested"

**Text:**
> Hey [NAME], it's been a while — this is [YOUR NAME] from TMMT Rentals.
> Just wanted to check back in. We have new cars on the fleet and rates are still competitive.
> Still thinking about driving for Uber/Lyft? I can get you started fast.

**Airtable note to add:** `Re-engaged [DATE]`

---

## TEAM RULES
1. Every lead gets a note update after EVERY contact attempt — date + initials + what happened
2. No lead sits more than 3 days without a note update
3. After Stage 3 with no response — move to "Cold" status in Airtable
4. Never send more than 3 unsolicited texts to the same number
5. If they say stop / not interested / DND — stop immediately, mark closed
