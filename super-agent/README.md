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

## Run
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

## Use it from other software
* **OpenAI-compatible API**: base URL `http://localhost:8770/v1`, any key, model `aixmos`
  (chat with vault + skills + memory) or `aixmos-agent` (runs the agent, streams steps).
* **MCP server**: `http://localhost:8770/mcp` (streamable HTTP). For Claude Code:
  `claude mcp add --transport http aixmos http://localhost:8770/mcp`. Tools follow the
  `mcp_autonomy` preference (default *builder*: files and commands inside the workspace).

## Super agent
Autonomy levels: **safe** (read, search, generate), **builder** (+ write files, run commands and
Python inside `memory/workspace` and any folders you allow), **full** (+ send email, only with the
allow-send preference). Doctrine from the kit: plan first, small steps, prove with output, never
fabricate, ask when unsure, finish with a summary. Runs are logged in the Agent panel.

## Hardware note
This machine (2 cores, 1 GB iGPU) cannot run diffusion or video models locally, and the 7B model
is too heavy for agent runs. Image and video *generation* use provider APIs (Pollinations needs no
key); editing, captions, speech-to-text, chat, vault, CRM and the agent run fully local on the 3B.
