# MacBook Setup — M1 Pro (Admin & Control)

Your **MacBook M1 Pro Max (32GB)** is the **control plane** — not the supreme brain.

| Machine | Role |
|---------|------|
| **Brainiac 7** (Windows PC) | Supreme intellect — Ollama + Docker + n8n |
| **This MacBook** | Edit kit, sync flash, Tailscale admin, remote WebUI, NAS edit |
| **iPhone** | Voice shortcuts → Brainiac 7 (see `setup/phone/IPHONE-SETUP.md`) |
| **60TB NAS** | Storage — mount from Mac for files |

With **32GB RAM** you *can* run a **test stack** on Mac (optional). Production stays on **Brainiac 7**.

---

## Part 1 — Install tools (15 min)

Open **Terminal**:

```bash
# Xcode CLI (if needed)
xcode-select --install

# Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Essentials
brew install git rsync tailscale

# Optional: Docker Desktop for Mac (test stack only)
# brew install --cask docker
```

**Tailscale:** Open from Applications → sign in → **same tailnet as Brainiac 7**.

---

## Part 2 — Copy the kit to your Mac

If the project is on USB:

```bash
export FLASH=/Volumes/AI-OPS   # your USB name
mkdir -p ~/AI-OPS-STARTER
rsync -av "$FLASH/AI-OPS-STARTER/" ~/AI-OPS-STARTER/
```

If copying from another folder:

```bash
rsync -av /path/to/AI-OPS-STARTER/ ~/AI-OPS-STARTER/
```

Run Mac installer:

```bash
cd ~/AI-OPS-STARTER
chmod +x *.sh scripts/*.sh
./install-mac.sh
```

With flash plugged in:

```bash
FLASH_DRIVE=/Volumes/AI-OPS ./install-mac.sh
```

---

## Part 3 — Tailscale (remote Brainiac 7)

1. Tailscale menu bar → **Connected**
2. Note **brainiac-7** in device list (green = online)
3. Test in Safari:

| Service | URL |
|---------|-----|
| Open WebUI | http://brainiac-7:3000 |
| n8n | http://brainiac-7:5678 |
| Ollama API | http://brainiac-7:11434 |

If MagicDNS fails, use the `100.x.x.x` IP from Tailscale → `http://100.x.x.x:3000`

**Bookmark:** “Brainiac 7” in Safari dock.

---

## Part 4 — Flash drive (portable kit)

Label USB **AI-OPS** (optional). Full kit + git history:

```bash
FLASH_DRIVE=/Volumes/AI-OPS ~/AI-OPS-STARTER/scripts/sync-to-flash.sh
```

Verify:

```bash
~/AI-OPS-STARTER/scripts/verify-flash-drive.sh /Volumes/AI-OPS/AI-OPS-STARTER
```

Open on stick: **START-HERE-FLASH.md**

Refresh after edits:

```bash
FLASH_DRIVE=/Volumes/AI-OPS ~/AI-OPS-STARTER/start-mac.sh
```

---

## Part 5 — Mount NAS (60TB UGREEN)

Finder → **Go** → **Connect to Server** (`Cmd+K`):

```
smb://UGREEN-NAS/AI-OPS
```

or

```
smb://192.168.x.x/AI-OPS
```

Terminal:

```bash
mkdir -p ~/NAS/AI-OPS
mount_smbfs //YOUR_USER@UGREEN-NAS/AI-OPS ~/NAS/AI-OPS
ls ~/NAS/AI-OPS
```

Edit relationship files for iPhone auto-reply training:

```bash
open ~/NAS/AI-OPS/life/relationships/
# or use template from ~/AI-OPS-STARTER/nas/templates/contact-response-profile.md
```

On **Brainiac 7**, NAS is `W:\` — Mac and PC share the same files.

---

## Part 6 — Daily Mac workflow

| Task | Command / action |
|------|------------------|
| Sync flash | `FLASH_DRIVE=/Volumes/AI-OPS ~/AI-OPS-STARTER/start-mac.sh` |
| Remote chat | Safari → http://brainiac-7:3000 |
| Edit deploy docs | `code ~/AI-OPS-STARTER/docs/DEPLOY-ORDER.md` |
| Team registry | `code ~/AI-OPS-STARTER/setup/operators/registry.yaml` |
| Commit + USB history | `cd ~/AI-OPS-STARTER && git add -A && git commit -m "update" && ./scripts/sync-to-flash.sh` |
| Check team roster | `open ~/AI-OPS-STARTER/docs/team-roster.md` |

You do **not** need Ollama on Mac for daily use — use Brainiac 7 over Tailscale.

---

## Part 7 — iPhone (from Mac admin)

Finish on phone: **`setup/phone/IPHONE-SETUP.md`**

Mac helps by:
- Editing `MOBILE_WEBHOOK_SECRET` in `.env` on Windows (not on flash)
- Creating contact files on NAS for Counsel
- Testing webhooks with curl from Mac:

```bash
curl -X POST "http://brainiac-7:5678/webhook/voice-memo" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_SECRET" \
  -d '{"transcript":"Test from Mac","verify_mode":"approve","source":"mac"}'
```

---

## Part 8 — OPTIONAL: Local test stack (M1, 32GB)

Only for testing when Windows PC is off. **Not** for production.

```bash
brew install ollama
brew install --cask docker
```

```bash
cd ~/AI-OPS-STARTER
cp .env.example .env
# Edit .env: WEBUI_NAME=Brainiac Mac Test, BRAINIAC_TIER=7 only if you understand this is not production
ollama pull llama3.2
ollama pull nomic-embed-text
docker compose --profile voice up -d
open http://127.0.0.1:3000
```

**Recommended models on M1 32GB:** `llama3.2`, `qwen2.5:7b` (slower but works), `nomic-embed-text`.

Stop test stack:

```bash
docker compose down
```

---

## Part 9 — Generate operator `.env` for flash handoff

Create env file for Dominique’s PC without putting secrets on USB:

```bash
cd ~/AI-OPS-STARTER
./scripts/provision-brainiac-node.sh 4 hq dominique "Brainiac 4 — Dominique Bibbs"
# Output: setup/operators/generated/brainiac-4-hq-dominique.env
# AirDrop or secure message the .env — NOT the flash stick
```

---

## Part 10 — Checklist

- [ ] Tailscale connected; `brainiac-7:3000` loads in Safari
- [ ] `~/AI-OPS-STARTER` installed; `install-mac.sh` OK
- [ ] Flash sync works; `verify-flash-drive.sh` passes
- [ ] NAS mounted at `~/NAS/AI-OPS` (when on home LAN)
- [ ] `registry.yaml` has your team names
- [ ] iPhone guide started (`IPHONE-SETUP.md`)
- [ ] Brainiac 7 Phase 1 done on Windows PC

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `brainiac-7` won’t resolve | Tailscale MagicDNS or use 100.x IP |
| Flash not found | `ls /Volumes/` — set `FLASH_DRIVE=/Volumes/YourName` |
| Permission denied scripts | `chmod +x scripts/*.sh` |
| NAS won’t mount | Same LAN as NAS; check SMB user/password |
| Slow WebUI | Normal over Tailscale; use LAN when at home |

---

## Key files on Mac

```
~/AI-OPS-STARTER/
├── setup/mac/MACBOOK-SETUP.md     ← this file
├── docs/DEPLOY-ORDER.md           ← who gets provisioned when
├── setup/operators/registry.yaml
├── scripts/sync-to-flash.sh
└── setup/phone/IPHONE-SETUP.md
```

**Supreme brain stays on Windows.** Mac commands the empire.
