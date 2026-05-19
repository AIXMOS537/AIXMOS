# AIX Command Center

Private operations hub for TMMT — daily command docs, SOPs, automation
configs, the AIX AI command system, and the investor workspace.

This repo is the **hub**: it holds the docs and configs you run operations
from, and it points to the apps. The apps themselves live in their own repos.

## Access

This is a **private** GitHub repository — only the owner can see it.
Access is controlled on GitHub, not in these files:

- **To grant someone access:** GitHub → repo → *Settings → Collaborators →
  Add people*. Add the minimum needed; remove them when done.
- Editing files here does **not** change who can see the repo.

## Start here

| When | Open |
|------|------|
| Every morning (20 min) | [`OWNER_DAILY_COMMAND.md`](./OWNER_DAILY_COMMAND.md) |
| This week's checklist | [`THIS_WEEK.md`](./THIS_WEEK.md) |
| Where things stand | [`STATUS_UPDATE.md`](./STATUS_UPDATE.md) |
| The 90-day plan | [`PRIORITY_PLAN_ALL_PILLARS.md`](./PRIORITY_PLAN_ALL_PILLARS.md) |

## Apps & Deployment

One app is built and deployed: **TMMT Rentals**.

| App | Repo | Hosting |
|-----|------|---------|
| **TMMT Rentals** — vehicle rental management (admin, customer forms, partner portal) | `AIXMOS537/TMMT` (private) | Vercel |

- Deployment steps and required environment variables: see `DEPLOY.md` in the
  `AIXMOS537/TMMT` repo.
- Vercel project: **`tmmt-c919`** (already connected; pushes auto-deploy).
- The older `tmmt-os` prototype was retired — see
  [`archive/TMMT_OS_ARCHIVE_NOTE.md`](./archive/TMMT_OS_ARCHIVE_NOTE.md).

## Directory map

| Folder | What it is |
|--------|------------|
| `AIX_AI_COMMAND_SYSTEM/` | **Canonical** AI command bundle — prompts, SOPs, Python CLI/API, scripts, Airtable templates. |
| `AIXMOSXTMMT-OPS/` | "Empire OPS" automation infrastructure — Docker, n8n workflows, SQL, ops scripts. |
| `ops/` | MOOSE automation stack (`ops/files/` — brain.js, moose.js, launchers). |
| `agents/` | Agent definition files (business brain, command center, media). |
| `docs/` | Investor workspace (pitch deck, financial model, one-pager) + local-AI guides. |
| `guides/` | Setup and how-to docs — channels, group chat, VA onboarding, install. |
| `archive/` | Dated reports and retired material. |
| `TMMT MANAGEMENT/` | Day-to-day TMMT ops docs. **Content is synced from another machine** — see the folder's `README.md` to restore it. |

## Root files

`README.md` (this map) · `OWNER_DAILY_COMMAND.md` · `THIS_WEEK.md` ·
`STATUS_UPDATE.md` · `PRIORITY_PLAN_ALL_PILLARS.md` · `.cursorignore`
