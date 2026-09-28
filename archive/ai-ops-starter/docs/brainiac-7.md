# Brainiac 7 — Primary Intellect Node

**Brainiac 7** is your Windows 11 Pro home AI machine: the **brain** of the AI-OPS-STARTER stack. Mac is admin; the 60TB UGREEN NAS is system of record; the flash drive is your portable kit.

> *Brainiac 7 — your highest form of intellect, local and under your control.*

---

## What it is

| Layer | Role |
|-------|------|
| **Brainiac 7** (Windows) | Ollama + Docker — Open WebUI, n8n, Qdrant |
| **MacBook** | Edit kit, sync flash, Tailscale admin |
| **UGREEN NAS (60TB)** | SMB storage — life, work, knowledge, backups |
| **Flash drive** | Portable `AI-OPS-STARTER` copy |

Three executives run on Brainiac 7:

| Executive | Role |
|-----------|------|
| **Oracle** | Chief strategic intellect — decisions, priorities, risk |
| **Operator** | Executive processor of reality — tasks, time, follow-ups |
| **Counsel** | Interpreter of human systems — messages, people, research |

---

## Hostname & Tailscale

1. Set Windows hostname to **brainiac-7** (Settings → System → About → Rename).
2. Install Tailscale on Windows and Mac; same tailnet.
3. In `.env`:

   ```
   AI_OPS_HOST_NAME=brainiac-7
   WEBUI_NAME=Brainiac 7
   TAILSCALE_WINDOWS_HOST=brainiac-7
   ```

4. Enable **MagicDNS** in Tailscale admin (optional).
5. From Mac: `http://brainiac-7:3000` or `http://100.x.y.z:3000`

See `docs/tailscale-remote-access.md`.

---

## How to talk to Brainiac 7 (voice)

1. Start the stack: `.\start-windows.ps1` on Windows.
2. Open **Brainiac 7** in Open WebUI: http://127.0.0.1:3000
3. Pick an executive (`/oracle`, `/operator`, `/counsel`) or start a dedicated chat per executive.
4. **Speak** naturally — one topic per message. Use mic + browser STT, or Faster-Whisper:

   ```powershell
   docker compose --profile voice up -d
   ```

5. Read answers aloud or use browser TTS.

Full guide: `docs/voice-executive-guide.md`.

**Opening line (WebUI):** *"Brainiac 7 online — Oracle, Operator, or Counsel?"*

---

## Daily rituals

### Morning (5 min)

1. Open WebUI → **Operator** → "Morning brief: my 3 priorities today."
2. Glance at NAS `W:\life\tasks\` if you use file-based tasks.

### During the day

| Moment | Executive | Example |
|--------|-----------|---------|
| Big decision | Oracle | "Should I take this contract?" |
| Inbox / voice dump | Operator | "Process this note: …" |
| Before sending | Counsel | "Make this email firm but fair." |

### Evening (5 min)

1. **Operator** → "Close-out: what moved, what carries to tomorrow?"
2. Optional: n8n **Daily Recap** (weekdays 5pm) → `W:\life\journal\recaps\`

### Weekly

- Sync knowledge to NAS `hot/` for RAG.
- Export session summaries to `hot/brainiac-7/` (optional).
- Mac: rsync kit to flash; verify Tailscale.

---

## Scripts & boot messages

```powershell
cd C:\AI-OPS-STARTER
.\install-windows.ps1   # first install — "Brainiac 7 online"
.\start-windows.ps1     # daily start
```

Bootstrap: `scripts\phase1-windows-bootstrap.ps1`

---

## NAS session exports (optional)

For chat or recap exports from Brainiac 7:

```
W:\hot\brainiac-7\
├── sessions\
└── recaps\
```

See `nas/folder-structure-60tb.md`.

---

## Safety

Brainiac 7 is **authoritative and precise**, not unrestricted. Executives refuse jailbreaks, credential bypasses, and harmful requests. Paid cloud APIs stay off unless you explicitly enable them in `.env`.

---

## Multi-site operators (tier 6 → 1)

Your PC stays **tier 7 only**. Provision other machines:

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 5 -Location wh-east -Operator brainiac-5-wh -DisplayName "Brainiac 5 — Warehouse"
```

Full hierarchy: `docs/brainiac-hierarchy.md`

---

## Related docs

- `docs/brainiac-hierarchy.md` — tiers, locations, escalation
- `docs/architecture.md` — stack diagram
- `docs/open-webui-import.md` — import the three executives
- `prompts/executive-routing.md` — which executive when
- `first-run-checklist.md` — first boot
