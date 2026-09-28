# Custom Domain — ship at yourbrand.com (not *.workers.dev)

Right now your product lives at `https://aixmos-gateway.aixmos.workers.dev`. A real brand domain
makes it look like the product it is, and is required for serious white-label sales. Everything is
pre-wired — you just need to **own a domain** (the one thing I can't buy for you).

## Step 1 — get a domain into THIS Cloudflare account (account: muhammad@allinonemanagementsolutions.com)
Pick one:
- **Buy via Cloudflare Registrar** (cheapest, auto-configured): dash.cloudflare.com → Domain Registration → Register. ~$10/yr.
- **Move an existing domain**: add the site to Cloudflare and point its nameservers (Cloudflare walks you through it).

A short brandable name is best (e.g., `tmmtos.com`, `aixmos.ai`, `<yourbrand>.com`). Avoid putting
"credit repair" in the domain — keep that offering separate (it's the high-risk flag).

## Step 2 — point the Worker at it (I can do this part once the domain is in your account)
Either:
- **Dashboard (easiest):** Workers & Pages → `aixmos-gateway` → Settings → **Domains & Routes** → **Add Custom Domain** → e.g. `app.yourbrand.com`. Cloudflare issues the SSL cert automatically (~1 min).
- **Or wrangler:** uncomment the `routes` block in `wrangler.toml`, set your hostname, `npx wrangler deploy`.

## Step 3 — update the brand
- Set the gateway's brand name: `npx wrangler secret put BRAND_NAME` → e.g. `TMMT OS` (changes the title on the landing/portal/console pages).
- For per-customer white-label (each buyer's own brand), the resale flow already stores their brand;
  point each buyer at their own subdomain or their own Worker on handover tiers.

## Result
- Landing: `https://app.yourbrand.com/`
- Portal: `https://app.yourbrand.com/me`
- Founder dash: `https://app.yourbrand.com/founder`
- Admin: `https://app.yourbrand.com/admin`
- Pay webhooks keep working (just the new hostname).

**Tell me the moment a domain is in your Cloudflare account and I'll wire the custom domain + cert + brand in one pass.**
