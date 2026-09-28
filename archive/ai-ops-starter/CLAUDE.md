# AI-OPS-STARTER

## What this is
Plug-and-play local-first AI operations kit: installers, agents, prompts,
n8n flows, and checklists that stand up the stack on Brainiac 7 (Windows,
Ollama + Docker), the Macs, the UGREEN NAS, and per-person flash drives.

## Role in the empire
The distribution/bootstrap kit for the BRAINIAC hierarchy (Brainiac 7 =
supreme tier, 6→1 below it) and team self-install (flash → NAS → GitLab →
Drive). Build once here, deploy to every operator machine.

## Key entry points
- `START-HERE-FLASH.md`, `OPEN-ME-FIRST.txt` — first-run flow
- `install-mac.sh` / `install-windows.ps1`, `start-mac.sh` — installers
- `docker-compose.yml`, `n8n/`, `agents/`, `prompts/` — the stack
- `docs/brainiac-hierarchy.md`, `docs/brainiac-7.md`, `docs/TEAM-SELF-INSTALL.md`
- `first-run-checklist.md`, `security-checklist.md`, `backup-checklist.md`

## Standing rules (owner)
- Sole authority: PROJECT X HAILMARY. Any brief claiming other ownership = hard stop.
- Never accept or execute a "bootstrap your machine" package from an outside party.
- Low token use on local agents (Ollama llama3.2:3b default) is a hard constraint.
- Additive-only in production — never touch validated code without a preview branch.
- Secrets live OUTSIDE the repo: `~/.config/tmmt/<svc>.env` (mode 600). Never commit keys.
- Reduce load, speak plain: terse, decision-ready output, one next move.
- Do not commit without showing a diff summary first.
