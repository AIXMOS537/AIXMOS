# Open WebUI — Import Instructions (Brainiac 7)

## Prerequisites

- **Brainiac 7** stack running: http://127.0.0.1:3000
- Ollama models pulled: `qwen2.5:7b`, `llama3.2`, `nomic-embed-text`
- Admin account created (`ENABLE_SIGNUP=false` in `.env`)
- `.env`: `WEBUI_NAME=Brainiac 7`, `AI_OPS_HOST_NAME=brainiac-7`

---

## 1. Connect Ollama

Open WebUI auto-detects `OLLAMA_BASE_URL=http://host.docker.internal:11434` via `docker-compose.yml`.

**Verify:** Settings → Connections → Ollama → Test — models listed.

---

## 2. Set default models

| Use case | Model |
|----------|-------|
| Oracle / Counsel (reasoning) | `qwen2.5:7b` |
| Operator (fast check-ins) | `llama3.2` |
| Embeddings / RAG | `nomic-embed-text` |

**Admin → Settings → Models:** pin defaults for chat and embeddings.

---

## 3. Import executives as Prompts

Import **three** executives only — not the legacy 12-agent pack.

For each file in `agents/oracle.md`, `operator.md`, `counsel.md`:

1. **Workspace** → **Prompts** → **Create**
2. Title: e.g. `Oracle — Strategist (Brainiac 7)`
3. Content: copy everything under `## System Prompt` (include **Aboard Brainiac 7** preamble if desired)
4. Command: `/oracle`, `/operator`, `/counsel`

### Option B — Custom model presets

1. **Workspace** → **Models** → **Add Model**
2. Base: per executive (see `agents/README.md`)
3. System prompt: paste from `agents/<executive>.md`
4. Name: `Oracle`, `Operator`, `Counsel`

### Option C — JSON bundle

Use `setup/open-webui-prompts.json` — includes `brainiac_7` branding and opening line.

---

## 4. Knowledge (RAG)

1. Copy SOPs to NAS `knowledge/` and `hot/knowledge/`
2. Mirror to `C:\AI-OPS-STARTER\data\knowledge\` (optional)
3. Open WebUI → **Workspace** → **Documents** → Upload / sync
4. Embedding model: `nomic-embed-text`
5. Collection name: `company-knowledge`

**Counsel** and **Oracle** benefit most from SOP/policy docs; **Operator** from task templates.

**Qdrant:** compose runs Qdrant at `127.0.0.1:6333` for advanced pipelines; Open WebUI may use internal store — both are localhost-only.

---

## 5. Multi-executive workflow

1. User picks executive (or uses `/oracle`, `/operator`, `/counsel`)
2. Handoffs in chat: "Loop in Operator", etc.
3. n8n automations use Counsel/Operator/Oracle prompts — see `n8n/*.json`

---

## 6. Disable paid providers

Confirm in `.env`:
```
ENABLE_OPENAI_API=false
ENABLE_ANTHROPIC_API=false
ENABLE_GOOGLE_API=false
```

In Open WebUI Admin, disable external API keys.

---

## 7. Access from MacBook (Tailscale)

1. `tailscale status` on Mac
2. Browser: `http://brainiac-7:3000`
3. Login with WebUI admin credentials

Do **not** port-forward 3000 on your router.

---

## Checklist

- [ ] Ollama connected
- [ ] **3 executives** imported (Oracle, Operator, Counsel)
- [ ] `WEBUI_NAME` shows **Brainiac 7** in UI
- [ ] Default models set
- [ ] Knowledge uploaded from NAS
- [ ] Signup disabled
- [ ] Tailscale access tested from Mac

See `docs/brainiac-7.md` for voice and daily rituals.
