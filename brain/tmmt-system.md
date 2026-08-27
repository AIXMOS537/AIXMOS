---
name: tmmt-system
description: "The TMMT production app — Next.js 16 + Supabase rental-management system, the \"TMMT brain\""
metadata: 
  node_type: memory
  type: project
  originSessionId: 05286da1-b7da-474a-bb4e-c792d0a2d7ff
---

The "TMMT brain / brainiac" is a **production vehicle-rental management system**: Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind 4 + Supabase Postgres (44 tables). Replaced an old Airtable workflow.

- **Local repo:** `C:\Users\AIXMOS\TMMT` (git, node_modules installed, branch `master`)
- **GitHub:** https://github.com/Metavibez4L/TMMT
- **Deploy:** Vercel (production runs there; `npm run build` is the CI gate)
- **Backend:** Supabase (RLS enabled on all tables); reachable via the Supabase MCP connector
- See `C:\Users\AIXMOS\TMMT\CLAUDE.md` for full architecture, patterns, and roadmap.

**Key gap on the Windows tablet (Surface Pro 4):** no local `.env`, so the app can't run locally — needs `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (+ optional `NEXT_PUBLIC_SENTRY_DSN`, `AIRTABLE_PAT`). Editing + pushing works fine; Vercel runs the deployed app.

The old `D:\TMMT MANAGEMENT` / `D:\AIX_AI_COMMAND_SYSTEM` lived on an external/SD drive that is **no longer mounted**. Ignore the dead `D:\` paths.

## ⚠️ Codebase topology (verified 2026-06-06 — there are TWO TMMT apps)
- **LIVE app = `C:\Users\AIXMOS\CommandCenter\tmmt-os`** — Next.js role-portal app (owner/team/vendor/client/internal portals, `/v/[venture]/*` multi-venture, AIXMOS agents in `src/lib/agents`). This is what serves **tmmt-ops.vercel.app** (its login "partner portal & operations" matches; build exposes `/internal/dispatch`, `/investor/dashboard`, `/team/dashboard`, `/v/[venture]/*` = the launcher links). Has `node_modules` + `.env.local`; `npm run typecheck`/`build` work locally. **BUT it is NOT a git repo locally**, and it deploys from a **private GitHub repo `AIXMOS537/TMMT`** that the local git credentials **can't access (403)** — so pushing/deploying needs the user to grant repo access or confirm their push path.
- **OLD gen = `C:\Users\AIXMOS\TMMT`** — the earlier `(admin)` app (pages `/fleet`, `/leads`, `/tickets`); git remote `Metavibez4L/TMMT` (HEAD `dada755`). Pushable, but NOT what's deployed at tmmt-ops. The CLAUDE.md there describes this older app.
- Both apps appear to point at the **same Supabase** project `uapxakmlwnpfsftfeezx`.
