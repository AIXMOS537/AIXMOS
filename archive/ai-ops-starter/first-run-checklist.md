# First-Run Checklist

Complete on **Brainiac 7** (Windows AI machine) first, then **MacBook**, then **flash drive** verification.

## Phase 0 — Hardware roles

- [ ] **Brainiac 7** (Windows 11 Pro) = primary intellect node — Ollama + Docker stack
- [ ] Hostname / Tailscale name: `brainiac-7` (see `docs/brainiac-7.md`)
- [ ] MacBook = edit/sync kit, Tailscale admin access
- [ ] UGREEN NAS = storage only (SMB share)
- [ ] Flash drive = portable copy of `AI-OPS-STARTER`

## Phase 1 — Brainiac 7 (Day 1)

- [ ] Copy `AI-OPS-STARTER` to `C:\AI-OPS-STARTER` (from flash or git)
- [ ] Set `.env`: `AI_OPS_HOST_NAME=brainiac-7`, `WEBUI_NAME=Brainiac 7`, `TAILSCALE_WINDOWS_HOST=brainiac-7`
- [ ] Install Docker Desktop (WSL2 backend enabled)
- [ ] Install Ollama for Windows
- [ ] Install Tailscale; sign in; note Windows machine name/IP
- [ ] Run **WINDOWS FIRST COMMAND** (see README) or `.\install-windows.ps1`
- [ ] Copy `.env.example` → `.env`; set strong passwords
- [ ] Confirm models: `ollama list` shows `qwen2.5:7b`, `llama3.2`, `nomic-embed-text`
- [ ] `docker compose ps` — all services healthy
- [ ] Open http://127.0.0.1:3000 — create Open WebUI admin (signup disabled in `.env`)
- [ ] Open http://127.0.0.1:5678 — change n8n default password
- [ ] Import n8n workflows from `n8n/*.json`
- [ ] Import three executives per `docs/open-webui-import.md`
- [ ] Read `docs/brainiac-7.md` — voice + daily rituals

## Phase 2 — NAS (60TB storage)

- [ ] Create NAS share `AI-OPS` (see `docs/nas-mount-guide.md`, `docs/nas-60tb-architecture.md`)
- [ ] Map Windows drive `W:` → `\\UGREEN-NAS\AI-OPS`
- [ ] `.\scripts\init-nas-layout.ps1`
- [ ] Edit `setup/operators/registry.yaml` (replace `EDIT_*` names)
- [ ] `.\scripts\sync-registry-nas.ps1`
- [ ] Point backups to `W:\backups\`

## Phase 2b — Deploy other operators (tier 6 → 1)

- [ ] Follow `docs/deploy-operators-checklist.md`
- [ ] Flash kit to each site; run `provision-brainiac-node.ps1` per tier
- [ ] Add `prompts/tier-preamble.md` to each executive in Open WebUI

## Phase 3 — MacBook (admin)

- [ ] Install Tailscale; verify you can ping Windows AI IP
- [ ] Run **MAC FIRST COMMAND** (see README) or `./install-mac.sh`
- [ ] Access Open WebUI via `http://<windows-tailscale-ip>:3000`
- [ ] Edit agents/workflows locally; rsync to flash

## Phase 4 — Flash drive

- [ ] Label volume `AI-OPS` (optional, helps Mac script)
- [ ] Copy entire kit (exclude `.env`)
- [ ] Run `scripts/verify-flash-drive.sh` on Mac
- [ ] Boot Windows from flash copy instructions in `docs/flash-drive-guide.md`

## Phase 5 — Security hardening

- [ ] Complete `security-checklist.md`
- [ ] Confirm no ports bound to `0.0.0.0` (`docker compose ps`)
- [ ] Windows Firewall: block inbound except Tailscale interface
- [ ] Rotate all `changeme` passwords in `.env`

## Phase 6 — Operations

- [ ] Test each executive (Oracle, Operator, Counsel) with one sample question
- [ ] Test n8n: team question → SOP workflow
- [ ] Schedule backup per `backup-checklist.md`
- [ ] Read `troubleshooting.md` — bookmark common fixes

## Sign-off

| Step | Owner | Date |
|------|-------|------|
| Brainiac 7 stack live | | |
| NAS mounted | | |
| Mac remote access | | |
| Flash verified | | |
| Security checklist | | |
