# Local AI Tool Guide — Mac + Windows (AIXMOS stack)

This guide matches your **AIXMOS USB agents** (CHUMMO, MOOSE, BRAIN), **Cursor/VS Code** workflow, and the **local AI fleet** plan in `you-have-the-right-hardware-for/LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md`.

**Practical combo for you:** **Cursor** for daily coding · **Ollama** (local or on `ai-1` over Tailscale) for cheap/offline experiments · **Anthropic API** for CHUMMO/BRAIN/MOOSE production messaging on the USB stack.

---

## Quick comparison

| Tool | Best for | Needs internet? | Cost | Works with AIXMOS USB agents? |
|------|----------|-----------------|------|--------------------------------|
| **Cursor** | Editing, refactors, cloud agent in IDE | Yes (cloud models default) | Subscription | Yes — open `<USB>` as workspace |
| **Ollama** | Private local inference, embeddings | No (after model pull) | Free (your hardware) | Only if you refactor agents to call Ollama API |
| **Claude Code / Claude Desktop** | Terminal/repo automation, long tasks | Yes | Anthropic usage | Yes — same repos, same API key pattern |
| **Codex (OpenAI)** | If you already pay for OpenAI | Yes | OpenAI usage | Separate from CHUMMO (Anthropic SDK) |
| **Continue** (VS Code/Cursor ext.) | Inline chat with **local** models in editor | Optional | Free + your GPU | Pair with Ollama on Mac or `http://ai-1:11434` |

---

## What requires an Anthropic API key today

These scripts use **`@anthropic-ai/sdk`** and **`ANTHROPIC_API_KEY`**:

| Component | Path | API key? |
|-----------|------|----------|
| CHUMMO (messaging) | `CHUMMOCLAUDEOS/chummo.js` | **Required** |
| BRAIN (orchestration) | `files/brain.js` | **Required** |
| MOOSE (execution) | `files/moose.js` | **Required** |
| Web server | `CHUMMOCLAUDEOS/serve.js` | No (static HTML only) |
| Drive menu | `CHUMMOCLAUDEOS/drive-agent.js` | No (launches other tools) |

**Ollama does not replace CHUMMO out of the box.** To use local models in those agents you would need a small adapter (e.g. OpenAI-compatible bridge or direct `fetch` to `http://localhost:11434/api/chat`).

**iMessage** (`shared-utils.js` → `sendText`) is **macOS only**.

---

## Recommended roles (when to use what)

### Cursor — primary IDE (Mac + Windows)

Use when:

- Writing or refactoring code on the USB repo or any Git project
- You want AI inside the editor (Tab, Agent, multi-file edits)
- You already live in Cursor (your `taha1/.cursor` profile)

Setup:

1. Install from https://cursor.com
2. **File → Open Folder** → `<USB>` or `CHUMMOCLAUDEOS`
3. Optional: point a local model via Cursor settings or use cloud models as default

**Note:** Cursor’s built-in models are cloud unless you configure a compatible local endpoint. It is still the best **control station** for your fleet.

### Ollama — local / fleet inference

Use when:

- Privacy, offline work, or high volume without API spend
- Brain-style experiments, drafts, embeddings (`nomic-embed-text`)
- Chat in browser via Open WebUI on a GPU desktop (`ai-1`)

**Do not store large models on the FAT32 USB** (4 GB file limit). Install Ollama and models on the Mac or `ai-1`.

#### macOS

```bash
brew install ollama
# or download from https://ollama.com/download
ollama serve   # often auto-starts as app
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text
```

Remote fleet GPU (from fast-track doc):

```bash
export OLLAMA_HOST=http://ai-1:11434
ollama list
```

Add to `~/.zshrc` for persistence.

#### Windows

1. Install from https://ollama.com/download  
2. Pull models in PowerShell:

```powershell
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text
```

Use **Continue** in VS Code/Cursor: provider **Ollama**, base URL `http://localhost:11434` (or `http://ai-1:11434` over Tailscale).

### Claude Code / Claude Desktop — terminal & desktop agent

Use when:

- Docker, Tailscale, SSH, install scripts, “fix my machine” tasks
- Repo-wide changes from the terminal
- You already copied configs under `taha1/.claude`

Install: https://docs.anthropic.com/en/docs/claude-code

Same **`ANTHROPIC_API_KEY`** as CHUMMO on Mac:

```bash
export ANTHROPIC_API_KEY="your_key"
```

Windows (persistent):

```cmd
setx ANTHROPIC_API_KEY "your_key"
```

### Codex (OpenAI)

Use only if you standardize on **OpenAI** models for some projects. It does not power the USB agents today. Keep API keys separate from Anthropic.

### Fleet layout (from your fast-track doc)

If you have multiple machines in one room:

| Machine | Role |
|---------|------|
| **mac-1** | Cursor, control, light Ollama client |
| **ai-1** | Ollama + Open WebUI (heavy models) |
| **build-1** | Docker, tests, tmux, long jobs |
| **data-1** | Repos, backups, vector DB later |

Rule: **local models for volume; cloud (Anthropic/Cursor) for hard judgment or when local fails twice.**

---

## USB agents — how to run (both OS)

From `<USB>` after `install.sh` / `install.bat`:

| Task | Command |
|------|---------|
| Setup once | `bash install.sh` (Mac) or `install.bat` (Win) |
| CHUMMO | `bash CHUMMOCLAUDEOS/start-mac.sh` or `start-windows.bat` |
| MOOSE | `bash MOOSECLAUDEOS/start-moose-mac.sh` or Windows `.bat` |
| BRAIN | `node files/brain.js` |
| Web UI | `node CHUMMOCLAUDEOS/serve.js` → http://localhost:3000 |
| Menu | `node CHUMMOCLAUDEOS/drive-agent.js` |

See root **`INSTALL.md`** for paths and FAT32 notes.

---

## Decision flowchart

```text
Need to edit code in a project?
  → Cursor

Need outreach/client copy on USB (CHUMMO)?
  → Anthropic API + chummo.js

Need multi-agent delegation (BRAIN/MOOSE)?
  → Anthropic API + brain.js / moose.js

Need free/local draft or embed without API cost?
  → Ollama (+ Continue or Open WebUI)

Need install/Docker/SSH automation?
  → Claude Code

Need OpenAI-specific toolchain?
  → Codex
```

---

## Security reminders

- Do **not** expose Ollama or Open WebUI to the public internet; use **Tailscale** or LAN only.
- Do **not** commit API keys; use env vars or OS keychain.
- Portal HTML on USB has **no auth** until you add it — localhost only for testing.

---

## Related docs on this drive

| File | Purpose |
|------|---------|
| `INSTALL.md` | Node setup, launchers, FAT32 |
| `you-have-the-right-hardware-for/LOCAL_AI_FLEET_FAST_TRACK_CLAUDE_READY.md` | Multi-machine fleet runbook |
| `you-have-the-right-hardware-for/USB_README_START_HERE.md` | Hardware/USB orientation |

---

*For the people. By the people.*
