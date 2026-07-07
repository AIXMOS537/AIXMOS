# AIXMOS — Launch Kit

Everything to launch the AI product to your waiting list. Free tier is LIVE today (no AIXMOS
funding needed); premium flips on when you fund Anthropic.

**Link to share:** https://aixmos-gateway.aixmos.workers.dev
(swap to your domain once set — see resale/CUSTOM_DOMAIN.md)

## 1) Launch message (paste to your list / socials / DMs)
**Short (text/DM):**
> AIXMOS is live 🚀 Your AI operating brain for the business — drafts, ops, agents, automations.
> **Free to start, no card.** Grab your key in 60 sec: https://aixmos-gateway.aixmos.workers.dev
> Want premium agents + automations? Reply "TOKENS" and I'll load you up.

**Longer (email/post):**
> I built AIXMOS — the same AI system I run my own business on, now open to you.
> • Start **free** (no card) — it answers, drafts, and helps run ops on day one.
> • Unlock premium models + my custom agents (ops, outbound closer, automations) with **TMMT tokens**.
> • White-label it as your own brand.
> It runs on my own real operation (TMMT) — this isn't theory, it's what pays my bills.
> Get in free: https://aixmos-gateway.aixmos.workers.dev — reply with questions.

## 2) 3-minute demo script (live or recorded)
1. **0:00 Hook (15s):** "This is AIXMOS — the AI brain that runs my rental business. I'll show you it live."
2. **0:15 Free signup (30s):** open the link → enter email → "Boom, free account, no card." Show the key.
3. **0:45 Real work (60s):** in `/me`, ask it a real task — "draft a follow-up to a customer who's late on payment" → show the answer.
4. **1:45 Agents + tokens (45s):** show `/wallet` (tokens, unlocked agents). "Free runs on edge AI; premium agents — my ops closer, automations — run on TMMT tokens. You buy tokens, they power everything."
5. **2:30 Close (30s):** "Start free today, upgrade when it's making you money. Link below. Reply and I'll set you up." 

## 3) First-customer onboarding SOP (so you/a VA run it identically)
1. **They sign up** at the link (free). Confirm they got their key.
2. **They paid for tokens?** (Zelle/CashApp/PayPal/crypto/cash) → open `/admin` on your phone → enter their **email** + token amount + tier → **Load**. (See resale/PAYMENTS.md.)
   - $25→600 (Haiku) · $100→3,000 (Sonnet) · $500→18,000 (Opus)
3. **Send them the portal:** "Go to `/me`, paste your key, you'll see your tokens + agents. Ask it anything."
4. **High-ticket buyer ($1,875+)?** run `resale/provision-customer.sh --tier N --customer <email> --brand <Brand> --paid <ref>` → deliver their brand.env secret via 1Password.
5. **Log it** — the sale auto-appears on `/founder`.

## 4) Pre-launch checklist
- [ ] Free signup works (test it yourself once)
- [ ] `/admin` loads tokens by email (test with your own free account)
- [ ] Decide token prices (defaults in src/index.js `PACKS`)
- [ ] (Premium) Fund AIXMOS + set spend cap
- [ ] (Optional) Custom domain + BRAND_NAME
- [ ] Pick ONE audience + ONE message, send to 5–10 people, watch `/founder`
