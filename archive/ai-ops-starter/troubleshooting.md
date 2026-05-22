# Troubleshooting

## Ollama

**Symptom:** Open WebUI cannot reach models  
**Fix:**
```powershell
ollama serve
ollama list
curl http://127.0.0.1:11434/api/tags
```
Ensure Docker uses `host.docker.internal` (compose includes `extra_hosts`).

**Symptom:** Model pull fails  
**Fix:** Check disk space; retry `ollama pull qwen2.5:7b`

## Docker

**Symptom:** Port already in use  
**Fix:** Change port in `.env` (e.g. `OPEN_WEBUI_PORT=3001`), `docker compose up -d`

**Symptom:** n8n won't start  
**Fix:** `docker compose logs postgres n8n`; wait for Postgres healthcheck

**Symptom:** Services unreachable from Mac  
**Fix:** Tailscale on both machines; use Windows Tailscale IP; confirm Windows Firewall allows Tailscale interface

## Open WebUI

**Symptom:** Embeddings fail  
**Fix:** `ollama pull nomic-embed-text`; set `RAG_EMBEDDING_MODEL=nomic-embed-text`

**Symptom:** Signup still visible  
**Fix:** Set `ENABLE_SIGNUP=false` in `.env`; recreate container

## n8n

**Symptom:** Webhook 404  
**Fix:** `WEBHOOK_URL` must match how you access n8n (localhost vs Tailscale IP)

**Symptom:** Cannot reach Ollama from n8n  
**Fix:** On Windows use `http://host.docker.internal:11434` in HTTP Request node

## NAS

**Symptom:** `Z:` not mapped  
**Fix:** See `docs/nas-mount-guide.md`; test `dir \\UGREEN-NAS\AI-OPS`

## Tailscale

**Symptom:** MagicDNS fails  
**Fix:** Enable MagicDNS in admin console; `tailscale status`

## Logs

```powershell
docker compose logs -f open-webui
docker compose logs -f n8n
docker compose logs -f qdrant
```

## Reset stack (destructive)

```powershell
docker compose down
# Remove volumes only if you have backups:
# docker compose down -v
```
