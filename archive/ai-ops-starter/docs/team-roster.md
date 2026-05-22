# Team Roster & Rollout Order

**Ryn = Claryn Troup (Mystique)** — one person, one node: `brainiac-4-hq-claryn`.

Kayleigh is **pending hire** — Phase 5 only when she starts.

---

## Deploy order

| Phase | Who | Node |
|-------|-----|------|
| **1** | **Muhammad Taha** | `brainiac-7` — first command |
| **2** | Dominique Bibbs | `brainiac-4-hq-dominique` |
| **3** | Mr Michael | `brainiac-4-hq-michael` |
| **3** | Mr Dyson | `brainiac-3-hq-dyson` |
| **4** | Nathan West | `brainiac-3-hq-nathan` |
| **4** | **Claryn Troup (Ryn / Mystique)** | `brainiac-4-hq-claryn` |
| **5** | Kayleigh Bristow | `brainiac-5-hq-kayleigh` — **NOT YET** |
| **Heroes** | Tahir Muhammad (**Superman**) | `brainiac-5-hq-tahir` |
| **Heroes** | Tayyeba Tahir (**Superwoman**) | `brainiac-5-hq-tayyeba` |

---

## Claryn / Ryn / Mystique

| | |
|--|--|
| **Legal name** | Claryn Troup |
| **Nickname** | Ryn |
| **Lane** | Mystique → **Counsel** executive in Open WebUI |
| **Tier** | 4 |
| **Deploy** | Phase 4, same round as Nathan |

---

## Phase 4 — Nathan + Claryn

```powershell
.\scripts\provision-brainiac-node.ps1 -Tier 3 -Location hq -Operator nathan -DisplayName "Brainiac 3 — Nathan West"
.\scripts\provision-brainiac-node.ps1 -Tier 4 -Location hq -Operator claryn -DisplayName "Brainiac 4 — Claryn Troup (Mystique / Ryn)"
```

Claryn’s primary Open WebUI chat: **Counsel** (tone, messages, client voice).

---

## Heroes

| Person | Archetype | Executive |
|--------|-----------|-----------|
| Tahir Muhammad (father) | **Superman** | **Oracle** |
| Tayyeba Tahir (sister) | **Superwoman** | **Operator** |

Full commands: `setup/operators/registry.yaml` → `provisioning`
