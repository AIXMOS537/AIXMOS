# Zapier / Make — Auto-Load Tokens From Any Payment (step-by-step)

Goal: when money hits ANY of your accounts, tokens auto-load into the customer's wallet — no code.
You'll point every payment tool at one endpoint:

```
POST  https://aixmos-gateway.aixmos.workers.dev/pay/webhook
Header:  x-pay-secret: <PAY_WEBHOOK_SECRET from your vault / 1Password>
Body (JSON):  { "email": "<customer email>", "amount_usd": <amount> }
```
`amount_usd` auto-maps to a pack: **25→600 (Haiku), 100→3,000 (Sonnet), 500→18,000 (Opus)**.
Or send `"tokens": <N>` to load an exact amount, and optional `"maxTier":"sonnet"`.

## The universal Zap (works for any tool)
1. **Trigger:** your payment app's "New Payment/Sale" (PayPal, Square, Stripe, etc.).
2. **Action:** **Webhooks by Zapier → POST**
   - URL: `https://aixmos-gateway.aixmos.workers.dev/pay/webhook`
   - Data: `email` = the payer's email field, `amount_usd` = the amount field
   - Headers: `x-pay-secret` = your secret
3. Test → you should see `{"ok":true,"wallet":…}`. Turn it on.

## Per-tool trigger notes
| Tool | Zapier trigger | Notes |
|---|---|---|
| **PayPal** | "Successful Sale" | maps payer email + gross amount directly |
| **Square** | "New Payment" / "New Order" | use buyer email; amount in dollars |
| **Stripe** | "New Payment" (if you ever use it) | or use the native `/stripe/webhook` instead |
| **Cash App / Venmo** | via linked **bank deposit** trigger or "New Email" parse | personal apps lack clean APIs — see Email parse below |
| **Bank (any)** | Plaid/"New Transaction", or your bank's email alerts | |
| **Invoices (Wave/Zoho)** | "Invoice Paid" | clean email + amount |

## No clean API? Use Email Parser by Zapier (covers Zelle/CashApp/Venmo)
1. Forward your payment-notification emails to your Zapier Email Parser address.
2. Teach it to grab the **payer email/name** and **amount**.
3. Action → POST to `/pay/webhook` as above. Now even Zelle/CashApp auto-loads.

## Manual fallback (always works)
No Zap? Open **`https://aixmos-gateway.aixmos.workers.dev/admin`** on your phone → enter the
customer's email + tokens → tap **Load**. 5 seconds.

## Refunds / chargebacks
- Deduct/zero a wallet: `provision-customer.sh --revoke --secret <theirs>` (kills access), or
  load a negative correction via `/admin/topup` isn't supported — instead revoke + re-provision.

## Security
- `x-pay-secret` is the key to your money flow — keep it in 1Password, rotate if exposed
  (`npx wrangler secret put PAY_WEBHOOK_SECRET` with a new value).
- Only your gateway + your Zaps should ever know it.
