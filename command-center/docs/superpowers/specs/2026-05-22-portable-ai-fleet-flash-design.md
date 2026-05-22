# Portable AI Fleet + Flash Drive Design

Date: 2026-05-22

## Goal

Create a local-first AI and app-building setup across three machines and three flash drives.

The system should let the owner code manually in a terminal, use low-cost local AI for routine work, reserve cloud models for high-judgment tasks, and keep production apps hosted only where public access is needed.

## Machine Roles

### Home PC: Brainiac 7

The home PC is the stationary primary AI brain. It never travels.

Responsibilities:

- Run Ollama for local models.
- Run Open WebUI for browser-based local AI chat.
- Run n8n and Qdrant when automations and memory are enabled.
- Host AIXMOS executive prompts and local-first workflows.
- Stay private behind Tailscale or LAN. No public port forwarding.

### Work Mac: Coding Brain

The work Mac normally stays at the office. It is the main app-building machine and can be remoted into while traveling.

Responsibilities:

- Run TMMT locally for development.
- Run Cursor, Codex, terminal tools, build checks, tests, and deploy tooling.
- Call Brainiac 7 over Tailscale for local model inference when useful.
- Keep a clean canonical code path and avoid duplicate Desktop working trees.

### Personal Mac: Mobile Control Station

The personal Mac is the mobile control and sync machine.

Responsibilities:

- Remote into the work Mac and Brainiac 7.
- Inspect, refresh, and verify flash drives.
- Do light local coding and review.
- Carry no unique source of truth that is not backed up elsewhere.

## Hosting Boundary

Local machines are for private development, local AI, automation, and operations.

Public production remains:

- GitHub for code source of truth.
- Vercel for public web hosting.
- Supabase for production database and auth.

Ollama, Open WebUI, n8n, Qdrant, SSH, and local dev servers must stay private through Tailscale or LAN only.

## Flash Drive Roles

### AIXMOS02: MASTER

Role: gold source and owner-only master kit.

Why: it is a 31 GB drive and currently has the broadest set of system materials, including TMMT, AIX command assets, AI-OPS materials, releases, and previous app build files.

Rules:

- Owner-only.
- Holds the clean master portable kit and archived source materials.
- May contain sensitive recovery material only if explicitly chosen by the owner.
- Must clearly label secrets and never pass them to FIELD.
- Should not be the daily scratch drive.

### CYBORG: WORK

Role: daily transport and active working kit.

Why: it is a 31 GB drive with AIXMOS agents, setup scripts, TMMT management materials, app build files, and plug-and-play launchers.

Rules:

- Used between personal Mac, work Mac, and office setup.
- Carries current docs, setup helpers, and machine bootstrap scripts.
- Excludes generated dependency/build folders such as `node_modules`, `.next`, `.venv`, and test artifacts from future syncs.
- Excludes secrets unless the owner explicitly places them in an owner-only encrypted vault.

### LEXAR: FIELD

Role: simplified operator/team/recovery drive.

Why: it is the smaller 16 GB drive and is best reserved for the safe, stripped kit that can be handed to a helper or used in an emergency.

Rules:

- No real `.env`, private keys, API tokens, service-role keys, production env dumps, or secret folders.
- No heavy generated folders like `node_modules`, `.next`, `.venv`, or test artifacts.
- Includes PDFs, simple guides, operator launchers, team workflows, and offline "what to do if the boss laptop is unavailable" docs.
- Customer-facing or money-facing actions remain human-approved.

## Standard Portable Layout

Each drive should expose a clear top-level entrypoint:

```text
START-HERE.md
README_LOAD_FIRST.txt
AI-OPS-STARTER/
AIXMOS-AGENTS/
AIX-Command-Center/
portable-setup/
installers/
docs/
scripts/
checksums/
```

Drive-specific files should make the role obvious:

```text
ROLE-MASTER.md
ROLE-WORK.md
ROLE-FIELD.md
```

## Sync Rules

Default exclusions for every sync:

```text
.env
.env.*
secrets/
SECRETS/
*secret*
*token*
*.key
*.pem
id_rsa
id_ed25519
node_modules/
.next/
.vercel/
.venv/
__pycache__/
.pytest_cache/
test-results/
*.tsbuildinfo
.DS_Store
._*
```

FIELD gets the strictest profile: docs, guides, installers, launchers, templates, and examples only.

WORK gets the developer profile: docs, source code, scripts, config examples, package files, and setup helpers.

MASTER gets the owner profile: all clean source materials plus archives, releases, and explicit owner-only recovery notes.

## First Implementation Pass

To avoid destructive changes, the first pass should create a clean kit folder and role markers on each drive without deleting existing material.

Proposed top-level folder:

```text
AIXMOS-PORTABLE-KIT/
```

Inside it:

```text
AIXMOS-PORTABLE-KIT/
  START-HERE.md
  ROLE-*.md
  MANIFEST.txt
  AI-OPS-STARTER/
  AIXMOS-AGENTS/
  AIX-Command-Center/
  portable-setup/
  docs/
  scripts/
  checksums/
```

After the clean kit is verified, a later cleanup can archive or remove old duplicate material from each drive.

## Verification

Verification should confirm:

- All three drives are mounted.
- Role markers exist.
- `START-HERE.md` exists at the root and inside `AIXMOS-PORTABLE-KIT`.
- FIELD contains no real `.env`, key, token, or secrets path inside the clean kit.
- No generated dependency/build directories exist inside the clean kit.
- Checksums or manifests are generated for the clean kit.

## Open Questions

- Whether to later wipe/reformat old clutter from the drives after the clean kit is verified.
- Whether MASTER should include an encrypted owner vault for secrets, or whether all secrets should remain only in a password manager.
- Whether Brainiac 7 is already reachable by Tailscale name, or still needs first-time networking setup.
