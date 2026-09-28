# Deploy Operators Checklist

Do these in order on **Brainiac 7** first, then repeat per location/operator.

---

## Step 1 — Registry (already filled)

Team is in `setup/operators/registry.yaml`. Deploy phases: **`docs/DEPLOY-ORDER.md`**.

**Rule:** Only **one** tier-7 node — your home PC `brainiac-7`. **Ryn = Claryn Troup (Mystique)** — Phase 4, not a separate person.

---

## Step 2 — NAS on Brainiac 7

1. Map NAS: `net use W: \\UGREEN-NAS\AI-OPS /persistent:yes` (or your IP)
2. Run full layout:

   ```powershell
   cd C:\AI-OPS-STARTER
   .\scripts\init-nas-layout.ps1
   ```

3. Sync folders from registry:

   ```powershell
   .\scripts\sync-registry-nas.ps1
   ```

4. Verify: `dir W:\locations`

---

## Step 3 — Hand off flash + provision each operator

### A. Refresh flash (Mac or Windows) — primary channel

```bash
# Mac (one command)
cd ~/AI-OPS-STARTER && ./scripts/publish-release.sh
```

```powershell
# Windows
.\scripts\publish-release.ps1 -FlashDrive E:
```

See **`docs/TEAM-SELF-INSTALL.md`** for NAS / GitLab / Google Drive.

### B. On each operator Windows PC

1. `robocopy E:\AI-OPS-STARTER C:\AI-OPS-STARTER /E /XD data /XF .env`
2. Run **their** installer (generated from registry):

   ```powershell
   cd C:\AI-OPS-STARTER
   .\scripts\installers\install-dominique.ps1
   # or: -InstallPrerequisites for winget Docker/Ollama/Tailscale
   ```

   Guides: `docs\install-guides\INSTALL-*.md`

   Manual provision (legacy): `docs\DEPLOY-ORDER.md` + `.\install-windows.ps1`

3. Rename PC hostname to match `hostname` in registry (Settings → Rename)
4. Join Tailscale; confirm they can reach `http://brainiac-7:3000` if tier ≤ 2

### C. Thin clients (tier 2–1)

No local Ollama required. Open browser → `http://brainiac-7:3000` via Tailscale.

---

## Step 4 — Open WebUI prompts (every tier)

On **each** node (including 7), for **Oracle**, **Operator**, **Counsel**:

1. Open WebUI → Workspace → Prompts (or per-chat system prompt)
2. Paste **`prompts/tier-preamble.md`** at the top
3. Replace `N` with that machine’s `BRAINIAC_TIER` from `.env`
4. Paste the rest from `agents/oracle.md` (or operator / counsel)

**Brainiac 7 opening line:** *"Brainiac 7 online — Oracle, Operator, or Counsel?"*

**Lower tiers:** *"Brainiac \<n\> online — escalations go to Brainiac 7."*

---

## Step 5 — Verify escalation path

1. On a tier-4 machine, ask Operator: *"Escalate test to Brainiac 7"*
2. Confirm file appears: `W:\locations\<code>\escalations\`
3. On **Brainiac 7**, review in Open WebUI or NAS

---

## Ongoing

| Task | When | Where |
|------|------|-------|
| Review escalations | Daily | Brainiac 7 + `W:\locations\*\escalations\` |
| Push SOPs downstream | Weekly | `W:\knowledge\` |
| Pull site recaps upstream | Daily | `W:\locations\*\exports\` |
| Update registry | When hiring/new site | `registry.yaml` → re-run `sync-registry-nas.ps1` |

---

## Need a custom registry?

Edit `registry.yaml` or ask for help filling locations — provide:

- Site names (home, office, warehouse, …)
- Who runs each machine
- Desired tier per person (4 = desk, 5 = site brain, 2 = tablet, …)
