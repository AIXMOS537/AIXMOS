# UGREEN NAS Mount Guide

NAS is **storage only** — no Docker/agents on the NAS.

## Recommended share layout

Create SMB share: `AI-OPS` on UGREEN NAS.

```
AI-OPS/
├── knowledge/          # RAG source markdown/PDF
├── sops/               # Standard operating procedures
├── clients/            # Client-specific (access controlled)
├── meetings/           # Transcripts (PII — restrict)
├── backups/            # Docker/volume exports from Windows
│   └── ai-ops/
├── incidents/          # Postmortems (human + Oracle review)
└── exports/            # n8n/Open WebUI exports
```

See `nas/folder-structure.md` for full tree.

---

## Windows 11 — Brainiac 7

### Map network drive `Z:`

1. Open **File Explorer** → **This PC** → **Map network drive**
2. Drive: `Z:`
3. Folder: `\\UGREEN-NAS\AI-OPS` (replace hostname with NAS IP or mDNS name)
4. ☑ Reconnect at sign-in
5. Use dedicated service account (not personal admin) with read/write to `AI-OPS` only

**PowerShell:**
```powershell
$nas = "\\192.168.1.50\AI-OPS"   # your NAS IP
net use Z: $nas /persistent:yes
dir Z:\
```

Set in `.env`:
```
NAS_MOUNT_PATH=Z:\
NAS_AI_OPS_PATH=\\UGREEN-NAS\AI-OPS
```

### Sync knowledge to RAG (manual / scheduled)

```powershell
robocopy Z:\knowledge C:\AI-OPS-STARTER\data\knowledge /MIR
# Then ingest via Open WebUI Documents UI
```

---

## MacBook (admin)

### Finder

1. **Go** → **Connect to Server** (`Cmd+K`)
2. `smb://UGREEN-NAS/AI-OPS` or `smb://192.168.1.50/AI-OPS`
3. Add to Login Items if needed

### Terminal

```bash
mkdir -p ~/NAS/AI-OPS
mount_smbfs //user@UGREEN-NAS/AI-OPS ~/NAS/AI-OPS
ls ~/NAS/AI-OPS
```

**Note:** Mac mounts NAS for editing files. **Do not** run the Docker brain stack on Mac for production unless testing.

---

## Tailscale access to NAS (optional)

If NAS is on LAN only, Mac/remote Windows reach files via:

- VPN to home network, or
- Tailscale subnet router on LAN (advanced — document in your network SOP)

Default kit assumes NAS is **LAN SMB**; Windows brain mounts `Z:` locally.

---

## Permissions

| Principal | knowledge/ | sops/ | clients/ | backups/ |
|-----------|------------|-------|----------|----------|
| ai-ops-svc (Windows) | RW | R | — | RW |
| admin (Mac) | RW | RW | RW | R |
| team | R | R | — | — |

---

## Verify

**Windows:**
```powershell
Test-Path Z:\knowledge
echo test > Z:\exports\mount-test.txt
```

**Mac:**
```bash
touch ~/NAS/AI-OPS/exports/mount-test-mac.txt
```
