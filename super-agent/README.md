> Current client release: see [LOCAL-AGENT.md](LOCAL-AGENT.md) for version 2.1.0, direct Claude/Cursor pairing, lifecycle commands and tested limits. The original project documentation below describes the broader legacy application. Shell execution uses normal user permissions, not an OS sandbox. The legacy free public image setting is enabled by default.

# Project AIXMOS — JARVIS super agent

Private, local-first assistant on `http://localhost:8770`. Python 3 standard library plus two
vendored packages (`requests`, `pillow`), talking to the local Ollama daemon. Nothing leaves the
machine unless you connect a cloud provider or an email account.

```
project_aixmos_server.py   HTTP server: chat streaming, intent routing, core /api routes
aixmos/surfaces.py         extra routes: vault / skills / CRM / carousel / agent, /v1 (OpenAI-style), /mcp
index.html                 JARVIS UI: Chat, Image Lab, Video Lab, Mail, Super Agent, Vault & Skills, Ops & CRM, Integrations
context_tools.py           live context (time / location / weather / CPU / RAM)
aixmos/
  settings.py    provider registry + memory/settings.json (keys, prefs, business profile, brand)
  llm.py         Ollama helper (JSON calls, tool calling)
  media.py       media store (memory/media/*), ffmpeg + ffprobe discovery
  jobs.py        background jobs with polling status
  intents.py     chat commands: /image /video /edit /email /agent /carousel /vault /skill /lead /book
  imagegen.py    image providers + the self-improving learning loop
  videogen.py    video providers + zero-key local storyboard fallback
  videoedit.py   prompt -> plan -> validated ffmpeg pipeline (captions via whisper.cpp)
  email_tools.py SMTP/IMAP any provider, Google OAuth, Microsoft OAuth+PKCE, AI draft/refine/send
  knowledge.py   the AI Building Kit vault: BM25 index over memory/kit
  skills.py      pack personas + prompt library + business profile
  crm.py         leads, scoring, appointments, revenue, follow-up sequences, weekly review
  carousel.py    carousel copy (local model) + Pillow slide renderer
  agent.py       the super agent: tool loop, sandboxed workspace, autonomy levels
vendor/          pip install --target vendor requests pillow   (gitignored)
memory/          conversation, settings, learning data, media, kit, workspace   (gitignored)
whisper/         whisper.cpp binary + ggml-base.en model         (gitignored)
```

## Install anywhere: the AIXMOS 4THEPEOPLE bundle (one path for every client)
`python installer/build_installer.py` produces `dist/AIXMOS-4THEPEOPLE/` (also on GitHub Releases):

| File | For |
|---|---|
| `AIXMOS-4THEPEOPLE-Setup.exe` | Windows 10/11, one file: native stub + payload (app, vendored packages, whisper.cpp + model, ffmpeg/ffprobe, the AI Building Kit, embeddable Python 3.14) |
| `mac-linux/AIXMOS-Install.command` (or `bash install.sh`) | macOS and Linux: installs to `~/AIXMOS`, creates a venv, installs Ollama, pulls the model |
| `START-HERE.txt`, `SHA256SUMS.txt` | the two-minute instructions and checksums |

Every install first works out **who the user is**, and Genesis adapts to the answer:

| Role (`--role`) | What AIXMOS does for them |
|---|---|
| `student` | study partner, deadline planner, research with sources, portfolio projects. It explains and coaches, and never writes graded work for them |
| `employee` | email/document drafts, meeting notes to actions, small automations. Work data stays on the machine, and it asks about company AI policy |
| `builder` (`aixmos_member`) | build partner for their own business or product |
| `everything` (`all`) | the full station: every feature in one place |

Every role gets its own intake questions, capability showcase, first plan and guardrails, which are carried into
every chat and agent prompt. Everyone gets the super agent, the vault, the CRM, media, mail and the first-boot **Genesis**.

The Windows installer needs no admin rights (`%LOCALAPPDATA%\AIXMOS`), installs Ollama silently if it
is missing, pulls `qwen2.5:3b` once (about 2 GB), writes Start/Stop launchers, a desktop shortcut and a
per-user logon autostart, then opens the UI. Re-running upgrades the app and keeps `memory/`.
Flags: `--role student|employee|builder|everything --dir PATH --port N --no-ollama --no-model
--no-autostart --no-launch --no-shortcuts --no-mcp --quiet`. No secrets ship in the payload; a build
gate refuses to package any live-looking key. Setup runs the downloaded Ollama installer only after
Windows confirms a valid Authenticode signature from Ollama.

## Security model (Phase 1)
* The server answers only this machine: the Host must be localhost on its port, any Origin must be its own, and a
  cross-site POST is refused. That stops web pages (CSRF) and DNS rebinding from driving it.
* `/mcp` and `/v1` default to **safe** (read-only) tools. When nobody can answer the agent's question, the run stops
  instead of the agent deciding for you.
* Once a run has read web content, every write, command, Python run or email needs your yes for that exact call. Web
  text is marked as untrusted data.
* The agent cannot fetch this machine, the LAN or mesh (Tailscale) addresses, and each redirect is re-checked.
* File access resolves links and junctions, so nothing escapes the workspace or the folders you allowed.
* Pollinations (free, **public**) is off until you choose it, so image prompts never leave the machine by default.
* Tests: `python -m unittest discover -s tests -v` (stdlib, no network, never touches `memory/`); CI runs them on Windows, macOS and Linux.

## Run from source
`START-PROJECT-AIXMOS.bat` (starts the server on 8770 if the port is silent, opens the UI).
Manual: `python project_aixmos_server.py 8770`.

## Talk to it
| Say | What happens |
|---|---|
| `generate an image of …` | learned-taste prompt enhancement, provider render, rate it in chat |
| `make a video of …` | background job; cloud providers when keyed, local storyboard otherwise |
| `trim the first 5 seconds and add captions` | edits the loaded video with ffmpeg |
| `write an email to x@y.com about …` | AI draft opens in Mail; you press Send |
| `/agent build me a …` or `build me a python script that …` | the super agent plans and executes with tools |
| `/skill receptionist` (or appointment-setter, cold-outreach, content-engine, sales-pack …) | AIXMOS follows that pack's playbook in every reply |
| `/vault how do I qualify a lead` | raw passages from the kit |
| `/lead …`, `/book …`, `/carousel …` | CRM lead, appointment, Instagram carousel |
| `/research …`, `google …`, `fact-check …`, `look up …` | scours the web, reads the top pages, and cross-references them against the vault: agreements, conflicts, gaps, sources |

## Web research and cross-referencing
`aixmos/research.py` searches Google through the official Custom Search JSON API when you add an API key
and Search-engine ID under Integrations (SerpAPI is also supported), and falls back to DuckDuckGo with no
key. It reads the top pages in parallel, extracts the passages that match the question, pulls the matching
vault passages, and has the local model produce a cited report: answer, where vault and web agree, where they
conflict, what only the vault says, what only the web adds, a confidence rating and a next step. Available in
chat, in the Vault panel's "Research the web" tab, and to the agent as the `research` tool.

## Use it from other software
* **OpenAI-compatible API**: base URL `http://localhost:8770/v1`, any key, model `aixmos`
  (chat with vault + skills + memory) or `aixmos-agent` (runs the agent, streams steps).
* **MCP server**: `http://localhost:8770/mcp` (streamable HTTP). For Claude Code:
  `claude mcp add --transport http aixmos http://localhost:8770/mcp`. Tools follow the
  `mcp_autonomy` preference (default *safe*: read, search, vault, drafts; raise it to *builder* under Integrations
  to allow files and commands inside the workspace).

## Super agent
Autonomy levels: **safe** (read, search, generate), **builder** (+ write files, run commands and
Python inside `memory/workspace` and any folders you allow), **full** (+ send email, only with the
allow-send preference). Doctrine from the kit: plan first, small steps, prove with output, never
fabricate, ask when unsure, finish with a summary. Runs are logged in the Agent panel.

## Performance build (why it feels smooth on a small laptop)
Treat the stack like a PC build; each part has one job and one bottleneck.

| Part | What it is here | What was tuned |
|---|---|---|
| CPU | i7-6650U class, 2 cores / 4 threads, 15 W | model runs on 3 threads (one left for the desktop); ffmpeg `superfast` with 3 threads; whisper base.en; web research reads 2 pages at a time |
| Memory bandwidth | prompt processing ≈ 20 tokens/s, generation ≈ 7 tokens/s on the 3B | the prompt is split into a **stable prefix** (base prompt, skill, profile, mission) and a **per-turn tail** (vault passages, time), so Ollama's prompt cache is reused and a turn only pays for what is new; history replayed is capped (12 messages, 1,200 chars each); vault passages 1,200 chars |
| Model loading | Ollama restarts its runner whenever the context size changes (~4 s) | one `llm_ctx` (4096) and one thread count for every feature; `keep_alive` 30 min |
| RAM (16 GB) | 3B ≈ 2 GB resident | 7B is opt-in only (it took the machine down once) |
| GPU / display | desktop drawn through a USB DisplayLink dock at 200 % scaling: every animated pixel is CPU work | Performance mode (auto on weak CPU, high-DPI, or battery): no blur, no scanlines, static reactor, slower HUD polling, none when the tab is hidden |
| Storage (NVMe) | media store under `memory/` | scratch clips older than a day are cleared at start |
| Power | Surface throttles at 15 W under sustained load | thread headroom above; run heavy jobs (video, research) one at a time |

All of it is adjustable under Integrations → Defaults (performance mode, threads, context size, history).

## Hardware note
This machine (2 cores, 1 GB iGPU) cannot run diffusion or video models locally, and the 7B model
is too heavy for agent runs. Image and video *generation* use provider APIs (Pollinations needs no
key); editing, captions, speech-to-text, chat, vault, CRM and the agent run fully local on the 3B.
