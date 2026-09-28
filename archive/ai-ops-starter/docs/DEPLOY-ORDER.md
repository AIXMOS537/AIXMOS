# Deploy Order — Canonical (copy/paste)

**Ryn = Claryn Troup (Mystique)** — not a separate person.  
**Kayleigh** — Phase 5 only when she starts working for you.

---

## Summary table

| Phase | Who | Node |
|-------|-----|------|
| **1** | **Muhammad Taha** | `brainiac-7` |
| **2** | Dominique Bibbs | `brainiac-4-hq-dominique` |
| **3** | Mr Michael | `brainiac-4-hq-michael` |
| **3** | Mr Dyson | `brainiac-3-hq-dyson` |
| **4** | Nathan West | `brainiac-3-hq-nathan` |
| **4** | Claryn Troup (**Ryn / Mystique**) | `brainiac-4-hq-claryn` |
| **5** | Kayleigh Bristow | `brainiac-5-hq-kayleigh` — **PENDING** |
| **Heroes** | Tahir Muhammad (**Superman**) | `brainiac-5-hq-tahir` |
| **Heroes** | Tayyeba Tahir (**Superwoman**) | `brainiac-5-hq-tayyeba` |

There is **no** separate “Later: Claryn” step — she is **Phase 4** with Nathan.

---

## Phase 1 — You (Brainiac 7, first command)

On your **home Windows AI PC** only:

```powershell
cd C:\AI-OPS-STARTER
.\scripts\phase1-windows-bootstrap.ps1
.\scripts\init-nas-layout.ps1
.\scripts\sync-registry-nas.ps1
```

Open http://127.0.0.1:3000 — *"Brainiac 7 online — Oracle, Operator, or Counsel?"*

---

## Phase 2 — Dominique

On **Dominique’s PC** (after `robocopy` kit from flash):

```powershell
cd C:\AI-OPS-STARTER
.\scripts\provision-brainiac-node.ps1 -Tier 4 -Location hq -Operator dominique -DisplayName "Brainiac 4 — Dominique Bibbs"
.\install-windows.ps1
```

---

## Phase 3 — Michael + Dyson

**Michael:**

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 4 -Location hq -Operator michael -DisplayName "Brainiac 4 — Mr Michael"
.\install-windows.ps1
```

**Dyson:**

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 3 -Location hq -Operator dyson -DisplayName "Brainiac 3 — Mr Dyson"
.\install-windows.ps1
```

---

## Phase 4 — Nathan + Claryn (Ryn / Mystique)

**Nathan:**

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 3 -Location hq -Operator nathan -DisplayName "Brainiac 3 — Nathan West"
.\install-windows.ps1
```

**Claryn** (Ryn = same person — Counsel / Mystique lane):

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 4 -Location hq -Operator claryn -DisplayName "Brainiac 4 — Claryn Troup (Mystique / Ryn)"
.\install-windows.ps1
```

Open WebUI → primary executive: **Counsel**.

---

## Phase 5 — Kayleigh (when hired)

**Do not run until she works for you.**

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 5 -Location hq -Operator kayleigh -DisplayName "Brainiac 5 — Kayleigh Bristow"
.\install-windows.ps1
```

---

## Heroes — Superman & Superwoman

After Phase 4 is stable:

**Father — Superman (Oracle lane):**

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 5 -Location hq -Operator tahir -DisplayName "Brainiac 5 — Tahir Muhammad (Superman)"
.\install-windows.ps1
```

**Sister — Superwoman (Operator lane):**

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 5 -Location hq -Operator tayyeba -DisplayName "Brainiac 5 — Tayyeba Tahir (Superwoman)"
.\install-windows.ps1
```

---

## Phase Mobile — Phone voice & message drafts (after Phase 1)

On **Brainiac 7** after stack is up:

```powershell
docker compose --profile voice up -d
# Import n8n: voice-memo-to-task.json, inbound-message-draft-response.json
# Set MOBILE_WEBHOOK_SECRET in .env
```

iPhone: **`setup\phone\IPHONE-SETUP.md`** (Tailscale + Siri Shortcuts)  
Guides: `docs\mobile-voice-command-center.md`, `docs\auto-response-playbook.md`

**Default:** speak → tasks **pending your approve** → then NAS + team.  
Messages → **Counsel draft** → you send (train via NAS contact files).

---

## Every node — Open WebUI

Paste `prompts/tier-preamble.md` (set **N** = tier from `.env`) + body from `agents/oracle.md`, `operator.md`, or `counsel.md`.

---

## Source of truth

- Registry: `setup/operators/registry.yaml`
- Roster: `docs/team-roster.md`
