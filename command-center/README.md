# AIX Command Center

Owner's work command center: agents, tools, configs.

## Quick links

- **Operating guide:** [`OPERATING_GUIDE.md`](OPERATING_GUIDE.md)
- **v1 spec (brain-dump → ClickUp):** see `~/Documents/TMMT/docs/superpowers/specs/2026-05-21-brain-dump-clickup-agent-design.md`
- **v1 plan:** see `~/Documents/TMMT/docs/superpowers/plans/2026-05-21-brain-dump-clickup-agent.md`

## Layout

```
config/              — venture registry (committed)
tools/               — Python tools registered with Open WebUI
agents/              — persona prompt markdown files
.env                 — secrets (gitignored)
```

## Runtime

Designed to run on the always-on home Windows PC. Open WebUI hosts the chat;
tools in `tools/` are registered in Open WebUI's admin → workspace → tools.
