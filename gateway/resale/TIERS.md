# AIXMOS / TMMT OS — White-Label Resale Tiers

Sell the system itself, branded as the buyer's. Access is gated by `provision-customer.sh`,
which grants **exactly** the paid tier (AI model ceiling + monthly credits + feature entitlements)
via the gateway's KV — instant, revocable, no redeploy. Source of truth = `tiers.json`.

## Tiers (DRAFT — confirm software per tier)
| # | Price | AI ceiling | Credits/mo | Software (script-granted) | Hosting | Physical (manual) |
|---|---|---|---|---|---|---|
| 1 | **$1,875** | free (your Ollama) | 200 | Airtable CRM base, no automations · white-label | **self** | — |
| 2 | **$3,750** | haiku | 500 | Airtable Pro (views/portals) · white-label | **self** | — |
| 3 | **$7,500** | sonnet | 1,500 | Airtable **+ automations** · integrations · white-label | **self** | — |
| 4 | **$15,000** | sonnet | 4,000 | **Business in a Box** — full TMMT OS stack · priority | **self** | — |
| 5 | **$25,000** | sonnet | 6,000 | Tier-4 stack | **handover** | 🚗 vehicle |
| 6 | **$35–50k** | opus | 12,000 | Full stack, max | **handover** | $50k: 🛒 gifted Amazon store |

**Hosting:** *self* = you run their instance on your Cloudflare/Supabase (easy to gate/revoke).
*handover* (≥$25k) = migrate to the **buyer's own** Airtable/Anthropic/Cloudflare accounts (true sale).

## Provision a paying customer
```bash
cd ~/dev/aixmos-gateway/resale
bash provision-customer.sh --tier 3 --customer "jane@acme.com" --brand "AcmeOps" \
     --paid "stripe_pi_… | wire | invoice#"   --days 365
```
→ mints their scoped secret, writes access to gateway KV, writes `customers/<Brand>/brand.env`
(their secret — deliver via 1Password), `grant-entitlements.sql`, and logs to `sales-ledger.csv`.
Payment trigger is **any source** — manual, Stripe webhook, or invoice; whatever you put in `--paid`.

**Revoke (refund/chargeback/expiry):**
```bash
bash provision-customer.sh --revoke --secret "<their secret>"   # dead instantly, no redeploy
```

## White-label
`brand.env` carries `BRAND_NAME` + their gateway secret. Ship them the flashdrive/`AIXMOS-KIT`
(or `bootstrap-*`) with their brand. Their AI persona is auto-set to their brand. For deeper
white-label (logo/domain/portal name), set those in their Airtable/portal config at setup.

## ⚠️ Fulfillment & legal (NOT handled by the script)
- **Tier 5 vehicle / Tier 6 Amazon store** are real assets — **title transfer, insurance, sales/income
  tax, 1099/asset-gift reporting, account/ToS transfer.** Handle via fulfillment + your accountant/counsel.
- **Reselling Claude AI access:** confirm you have the right **Anthropic commercial/reseller terms**;
  self-hosted tiers run on *your* Anthropic key (your spend — watch the cap), handover tiers should move
  to the **buyer's own Anthropic key** so their usage is their cost.
- **IP:** your code/configs are yours to license; Airtable/Anthropic/Cloudflare are the buyer's platforms
  (their accounts on handover tiers). Put terms in a simple resale agreement.
- **Spend safety:** every self-hosted customer draws on your Anthropic balance — keep the monthly cap on,
  and watch `/usage`. Per-customer credits cap each one; auto-downgrade to free protects you.
