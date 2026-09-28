# Getting Paid — Crypto + Every US Rail (no Stripe required)

TMMT tokens power everything; money loads tokens into a customer's wallet. Payment is fully
decoupled from access, so you can take **any** form of money. Nothing here needs a high-risk
processor approval to start.

## The pieces (all built into the gateway)
| Endpoint | What | Auth |
|---|---|---|
| `/admin` | **Phone console** — load tokens in seconds after any payment | your admin key (typed in the page) |
| `/pay/webhook` | **Universal** — any tool/Zapier loads tokens | `x-pay-secret` (PAY_WEBHOOK_SECRET, in your vault) |
| `/pay/crypto` | Crypto checkout (Coinbase Commerce) | buyer's key |
| `/pay/coinbase` | Crypto webhook (auto-load) | Coinbase HMAC |
| `/buy` + `/stripe/webhook` | Cards via Stripe (if ever approved) | — |
| `/admin/topup` | API top-up (for automations) | admin key |

## 🟢 Start TODAY (zero setup, ban-proof)
**Manual:** customer pays by Zelle / CashApp / Venmo / wire / cash / PayPal invoice →
open **`/admin` on your phone** → enter their email + token amount → tap **Load**. Done.
(Works because every signup is indexed by email.)

## 🔁 Automate ANY rail with Zapier/Make (no code)
Connect any US payment tool to your tokens:
> **Zap:** *When [Square / PayPal / Venmo / CashApp / your bank / Stripe / Helcim / anything] gets a payment*
> → **POST** `https://aixmos-gateway.aixmos.workers.dev/pay/webhook`
> Header: `x-pay-secret: <PAY_WEBHOOK_SECRET from your vault>`
> Body: `{"email":"{{customer_email}}", "amount_usd":{{amount}}}`

`amount_usd` auto-maps to a token pack (25→600, 100→3000, 500→18000). Or send explicit `"tokens": N`.

## ₿ Crypto self-serve (recommended for high-risk — no chargebacks)
1. Create a **Coinbase Commerce** account (commerce.coinbase.com) — accepts BTC/ETH/**USDC**+more, no underwriting.
2. ```bash
   cd ~/dev/aixmos-gateway
   npx wrangler secret put COINBASE_COMMERCE_KEY      # Commerce → Settings → API keys
   npx wrangler secret put COINBASE_WEBHOOK_SECRET    # Commerce → Settings → Webhooks → shared secret
   ```
3. In Coinbase Commerce → add webhook: `https://aixmos-gateway.aixmos.workers.dev/pay/coinbase` (event `charge:confirmed`).
4. The landing page's **"₿ Pay with crypto"** button now creates a hosted checkout; tokens auto-load on confirm.

## 💳 Native cards at volume (later)
High-risk merchant accounts (PaymentCloud, Durango, Authorize.net) accept credit-repair-adjacent
businesses Stripe won't. Point their webhook/Zapier → `/pay/webhook`. Stripe adapter stays ready if approved.

## Token packs (edit in src/index.js `PACKS`)
- Starter $25 → 600 tokens (Haiku) · Pro $100 → 3,000 (Sonnet) · Scale $500 → 18,000 (Opus)

## ⚠️ Keep clean
- Separate the **credit-repair** offering — it's the #1 thing that gets payment accounts frozen.
- TMMT tokens are **prepaid utility credits**, never an investment (no securities framing).
- `PAY_WEBHOOK_SECRET` + admin key = keys to your money flow. 1Password them; rotate if leaked.
