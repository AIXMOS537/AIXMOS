---
name: command-center-dashboards
description: "The role-based personal dashboard system in CommandCenter — one HTML template generates a sleek voice-enabled launcher per person; roles control which tiles show. Load when asked to make/edit someone's dashboard or change the launcher."
metadata: 
  node_type: memory
  type: project
  domain: system
  originSessionId: ab102950-8548-4e2c-b418-f311ce8d01d8
---

A reusable launcher system lives in `C:\Users\AIXMOS\CommandCenter\`. Sleek, big touch tiles (built for the Surface tablet), dark theme, **voice control** (tap-to-speak opens tiles by name; "ask …" routes to the TMMT Assistant for staff; hands-free wake-word "command …"). Needs Edge/Chrome for voice.

- **CEO-Dashboard.html** — the owner's (role `owner`, sees everything). The user's daily driver.
- **Dashboard-Template.html** — master. Copy + edit the `PROFILE` block (name, role, subtitle, optional `extraTiles`) to make anyone's. To make a new one, change 3 lines.
- **TeamDashboards\** — 17 generated per-person dashboards (see [[people-hub]] roster).
- **README-Dashboards.md** — the how-to + role chart.

**Roles** (least→most access): family/friend/vendor (personal links only) · operator · sales · dispatch · manager · owner. The tile **catalog (`SECTIONS`) is duplicated in every file** so each is self-contained/shareable — to change a link for everyone, edit the template and re-copy (or refactor to a shared `dashboard.js`, not yet done).

**Owner-only tiles, never shown to anyone else:** Stripe, Supabase, Vercel, GitHub, Investor, Local dev, Cursor. This was an explicit user requirement (least exposure). Access is also login-gated, but the links don't even render for non-owners.

## Mission Control (built 2026-06-06, in [[tmmt-system]] = tmmt-os, verified typecheck+build, NOT yet deployed)
Live "Your Mission Now" board in tmmt-os: every role sees what's happening (live counts), what they're needed for (with the AIXMOS agent that flagged it), grow-&-scale moves, the 5 agents on watch, and (owner) a ventures roll-up. Files: `src/lib/mission/{types,board,generate,notify}.ts`, `src/components/mission/mission-board.tsx`, wired into owner/team/vendor dashboards. Phase 2: new isolated `mission_items` table (migration `0008_mission_control.sql`, applied to Supabase with RLS) — agent/system missions persisted; computed content is the always-on fallback. Route `POST /api/mission/generate` (header `X-Mission-Secret: $MISSION_WEBHOOK_SECRET`, body `{notify}`) regenerates + optionally pushes Telegram. Phase 3: `src/lib/telegram/send.ts` token-ready (no-op until `TELEGRAM_BOT_TOKEN` set; uses `profiles.telegram_chat_id`).
**Open to go live:** (1) git access to the deployed private repo `AIXMOS537/TMMT` (currently 403) or the user's push path for tmmt-os; (2) `TELEGRAM_BOT_TOKEN`; (3) a daily cron (Vercel cron / n8n) hitting `/api/mission/generate`.

**Why:** user wanted to hand a personalized, dead-simple ("a 5-year-old could use it"), voice-driven dashboard to everyone — team, family, friends, vendors.
**How to apply:** new person → copy template, set name+role, drop in `TeamDashboards\` (work) or hand off directly. Family/friends need real personal links in `extraTiles` (ask the user). The "Message Muhammad" tile points to tmmtautodetail@gmail.com — swap if they want SMS/booking instead.