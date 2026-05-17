# Week 1 — GHL + WhatsApp (Car Rentals)

**Goal by end of week:** Rental WhatsApp lives in GHL, pipeline exists, **overdue alert workflow** fires when you tag `payment-overdue`.

**Time:** ~3–5 hours total (split across you + ops VA).  
**Stack:** WhatsApp → GHL only · Slack **not** used for rentals this week.

---

## Who does what

| Task | Owner (you) | Ops VA |
|------|-------------|--------|
| Connect WhatsApp in GHL | Approve business number | Help verify Meta/WhatsApp if prompted |
| Name pipeline stages | Final say on stage names | Create pipeline + fields in GHL |
| Top 5 collections calls | **You** call | Update GHL after each call |
| Enter `amount_due` / dates for overdue renters | Spot-check | Data entry from `TODAY_COLLECTIONS.md` |
| Build overdue workflow | Review test | Click through automation OR give screen share to tech |
| Tag `payment-overdue` | — | Apply tag when balance overdue |
| Test workflow | Confirm you got alert | Create test contact |

---

## Before you start

- [ ] GHL login (agency or location — use **TMMT / rental location**)
- [ ] Business phone number ready for WhatsApp Business (not your personal iMessage number unless you mean to)
- [ ] Open on second screen: `TMMT MANAGEMENT/OPERATIONS/TODAY_COLLECTIONS.md`
- [ ] Payment message wording: `TMMT MANAGEMENT/CUSTOMERS/MESSAGE_TEMPLATE_LIBRARY.md` → Payment Overdue Notice

---

## Day 1 (Monday) — WhatsApp in GHL (~45 min)

### 1.1 Connect WhatsApp

1. Log in to **GoHighLevel** → select your **rental location**.
2. Go to **Settings** (gear) → **Phone Numbers** (or **Communication** → **Phone System**).
3. Choose **Add number** → **WhatsApp** (or **WhatsApp Business** / LC Phone WhatsApp — label varies).
4. Follow Meta/WhatsApp verification (business name, display name, number SMS verify).
5. When connected, open **Conversations** → confirm the WhatsApp channel appears.

**Done when:** You can send yourself a test WhatsApp from GHL Conversations.

### 1.2 One inbox rule (tell the team)

Post in ops chat:

```text
All CUSTOMER rental messages go through GHL WhatsApp — not the owner's personal WhatsApp.
Internal shift updates stay in our ops group (English templates). VA sends owner brief daily.
```

### 1.3 Checklist Day 1

- [ ] WhatsApp connected in GHL
- [ ] Test message sent + received
- [ ] Team announcement posted

---

## Day 2 (Tuesday) — Rental pipeline + custom fields (~60 min)

**VA does clicks; you confirm stage names match how you sell.**

### 2.1 Create pipeline

1. **Opportunities** → **Pipelines** → **Create pipeline**.
2. **Name:** `TMMT Rentals` (or your exact brand — write it in `RENTAL_GHL_PIPELINE.md`).
3. **Stages** (in order — create exactly):

| # | Stage name |
|---|------------|
| 1 | New lead |
| 2 | Contacted |
| 3 | Qualified |
| 4 | Booking sent |
| 5 | Booked / active |
| 6 | Active rental |
| 7 | Payment overdue |
| 8 | Returned / closed |
| 9 | Lost / DNR |

4. Save pipeline.

### 2.2 Custom fields (Contact)

**Settings** → **Custom Fields** → **Contact** → add:

| Field name | Type | Notes |
|------------|------|--------|
| `payment_due_date` | Date | Next payment due |
| `payment_status` | Dropdown | `paid` · `due` · `overdue` |
| `amount_due` | Monetary / Text | Current balance |
| `vehicle_assigned` | Text | Unit / plate |
| `pickup_date` | Date | |
| `return_date` | Date | |
| `rental_customer_yn` | Dropdown | Y / N |

Map GHL merge names if different (e.g. `{{ contact.payment_due_date }}`).

### 2.3 Create tag

**Settings** → **Tags** → create: **`payment-overdue`**

### 2.4 Update doc

Edit `TMMT MANAGEMENT/CUSTOMERS/RENTAL_GHL_PIPELINE.md` — fill **Pipeline name in GHL** with exact name.

### 2.5 Checklist Day 2

- [ ] Pipeline `TMMT Rentals` live with 9 stages
- [ ] All custom fields created
- [ ] Tag `payment-overdue` exists
- [ ] `RENTAL_GHL_PIPELINE.md` pipeline name filled in

---

## Day 3 (Wednesday) — Load top 5 overdue contacts (~60–90 min)

**Source:** `TMMT MANAGEMENT/OPERATIONS/TODAY_COLLECTIONS.md` (Priority 1).

For each customer ([customer], [customer], [customer], [customer], [customer]):

1. **Contacts** → search name → open (or create if missing).
2. Set custom fields from queue (`amount_due`, dates, `payment_status` = **overdue**).
3. **Opportunity** → pipeline **TMMT Rentals** → stage **Payment overdue**.
4. Add tag **`payment-overdue`**.
5. Log last contact attempt in notes.

**You:** Make at least **one** collection call (top name). VA updates GHL within 1 hour of call.

### Checklist Day 3

- [ ] 5 contacts in GHL with correct $ and stage
- [ ] 5 tagged `payment-overdue`
- [ ] Owner completed call #1 ([customer])

---

## Day 4 (Thursday) — Overdue workflow (~45–90 min)

**Name workflow:** `TMMT - Overdue Payment Alert`

**Path:** **Automation** → **Workflows** → **Create workflow** → start from scratch.

### Trigger (use Option A — simplest for Week 1)

**Trigger:** Contact **Tag** → `payment-overdue` is added.

*(Option B/C from `GHL_OVERDUE_WORKFLOW_SETUP.md` can wait until fields are always accurate.)*

### Filter (stop spam)

Add condition: **Tag** does **not** contain `overdue-alert-sent-today`  
*(Create tag `overdue-alert-sent-today` — remove next day via second workflow or manual; OR use "wait until event" — for Week 1 keep one alert per tag apply.)*

**Simpler Week 1:** accept one alert per tag; VA only adds tag once per week per contact unless balance still owed.

### Actions (in order)

**1. Internal notification — YOU**

- Action: **Send internal notification** / **Email** / **SMS to user** (owner).
- To: your phone + email on file.
- Body:

```text
OVERDUE: {{contact.name}} — ${{contact.amount_due}} — due {{contact.payment_due_date}}
Pipeline: Payment overdue. Call today.
```

**2. Task**

- Action: **Create task**
- Title: `Collect {{contact.name}} — ${{contact.amount_due}}`
- Due: **Today**
- Assign: you or finance VA

**3. Wait 24 hours**

- Action: **Wait** 24h

**4. If still tagged** (optional Week 1 — skip if complicated)

- If tag still `payment-overdue` → second internal notification only (no auto customer message yet).

**5. Customer WhatsApp/SMS (OPTIONAL — off until you approve copy)**

- Action: **Send SMS** or **WhatsApp** (if template approved in Meta).
- Copy from MESSAGE_TEMPLATE_LIBRARY — Payment Overdue Notice:

```text
Hi {{contact.first_name}}, our records show ${{contact.amount_due}} was due on {{contact.payment_due_date}} and is now overdue.

Please contact us today at [YOUR PHONE] to pay or set up a plan.

Unpaid balances may affect your rental status per your agreement.

[YOUR BUSINESS NAME]
```

**Week 1 recommendation:** Leave step 5 **disabled** until you've sent 5 manual collection texts and legal is OK.

### Publish

- **Publish** workflow ON.
- Document in GHL notes: "Week 1 live — tag trigger only."

### Checklist Day 4

- [ ] Workflow published
- [ ] Customer auto-message **off** OR approved and tested
- [ ] VA knows: add tag `payment-overdue` when balance is overdue

---

## Day 5 (Friday) — Test + go live (~30 min)

### 5.1 Test contact

1. Create contact **Test Overdue** with your phone/email.
2. Set `amount_due` = `1.00`, `payment_status` = overdue.
3. Add tag **`payment-overdue`**.
4. Confirm within 2 minutes:
   - [ ] You received internal alert
   - [ ] Task created with correct title
5. Remove tag + delete test contact.

### 5.2 Production check

- [ ] Tag one real overdue contact (if not already) — alert fires once
- [ ] VA removes tag only when paid or payment plan logged

### 5.3 Owner end of week

- [ ] 5 collection calls attempted (from TODAY_COLLECTIONS)
- [ ] Update `THIS_WEEK.md` → Wire GHL overdue alert ✅
- [ ] Update `COMMAND_CENTER.md` → GHL workflow row to Done

---

## Daily habit after Week 1 (you — 10 min)

1. **GHL Conversations** — unread rental WhatsApp
2. **GHL Tasks** — overdue collection tasks due today
3. **OWNER BRIEF** from VA (ops chat) — BLOCKED + overdue
4. **One** collection action before noon

---

## VA copy-paste (send today)

```text
Week 1 GHL job — Car rentals only

Day 1: Help owner confirm WhatsApp shows in GHL Conversations.
Day 2: Create pipeline "TMMT Rentals" (9 stages) + custom fields + tag payment-overdue — see WEEK_1_GHL_WHATSAPP.md on owner drive.
Day 3: Enter top 5 overdue customers from TODAY_COLLECTIONS into GHL — stage Payment overdue + tag payment-overdue.
Day 4: Build workflow "TMMT - Overdue Payment Alert" OR schedule 30 min screen share with owner.
Day 5: Test contact with owner; confirm alert + task.

Report done each day with screenshot. English only in customer messages.
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| WhatsApp won't connect | Meta business verification; try LC Phone support in GHL |
| Merge field blank | Custom field not on contact; check field key in workflow |
| Duplicate alerts | Don't re-add tag daily; use notes for call attempts |
| Workflow doesn't fire | Workflow published? Correct location? Tag spelled exact |
| Customer message fails | WhatsApp template not approved — keep internal alert only |

---

## Week 2 preview (don't do yet)

- Payment **due** reminder (3 days before) — rank 2 in automation backlog
- GHL webhook → n8n (see `CHANNEL_STACK_GHL_WHATSAPP_SLACK.md`)
- Slack `#credit-commands` for credit business only

---

## Files

| File | Use |
|------|-----|
| `WEEK_1_GHL_WHATSAPP.md` | This guide |
| `GHL_OVERDUE_WORKFLOW_SETUP.md` | Technical reference |
| `RENTAL_GHL_PIPELINE.md` | Stage definitions |
| `TODAY_COLLECTIONS.md` | Who to enter Day 3 |
| `CHANNEL_STACK_GHL_WHATSAPP_SLACK.md` | Full stack after Week 1 |
