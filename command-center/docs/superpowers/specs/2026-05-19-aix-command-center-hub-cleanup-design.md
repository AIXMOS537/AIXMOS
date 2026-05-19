# AIX Command Center — Operations Hub Cleanup

**Date:** 2026-05-19
**Status:** Approved design — ready for implementation plan

## Goal

Turn `AIXMOS537/AIX-Command-Center` into a clean, private operations hub for a
solo operator. The hub holds operational docs, SOPs, and automation configs. It
*points to* the TMMT Rentals application — it does not contain the app code. The
TMMT Rentals app stays in its own private repo (`AIXMOS537/TMMT`) and deploys to
Vercel from there.

## Decisions (locked with the owner)

1. **Access:** `AIX-Command-Center` and `TMMT` are both now **private** on
   GitHub. Owner (`AIXMOS537`) is sole collaborator. Access is granted by adding
   GitHub collaborators — not by editing files.
2. **One app, not two.** "TMMT Rentals" (the `TMMT` repo, Next.js 16, full
   admin + customer forms + partner portal) is the product. "TMMT OS" (the
   Next.js 14 prototype buried in `AIX_AI_COMMAND_SYSTEM/integrations/tmmt-os/`)
   is an earlier prototype that TMMT Rentals supersedes. It is archived, not
   deployed.
3. **Reorg scope = Medium.** Add a map + tidy the root. Do **not** rename or
   merge the large system folders (`AIX_AI_COMMAND_SYSTEM`, `AIXMOSXTMMT-OPS`,
   `ops`). The README explains them instead.
4. **`TMMT MANAGEMENT/` content lives on another machine.** The repo currently
   has a broken, empty submodule pointer (gitlink mode 160000, no `.gitmodules`).
   Replace it with a normal folder + a restore-instructions README, preserving
   the existing paths so daily-doc links work once the content is synced back.
5. **Vercel state unknown.** Provide a verify-and-connect guide; the owner runs
   the Vercel connection (it needs their Vercel login).

## Part A — Clean up `AIX-Command-Center`

### A1. New root `README.md`

The single entry point. Sections:

- **What this is** — private operations hub for TMMT.
- **Access** — private repo, owner-only; grant access via GitHub collaborators.
- **Start here** — `OWNER_DAILY_COMMAND.md` is the daily entry point.
- **Directory map** — a table with one row per top-level folder explaining its
  purpose and whether it is canonical or legacy:
  - `AIX_AI_COMMAND_SYSTEM/` — main AI command bundle (prompts, SOPs, scripts).
  - `AIXMOSXTMMT-OPS/` — "Empire OPS" automation infra (docker, n8n, SQL).
  - `ops/` — moose automation stack.
  - `agents/` — agent definition files.
  - `docs/` — investor workspace + AI guides.
  - `guides/` — setup / how-to docs (new folder).
  - `archive/` — dated reports and superseded material (new folder).
  - `TMMT MANAGEMENT/` — operational docs; content synced from another machine.
- **Apps & Deployment** — TMMT Rentals lives in the private `AIXMOS537/TMMT`
  repo, deployed to Vercel. Links to the repo, the Vercel project (once known),
  and the env-var checklist.

### A2. Root tidy — 14 loose files become 5

Keep at root (daily-driver / always-visible):

- `README.md` (new)
- `OWNER_DAILY_COMMAND.md`
- `THIS_WEEK.md`
- `STATUS_UPDATE.md`
- `PRIORITY_PLAN_ALL_PILLARS.md`

Move into `guides/`:

- `CHANNEL_SETUP_GUIDE.md`
- `CHANNEL_STACK_GHL_WHATSAPP_SLACK.md`
- `GROUP_CHAT_OPERATING_SYSTEM.md`
- `GROUP_CHAT_TEMPLATES_PRINT.md`
- `VA_SETUP_TODAY.md`
- `WEEK_1_GHL_WHATSAPP.md`
- `INSTALL.md`
- `OPEN_IN_CURSOR.md`

Move into `archive/`:

- `CONSOLIDATION_REPORT.md` (dated 2026-05-16 report — historical)

Convert:

- `CURSOR_IGNORE_RULES.txt` → a proper `.cursorignore` file at the repo root;
  delete the `.txt`.

### A3. Remove the broken `TMMT MANAGEMENT` submodule

The directory is registered as a gitlink (`160000`) but there is no
`.gitmodules` file, so it can never be cloned and is permanently empty.

- Remove the gitlink from the index (`git rm --cached "TMMT MANAGEMENT"`).
- Create a normal `TMMT MANAGEMENT/` directory containing a `README.md` that
  explains: the operational content (`OPERATIONS/`, `FLEET/`, `AI_BRAIN/`,
  `AUTOMATIONS/`, `CUSTOMERS/`, `SOPS/`) lives on another machine, and must be
  copied into this folder to restore the links used by `OWNER_DAILY_COMMAND.md`.
- Keep the folder path `TMMT MANAGEMENT/` unchanged so existing relative links
  resolve once the content is restored.

### A4. Delete the superseded TMMT OS prototype

- Delete `AIX_AI_COMMAND_SYSTEM/integrations/tmmt-os/`.
- Add a one-line note to `archive/` recording that TMMT OS was a Next.js 14
  prototype superseded by TMMT Rentals (`AIXMOS537/TMMT`).

### A5. Delete `all_in_one_platform/`

Abandoned Next.js scaffold. Its `package.json` is byte-corrupted (a space
inserted between every character — not valid JSON, cannot build). It is neither
TMMT OS nor TMMT Rentals. Delete the directory.

### A6. Delete the dead `AIXMODE/` stub

`AIXMODE/` contains only a 7-line "portable shortcut" README. Delete it and
clean its three stale references:

- `AIX_AI_COMMAND_SYSTEM/scripts/sync-to-lexar.sh`
- `AIX_AI_COMMAND_SYSTEM/scripts/sync-to-lexar.ps1`
- `INSTALL.md` (now in `guides/`)
- (`CONSOLIDATION_REPORT.md` mentions it historically — left as-is in `archive/`.)

### A7. Fix links

For every file moved in A2 and every file deleted in A3–A6:

- Rewrite relative links inside moved files (e.g. `INSTALL.md` and
  `OPEN_IN_CURSOR.md` use `./` paths that become `../` from `guides/`).
- Rewrite inbound links from files that point at moved targets (e.g.
  `OWNER_DAILY_COMMAND.md` links to `OPEN_IN_CURSOR.md` and `INSTALL.md`).
- Verify no remaining link points at a deleted path (`AIXMODE/`,
  `all_in_one_platform/`, `AIX_AI_COMMAND_SYSTEM/integrations/tmmt-os/`).

## Part B — TMMT Rentals → Vercel

### B1. `DEPLOY.md` in the `TMMT` repo

Add a `DEPLOY.md` to `AIXMOS537/TMMT` covering:

- Connecting the repo to a Vercel project (owner runs this — needs Vercel login).
- Framework preset: Next.js. Build command `next build`, output default.
- Required environment variables: Supabase URL + anon key + service role key,
  Sentry DSN. Cross-reference the repo's existing `scripts/check-env.mjs`.
- Production vs. preview branch behavior.
- A note that the repo is private and the Vercel project must be too.

### B2. Hub ↔ app link

The `README.md` "Apps & Deployment" section (A1) ties the hub to the app: the
`TMMT` repo URL, the Vercel project URL (filled in once known), and the env-var
checklist.

## Out of scope

- Renaming or merging `AIX_AI_COMMAND_SYSTEM`, `AIXMOSXTMMT-OPS`, or `ops`
  (this is the "Heavy" reorg the owner declined).
- Any change to TMMT Rentals application code.
- Performing the Vercel deployment (requires the owner's Vercel account).
- Recovering the `TMMT MANAGEMENT/` content (it is on another machine).

## How changes land

All edits are made in local clones, committed, and **pushed to the private
GitHub repos**. Diffs are shown to the owner before pushing. Two repos are
touched: `AIX-Command-Center` (Part A) and `TMMT` (Part B).

## Success criteria

- Opening `AIX-Command-Center` shows a `README.md` that maps the whole repo.
- Repo root has 5 files instead of 14; everything else is filed.
- No broken internal links; no dangling submodule.
- No corrupted or duplicated app code in the repo.
- `TMMT` repo has a `DEPLOY.md` describing the Vercel path.
- Both repos are private.
