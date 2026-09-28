# AIXMOS for iPhone — Complete System (Secure Build)
**Device:** iPhone 16 Pro (iOS 26 — full Apple Intelligence + API)
**Architecture:** Shortcuts = body · AIXMOS = brain · Siri = trigger · Gateway = secret-keeper
**Status:** Fully designed and security-hardened. You deploy + supply keys; nothing left to figure out.

---

## ⓪ CHOOSE YOUR SETUP (30-second decision)
- **Secure Gateway (recommended).** A tiny free Cloudflare Worker holds your API key. The phone never carries a secret. Best for anything you'll reuse, replicate, or hand to a team. ~10 min one-time setup. → Do sections ①–④.
- **Direct (quick, personal-device-only).** Key lives inside the shortcut. Fine for a single private phone you never share the shortcut from. → Skip section ③; in ④ call AIXMOS directly (noted inline).

Given you build infrastructure for operators/VAs, use the Gateway.

---

## ① FILL THESE IN (every secret, one place)
| Placeholder | Where | Format | Lives in |
|---|---|---|---|
| `ANTHROPIC_KEY` | console.anthropic.com → API Keys | `sk-ant-...` | **Gateway only** |
| `SHARED_SECRET` | invent a long random string | 30+ random chars | Gateway + phone |
| `GATEWAY_URL` | from deploying the Worker (§③) | `https://...workers.dev` | phone |
| `AIRTABLE_TOKEN` | airtable.com/create/tokens — scope to **your base only**, data.records:read+write | `pat...` | Gateway (or phone) |
| `AIRTABLE_BASE` | Rental Ops Hub URL, the `app...` part | `appXXXX` | phone |
| `GHL_WEBHOOK_URL` | GHL → Workflow → Inbound Webhook | `https://...` | Gateway (or phone) |
| `LOT_LOCATION` | address for the location automation | a place | phone |

AIXMOS billing is pay-as-you-go, **separate** from your AIXMOS subscription. Use least-privilege tokens (scope Airtable to the one base).

---

## ② THE MODEL (one paragraph)
Siri or a Personal Automation fires a shortcut. The shortcut POSTs to your **Gateway**, which attaches the real API key and forwards to AIXMOS, then returns the answer. The phone holds only a shared-secret password, not the key. The same Gateway can later proxy Airtable and GHL too, so **zero secrets ever sit on the device**.

---

## ③ DEPLOY THE GATEWAY — `aixmos-gateway` (Cloudflare Worker, free)
1. Cloudflare account → **Workers & Pages** → **Create** → **Create Worker** → name `aixmos-gateway` → Deploy.
2. **Edit code**, paste this, Deploy:
```js
export default {
  async fetch(req, env) {
    if (req.method !== "POST") return new Response("POST only", { status: 405 });
    // gate: reject anyone without the shared secret
    if (req.headers.get("x-aixmos-auth") !== env.SHARED_SECRET)
      return new Response("Unauthorized", { status: 401 });

    const body = await req.text(); // pass the model/messages JSON straight through
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": env.ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body,
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": "application/json" },
    });
  },
};
```
3. Worker → **Settings → Variables and Secrets** → add two **Secrets** (encrypted):
   - `ANTHROPIC_KEY` = your `sk-ant-...`
   - `SHARED_SECRET` = your long random string
4. Copy the Worker URL → that's `GATEWAY_URL`.

The key is now encrypted server-side and never touches your phone or any shortcut you share.

---

## ④ CORE ENGINE — `AIXMOS Brain` (build once; everything reuses it)
New Shortcut → name `AIXMOS Brain` → enable **Show in Share Sheet** (accept Text).

1. Receive **Text**; if empty → **Ask for Input** → call it **Input**.
2. **Get Contents of URL**
   - URL: `GATEWAY_URL`  *(Direct setup: use `https://api.anthropic.com/v1/messages` instead)*
   - **Method: POST**
   - **Headers:** `x-aixmos-auth`=`SHARED_SECRET`, `content-type`=`application/json`
     *(Direct setup headers instead: `x-api-key`=`ANTHROPIC_KEY`, `anthropic-version`=`2023-06-01`, `content-type`=`application/json`)*
   - **Request Body: JSON**
     - `model` *(Text)* = `claude-sonnet-4-6`
     - `max_tokens` *(Number)* = `1024`  ← caps cost per call
     - `system` *(Text)* = AIXMOS system prompt (below)
     - `messages` *(Array)* → Item 1 *(Dictionary)*: `role`=`user`, `content`=**Input**
3. **Get Dictionary Value** → `error` from (Contents of URL).
4. **If** `error` *has any value* → **Show Alert** "AIXMOS error: [error]" → **Stop Shortcut**.
   **Otherwise:**
   5. **Get Dictionary Value** → `content` → **Get Item from List** (First) → **Get Dictionary Value** → `text`.
   6. **Stop and Output** that text.

**System prompt:**
```
You are AIXMOS, the operating brain for Muhammad Taha, founder/CEO of TMMT Auto
Services (TMMT Rentals — luxury Turo fleet; AIXMOS automation/CRM on GoHighLevel;
operator network). Push Muhammad toward the CEO/orchestrator role: decisive,
systems-oriented, brief. Lead with the answer, no filler. When asked to structure
data, return clean JSON only — no prose, no code fences.
```
Test: run it, type "3 priorities for a Turo rental business today." Crisp answer = engine live.

---

## ⑤ `AIXMOS Brief` — CEO morning brief
1. **Find Calendar Events** — Start *is Today* (limit 15)
2. **Find Reminders** — not completed, due Today
3. **Text:**
   ```
   Write my CEO morning brief: top 3 priorities, what to delegate to a VA vs.
   handle myself, one thing I'm likely forgetting. Then list items below.
   CALENDAR: [Calendar Events]
   REMINDERS: [Reminders]
   ```
4. **Run Shortcut** → `AIXMOS Brain` (pass the Text). For sharper output, duplicate Brain as `AIXMOS Brain (Opus)` with model `claude-opus-4-8`.
5. **Speak Text** + **Show Notification**.
6. Automation → Time of Day → 7:00 AM → Run Immediately. Or *"Hey Siri, AIXMOS brief."*

## ⑥ `AIXMOS Capture` — voice capture that routes itself
1. **Dictate Text** → **Note**
2. **Run Shortcut** → `AIXMOS Brain`:
   `Classify into JSON only: {"type":"task|lead|idea","title":"","notes":"","due":"YYYY-MM-DD or null"} Note: [Note]`
3. Get `type`, `title`, `notes`, `due`.
4. **If** task → **Add Reminder**. **Else if** lead → Airtable POST (§⑦ pattern, Leads table). **Else** → append to "AIXMOS Ideas" note.
- *"Hey Siri, AIXMOS capture."* Set model `claude-haiku-4-5-20251001` (fast/cheap).

## ⑦ `AIXMOS Rental` — log a rental + save condition photos to the NAS
Records go to Airtable; the condition photos go to your private NAS; the Airtable row points at the NAS folder. Voice-driven, works for both check-in and check-out.

**Prereq (one-time):** mount the NAS in the Files app — Files → Browse → ⋯ → **Connect to Server** → `smb://NAS-HOST` → sign in. It now appears as a Files location your shortcuts can write to. (Reachable from the lot once Tailscale is on — see the Mesh doc's "Owned Data Tier" section.)

1. **Choose from Menu** → `Check-In` / `Check-Out`. Set **Phase** = `in` or `out` and **Status** = `Active` or `Returned` accordingly.
2. **Dictate Text** → **RentalNote** (say it naturally: "SQ8 to James Carter, pickup Friday, return Monday, $300/day").
3. **Run Shortcut** → `AIXMOS Brain`:
   `Extract a Turo rental, JSON only: {"customer":"","vehicle":"","pickup":"YYYY-MM-DD","return":"YYYY-MM-DD","daily_rate":0,"total":0,"notes":""} Booking: [RentalNote]`
4. **Get Dictionary Value** for each field. Build **Folder** = `[customer]` (Text action; strip spaces if you like).
5. **Take Photos** (allow multiple) → **Photos**. *(Or "Select Photos" from the library.)*
6. **Repeat with Each** **Photo**:
   - **Save File** → turn **Ask Where to Save OFF** → destination = the **NAS** location, path `TMMT/Rentals/[Folder]/[Phase]/` , filename `[vehicle]-[Phase]-[Current Date]-[Repeat Index].jpg`. Shortcuts creates the folders.
7. **Get Contents of URL** → Airtable **Condition Logs** table (one row per check-in and check-out):
   - URL: `https://api.airtable.com/v0/AIRTABLE_BASE/Condition%20Logs`
   - **POST**; Headers: `Authorization`=`Bearer AIRTABLE_TOKEN`, `content-type`=`application/json`
   - Body JSON → `fields`: `Customer`, `Vehicle`, `Phase` (in/out), `Status`, `Pickup Date`, `Return Date`, `Daily Rate`, `Total`, `Notes`, `Photos Path`=`TMMT/Rentals/[Folder]/[Phase]/`
   - **Rename keys to match your base exactly — case-sensitive.**
8. *(Optional, makes the NAS folder self-describing)* **Save File** a small `rental.json` (the JSON from step 3) into `TMMT/Rentals/[Folder]/`.
9. **Show Notification** → "Check-[Phase] logged: [count] photos on NAS + record in Airtable."
- *"Hey Siri, AIXMOS rental."* Keep "Ask Before Running" ON until tested — this writes to your live base and NAS.
- **Why this split:** Airtable = the searchable record (who/what/when + the path), NAS = the private photo trail and PII. Every rental ends up with a dated in/out photo set you own, created by voice.

## ⑧ `AIXMOS Shift` — VA shift summary
1. **Dictate Text** / Share-Sheet notes → **ShiftNotes**
2. **Run Shortcut** → `AIXMOS Brain`:
   `Write a VA shift summary from the notes: vehicles out/returned; issues or damage flags; customer follow-ups; clear action items for the VA. Tight and skimmable. Notes: [ShiftNotes]`
3. **Copy to Clipboard** + **Quick Look** to review before sending; optionally pipe to Slack/Messages.
- *"Hey Siri, AIXMOS shift."*

## ⑨ `AIXMOS Follow-Up` — leave-the-lot automation
1. Automation → **Leave** `LOT_LOCATION`.
2. **Dictate Text** "What's still open?" → **Open**
3. **Run Shortcut** → `AIXMOS Brain`:
   `Turn this into 1–4 same-day follow-ups, JSON list only: [{"title":"","due":"today 6pm"}] Open: [Open]`
4. **Repeat with Each** → **Add Reminder**.

## ⑩ `AIXMOS → GHL` — fire a GoHighLevel workflow by voice
1. GHL Workflow with **Inbound Webhook** trigger → URL into `GHL_WEBHOOK_URL`.
2. **Dictate Text** → **Cmd** (optionally structure via `AIXMOS Brain` first).
3. **Get Contents of URL** → `GHL_WEBHOOK_URL`, **POST**, `content-type: application/json`, body `{"source":"AIXMOS iPhone","command":"[Cmd]"}`.
4. Branch in GHL on `command` to send SMS, tag a contact, start a pipeline.
- *"Hey Siri, AIXMOS GHL."* (Treat the webhook URL as a secret — it's a capability link.)

---

## ⑪ SECURITY & COST SAFEGUARDS (the "safe and recommended" layer)
- **Key off the phone.** Gateway holds `ANTHROPIC_KEY`; shortcuts carry only `SHARED_SECRET`. Never share a Direct-setup shortcut — it contains your key.
- **Spend cap + alert.** console.anthropic.com → set a monthly spend limit and a usage alert. A leaked key or runaway loop can't drain the account.
- **`max_tokens` caps each call;** keep it at 1024 unless a flow needs more.
- **Least-privilege tokens.** Scope the Airtable PAT to the single base, read+write only. (You can also move `AIRTABLE_TOKEN` and `GHL_WEBHOOK_URL` behind the Gateway so the phone holds zero secrets.)
- **Confirm before writes.** Keep "Ask Before Running" ON for Rental/GHL automations until tested; they hit live systems.
- **Rotate** the AIXMOS key and `SHARED_SECRET` if a device is lost; update the Gateway secret, done — no shortcut edits needed.
- **Version your shortcuts.** Export each to Files after it works, so a bad edit is recoverable.

## ⑫ REFERENCE
- Models: `claude-sonnet-4-6` (default) · `claude-opus-4-8` (Brief / strategy) · `claude-haiku-4-5-20251001` (Capture / frequent). Set per-shortcut in the `model` field.
- Siri: distinct "AIXMOS"-prefixed names = reliable triggers.

## HONEST LIMITS (what I can't do from here)
- I can't install or run anything on your phone, or deploy the Worker for you — both need your accounts. You tap through the builds once (~10 min Gateway, ~15 min engine, ~5 min each flow).
- iOS shortcuts are signed binaries, so I can't hand you an importable `.shortcut` file — the action-by-action specs are the reliable path. The Gateway code, by contrast, is copy-paste-ready.
- The secrets in §① are the only things only you can supply.
