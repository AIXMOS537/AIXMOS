# WHAT AIXMOS DOES ON A CLIENT'S MACHINE

Verified by reading the code, 2026-09-17. Anything conditional says so.

---

## THE SHORT VERSION

Ten specialist agents that **think on the client's own machine**, hand work to each other in
a defined order, and produce written output. Plus a scheduler, a messaging rail with a
do-not-contact gate, and an iMessage relay on macOS.

**It runs with no API key and no internet** if the client installs Ollama. Nothing leaves
their machine in that mode.

---

## 1. THE TEN AGENTS

All ten run through one backend selector (`lib/llm.js`) — Claude, Ollama, or auto. Every one
of them works offline.

| Agent | Role | What it actually produces |
|---|---|---|
| **CHUMMO** | communication | Customer-ready SMS and email copy. Warm, one CTA, under 160 chars for SMS. Ends with a handoff note for MOOSE. |
| **MOOSE** | execution | Turns a situation into action items. Bookings, CRM updates, handoffs, task closure. No fluff. |
| **CAPTAIN** | command | Priorities, routing, team assignments, which claim goes where. |
| **WONDER WOMAN** | trust guard | Reputation and moral check. Flags an unhappy customer or a bad look before it ships. Raises owner alerts. |
| **VISION** | governance | Go / no-go. Blocks a bad idea, checks long-term fit, applies policy. |
| **JARVIS** | orchestrator | Routes a request across the others. Bottleneck briefs, payout explanations, business-model answers. Can run a **council vote** (`--vote`). |
| **TANK** | infrastructure | Docker / hub-brain up, down, status, logs. **Needs Docker installed.** |
| **FLY GUY** | comms support | Message templates, portal copy, comms QA. |
| **BOB** | audit | Logs, SOPs, documentation, audit trail, explainability. |
| **STICKS** | monitoring | SLA and overdue scanning, alerts. **Needs Supabase + GHL credentials.** |

**They hand off in a defined order** — `vision → captain → moose → chummo → wonder_woman`,
with JARVIS routing and BOB auditing. That sequence is in `agents/registry.json`, not
improvised per run.

---

## 2. WHAT IT DOES WITHOUT ANY ACCOUNTS AT ALL

With Ollama installed and nothing else configured — **8 of the 10 agents work**:

- Draft customer messages, emails, templates and portal copy
- Turn a messy situation into a prioritised action list
- Get a second opinion before doing something — a go/no-go, a reputation check
- Run a multi-agent council vote on a decision
- Write SOPs, document what happened, keep an audit trail
- Do all of it **with no API key, no subscription, and no data leaving the machine**

Only TANK (Docker) and STICKS (Supabase + GHL) need anything external.

---

## 3. MESSAGING — WHAT IS AND IS NOT AUTOMATIC

### The agents WRITE. Sending is a separate, gated step.
CHUMMO produces the message text. It does not send it. Delivery goes through
`lib/sender.js`, which supports **GHL**, **Quo** and **iMessage** — and only if the client
configures one and turns sending on.

**Nothing sends on a default install.** `imessage-relay/config.example.json` ships
`allow_send: false`, `safe_mode: true`, empty allowlists, and hourly rate caps.

### Telegram
The scheduler can push briefs and alerts to Telegram. The client supplies **their own** bot
token from `@BotFather`.

### iMessage (macOS only)
A relay that reads inbound iMessage and can draft or send replies, with tiering, rate limits
and a kill switch. **Requires Full Disk Access** — it reads the message database. That is a
real privilege and the install guide says so plainly rather than burying it.

### The do-not-contact gate — on by default, cannot be bypassed
Every outbound path funnels through one function that checks a local suppression list first:

- **STOP / UNSUBSCRIBE / CANCEL / QUIT** → suppressed immediately, ahead of every other check
- **START** → released
- *"stop texting me"* → **held for a human**, never auto-suppressed
- **Fails closed** — unreadable list means the send is refused, not assumed safe
- Dry runs to a suppressed number are refused too

`npm test` runs 33 tests covering this. It is the difference between a message that says
"Reply STOP" and one that means it.

---

## 4. SCHEDULING AND MONITORING

- A scheduler for recurring jobs (daily interval), pushing to Telegram
- **STICKS** scans for overdue items and SLA breaches, and can tag them in GHL
  (`--dry-run` supported)
- **JARVIS** health-sweeps configured endpoints
- **BOB** keeps the audit trail

---

## 5. HOW THEY START IT

**One file.** `AIXMOS.command` (Mac) or `AIXMOS.bat` (Windows).

It probes the machine — node, backend, whether anything can send — reports honestly, then
offers: talk to an agent · install · set up offline mode · run the safety tests · manage the
do-not-contact list.

`bash bin/aixmos doctor` exits non-zero if the machine is not in a state to run. Safe in a
script or a cron.

After install, each agent is a terminal command: `chummo`, `moose`, `vision` …

---

## 6. 🔴 THE HONEST GAP — IT STILL THINKS IT WORKS FOR TMMT

The agent personas in `orchestrator.js` hardcode one specific operation:

> *"AIXMOS serves three businesses: TMMT Auto Services (car rentals/chauffeur/detailing/
> drivers), AIXMOS Platform ($97/month members, credit guidance, GHL setup, 100+ pipeline
> targeting $10K/month), and Ecommerce."*

A client installing this today gets a CHUMMO that believes it works for TMMT Auto Services
and will reference those businesses and that price in customer-facing copy.

**Everything else is generic. This is not.** Until the persona context is config-driven —
read from a per-install profile rather than baked into the prompt — the pack is a
*TMMT-flavoured* agent network rather than a white-label one.

That is a contained fix (one prompt file, one config block), and it is the single thing
standing between this and true plug-and-play for a stranger.

---

## 7. WHAT IS DELIBERATELY NOT INCLUDED

- **No credentials.** Every key is a blank the client fills in.
- **No customer data.** No contacts, lists or CRM records ship with it.
- **No owner agent.** `agents/rick.js` targets one operation's Slack and deployments; both
  installers exclude it and it refuses to run without `AIXMOS_OWNER_TIER=1`.
