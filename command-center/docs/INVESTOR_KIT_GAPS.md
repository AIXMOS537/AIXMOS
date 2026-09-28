# Investor Kit — What's Missing

**Master kit path:** `~/Desktop/INVESTOR_FLASH_MASTER`  
**Last reviewed:** 2026-05-16

---

## Already on the flash master

| Item | Path |
|------|------|
| Sanitized AIX AI Command System | `AIX_AI_COMMAND_SYSTEM/` |
| TMMT Management stack | `TMMT MANAGEMENT/` |
| Install guide | `guides/INSTALL.md` |
| Investor readme | `INVESTOR_README.md` |
| Install checklist | `INVESTOR_INSTALL_CHECKLIST.md` |
| Clone scripts | `prepare-three-drives.sh`, `clone-to-flash.sh`, `strip-secrets.sh` |
| One-pager (operator draft) | Sync from `AIX_Command_Center/docs/INVESTOR_ONE_PAGER.md` |

---

## Missing or incomplete (build before serious fundraise)

| Priority | Document | Purpose | Location |
|----------|----------|---------|----------|
| P0 | **Pitch deck** (markdown → Slides) | Narrative + ask | [`INVESTOR_PITCH_DECK.md`](./INVESTOR_PITCH_DECK.md) — **fill [FILL:]** |
| P0 | **Financial model** scaffold | 12–36 mo scenarios | [`INVESTOR_FINANCIAL_MODEL.md`](./INVESTOR_FINANCIAL_MODEL.md) — **fill [FILL:]** |
| P0 | **Dealership roadmap** | Rental → dealer parallel path | [`DEALERSHIP_TRANSITION_ROADMAP.md`](./DEALERSHIP_TRANSITION_ROADMAP.md) |
| P0 | **Automation ROI backlog** | What to wire first | [`AUTOMATION_PRIORITY_BACKLOG.md`](./AUTOMATION_PRIORITY_BACKLOG.md) |
| P0 | **Historical P&L / bank summary** | Proof, not projections | Data room only — not on USB |
| P1 | **3-page executive summary** | Email-forwardable | `docs/INVESTOR_EXEC_SUMMARY.md` |
| P1 | **Cap table / ownership** | Who owns what | Counsel + data room |
| P1 | **Use of funds detail** | Tie to one-pager | Section in deck |
| P1 | **Customer metrics export** | Collection rate, churn, LTV | From Supabase — monthly CSV |
| P2 | **Legal pack** | LLC docs, rental agreements, insurance certs | Data room |
| P2 | **FAQ** | Objections, competitor, risk | `docs/INVESTOR_FAQ.md` |
| P2 | **Demo script** | 15-min TMMT OS walkthrough | `docs/INVESTOR_DEMO_SCRIPT.md` |
| P2 | **Investor update template** | Monthly rhythm | `docs/INVESTOR_UPDATE_TEMPLATE.md` |
| P3 | **Recorded demo video** | Async review | External link |
| P3 | **Terms sheet template** | SAFE / note / equity | Counsel |

---

## Software vs story gap

| Area | Kit status |
|------|------------|
| Prompts, SOPs, templates | Strong |
| tmmt-os investor dashboard UI | Scaffold only — needs `investor_updates` content |
| Live metrics API for investors | Not packaged for external LP login |
| Rental-specific GHL pipeline doc on USB | Missing — operator to add after Week 2 |

---

## Sync checklist (when refreshing INVESTOR_FLASH_MASTER)

- [ ] Run `strip-secrets.sh` / no `.env` with real keys
- [ ] Copy latest `docs/INVESTOR_ONE_PAGER.md` to flash root
- [ ] Copy `docs/INVESTOR_PITCH_DECK.md`, `INVESTOR_FINANCIAL_MODEL.md`, `DEALERSHIP_TRANSITION_ROADMAP.md`, `AUTOMATION_PRIORITY_BACKLOG.md` to `INVESTOR_FLASH_MASTER/docs/`
- [ ] Copy `OWNER_DAILY_COMMAND.md` + `PRIORITY_PLAN_ALL_PILLARS.md` if sharing operator discipline
- [ ] Do **not** copy BROTHER I originals, dispute letters, or personal media
- [ ] Test `setup-mac.sh` on one machine before `prepare-three-drives.sh`

---

## Established operator rule

**Lead with traction** ($1M+ rental revenue, fleet, markets). Pair the USB / deck with:

- Filled `[FILL:]` on deck, model, and one-pager (same numbers everywhere)  
- Historical P&L or bank summary in data room (not on USB)  
- Live demo: daily brief → collections → fleet  

Collections and maintenance discipline are **proof of operational excellence**, not a reason to delay investor meetings.
