# AIXMOS Command Center — Product Brief

**Positioning:** Sold **separately** from TMMT OS. Workforce infrastructure + AI operating brain for everyday operators — not the rental spreadsheet replacement.

**Tagline:** For the people. By the people.  
**Founder:** Muhammad Taha / Project AIXMOS

## What is included

| Component | Location | Status |
|-----------|----------|--------|
| **Business Brain** | `agents/TMMT_Business_Brain.md` | Living doc |
| **Cursor agents** | `agents/*.agent.md` | TMMT, document, video |
| **Five-agent panel** | `tmmt-os` — VISION, TANK, FLY GUY, BOB, STICKS | API + DB (`0004_aixmos_ecosystem.sql`) |
| **Command system** | `AIX_AI_COMMAND_SYSTEM/` | SOPs, prompts, `aix_operator.py` |
| **CHUMMO voice** | `docs/AIXMOS/project_aixmos_chummo.md` | 10 message types |
| **Local ops stack** | `AIXMOSXTMMT-OPS/`, `ops/chummo-stack/` | n8n/Ollama portable |

## Agents (governance model)

| Agent | Role |
|-------|------|
| VISION | Policy / go-no-go |
| TANK | Execution |
| FLY GUY | Customer comms |
| BOB | Audit / documentation |
| STICKS | Monitoring / SLA |

Decisions: **3-of-5 votes** via `POST /api/agents/evaluate` (requires `X-Agent-Secret`).

## Differentiation vs TMMT OS

| | TMMT OS | AIXMOS Command Center |
|--|---------|------------------------|
| Buyer | Owner running a business | Operator wanting AI + systems IP |
| Core value | Apps, portals, ledger, cases | Agents, brain, prompts, automation |
| Delivery | Web app (Vercel) | Docs + API + optional local stack |
| Price signal | [FILL] monthly OS fee | $97/mo membership; $3.75K–$50K projects |

## Pricing (from AIXMOS docs)

- $97/month Membership
- $397 LLC Formation
- $500–$1K Credit Guidance
- $3,750 Base Infrastructure
- $7,500 Enterprise Systems
- **$15,000 Car Rental in a Box** (mentorship / BIAB — includes Rentals positioning)
- $25,000 E-Commerce Ecosystem
- $50,000 Full Ecosystem

## GTM

- Upsell from $97 membership → TMMT OS subscription
- BIAB buyers get Rentals **included** (no $97) — enforce via Stripe coupon or entitlement grant
- Investor story: **IP + agent governance** as platform moat, not just rental SaaS

## Gaps for sellable product

1. Standalone marketing site + checkout for AIXMOS SKU
2. Agent panel UI polish (today: admin console + API)
3. Package agent definitions into customer-facing “brain” dashboard
