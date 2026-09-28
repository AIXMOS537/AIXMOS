# AIXMOS

The AIXMOS engine in one repo.

| Folder | What it is | Came from |
|---|---|---|
| `command-center/` | Ops cockpit, dashboards, SOPs | AIX-Command-Center |
| `agents/` | Operations agent toolkit | AIXMOS-AGENTS |
| `brain/` | Business playbooks and architecture notes | aixmos-brain |
| `super-agent/` | Local all-in-one assistant (chat, images, email, CRM) | project-aixmos |
| `kit/` | Installer that sets up the stack on a new machine | aixmos-kit |
| `gateway/` | Cloudflare Workers AI proxy | aixmos-gateway |
| `llm-router/` | Cost-controlled LLM gateway | llm-lane-router |
| `starter-pack/` | Portable local-AI starter pack | AIXMOS-COMMAND (local) |
| `archive/` | Earlier versions, kept for reference | PROJECTAIXMOS, AI-OPS-STARTER, voice agent |

Each folder keeps its full git history. Branches that were not an old repo's main line are kept as tags named `legacy/<folder>/<branch>`.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first change.
