# 🛠️ OPERATOR OS — Master Blueprint
_The single plug-everything-in system for running TMMT across 5–7 machines + overseas assistants._
_Drafted 2026-06-06. Status: **MAP / approved-to-build pending**. Owner: Muhammad (AIXMOS)._

---

## 0. The one-line vision
> **One front door.** Any device — your 5–7 machines or an overseas assistant's own PC — gets plugged into the same brain in **one step**, lands on a **role-locked dashboard**, and follows a **per-vertical playbook that's scored** — so operators don't just get *connected*, they get *better*.

You already own every hard piece. This blueprint ties them into one process and adds the two things missing: **device sync** and an **operator level-up engine**.

---

## 1. The architecture — 4 layers (plain English)

| Layer | What it is | Status |
|---|---|---|
| 🧠 **1. The Brain** | The single source of truth. The TMMT cloud app (GitHub + Supabase + Vercel, always-on) **+** the AIXMOS-Brain vault (SOPs, playbooks, memory). | App: ✅ live · Brain sync: ⚠️ not wired yet |
| 🔌 **2. The Plug** | Onboarding. Turns any machine/person into a working node. Two paths (yours vs. overseas — see §4). | USB kit ✅ · cloud path ❌ to build |
| 🎛️ **3. The Face** | The role-locked Command Center dashboard each person sees. Voice-enabled, "a 5-year-old could use it." | ✅ 17 built · needs vertical tiles |
| 📋 **4. The Playbook** | The level-up engine: per-vertical SOPs + training + scorecards. Turns connected people into top-tier operators. | ❌ to build |

**Rule of the whole system:** the Brain is the *only* source of truth. Devices are disposable windows into it. Lose a laptop → plug in a new one → you're back in 10 minutes. Nothing important lives *on* a device.

---

## 2. The 4 verticals + who runs them

Everything routes through the one main business (TMMT), but each vertical gets its own playbook, dashboard tiles, and operator roles.

| Vertical | Covers | TMMT/MCP systems it touches | Operator roles |
|---|---|---|---|
| 🚗 **Vehicle rentals** | Bookings, fleet availability, customers, operator/agency partners | `active_customers`, `operator_profiles`, `incoming_leads`, Supabase app, OpenPhone | operator, dispatch, manager |
| ✨ **Auto detailing** | Detail jobs, detailers/VAs, scheduling, QA | ClickUp (detail tasks), `vendors`/`shops_mechanics_cleaning`, OpenPhone | operator (detailer), manager |
| 💰 **Sales / leasing** | Lead-gen, outreach, closing, follow-up | `incoming_leads` → `active_customers`, `ghl_contacts`, Gmail, OpenPhone, Slack | sales |
| 🚦 **Dispatch / fleet ops** | Vehicle movement, mechanics/shops, vendor coordination | `vendors`, `shops_mechanics_cleaning`, Calendar, ClickUp, OpenPhone | dispatch, operator |

> Roster of who's in each is in [[people-hub]]. As you confirm who runs what, I tag each person to a vertical + role.

---

## 3. The sync backbone — how all devices share ONE truth

Three channels keep every machine + person aligned:

1. **The app = cloud.** `tmmt-ops.vercel.app` is always-on. Every device already reaches it with zero install. ✅ done.
2. **The Brain vault = UGREEN NAS (on-prem, NOT GitHub).** The `AIXMOS-Brain` Obsidian vault (SOPs + playbooks + memory) lives on the **UGREEN NAS** (`192.168.68.59`) — see [[ugreen-nas]]. Every home machine mounts the same share and opens it as a vault; the tablet's memory junction points at it so writes land on the NAS. **Why not GitHub:** the user's `AIXMOS537` account can't create repos and `Metavibez4L` is the partner's account — using it would leak the private family/personal lanes. NAS keeps the brain private + on-prem. ⚠️ **blocked:** SMB file service is OFF on the NAS (only the 9999 console is up) — must be enabled + a share/user created before mounting.
3. **Remote control = Tailscale + AnyDesk.** Already installed — lets you reach any of your machines (incl. `BRAINIAC-7` at `192.168.68.61`) from anywhere, and Tailscale can reach the NAS off-LAN too. ✅ keep.

**Overseas assistants are a special case (their own PCs):** they get **none of the above git/secrets**. They get a **browser-only slice**:
- The cloud app (role-limited login)
- Their role dashboard (hosted as a web link, not a local file)
- Their vertical's SOPs as **read-only web pages** (published from the Brain, not the repo)
- Their tools: Slack, ClickUp, OpenPhone — all browser/app, no install

This keeps the **service-role key and the private Brain off machines you don't control** (carries the existing rule from [[team-drive-kit]] + [[command-center-dashboards]]).

---

## 4. The onboarding — two front doors

### 🟢 Path A — Your machines (trusted: tablet, carry Mac, work Mac, Brainiac, +)
One enhanced command (evolves the existing [[team-drive-kit]]) that does, in order:
1. Install Claude Code + Node + Git + `gh` (winget / Homebrew)
2. Clone the TMMT app + write `.env` (service-role key only on trusted power machines)
3. **Clone the Brain vault** ← new step, gives this machine the SOPs + memory
4. Drop the **owner/manager dashboard** on the desktop + set autostart
5. Two manual steps that no script can do: `claude` sign-in once, `gh auth login` if it pushes code

### 🔵 Path B — Overseas assistants (their own PC, zero install, zero secrets)
A **single web link per person**. Clicking it gives them:
1. Their **role dashboard** (hosted online — operator/sales/dispatch tiles only, owner tiles never render)
2. Login to the cloud app, scoped to their vertical
3. Their **SOP playbook pages** (read-only)
4. Their tools (Slack/ClickUp/OpenPhone invites)
No USB, no `.env`, no Brain repo, no keys. If their laptop dies, you re-send the link — nothing to clean up.

> Both paths end the same way: **person lands on a dashboard + knows exactly what to do next.**

---

## 5. The operator level-up engine — "top tier" = all 4 metrics

You said top-tier means **SOP adherence + speed + output + quality**. Here's how each gets measured (all from systems you already run) and rolled into one scorecard.

| Metric | What it answers | Measured from |
|---|---|---|
| 📋 **SOP adherence** | Did they follow the playbook, every step? | ClickUp checklists completed, no skipped steps |
| ⚡ **Speed / response** | How fast on leads, tickets, messages, dispatch? | OpenPhone response time, ClickUp time-in-status |
| 📦 **Output / volume** | How much got done? | ClickUp tasks closed, bookings handled, details completed, time tracking |
| ✅ **Quality** | How clean was it — redos, complaints? | QA checklist pass rate, complaint/redo count, customer satisfaction |

**Operator scorecard** (one card per person, per vertical), reviewed weekly:
- Each metric scored, rolled into a tier: **🥉 Rookie → 🥈 Operator → 🥇 Senior → 💎 Top-Tier**
- Tier unlocks more dashboard access + autonomy (gamified leveling)
- The Brain stores each operator's scorecard history so progress is visible over time

**The weekly loop:** (1) scores auto-pull from ClickUp/OpenPhone/app → (2) scorecard updates → (3) you get a Monday digest of who's rising/slipping → (4) coaching nudges sent to anyone below tier on a metric.

**Training side:** each vertical playbook has a short onboarding path (read SOPs → shadow → first supervised tasks → cleared solo). New assistant follows it; the system tracks where they are.

---

## 6. Security & lane separation (non-negotiables carried forward)
- 🔑 **Service-role / Stripe / Supabase keys** only on machines YOU control — never overseas PCs.
- 🙈 **Owner-only tiles** (Stripe, Supabase, Vercel, GitHub, Investor, dev, Cursor) never even render for non-owners — least exposure (from [[command-center-dashboards]]).
- 🔒 **Work / Family / Personal stay separated** — no family/personal info ever in operator-facing output (from [[home-bot]]).
- ✋ **Real access changes need your OK** — creating accounts, granting rights, inviting to Slack/ClickUp, writing to live Supabase always confirmed first (from [[people-hub]]).

---

## 7. The build roadmap (what I do once you say go)

| Phase | Deliverable | Unblocks |
|---|---|---|
| **1. Sync backbone (NAS)** | Enable SMB on the UGREEN NAS + create `Brain` share/user → mount it → move `AIXMOS-Brain` onto it → re-point the memory junction → mount the same share on Brainiac + Macs (Obsidian vault). SOP/playbook folder structure already seeded. See [[ugreen-nas]]. | Every device shares one truth, on-prem/private |
| **2. Onboarding front doors** | Path A enhanced one-command kit; Path B hosted dashboard + SOP web link per overseas assistant | Anyone plugs in fast |
| **3. Vertical playbooks** | Write the SOP + training path for each of the 4 verticals | Operators know exactly what to do |
| **4. Scorecard engine** | Operator scorecard template + the 4-metric pulls from ClickUp/OpenPhone/app + tier system | "Top tier" becomes measurable |
| **5. Automation** | Weekly operator digest, coaching nudges, plug into your 7am morning briefing | Runs itself; you just steer |

---

## 8. Open decisions still needed (before/within each phase)
- [ ] Who runs which vertical(s)? (tag the [[people-hub]] roster)
- [ ] Confirm overseas assistants' names + which vertical each → generates their Path-B link
- [ ] Where to host the overseas dashboards + SOP pages (Vercel is easiest — already in stack)
- [ ] Exact tier thresholds for each metric (I'll propose defaults you tweak)
- [ ] Whether the weekly digest goes to you only, or managers too

---
_Built on: [[tmmt-system]] · [[team-drive-kit]] · [[command-center-dashboards]] · [[device-architecture]] · [[people-hub]] · [[work-team]] · [[home-bot]] · [[tablet-desktop-setup]]_
