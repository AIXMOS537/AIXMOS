# AIXMOS Brain 🧠

Private knowledge base / second brain for Muhammad Taha (AIXMOS / TMMT). This is the **single source of truth** that the AI bot reads and writes — it syncs across devices (this Surface tablet ↔ Brainiac ↔ Macs) and opens directly as an **Obsidian vault** (every file is markdown with `[[wiki-links]]`).

## How it's wired
- On the **home tablet**, Claude's memory folder (`~/.claude/projects/C--/memory`) is a **junction** to this repo — so anything the bot learns is written here automatically.
- This repo is **private** (separate from the business code repo `Metavibez4L/TMMT`) so family/personal info stays private.
- Push from the tablet → pull on Brainiac → open in Obsidian.

## Domain lanes (kept separate — see `home-bot.md`)
- 🧠 **Core** — `user-aixmos.md`
- 💼 **Work** — `work-team.md`, `tmmt-system.md`, `people-hub.md`, `team-drive-kit.md`
- 👨‍👩‍👧 **Family** — `family.md`
- 🤝 **Personal & friends** — `personal-and-friends.md`
- ⚙️ **System** — `home-bot.md`, `device-architecture.md`, `tablet-desktop-setup.md`, `tmmt-cleanup-prefs.md`

Start at [`MEMORY.md`](MEMORY.md) — the index.
