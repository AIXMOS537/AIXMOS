# 60TB UGREEN NAS — Architecture

Your **60TB UGREEN NAS** is the **system of record**. **Brainiac 7** (Windows) **thinks**; the NAS **remembers**. MacBook **edits and syncs**. Flash drive **bootstraps**.

```
┌──────────────┐     Tailscale      ┌─────────────────────┐
│   MacBook    │◄──────────────────►│ Brainiac 7          │
│ edit / voice │                    │ Windows AI brain    │
└──────┬───────┘                    └──────────┬──────────┘
       │ SMB (LAN)                             │ SMB (LAN)
       └──────────────────┬────────────────────┘
                          ▼
              ┌───────────────────────┐
              │  UGREEN NAS ~60TB     │
              │  RAID (your choice)   │
              │  snapshots / backup   │
              └───────────────────────┘
```

**Do not run** Docker, Ollama, or agents on the NAS. Storage and backups only.

---

## Capacity planning (~60TB)

| Tier | Share / folder | Target size | What goes here |
|------|----------------|-------------|----------------|
| **Hot** | `AI-OPS/hot/` | 500 GB–2 TB | Active projects, this month's knowledge ingest, recent voice notes |
| **Warm** | `AI-OPS/life/`, `AI-OPS/work/` | 2–10 TB | Daily life, clients, meetings, decisions log |
| **Cold** | `AI-OPS/archive/` | 10–40+ TB | Old projects, media, yearly exports, immutable backups |
| **Vault** | `AI-OPS/vault/` | as needed | Encrypted backups, sensitive exports (restricted ACL) |
| **Models cache** (optional) | `AI-OPS/models/ollama/` | 50–200 GB | Backup of `ollama pull` blobs — optional, re-pull is OK |

Leave **15–20% free** on the pool for RAID rebuilds and snapshots.

---

## Recommended UGREEN setup

1. **RAID** — RAID5/6 or SHR-equivalent for balance of capacity and redundancy (your risk tolerance).
2. **Snapshots** — weekly on `AI-OPS/life/` and `AI-OPS/work/`; daily on `hot/`.
3. **SMB share** — single share `AI-OPS` (simpler than many shares).
4. **Users**
   - `ai-ops-svc` (Windows) — RW hot, life, work, backups; no vault
   - `admin-mac` (Mac) — RW all except vault optional
   - `backup` — append-only to `archive/backups/` if supported
5. **10GbE or 2.5GbE** — if possible between NAS ↔ Windows AI (faster ingest/RAG sync).
6. **UPS** — NAS + Windows AI on battery backup.

---

## Folder tree (60TB-aware)

See `nas/folder-structure-60tb.md` for the full tree.

High level:

```
AI-OPS/
├── hot/              # fast access, RAG sync source
├── life/             # personal executive data
├── work/             # business executive data
├── knowledge/        # SOPs, reference (Counsel + Oracle)
├── archive/          # cold storage
├── vault/            # sensitive
├── backups/          # docker/volume exports from Windows
└── models/           # optional ollama backup
```

---

## Windows mount

```powershell
# Replace IP/hostname
net use W: \\UGREEN-NAS\AI-OPS /persistent:yes
```

`.env`:
```
NAS_MOUNT_PATH=W:\
NAS_AI_OPS_PATH=\\UGREEN-NAS\AI-OPS
NAS_CAPACITY_TB=60
```

Run once:
```powershell
.\scripts\init-nas-layout.ps1
```

---

## Mac mount

```bash
mkdir -p ~/NAS/AI-OPS
mount_smbfs //admin@UGREEN-NAS/AI-OPS ~/NAS/AI-OPS
```

---

## RAG / knowledge sync

1. Authoritative docs live on NAS `hot/knowledge/` and `knowledge/`.
2. Windows mirrors to `C:\AI-OPS-STARTER\data\ingest\` via `scripts/sync-nas-knowledge.ps1`.
3. Open WebUI **Documents** ingests from ingest folder (not the whole 60TB).
4. **Never** point Qdrant/WebUI at the entire NAS — curate `hot/` only.

---

## Backup strategy

| Source | Destination | Tool |
|--------|-------------|------|
| Docker volumes | `W:\backups\ai-ops\YYYY-MM-DD\` | `scripts/backup-windows.ps1` |
| Mac kit edits | `archive/kit-versions/` | git + rsync |
| NAS → offsite | External drive or cloud **vault** only | UGREEN Hyper Backup / manual |

---

## What NOT to store on NAS

- Running databases as primary (Postgres/Qdrant live in Docker volumes; **backup** copies go to NAS)
- `.env` secrets (password manager + vault only)
- Unbounded chat logs — export summaries to `life/journal/` instead

---

## Executive ↔ NAS mapping

| Executive | Primary NAS areas |
|-----------|-------------------|
| Oracle | `life/decisions/`, `work/strategy/` |
| Operator | `life/tasks/`, `life/inbox/`, `work/tasks/` |
| Counsel | `life/comms/`, `life/relationships/`, `work/clients/` |
