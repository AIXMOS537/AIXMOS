# Brainiac Hierarchy (7 → 1)

**Brainiac 7** is yours — the **supreme intellect node**. Every other location and operator runs at a **lower tier** (6 down to 1). Lower tiers serve upstream; **Brainiac 7** is the final AI authority before human escalation (you).

```
                    ┌─────────────────┐
                    │   YOU (human)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   BRAINIAC 7    │  ← your PC — supreme
                    │  (home / owner) │
                    └────────┬────────┘
                             │ escalate strategy / sync knowledge
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Brainiac │  │ Brainiac │  │ Brainiac │
        │    6     │  │    5     │  │   4…1    │
        │ office   │  │ branch   │  │ operators│
        └──────────┘  └──────────┘  └──────────┘
```

---

## Tier definitions

| Tier | Role | Typical hardware | Stack | Default model | Escalates to |
|------|------|------------------|-------|---------------|--------------|
| **7** | Supreme intellect (owner) | Your Windows AI PC | Full Docker + Ollama | `qwen2.5:7b` | Human (Taha) |
| **6** | Regional / second HQ brain | Windows workstation | Full stack | `qwen2.5:7b` | **7** |
| **5** | Site brain (branch office) | Windows mini PC | Full stack | `qwen2.5:7b` | **6**, **7** |
| **4** | Lead operator station | Windows laptop | Docker + Ollama | `llama3.2` | **5–7** |
| **3** | Field operator | Laptop | Ollama + WebUI only | `llama3.2` | **4–7** |
| **2** | Thin client | Tablet / low-power | Tailscale → upstream WebUI | (remote) | **4–7** |
| **1** | Pocket / ad-hoc | Phone / flash | Prompts + Tailscale to **7** | (remote) | **7** |

**Rule:** A node may not override a higher tier. Knowledge and hard decisions flow **up**; policies and SOPs flow **down** from **7**.

---

## Locations & operators

Each physical site gets a **location code**. Each person/machine gets an **operator id**.

Example registry (`setup/operators/registry.yaml`):

| Location | Code | Operators | Typical tier |
|----------|------|-----------|--------------|
| Owner home | `home` | you → `brainiac-7` | 7 |
| Main office | `hq` | `brainiac-6`, ops laptops | 6, 4 |
| Warehouse | `wh-east` | `brainiac-5` | 5 |
| Client site | `field` | tablets `brainiac-2` | 2 |

NAS paths:

```
W:\locations\<location-code>\operators\<operator-id>\
```

---

## Provision a new node

**Windows (operator PC):**

```powershell
cd C:\AI-OPS-STARTER
.\scripts\provision-brainiac-node.ps1 -Tier 5 -Location wh-east -Operator brainiac-5-wh -DisplayName "Brainiac 5 — Warehouse"
.\install-windows.ps1
```

**Mac (admin prep for flash):**

```bash
./scripts/provision-brainiac-node.sh 4 hq ops-jane "Brainiac 4 — HQ Jane"
```

This writes `.env` from `setup/tiers/brainiac-N.env.example` and sets upstream to **brainiac-7**.

---

## Tailscale naming

| Tier | Hostname pattern | Example |
|------|------------------|---------|
| 7 | `brainiac-7` | `brainiac-7` |
| 6 | `brainiac-6-<loc>` | `brainiac-6-hq` |
| 5 | `brainiac-5-<loc>` | `brainiac-5-wh-east` |
| 4–1 | `brainiac-<n>-<operator>` | `brainiac-4-jane` |

All nodes join the **same tailnet**. ACLs: lower tiers can reach their upstream; only **7** and admin Mac reach all.

---

## What each tier does with the 3 executives

Same three executives everywhere — **Oracle**, **Operator**, **Counsel** — but authority scales:

| Tier | Oracle | Operator | Counsel |
|------|--------|----------|---------|
| **7** | Final AI strategy | Master task system | Final comms polish |
| **6–5** | Site strategy; escalate big bets to **7** | Site tasks; sync to NAS | Site comms |
| **4–3** | Day decisions; escalate non-routine to **7** | Personal queue | Drafts for review |
| **2–1** | Read-only / relay questions to **7** | Capture notes → sync up | Draft locally; send from **7** if critical |

**Escalation phrase in chat:** *"Escalate to Brainiac 7"* — Operator logs to `W:\locations\<loc>\escalations\`.

---

## Knowledge sync (60TB NAS)

| Direction | What |
|-----------|------|
| **7 → down** | SOPs, policies, approved templates (`knowledge/`) |
| **Up → 7** | Site decisions, escalations, daily recaps (`locations/*/exports/`) |
| **Hot folder** | Each node: `hot/brainiac-<n>/` — RAG ingest on **7** only |

**7** runs RAG on curated `hot/` — do not ingest entire NAS.

---

## WebUI display names

| Tier | `WEBUI_NAME` example |
|------|---------------------|
| 7 | `Brainiac 7` |
| 6 | `Brainiac 6 — HQ` |
| 5 | `Brainiac 5 — Warehouse` |
| 4 | `Brainiac 4 — Jane` |

Opening line (tier 7): *"Brainiac 7 online — Oracle, Operator, or Counsel?"*

Lower tiers: *"Brainiac \<n\> online — connected to Brainiac 7."*

---

## Quick reference

- Tier templates: `setup/tiers/brainiac-*.env.example`
- Operator registry: `setup/operators/registry.template.yaml`
- NAS layout: `nas/locations/README.md`
- Supreme node doc: `docs/brainiac-7.md`
