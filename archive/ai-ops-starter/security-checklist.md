# Security Checklist

Local-first AI ops — safe defaults, no public exposure.

## Network

- [ ] Docker services bind to `127.0.0.1` only (verify `docker-compose.yml`)
- [ ] No router port-forwarding to Open WebUI, n8n, Qdrant, or Ollama
- [ ] Remote access **only** via Tailscale (MagicDNS or stable IPs)
- [ ] Tailscale ACLs restrict who can reach Windows AI ports
- [ ] Windows Firewall: deny public profile inbound for app ports

## Authentication

- [ ] Open WebUI: `WEBUI_AUTH=true`, `ENABLE_SIGNUP=false`
- [ ] n8n: `N8N_BASIC_AUTH_ACTIVE=true` + strong password
- [ ] PostgreSQL/Redis: unique passwords in `.env` (not `changeme`)
- [ ] Separate admin accounts per human; no shared passwords in chat

## Secrets

- [ ] `.env` never committed to git (in `.gitignore`)
- [ ] `.env` never copied to flash drive
- [ ] No API keys in agent prompts, n8n exports, or NAS public folders
- [ ] Paid APIs remain `false` / commented unless consciously enabled

## Data

- [ ] NAS share permissions: least privilege (team write, no guest write)
- [ ] Backups encrypted at rest if leaving premises (BitLocker/USB encryption)
- [ ] Meeting transcripts with PII stored only on NAS with access controls
- [ ] Qdrant/Open WebUI data volumes included in backup plan

## AI safety (operational)

- [ ] Agents refuse jailbreaks, bypass prompts, and unauthorized system changes
- [ ] No instructions in kit to disable Defender, bypass licensing, or exfiltrate creds
- [ ] Human escalation path defined (`ESCALATION_NAME=Taha`)
- [ ] Review executive outputs before client send (Counsel drafts ≠ auto-send)

## Updates

- [ ] Monthly: `docker compose pull` + restart window
- [ ] Monthly: Ollama model updates (`ollama pull` for pinned tags)
- [ ] Quarterly: Tailscale + OS security updates
- [ ] After incidents: document postmortem on NAS + update SOPs in `knowledge/`

## Incident response (quick)

1. Stop stack: `docker compose down`
2. Rotate n8n/WebUI/DB passwords
3. Review Tailscale device list for unknown nodes
4. Restore from last good backup if data tampered
5. Document in `nas/incidents/YYYY-MM-DD.md`
