# A2P 10DLC Registration — Ready-to-Paste

Submit through GHL: **Settings → Phone Numbers → Trust Center → Brand & Campaigns**. This document gives you the exact field values to paste, plus the website disclosure copy that has to appear on your landing pages BEFORE you submit (carrier reviewers visit your URL during vetting).

**Timing:** Brand approval = 1-3 business days. Campaign approval = 1-3 weeks after brand. Don't ship the warm-launch SMS until both are GREEN.

**Vertical note:** Credit repair is in a higher-scrutiny bucket. Be precise, be honest, don't hype. Carriers reject vague campaigns 70% of the time on the credit repair vertical.

---

## Part 1 — Brand Registration (one-time)

| Field | Value |
|---|---|
| **Legal business name** | All In One Management Solutions LLC |
| **DBA / Brand name** | AIXMOS |
| **Brand alias for display** | AIXMOS |
| **Entity type** | Private For-Profit (LLC) |
| **EIN / Tax ID** | [your EIN, format: XX-XXXXXXX] |
| **Country of registration** | United States |
| **State of registration** | Maryland |
| **Business address line 1** | [your registered MD business address] |
| **Business address line 2** | [suite, if any] |
| **City / State / ZIP** | [your city] / MD / [ZIP] |
| **Business phone (must be reachable)** | [your business line — not the 10DLC number you're registering] |
| **Website URL** | https://aixmos.com (must be live with privacy + terms BEFORE submitting) |
| **Vertical / Industry** | Professional Services (closest match — `Financial` requires lender status) |
| **Sub-vertical** | Credit Repair / Financial Education |
| **Stock symbol / exchange** | N/A (private) |
| **Brand relationship** | Basic (upgrade to Standard after first 30 days of clean sending) |
| **Authorized representative — name** | Muhammad Taha |
| **Authorized representative — email** | muhammad@aixmos.com |
| **Authorized representative — phone** | [your direct line] |
| **Authorized representative — title** | Founder / Managing Member |
| **Brand description (1-3 sentences)** | AIXMOS is a membership network for entrepreneurs that provides credit repair fulfillment (via licensed white-label partner), business operations tooling, and a verified operator community. Members opt in through our website to receive transactional account notifications and optional marketing messages about their membership. |

### Optional but recommended: Standard Vetting

Pay the extra $40 for Aegis Mobile vetting. It raises your throughput from ~3,000 segments/day to 15,000+/day across carriers and dramatically improves campaign approval odds for credit-adjacent verticals. Worth it.

### Things to have ready BEFORE you click submit

- [ ] **aixmos.com is live** with: homepage, Privacy Policy, Terms of Service, Member Agreement, contact page
- [ ] **Privacy Policy explicitly states:** "We do not share your phone number or SMS opt-in data with third parties or affiliates for marketing purposes." (Carriers reject brands that don't have this exact-meaning clause.)
- [ ] **Business phone answered** by you, a VA, or a forwarding service. Reviewers do call sometimes.
- [ ] **EIN matches the IRS letter** — typo on EIN = 5-day delay.
- [ ] **MD business address matches your SDAT registration** — mismatch = rejection.

---

## Part 2 — Campaign 1 of 2: Account Notifications (Transactional)

This is the lower-risk campaign. Approve this first, start using it, then submit the marketing campaign once you have clean sending history.

| Field | Value |
|---|---|
| **Campaign name (internal)** | AIXMOS Membership — Account Notifications |
| **Use case** | Account Notification (TCR primary code: `ACCOUNT_NOTIFICATION`) |
| **Sub-use cases (multi-select if asked)** | Customer Care, 2FA (if you do login OTP), Polling/Voting (no — leave unchecked) |
| **Campaign description (1-3 sentences)** | Transactional messages sent only to AIXMOS members who have opted in via aixmos.com. Messages include trial start confirmations, payment receipts and failure notices, credit-dispute status updates, account changes, and onboarding instructions. Members can reply STOP at any time to opt out, or HELP for support. |
| **Message flow / opt-in description** | Consumers opt in via the trial sign-up form on apply.aixmos.com (and sub-paths). The form contains an explicit SMS consent checkbox with disclosure language (see Part 4 below). Consent is recorded with timestamp, IP, and form-version in our CRM. No SMS is sent prior to checkbox confirmation. |
| **Embeds links?** | Yes (yes — to member portal, trial-confirmation, payment-update links) |
| **Embeds phone numbers?** | Yes (support line for HELP responses) |
| **Age-gated content?** | No |
| **Direct lending / loan content?** | No (you are not a direct lender — credit repair is the service) |
| **Affiliate marketing?** | No (this campaign is transactional only) |
| **Number pool (number of phones)** | 1 (start with one number, expand later) |
| **Estimated monthly throughput** | 500–5,000 messages in month 1 (be conservative on first submission) |
| **Throughput tier requested** | Low-Volume Standard |
| **Opt-out keywords** | STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT |
| **Help keywords** | HELP, INFO |

### Sample messages (paste 5 — TCR requires real, plausible samples)

```
1. Hey Marcus — your AIXMOS trial just started. Reply ID with a picture of your ID to fast-track your file. Help: reply HELP. Stop: reply STOP.

2. Marcus, your $7 AIXMOS trial converted to $97/mo today. Receipt: aixmos.com/r/4A92. Manage anytime at members.aixmos.com. Reply STOP to opt out.

3. AIXMOS: Your first dispute round was mailed today. Bureau response in 30-45 days. Questions? Reply HELP. Reply STOP to opt out.

4. Marcus, your card on file at AIXMOS failed today. Update: members.aixmos.com/billing. Reply HELP for support. Reply STOP to opt out.

5. AIXMOS: Office hours tomorrow at 7pm ET. Join: members.aixmos.com/oh. Reply STOP to opt out.
```

### Required auto-responses

| Keyword | Auto-response (paste exactly into GHL) |
|---|---|
| HELP, INFO | `AIXMOS — All In One Management Solutions LLC. Support: hello@aixmos.com or [your business phone]. Reply STOP to opt out. Msg & data rates may apply.` |
| STOP, UNSUBSCRIBE, CANCEL, END, QUIT, STOPALL | `You're unsubscribed from AIXMOS SMS. No more messages will be sent. Email hello@aixmos.com to re-opt-in.` |

---

## Part 3 — Campaign 2 of 2: Marketing

Submit this AFTER Campaign 1 is approved and you've sent ~100+ clean transactional messages.

| Field | Value |
|---|---|
| **Campaign name (internal)** | AIXMOS Membership — Marketing & Nurture |
| **Use case** | Marketing (TCR primary code: `MARKETING`) |
| **Sub-use cases** | Customer Care, Promotional |
| **Campaign description (1-3 sentences)** | Marketing messages sent only to leads and members who have opted in via aixmos.com or related funnels. Messages include trial reminders, event invitations (DMV-region workshops), member success stories, promotional offers, and educational content related to credit and entrepreneurship. Members can reply STOP at any time. |
| **Message flow / opt-in description** | Same as Campaign 1 — opt-in on aixmos.com trial sign-up form with explicit SMS consent checkbox and disclosure (Part 4). Consent timestamp, IP, and form-version logged in CRM. Marketing messages are sent only to contacts whose record shows verified opt-in for marketing specifically. |
| **Embeds links?** | Yes |
| **Embeds phone numbers?** | No (marketing keeps phone out to reduce spam-flag risk) |
| **Age-gated content?** | No |
| **Direct lending / loan content?** | No |
| **Affiliate marketing?** | No (your 50/50 affiliate program does not push SMS through the marketing campaign — affiliates have their own channels) |
| **Number pool** | 1 (same as Campaign 1 — can pool if needed) |
| **Estimated monthly throughput** | 1,000–10,000 messages |
| **Throughput tier requested** | Low-Volume Standard |
| **Opt-out keywords** | STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT |
| **Help keywords** | HELP, INFO |

### Sample messages (paste 5)

```
1. Marcus — Muhammad here. Saw you grabbed the credit starter pack. $7 starts your 14-day AIXMOS trial: aixmos.com/r/x. Reply STOP to opt out.

2. AIXMOS — DMV workshop next Tuesday at 7pm in Silver Spring. Free RSVP: aixmos.com/dmv. Reply STOP to opt out.

3. Marcus — credit repair for life + the AI ops network I built running TMMT. $97/mo. Start with $7: aixmos.com/r/x. STOP to opt out.

4. AIXMOS: A member's score just crossed 700 — full breakdown in tonight's office hours. Members get the link automatically. Not in yet? aixmos.com. STOP to opt out.

5. Marcus, last nudge — your AIXMOS trial offer expires at midnight. $7 starts 14 days: aixmos.com/r/x. Reply STOP to opt out.
```

### Why no embedded phone in marketing

Carriers flag SMS that contain both a link AND a phone number as higher spam-risk in marketing campaigns. Transactional campaign keeps the phone (support context); marketing campaign keeps just the link.

---

## Part 4 — Required website disclosure (MUST be on aixmos.com BEFORE submitting)

This is the single most common rejection reason. The carrier reviewer visits your trial-signup form and looks for the exact pattern below. Copy it verbatim.

### A. SMS consent checkbox copy (under the phone field on every signup form)

```
☐ I agree to receive recurring automated text messages (SMS) from AIXMOS at the
phone number provided, including account notifications, trial reminders, billing
notices, dispute updates, event invites, and promotional offers. Consent is not a
condition of purchase. Message frequency varies. Message & data rates may apply.
Reply HELP for help, STOP to cancel. View our Privacy Policy at aixmos.com/privacy
and Terms at aixmos.com/terms.
```

The checkbox MUST be:
- Unchecked by default (no pre-checked checkboxes — that's a hard rejection)
- Required to proceed (form won't submit unless ticked)
- Separately ticked from the Terms of Service checkbox (don't bundle consents)

### B. Privacy Policy must contain this exact-meaning section

Paste this section into `aixmos.com/privacy` under a heading **"SMS / Text Messaging"**:

```
SMS / Text Messaging

When you opt in to receive text messages from AIXMOS, we collect and process the
phone number you provide and the timestamp of your consent. We use this number
to send you transactional and marketing messages about AIXMOS services.

We do not share your mobile phone number, SMS opt-in data, or consent records with
third parties or affiliates for their marketing purposes. We may share your phone
number with our credit-repair fulfillment partner only to the extent necessary to
provide the credit-repair service you purchased.

You can opt out of SMS at any time by replying STOP to any message. You can request
help by replying HELP. Standard message and data rates may apply.

For SMS-related questions, contact hello@aixmos.com.
```

### C. Terms of Service must reference messaging consent

Add to `aixmos.com/terms` under "Communications":

```
By providing your phone number and ticking the SMS consent box on our sign-up
forms, you agree to receive recurring automated text messages from AIXMOS,
including transactional account notifications and (if opted in) marketing
messages. Consent is not a condition of purchase. You can opt out at any time
by replying STOP.
```

---

## Part 5 — Per-message footer requirements (in addition to STOP/HELP)

Every marketing SMS must include either:
- The brand name (AIXMOS) in the body, AND
- "Reply STOP to opt out" (or equivalent) at least every fourth message

Transactional SMS can drop the STOP footer after the first few messages BUT including it every time is safest. Carriers don't penalize over-disclosure.

Embedded link best practices:
- Use a branded short link (`aixmos.com/r/xxxx`) — NOT bit.ly, NOT tinyurl. Carriers flag generic shorteners as phishing-suspect.
- Set up a redirect service at `r.aixmos.com` if branded shortlinks aren't feasible inside GHL — Cloudflare Workers can do this in 30 lines of code.

---

## Part 6 — Common rejection reasons (avoid these)

| Rejection reason | What it actually means | Fix |
|---|---|---|
| "Sample messages don't match campaign description" | You said "transactional" but sample looks promotional | Make sure samples reflect the use case exactly |
| "Missing opt-in flow" | Reviewer couldn't find the consent checkbox on your form | Make it visible above the fold + the exact copy in Part 4A |
| "Privacy policy missing SMS clause" | Reviewer looked at your privacy page, didn't see the section | Add the Part 4B section verbatim |
| "Embedded link uses unbranded shortener" | bit.ly / tinyurl / t.ly etc. | Switch to branded `aixmos.com/r/xxx` |
| "Brand identity not verifiable" | EIN mismatch, address mismatch, or no business phone answered | Verify EIN with IRS letter; confirm SDAT registration; have phone manned |
| "Direct lending content flagged" | You said "no direct lending" but messages mention loans or interest rates | Don't talk about lending in any message. Stay strictly on credit repair service. |
| "Inconsistent brand name" | Form says "AIXMOS", privacy page says "All In One Management Solutions", footer says something different | Keep it consistent — use "AIXMOS (All In One Management Solutions LLC)" |
| "Suspected credit repair gating" | Implying you can guarantee credit improvements | Strip any "guaranteed" language; CROA forbids it anyway |

---

## Part 7 — Submission sequence (do these in order)

| Step | Action | Owner |
|---|---|---|
| 1 | Make sure aixmos.com is live with homepage + privacy + terms + Member Agreement | TANK (build) |
| 2 | Add SMS consent checkbox to all 4 funnel sign-up forms (Part 4A copy verbatim) | TANK |
| 3 | Add the Part 4B SMS section to privacy policy | You / counsel |
| 4 | Add the Part 4C Communications section to terms | You / counsel |
| 5 | Smoke-test the signup form: submit a real signup → confirm consent is logged in GHL with timestamp + IP + form version | You |
| 6 | In GHL Trust Center, submit Brand registration with Part 1 values | You (in GHL UI) |
| 7 | Wait for brand approval (1-3 business days) | — |
| 8 | After brand approved, submit Campaign 1 (transactional) with Part 2 values | You |
| 9 | Wait for Campaign 1 approval (~1-3 weeks) | — |
| 10 | Send first 100+ transactional messages (real trial signups), keep delivery rate >95% | CHUMMO + STICKS monitor |
| 11 | Submit Campaign 2 (marketing) with Part 3 values | You |
| 12 | After Campaign 2 approved, run the warm-launch sequence to 700 B2C + 74 B2B | CHUMMO + you |

**Hard rule:** do NOT mass-text the 700 B2C list before Campaign 2 is approved. Carriers will shut your number down and the brand reputation hit follows you to future numbers.

---

## Part 8 — Backup plan if registration takes longer than expected

If Campaign 2 (marketing) is stuck >3 weeks:

**Plan A — Email-first warm launch.** Send the B2C-2 and B2B-2 emails from `WARM-LAUNCH.md` to the full warm list. Email doesn't need A2P 10DLC. SMS follow-up runs only after registration is green.

**Plan B — Voice / direct call.** For the 74 B2B leads, JARVIS-style direct calls don't need 10DLC. Call them, refer to the email, book discovery calls.

**Plan C — Manually paced SMS at low volume.** Up to ~10 SMS per hour from an unregistered 10DLC works but is risky. Don't recommend it; only use if a single high-value B2B lead is hot and waiting.

---

## Part 9 — After approval: monitoring

STICKS monitors these daily in GHL:

| Metric | Healthy | Investigate if |
|---|---|---|
| Delivery rate | >95% | <90% |
| Opt-out rate | <2% | >3% (campaign-level) |
| Complaint / spam rate | <0.5% | >1% (any) |
| Reply rate (transactional) | n/a — informational | — |
| Reply rate (marketing) | 1-5% is normal | <0.5% = list quality issue |

If opt-out rate spikes >3%, pause the campaign and review the last 50 sent messages with VISION before resuming. The carriers track this and a single bad week can downgrade your brand for months.

---

## Quick reference card (laminate this)

```
BRAND:     AIXMOS (All In One Management Solutions LLC)
EIN:       [your EIN]
WEBSITE:   aixmos.com
SUPPORT:   hello@aixmos.com / [phone]
CAMPAIGN 1: Account Notifications (transactional)
CAMPAIGN 2: Marketing & Nurture
STOP / HELP: auto-replies set in GHL (Part 2 + Part 3 tables)
NEVER:     pre-checked checkboxes, generic shorteners, "guaranteed score", direct-lending language
ALWAYS:    branded short link, STOP footer, opt-in timestamp logged
```
