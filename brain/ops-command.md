---
name: ops-command
description: "The single `ops` terminal command that runs the whole operation from the command-hub tablet"
metadata: 
  node_type: memory
  type: project
  originSessionId: c0397b4e-80db-436d-88b3-41c8643364a1
  modified: 2026-08-25T16:52:13.685Z
---

`ops` is THE terminal entry point on the command-hub tablet (see [[device-architecture]]). Built 2026-08-25. Type `ops` from any PowerShell prompt.

- Script: `C:\Users\AIXMOS\CommandCenter\ops\ops.ps1` (+ `ops.cmd` shim). Folder is on the **user PATH**.
- Subcommands: `ops` (dashboard), `check` (runs [[closed-loop-ops]] cycle), `mesh`, `wifi`, `wifi-join "NAME"`, `ai "question"` (offline Ollama, see [[local-ai-ollama]]), `tools`, `clean`, `go` (Mission Control), `help`.
- PowerShell profiles created for BOTH Windows PS 5.1 (`Documents\WindowsPowerShell\`) and PS7 (`Documents\PowerShell\`) — they add ops to PATH, define the `ops` function, plus `cc` / `tmmt` / `brain` directory jumps. There were no pre-existing profiles.
- Desktop launcher `OPS.bat` opens a terminal, shows the dashboard, stays open. Sits beside the existing `TMMT.bat`.
- `ops clean` follows [[tmmt-cleanup-prefs]]: MOVES to `C:\Users\AIXMOS\_QUARANTINE\<timestamp>\`, never deletes.

Constraints learned the hard way: scripts must be **ASCII only** (em-dashes break Windows PowerShell 5.1 parsing) and counts must be wrapped in `@()` or a single result returns a scalar with no `.Count`.

- `ops brain "task"` = the **local agent** (`brain.ps1`): a real tool-using loop on Ollama, free and offline. Tools: get_status, list_files, read_file, search_files, run_closed_loop_check, save_note. Default model `qwen3b-max`, `-Big` switches to `qwen7b-max`. Notes land in the ops notes folder.
- `ops agents` lists every agent + what it costs.
- Agent safety: **read-mostly, no arbitrary shell.** Whitelisted roots only (CommandCenter, TMMT, AIXMOS-Brain, Automation, LocalModels, Desktop); regex-blocks secret/token/password/.env/.pem/id_rsa.
- **Claude Code CLI v2.1.245 IS installed and working** (`AppData/Roaming/npm/claude.ps1`). The `.claude-code-Hjeie59T` dir quarantined 2026-08-25 was a stale temp dir from an older interrupted install - the live install was untouched.
- **opencode v1.18.21** is wired to Ollama via `~/.config/opencode/opencode.json` (openai-compatible provider at `localhost:11434/v1`, default `ollama/qwen7b-max:latest`) - free local coding agent.

Two PowerShell traps hit while building the agent loop, both fixed - worth remembering:
1. `@($null)` yields a **1-element array**, so an LLM's final answer looked like an empty tool call. Filter: `Where-Object { $_ -and $_.function -and $_.function.name }`.
2. Echoing Ollama's `id`/`index` fields back inside `tool_calls` confuses the model - rebuild each call with only `function.name` + `function.arguments`.
