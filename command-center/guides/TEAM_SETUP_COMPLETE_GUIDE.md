# Team Setup — Complete Guide (Read Before Using Owner's PC)

**For:** Operators · Overseas VAs · Money lead · Fleet · Admin Recorder · Acting manager  
**Owner:** You set up accounts and tools first. Team works on **their own phones and computers**.

**Rule:** Nobody needs the owner's Mac for daily work. The owner's laptop is for building apps and owner review — not for shift posts or collections.

---

## 1. How everything fits together

```text
┌─────────────────────────────────────────────────────────────┐
│  TEAM (phones) — WhatsApp ops group                         │
│  SHIFT START / SHIFT END templates · English only         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  TRUTH LAYER (pick what is live — owner sets these up)      │
│  • Airtable — leads, tasks, payments, overdue flags         │
│  • GoHighLevel (GHL) — customer WhatsApp + rental pipeline  │
│  • TMMT Rentals web app — fleet, customers, tickets         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  OWNER (20 min/day) — reads chat + board, not 500 messages  │
│  COMMAND_CENTER · TODAY_COLLECTIONS · OWNER_DAILY_COMMAND   │
└─────────────────────────────────────────────────────────────┘

Owner Mac ONLY (do not share):
• Pre-Send Review (⌘⇧M) — owner message checker
• Local dev: AIXMOS, TMMT localhost — building/testing
• API keys (.env) — never in group chat
```

| Tool | Who uses it | What it is for |
|------|-------------|----------------|
| **WhatsApp ops group** | Everyone on shift | Shift reports, BLOCKED, handoffs |
| **GHL WhatsApp** | Sales / dispatch / money | **Customer** rental messages only |
| **Airtable** | Admin Recorder + leads | Structured records (if base is live) |
| **TMMT Rentals (web)** | Ops, fleet, manager | Dashboard — https://allinonemanagementsolutions.com (when login exists) |
| **ChatGPT / Claude** | Owner + managers | Morning decisions from pasted chat |
| **Owner Mac** | Owner only | Apps under development + review tools |

**Team rule (pin in chat):**  
> If it isn't in the shift post or Airtable by end of day, it didn't happen.

---

## 2. What is NOT set up yet (owner must do first)

Check these before telling the team "go live":

| Item | Status | Owner action |
|------|--------|--------------|
| Ops WhatsApp group | ⬜ | Create group, add all shift workers + Admin Recorder |
| Pinned START/END templates | ⬜ | VA follows `guides/VA_SETUP_TODAY.md` |
| Airtable base + team logins | ⬜ | Create base, invite by email, role views |
| GHL WhatsApp (customers) | ⬜ | `guides/WEEK_1_GHL_WHATSAPP.md` |
| TMMT staff logins | ⬜ | Create users in deployed app / Supabase auth |
| COMMAND_CENTER updated today | ⬜ | `TMMT/business-ops/OPERATIONS/COMMAND_CENTER.md` |
| Escalation rule (@OWNER) | ⬜ | Pin escalation template in ops chat |
| `.env` / API keys on owner Mac | ⬜ | Owner only — `AIX_AI_COMMAND_SYSTEM/.env` |

Until the first four rows are done, team runs on **WhatsApp templates + owner text instructions** only.

---

## 3. Owner setup (one afternoon — before team Day 1)

Do these in order. **Do not hand out your laptop.**

### Step A — WhatsApp ops (30 min)

1. Create **Main ops** WhatsApp group (English only for posts).
2. Add: operators, fleet, money VA, Admin Recorder, acting manager.
3. Send your VA `guides/VA_SETUP_TODAY.md` — they pin templates + rollout message.
4. Post today's **DAILY COMMAND** (collections + fleet list from COMMAND_CENTER).

### Step B — Airtable (45 min, if using)

1. Create or open TMMT base at [airtable.com](https://airtable.com).
2. Create personal access token (owner + Admin Recorder only).
3. Import templates: `AIX_AI_COMMAND_SYSTEM` → `./scripts/aix airtable sync-templates` (owner Mac, once).
4. Invite each person by **email** → **Editor** or **Commenter** per role (see §5).
5. Share link to their **view** only (Leads view, Tasks view, etc.).

### Step C — GHL customer WhatsApp (45 min)

Follow `guides/WEEK_1_GHL_WHATSAPP.md` Day 1.

Post in ops chat:

```text
CUSTOMER messages = GHL WhatsApp only.
INTERNAL shift updates = this ops group + START/END template.
```

### Step D — TMMT web app (30 min, when ready)

1. Production: https://allinonemanagementsolutions.com  
2. Create login per role (admin / ops / read-only) — owner or tech lead.
3. Send each person: URL + email + temp password (change on first login).
4. **They use browser on phone or PC** — not your Mac.

### Step E — Roles named (15 min)

Fill `Employees` or a simple roster doc:

| Role | Name | Phone | Tools |
|------|------|-------|-------|
| Acting Manager | | | Airtable + TMMT + ops chat |
| Money Lead | | | Airtable payments + GHL |
| Operations / Fleet | | | TMMT fleet + ops chat |
| Admin Recorder | | | Airtable + COMMAND_CENTER file access |
| VA / overseas | | | Ops chat (short template) |

---

## 4. Each team member — setup on THEIR device

### Everyone (15 min on phone)

1. **Join** the ops WhatsApp group (owner adds you).
2. **Save** pinned messages: SHIFT START, SHIFT END, team rule.
3. Install **Airtable** app (if owner sent invite).
4. Install **GoHighLevel** app or use GHL in browser (if you message customers).
5. **Do not** ask for owner Mac, Terminal, or API keys.

**First shift checklist:**

- [ ] Posted SHIFT START within 15 min of clock-in  
- [ ] Used customer **name + $** for every money line  
- [ ] Posted SHIFT END before log-off  
- [ ] Used @OWNER ESCALATION only for real blockers  

---

### Admin Recorder (plus 30 min)

**Job:** Turn chat into the daily board so owner reviews in 20 minutes.

**Setup:**

1. Airtable **Editor** on: Leads, Tasks, Payments, Decision log.
2. Access to update `COMMAND_CENTER.md` (Google Doc copy, Notion, or shared drive — owner chooses).
3. Read `guides/GROUP_CHAT_OPERATING_SYSTEM.md` Part 3.

**Daily:**

| Time | Task |
|------|------|
| Morning | Read overnight chat → update Top 3 + Active Tasks |
| Midday | Flag @OWNER escalations to owner DM |
| EOD | SHIFT END summary → Airtable + COMMAND_CENTER EOD section |
| Monday | Post WEEKLY OPS SUMMARY template |

**Send owner every morning:**

```text
OWNER BRIEF | [date]
• Top 5 overdue still open (name — $)
• Cash collected yesterday: $
• Fleet: down __ | maint overdue __
• Open BLOCKED (list)
• @OWNER items (list)
• Today top 3 for team: 1) 2) 3)
```

---

### Money Lead / collections VA

**Setup:**

1. GHL login — Conversations + contacts.
2. Airtable payments / overdue view.
3. Copy `TODAY_COLLECTIONS.md` queue (owner sends link or screenshot weekly).

**Daily:**

1. Work collections **top to bottom** (name + $ + outcome in chat).
2. Post **MONEY CHECK** midday (template in `GROUP_CHAT_TEMPLATES_PRINT.md` §D).
3. Log every payment in Airtable/GHL same day.

---

### Operations / Fleet

**Setup:**

1. TMMT login (fleet + maintenance screens) OR spreadsheet owner provides.
2. Ops WhatsApp — use FLEET template (§E in templates doc).

**Daily:**

1. Post vehicle status: Available / Rented / Shop.
2. Clear overdue maintenance list owner sends.
3. Confirm pickups/returns — no conflict before customer arrives.

---

### Sales / dispatch (leads & renters)

**Setup:**

1. GHL pipeline — rental stages (owner confirms names).
2. Message templates: `MESSAGE_TEMPLATE_LIBRARY.md` (owner shares PDF or link).
3. Ops chat for internal; GHL for **customers**.

**Daily:**

1. Follow up leads (name + channel + result in SHIFT post).
2. Log new leads in Airtable/GHL same day.

---

### Acting Manager (when owner is away)

**Setup:** All of the above views + `OWNER_DAILY_COMMAND.md` (manager sections).

**Authority:** Can approve payment plans, scheduling, vendor jobs — **not** legal/repo, new pricing, hiring, or API keys.

**Daily:** Run OWNER BRIEF for owner DM; resolve BLOCKED lines; escalate only what needs owner signature.

---

### Overseas VA (short English template)

Use **SHORT** template in `GROUP_CHAT_TEMPLATES_PRINT.md` §C.

Spanish / Tagalog / Urdu in `VA_SETUP_TODAY.md` Step 2B = **training only**, not for group posts.

---

## 5. What runs on the owner's Mac (team does NOT use)

| On owner Mac | Purpose | Team access |
|--------------|---------|-------------|
| `~/AIX-Ecosystem/pre-send-agent` | Review messages before send (⌘⇧M) | **No** — owner only |
| `localhost:3000` AIXMOS | Funding app in development | **No** |
| `localhost:3001` TMMT | Local dev copy | **No** — use production URL |
| `AIX-Command-Center` folder | Docs, SOPs, COMMAND_CENTER | **Copy/share** specific files only |
| `.env` API keys | Airtable, OpenAI, Supabase | **Never** share |

If someone says they need your computer: **default answer is no** — give them a login, screenshot, or shared doc instead.

---

## 6. Day 1 — team timeline (owner offline)

| Time | Who | Action |
|------|-----|--------|
| Shift start | Each operator | SHIFT START post |
| +2 hr | Money lead | MONEY CHECK or collections update |
| Midday | Fleet | FLEET post if anything changed |
| Before EOD | Everyone | SHIFT END |
| 6pm | Admin Recorder | OWNER BRIEF to owner DM |
| Urgent only | Anyone | @OWNER ESCALATION in ops chat |

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| "I need the boss laptop" | Use your phone + GHL/Airtable/TMMT link |
| "Template not pinned" | Admin Recorder or VA completes `VA_SETUP_TODAY.md` |
| "Where do I log payment?" | Airtable + GHL — ask Admin Recorder |
| "Customer texted personal WhatsApp" | Move thread to GHL; reply from GHL |
| "Supabase / dashboard empty" | Owner still wiring data — use chat + COMMAND_CENTER until live |
| "I don't have Airtable invite" | Owner Step B — send email invite |

---

## 8. File map (owner shares links, not the whole repo)

| Who | Send them |
|-----|-----------|
| Everyone | `GROUP_CHAT_TEMPLATES_PRINT.md` (or photos of pinned templates) |
| VA / Admin | `VA_SETUP_TODAY.md` + `GROUP_CHAT_OPERATING_SYSTEM.md` |
| Money | `TODAY_COLLECTIONS.md` + GHL guide |
| Manager | `OWNER_DAILY_COMMAND.md` + `TEAM_DEPLOY.md` |
| Tech (optional) | `CHANNEL_SETUP_GUIDE.md` |

---

## 9. Owner "ready for team?" checklist

- [ ] Ops WhatsApp group live with pinned templates  
- [ ] Rollout message sent (`VA_SETUP_TODAY.md` Step 3)  
- [ ] Every person has a **named role** in roster  
- [ ] Airtable invites sent OR owner accepts chat-only for Week 1  
- [ ] GHL customer WhatsApp connected (or clear "customers = personal" interim rule)  
- [ ] TMMT logins created OR fleet tracked in chat until app ready  
- [ ] Admin Recorder confirmed for first OWNER BRIEF  
- [ ] Owner nap/offline message posted with today's non-negotiables  
- [ ] Team guide sent (this file or PDF export)  

---

*AIX Command Center — `guides/TEAM_SETUP_COMPLETE_GUIDE.md`*
