---
name: device-architecture
description: "Operator's 3-device setup — Windows tablet on-person, carry Mac heavy, work Mac command hub"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05286da1-b7da-474a-bb4e-c792d0a2d7ff
---

Operator wants to run [[tmmt-system]] and the whole business from any device, anywhere. Intended roles:

- **Windows tablet (Surface Pro 4, user AIXMOS)** — "on-person" device; light field/command use. Has git, node v24, npm, python 3.14. Missing: GitHub CLI (`gh`), VS Code, PowerShell 7.
- **Carry Mac** — heavier development / on-the-go work.
- **Work Mac (home)** — the "command hub" / personal assistant that reaches the entire TMMT brain.

**Why this already works "from anywhere":** the actual brain is cloud-based — the GitHub repo, the Supabase DB, the Vercel deployment, and the cloud MCP connectors. Any device running Claude Code signed into the same account reaches all of it. Each new device only needs: Claude Code installed + repo cloned (`git clone https://github.com/Metavibez4L/TMMT.git`) + a local `.env` if it needs to run the app locally (vs. just edit + push).

## 🧠 The Brain repo (this file lives in it)
The AI bot's memory is now a **private git repo at `C:\Users\AIXMOS\AIXMOS-Brain`** (set up 2026-06-06). On the home tablet, Claude's memory folder (`~/.claude/projects/C--/memory`) is a **directory junction** pointing at this repo — so every memory write lands here automatically. It's an **Obsidian vault** (plain markdown). Kept SEPARATE from the business code repo so family/personal stays private. To reach **Brainiac** + Macs: push from tablet → `git clone https://github.com/Metavibez4L/AIXMOS-Brain.git` on each device → open in Obsidian. Remote not yet connected (needs the private GitHub repo created; `gh` CLI is not installed on the tablet).
