# Architecture

## Roles

| Device | Function |
|--------|----------|
| **Brainiac 7** (Windows 11 Pro) | Primary intellect node — Ollama + Docker (Open WebUI, n8n, Qdrant, Postgres) |
| MacBook | Edit kit, sync flash, Tailscale admin UI access |
| UGREEN NAS (60TB) | SMB system of record — life, work, knowledge, backups |
| Flash drive | Portable `AI-OPS-STARTER` copy |

## Data flow

```
User (Mac/Windows browser via Tailscale)
        │
        ▼
Brainiac 7 — Open WebUI :3000 (localhost)
        │
        ├──► Ollama :11434 (host) — qwen2.5:7b, llama3.2, nomic-embed-text
        │
        └──► Qdrant :6333 (RAG vectors)

n8n :5678
        │
        ├──► Ollama (workflows — Oracle / Operator / Counsel prompts)
        └──► Postgres (workflow DB)

NAS W:\
        │
        └──► hot/, life/, work/, knowledge/  (ingested by Open WebUI RAG)
```

## Security boundaries

- Bind services to `127.0.0.1`
- Remote = Tailscale only (`brainiac-7` MagicDNS)
- Paid APIs off in `.env`
- Executives refuse bypass/jailbreak patterns

## Executive orchestration

1. User picks **Oracle**, **Operator**, or **Counsel** in Open WebUI (or n8n workflow)
2. Executive responds; handoffs via "loop in …" in chat
3. Human escalation to **Taha** when SLA exceeded

## Optional components

`docker compose --profile optional up -d`

- Redis
- faster-whisper

See `docs/brainiac-7.md` for daily rituals and hostname setup.
