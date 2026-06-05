# Team Workflow & Cleanup Guide

**Give this to:** Lead Assistant · VAs with computer access · Anyone doing data or app cleanup  
**Owner reads:** `OWNER_DAILY_COMMAND.md` · `TEAM_SETUP_COMPLETE_GUIDE.md`  
**Last updated:** May 2026

---

## The one rule

> **Phones run the day. Computers clean the truth.**

| Who | Daily tool | Never needs |
|-----|------------|-------------|
| Operators on shift | WhatsApp (Community + Ops chat) | Owner's Mac · Cursor · Codex |
| Admin / Lead Assistant | WhatsApp + Airtable (if invited) | API keys · Terminal |
| Tech / cleanup role | Cursor · Vercel · Airtable · Codex (heavy only) | Owner's personal `.env` |

If it is not in a **shift post** or **Airtable** by end of day, it did not happen.

---

## What needs to be fixed (cleanup priorities)

Work top to bottom. Check the box when done.

### Tier 1 — Ops truth (everyone, phones)

- [ ] **Old lists are wrong** — Do not copy old names or dollar amounts. Call, confirm, write what is true in SHIFT START/END.
- [ ] **Community structure** — Announcements = rules + daily command. Ops chat = shift work only.
- [ ] **Customer vs internal** — Customer texts → GHL WhatsApp. Internal → ops group templates only.
- [ ] **Pinned templates** — SHIFT START, SHIFT END, RULES, ESCALATION (`guides/VA_SETUP_TODAY.md`).
- [ ] **Roster** — Everyone replied DONE + role in ops chat.

### Tier 2 — Data layer (Admin + Airtable access)

- [ ] **Airtable invites** — Each role has the right view (Leads / Tasks / Payments — not full base unless needed).
- [ ] **Duplicate rows** — Merge or archive stale leads and closed tickets.
- [ ] **Missing fields** — Phone, amount, status, owner — fill from today's calls, not old spreadsheets.
- [ ] **Overdue flags** — Match what ops posted in WhatsApp today.

### Tier 3 — Apps & deploy (tech role only)

- [ ] **TMMT Rentals (Vercel)** — Production app is the `TMMT` repo, not old prototypes in Command Center.
- [ ] **Failed deploys** — Fix in Vercel dashboard → Redeploy, or use Cursor for code fixes.
- [ ] **Env vars** — Owner sets in Vercel; never paste keys in WhatsApp or group chat.
- [ ] **Command Center repo** — Hub for docs/SOPs only; app code lives in `TMMT` repo.

### Tier 4 — Repo & docs cleanup (owner or Codex session)

- [ ] Root folder clutter moved to `guides/` or `archive/` (see cleanup spec below).
- [ ] Broken `TMMT MANAGEMENT/` submodule — follow restore README or sync from owner machine.
- [ ] One canonical README at repo root — what this hub is vs where the live app lives.

**Spec reference:** `docs/superpowers/specs/2026-05-19-aix-command-center-hub-cleanup-design.md`

---

## Pick the right tool (decision chart)

```text
What are you doing?
│
├─ Posting shift / collections / BLOCKED?
│     → WhatsApp Ops chat (template only)
│
├─ Updating a lead, task, or payment record?
│     → Airtable (if you have login)
│
├─ Small copy fix, one file, "fix this button"?
│     → Cursor (Agent mode, normal model)
│
├─ Big refactor, many files, migrations, "clean the whole module"?
│     → Codex (GPT-5.x-Codex) — see § Codex below
│
├─ Deploy failed / env / domain / preview URL?
│     → Vercel dashboard (vercel.com) — see § Vercel below
│
└─ Customer message?
      → GHL WhatsApp — NOT the Community ops chat
```

---

## Speak to your computer & vibe code (save time)

**Full guide:** `guides/SPEAK_AND_VIBE_CODE_GUIDE.md` — give this to anyone with a laptop.

**Quick idea:** Turn on dictation (Mac: **fn twice** · Windows: **Win+H**). Describe the job in plain English; AI types the fix or the message. You review before send.

| Role | Tool |
|------|------|
| Admin / VA | Dictate → ChatGPT/Claude → paste into Airtable or WhatsApp |
| Tech | Dictate → **Cursor Agent** → read diff → Accept |
| Operator | Voice note on phone → Admin transcribes (no laptop needed) |

**Rule:** Dictate only facts you verified today. Never speak API keys or passwords.

---

## Install AI tools (tech role)

### Cursor — daily edits (install once)

1. Download: https://cursor.com  
2. Sign in with your Cursor account (owner invites you to the team if using Business).  
3. **File → Open Folder** → clone or open only the repo you are allowed to touch:
   - **App work:** `TMMT` repo (rentals product)
   - **Docs/SOPs:** `AIX-Command-Center` (operations hub)
4. In chat, use **Agent** mode for multi-file changes.  
5. **Do not** ask Cursor to paste API keys into chat. Use `.env.local` locally; production keys stay in Vercel.

**More detail:** `guides/OPEN_IN_CURSOR.md` · `docs/LOCAL_AI_TOOL_GUIDE.md`

### Codex — heavy changes only (install once)

Use Codex when the job is **large, risky, or spans many files** — refactors, migration scripts, repo cleanup, test sweeps.

**Install (Mac):**

```bash
# Option A — Desktop app (easiest)
# Download from https://chatgpt.com/codex or OpenAI Codex app

# Option B — CLI (terminal power users)
npm install -g @openai/codex
codex login
```

**Install (Windows):**

- Install Codex desktop from OpenAI, or use WSL + `npm install -g @openai/codex`.

**How to run a heavy cleanup session:**

1. Open the repo folder in Codex (same as Cursor — `TMMT` or `AIX-Command-Center`).
2. Choose model: **GPT-5.4** or **GPT-5.3-Codex** (long tasks).
3. Paste a **bounded prompt** (example below).
4. Review every diff before merge. Owner approves anything touching production or secrets.

**Example Codex prompt (repo cleanup):**

```text
You are cleaning the AIX-Command-Center ops hub only.
Goals:
1. Do not move or rename AIX_AI_COMMAND_SYSTEM, ops, or agents folders.
2. Move loose root markdown files into guides/ or archive/ per
   docs/superpowers/specs/2026-05-19-aix-command-center-hub-cleanup-design.md
3. Add README.md at root explaining this is docs/SOPs hub; TMMT app is separate repo.
4. No .env changes, no API keys, no deploy commands.
Show a file list before and after. Small commits per logical group.
```

**Low-token prompts:** `imports-from-lexar/mentorship/prompts/LOW_TOKEN_CODEX_PROMPT.md`

**When NOT to use Codex:** Shift posts, Airtable row updates, WhatsApp copy, one-line UI tweaks → use Cursor or do manually.

---

## Vercel — deploy & app cleanup (no local Mac required)

**Who:** Person with Vercel team invite (owner adds you in Vercel → Project → Settings → Members).

**Login:** https://vercel.com → open project **TMMT** (or name owner gives you).

### What you can fix in the Vercel UI (no code)

| Problem | Where in Vercel | Action |
|---------|-----------------|--------|
| Build failed | Deployments → failed deployment → Logs | Read error; fix code in Cursor/Codex, or env var |
| Wrong env var | Settings → Environment Variables | Owner approves changes; redeploy |
| Old preview clutter | Deployments | Filter previews; cancel stuck builds |
| Domain / SSL | Settings → Domains | Owner only unless delegated |
| Cron not running | Settings → Cron Jobs | Check path and schedule |

### Safe cleanup workflow on Vercel

1. Open latest **Production** deployment — confirm it is green.  
2. If red, open **Build Logs** — copy last 30 lines to ops Slack/DM (not WhatsApp customer chat).  
3. Fix code in `TMMT` repo branch → push → wait for preview → owner promotes to production.  
4. **Never** delete production env vars without owner OK.

**CLI (optional):** `npx vercel login` → `npx vercel ls` → `npx vercel logs <url>`

---

## Airtable — data cleanup (if you have access)

**If you do not have a login:** Skip this section. Use shift posts only; Admin Recorder updates Airtable.

**If you have a login:**

1. Open only **your view** (Leads, Tasks, Payments — not whole base unless lead).  
2. **Today's rule:** Verify by phone call before changing amount or status.  
3. **Cleanup tasks:**
   - Archive records marked closed > 90 days ago (owner rule).
   - Fix blank Status / Owner / Phone.
   - Add source = `WhatsApp shift YYYY-MM-DD` in notes when confirming from ops chat.
4. **Do not:** Export full base to personal Google Drive. Do not share base link publicly.

**Owner setup:** `TEAM_SETUP_COMPLETE_GUIDE.md` § Step B

---

## Role cheat sheet

| Role | WhatsApp | Airtable | GHL | Cursor | Codex | Vercel |
|------|----------|----------|-----|--------|-------|--------|
| Operator | ✅ daily | ❌ | maybe | ❌ | ❌ | ❌ |
| Admin Recorder | ✅ | ✅ | maybe | ❌ | ❌ | ❌ |
| Lead Assistant | ✅ + owner DM | ✅ | ❌ | ❌ | ❌ | ❌ |
| VA Ops | ✅ pins | ❌ | ❌ | ❌ | ❌ | ❌ |
| Tech / cleanup | ❌ | ✅ if invited | ❌ | ✅ | ✅ heavy | ✅ if invited |

---

## Escalation to owner

Ping owner (DM or `@OWNER` per pinned rule) only for:

- Money dispute or legal threat  
- BLOCKED > 2 hours with customer waiting  
- Production site down  
- Need new API key or Vercel permission  

Everything else: fix in Airtable / Vercel / Cursor first, then summarize in **OWNER BRIEF** format (Lead Assistant, once per morning).

---

## Related guides (read in order)

| Order | File | For |
|-------|------|-----|
| 1 | `guides/TEAM_SIMPLE_SETUP_GUIDE.html` | Everyone — print/PDF |
| 2 | `guides/ASSISTANT_AND_VA_SETUP_PLAYBOOK.md` | Lead Assistant + VAs |
| 3 | `guides/TEAM_SETUP_COMPLETE_GUIDE.md` | Full system map |
| 4 | **This file** | AI + cleanup + Vercel + Airtable |
| 4b | `guides/SPEAK_AND_VIBE_CODE_GUIDE.md` | Voice + vibe coding (talk to laptop) |
| 5 | `guides/VA_SETUP_TODAY.md` | Pin WhatsApp templates |
| 6 | `docs/LOCAL_AI_TOOL_GUIDE.md` | Cursor vs Ollama vs Claude |
| 7 | `OWNER_DAILY_COMMAND.md` | Owner daily entry |

---

## Owner-only (do not share with operators)

- Owner Mac: Pre-Send Review, local dev, `./scripts/aix`, `.env` files  
- GitHub: add collaborators on private repos — not zip files with secrets  
- Codex/Cursor on owner machine for hub cleanup and TMMT features  

---

*Questions? Lead Assistant collects them in one DM to owner — not 20 separate threads.*
