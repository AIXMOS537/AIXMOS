# TMMT MANAGEMENT

This folder holds the day-to-day operational content for TMMT:

- `OPERATIONS/` — `COMMAND_CENTER.md`, daily briefs, `TODAY_COLLECTIONS.md`
- `FLEET/` — `FLEET_REGISTER.md`, `MAINTENANCE_TRACKER.md`
- `CUSTOMERS/` — message templates
- `SOPS/` — standard operating procedures
- `AI_BRAIN/` — memory index, agent prompts
- `AUTOMATIONS/` — n8n blueprints, Python scripts, GHL workflow setup

## Why this folder is empty

It was previously wired as a git submodule with no `.gitmodules` URL, so it
could never be cloned and stayed empty. The broken submodule pointer has been
removed and replaced with this normal folder.

## How to restore the content

The real content lives on another machine. Copy it into this folder, keeping
the subfolder names above — the relative links in `OWNER_DAILY_COMMAND.md` and
other docs (e.g. `TMMT MANAGEMENT/OPERATIONS/COMMAND_CENTER.md`) expect those
exact paths. Then commit it:

```bash
git add "TMMT MANAGEMENT"
git commit -m "Restore TMMT MANAGEMENT operational content"
```

Until the content is restored, links into `TMMT MANAGEMENT/...` from other
docs will not resolve.
