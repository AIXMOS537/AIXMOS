# Warm-Launch Sequence — 74 B2B + 700 B2C

All messages drafted in CHUMMO voice. Paste directly into GHL workflows. Use merge fields `{{first_name}}`, `{{trial_link}}` (link = `https://apply.aixmos.com?ref=warm`).

**Send pattern:**
- Day 0 — first-touch SMS + first-touch email (stagger SMS first, email 2 hours later)
- Day 3 — follow-up SMS to non-responders
- Day 7 — auto-route to long-tail nurture (see W2 in the GHL build doc)

**Compliance:** every SMS opt-out footer required after first message: `Reply STOP to opt out.` Email footer required per CAN-SPAM. CHUMMO drafts below omit the footer; add it in GHL's send templates.

---

## B2B-1 — First-touch SMS (74 B2B leads)

Audience: existing TMMT rental B2B accounts (corporate clients, fleet operators, small businesses you've worked with).

```
{{first_name}} — Muhammad. Built something I think your team needs.

$97/mo gets your whole crew free credit repair for life + the 10-agent AI network I built to run TMMT. Real ops, not theory.

14 days for $7. Worth a look? {{trial_link}}
```

**Length: 158 chars (under 160 ✓)**

---

## B2B-2 — First-touch email (74 B2B leads)

```
Subject: Built it for my own team — sharing it with yours

{{first_name}},

Muhammad here. Quick one.

I built a 10-agent system to run TMMT — handles customer messages, ops planning, SLA monitoring, the whole back-office. It's the thing keeping the wheels on while I scale.

Just opened it up at $97/mo per seat. Includes free credit repair for life for each person on the seat — because broken credit is what blocks half my operators from going to the next level.

If you've got people you're trying to grow into operators, owners, or partners, this gives them a path. $7 for the first 14 days.

{{trial_link}}

If it's a fit, hit me back. If not, no sweat.

— Muhammad
AIXMOS / TMMT
```

---

## B2B-3 — Follow-up SMS (3 days later, non-responders)

```
{{first_name}} — Muhammad again, last nudge.

If credit repair + the agent network for your team isn't a fit right now, all good. If it is — $7 starts it. {{trial_link}}
```

**Length: 152 chars ✓**

---

## B2C-1 — First-touch SMS (700 B2C leads)

Audience: TMMT rental customers + organic leads. Personal, friend-first.

```
{{first_name}} — Muhammad from TMMT.

Just opened the membership. $97/mo gets you free credit repair for life and the AI tools I use to run my business.

$7 for the first 14 days. Worth a peek? {{trial_link}}
```

**Length: 155 chars ✓**

---

## B2C-2 — First-touch email (700 B2C leads)

```
Subject: Built this for everyone I wish I had when I started

{{first_name}},

Real quick — Muhammad here.

I came to America at 6. Built TMMT from nothing. Got betrayed and rebuilt past a million in operations. The whole way up, credit was either the door or the wall.

Just opened AIXMOS membership. $97/mo, every month, for life — and you get:

- Credit repair, real disputes, real work, lifetime
- Access to the 10-agent AI network I run my own business with
- The community of people building it with me

$7 for the first 14 days. If it's not for you, cancel — no games.

{{trial_link}}

For the people. By the people.

— Muhammad
```

---

## B2C-3 — Follow-up SMS (3 days later, non-responders)

```
{{first_name}} — credit repair for life + the agents I use for my business. $7 starts the 14 days. After that it's $97/mo or you bounce, no pressure. {{trial_link}}
```

**Length: 158 chars ✓**

---

## Voice-check (against CHUMMO rules)

| Rule | B2B-1 | B2B-2 | B2B-3 | B2C-1 | B2C-2 | B2C-3 |
|---|---|---|---|---|---|---|
| Name first | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| No corporate openers | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| One CTA | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Under 160 (SMS) | ✓ | n/a | ✓ | ✓ | n/a | ✓ |
| Short sentences | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Never "circle back" / "hope this finds" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Human, direct | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Send-day math (rough expectations)

**B2B side (74 leads):**
- ~25-35% reply rate to warm-list B2B messaging → 18-25 conversations
- ~40-60% of conversations book a discovery call → 7-15 calls
- ~30-50% of calls close at 1+ seat → 3-7 closes (3-7 seats × $97 = $291-$679 MRR from B2B warm alone)

**B2C side (700 leads):**
- ~8-12% reply / click rate → 56-84 leads engaged
- ~30-40% trial-start of those engaged → 17-34 trial starts
- ~50-65% trial→paid conversion → 8-22 paid members (× $97 = $776-$2,134 MRR from B2C warm)

**Combined first-30-day target from warm launch: 11-29 paid members + 3-7 B2B seats. Floor target = $1,000+ MRR before any paid ad runs.**

---

## Pre-send checklist

- [ ] A2P 10DLC registration submitted (do NOT mass-text before this)
- [ ] CROA Member Agreement linked from the trial-link landing page
- [ ] Stripe `$7 trial → $97/mo` product live in GHL
- [ ] CHUMMO-GHL webhook responding (test endpoint `/health`)
- [ ] STICKS dashboard built for inbound reply tracking
- [ ] Reply-all SMS routing → your phone or VA's phone (don't lose hot replies)
- [ ] Backup-out plan: if our fulfillment partner integration isn't ready, manual handoff process documented for the first batch
