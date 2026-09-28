# Streamline Roadmap — Investor Readiness (30/60/90)

## Principles

- **Do not merge** TMMT Rentals and TMMT OS codebases — merge **auth, billing, and narrative** only
- **Mock** only: multi-venture #2–50, NAS backup, full marketplace checkout
- **Build** for demo: one login, one Stripe, filled metrics, 15-min script

## Days 0–30

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Fill `[FILL]` in `INVESTOR_PITCH_DECK.md`, `INVESTOR_FINANCIAL_MODEL.md`, `INVESTOR_ONE_PAGER.md` | Operator |
| P0 | Create `INVESTOR_DEMO_SCRIPT.md` — 15 min walkthrough | Product |
| P0 | One Stripe account: Products = Rentals ($97), TMMT OS ([FILL]), AIXMOS ($97), BIAB ($15K) | Eng |
| P1 | Confirm Supabase: one project vs two — document in `COMMAND_CENTER_MAP.md` | Eng |
| P1 | Fix Supabase connectivity for daily brief / metrics export | Ops |
| P1 | Sync investor-flash quartet to USB via `clone-to-flash.sh` | Ops |

**Demo order (investor meeting):**

1. Portfolio home `/` (30 sec — multi-venture platform)
2. TMMT Rentals dashboard — fleet, leads, collections (5 min)
3. TMMT OS — client portal + internal ledger (4 min)
4. AIXMOS — admin agent console + USB kit (3 min)
5. Ask + use of funds (3 min)

## Days 31–60

| Priority | Action |
|----------|--------|
| P0 | Stripe Checkout or Customer Portal for $97 Rentals + OS subscription |
| P0 | Entitlement webhook: payment → `profiles.package_id` in tmmt-os |
| P1 | SSO: same Supabase project OR Clerk org with `products` in app_metadata |
| P1 | TMMT Management interfaces in tmmt-os (remove external rentals admin links) |
| P2 | Investor portal: populate `investor_updates` + monthly memo template |
| P2 | Record 5-min Loom async demo |

## Days 61–90

| Priority | Action |
|----------|--------|
| P1 | Portfolio Command Center Phase 1 (teams workspace) — or mock second venture |
| P1 | Marketplace booking + payment stub or GHL-only for v1 |
| P2 | Refresh 3 investor USBs with `prepare-three-drives.sh` |
| P2 | BIAB onboarding checklist productized in Notion/GHL, linked from OS |

## Merge vs keep separate

| Keep separate | Unify |
|---------------|-------|
| `tmmt-app` vs `tmmt-os` | Stripe billing |
| AIXMOS markdown/agents as IP | Auth / user table |
| INVESTOR_FLASH_MASTER (sanitized) | Pricing table in docs |

## Mock for investors (OK short-term)

- Second venture tile on portfolio home
- Marketplace checkout completion
- Full 50-venture scale

## Must be real for investors

- Rentals KPIs from Supabase
- One successful agent evaluation session
- Consistent revenue numbers across deck, one-pager, model
