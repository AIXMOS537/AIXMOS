// AIXMOS Gateway — one brain, scoped access, cost-controlled, credit-metered ("TMMT tokens").
// Holds your API key server-side. Each person sends a prompt + their secret.
//
// THREE LANES:
//   free   -> your own Ollama (via Cloudflare Tunnel). $0. Most employees live here.
//   haiku  -> cheap cloud. sonnet/opus -> premium cloud (limited people only).
// CREDITS ("TMMT tokens"): each person gets a monthly allowance; each cloud call debits by
//   model. When a person runs out, they DON'T get cut off — they auto-drop to the free lane.

const TIERS = {
  haiku:  "claude-haiku-4-5-20251001",  // cheapest cloud
  sonnet: "claude-sonnet-4-6",          // balanced
  opus:   "claude-opus-4-8",            // premium — your strategic work only
};
// TMMT-token cost per call by model. free = your own hardware = 0.
const COST = { free: 0, haiku: 1, sonnet: 5, opus: 25 };
const RANK = { free: 0, haiku: 1, sonnet: 2, opus: 3 };
// TMMT TOKEN PACKS (buy with Stripe → auto-loaded into wallet). usd in cents. Bonus scales up.
// Bumps maxTier so buying tokens also unlocks premium models. Adjust pricing freely.
const PACKS = {
  starter: { usd: 2500,  tokens: 600,   maxTier: "haiku",  label: "Starter — 600 TMMT tokens" },
  pro:     { usd: 10000, tokens: 3000,  maxTier: "sonnet", label: "Pro — 3,000 TMMT tokens" },
  scale:   { usd: 50000, tokens: 18000, maxTier: "opus",   label: "Scale — 18,000 TMMT tokens" },
};

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const auth = req.headers.get("x-aixmos-auth");
    const BRAND = env.BRAND_NAME || "AIXMOS";

    // ── PUBLIC: landing page (top of funnel) — no auth. ──
    if ((url.pathname === "/" || url.pathname === "/join") && req.method === "GET") {
      const html = `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">
<title>${BRAND} — your AI operating brain</title><style>
body{font-family:system-ui,sans-serif;background:#0b0b0f;color:#eee;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center}
.card{max-width:520px;padding:40px;text-align:center}h1{font-size:2rem;margin:.2em 0}p{color:#aaa;line-height:1.5}
input,button{font-size:1rem;padding:12px 14px;border-radius:10px;border:1px solid #333;margin:6px}
input{background:#15151c;color:#fff;width:60%}button{background:#5b8cff;color:#fff;border:0;cursor:pointer;font-weight:600}
#out{margin-top:18px;text-align:left;background:#15151c;padding:14px;border-radius:10px;display:none;white-space:pre-wrap;font-size:.85rem}
small{color:#777}</style></head><body><div class=card>
<h1>${BRAND}</h1><p>Your AI operating brain — runs your ops, agents, and automations. <b>Free to start.</b> Add TMMT tokens to unlock premium models & agents.</p>
<div><input id=email type=email placeholder="you@email.com"><button onclick=go()>Get free access</button></div>
<div id=out></div><small>Free tier runs on our edge AI. No card required.</small>
<script>let SEC='';
async function go(){const e=document.getElementById('email').value;const o=document.getElementById('out');o.style.display='block';o.textContent='Creating your free account…';
const r=await fetch('/signup',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email:e})});const d=await r.json();
if(d.secret){SEC=d.secret;o.innerHTML='✅ You\\'re in! Save your key:<br><code style="color:#5b8cff">'+d.secret+'</code><br><br>Unlock premium models + agents with TMMT tokens:<br><button onclick="buy(\\'starter\\')">Card $25</button> <button onclick="buy(\\'pro\\')">Card $100</button> <button onclick="buy(\\'scale\\')">Card $500</button><br><button onclick="buyCrypto(\\'pro\\')">₿ Pay with crypto</button>';}else{o.textContent='Error: '+(d.error||'try again');}}
async function buy(p){const r=await fetch('/buy',{method:'POST',headers:{'content-type':'application/json','x-aixmos-auth':SEC},body:JSON.stringify({pack:p})});const d=await r.json();if(d.url){location.href=d.url;}else{alert(d.error||'card payments not live yet — use crypto or contact us');}}
async function buyCrypto(p){const r=await fetch('/pay/crypto',{method:'POST',headers:{'content-type':'application/json','x-aixmos-auth':SEC},body:JSON.stringify({pack:p})});const d=await r.json();if(d.url){location.href=d.url;}else{alert(d.error||'crypto not live yet');}}</script>
</div></body></html>`;
      return new Response(html, { headers: { "content-type": "text/html;charset=utf-8" } });
    }

    // ── ADMIN console (phone-friendly): load TMMT tokens after ANY payment. Needs your admin key (entered here). ──
    if (url.pathname === "/admin" && req.method === "GET") {
      const html = `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">
<title>${BRAND} — Load Tokens</title><style>
body{font-family:system-ui,sans-serif;background:#0b0b0f;color:#eee;margin:0;padding:24px;max-width:460px;margin:auto}
h2{margin-top:0}label{display:block;margin:14px 0 4px;color:#aaa;font-size:.85rem}
input,select,button{width:100%;font-size:1rem;padding:12px;border-radius:10px;border:1px solid #333;background:#15151c;color:#fff;box-sizing:border-box}
button{background:#5b8cff;border:0;font-weight:700;margin-top:18px;cursor:pointer}#msg{margin-top:14px;white-space:pre-wrap}small{color:#777}</style></head>
<body><h2>${BRAND} · Load Tokens</h2><small>After a Zelle/CashApp/PayPal/crypto/cash payment, load the customer's TMMT tokens.</small>
<label>Your admin key</label><input id=adm type=password placeholder="admin secret (saved on this device)">
<label>Customer email</label><input id=email type=email placeholder="customer@email.com">
<label>TMMT tokens to add</label><input id=tok type=number value=3000>
<label>Unlock model up to</label><select id=tier><option>free</option><option>haiku</option><option selected>sonnet</option><option>opus</option></select>
<button onclick=load()>Load tokens</button><div id=msg></div>
<script>const A=localStorage.getItem('aixadm');if(A)document.getElementById('adm').value=A;
async function load(){const adm=document.getElementById('adm').value;localStorage.setItem('aixadm',adm);
const m=document.getElementById('msg');m.textContent='Loading…';
const r=await fetch('/admin/topup',{method:'POST',headers:{'content-type':'application/json','x-aixmos-auth':adm},
body:JSON.stringify({email:document.getElementById('email').value,tokens:parseInt(document.getElementById('tok').value),maxTier:document.getElementById('tier').value})});
const d=await r.json();m.textContent=d.ok?('✅ Loaded. New balance: '+d.wallet+' tokens'):('❌ '+(d.error||'failed — check admin key / that the customer signed up'));}</script>
</body></html>`;
      return new Response(html, { headers: { "content-type": "text/html;charset=utf-8" } });
    }

    // ── PUBLIC: self-serve free signup — issues a free account on the spot. ──
    if (url.pathname === "/signup" && req.method === "POST") {
      const b = await req.json().catch(() => ({}));
      const email = (b.email || "").toString().slice(0, 120);
      if (!email || !email.includes("@")) return Response.json({ error: "valid email required" }, { status: 400 });
      // light abuse guard: cap signups/day globally
      const sd = `signups:${new Date().toISOString().slice(0,10)}`;
      const sc = parseInt((await env.AIXMOS_KV.get(sd)) || "0", 10);
      if (sc > 500) return Response.json({ error: "signups paused, try later" }, { status: 429 });
      await env.AIXMOS_KV.put(sd, String(sc + 1), { expirationTtl: 172800 });
      const secret = "ax_free_" + crypto.randomUUID().replace(/-/g, "");
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(secret));
      const hash = [...new Uint8Array(buf)].map(x => x.toString(16).padStart(2, "0")).join("");
      const cfg = { name: email, brand: "free", maxTier: "free", monthly: 0,
        agents: ["tmmt-brain"], persona: `${BRAND} free assistant. Helpful, brief.`, tier: "free_signup" };
      await env.AIXMOS_KV.put(`cust:${hash}`, JSON.stringify(cfg));
      await env.AIXMOS_KV.put(`wallet:${hash}`, "0");
      await env.AIXMOS_KV.put(`emailidx:${email.toLowerCase()}`, hash);   // load tokens later by email
      return Response.json({ ok: true, secret, plan: "free", note: "Free edge AI. Buy TMMT tokens to unlock premium models + agents." });
    }

    // ── PUBLIC: Stripe webhook — payment confirmed → auto-load TMMT tokens into the buyer's wallet. ──
    if (url.pathname === "/stripe/webhook" && req.method === "POST") {
      const raw = await req.text();
      const sigHeader = req.headers.get("stripe-signature") || "";
      if (!env.STRIPE_WEBHOOK_SECRET) return new Response("stripe not configured", { status: 503 });
      // verify Stripe signature (HMAC-SHA256 over `${t}.${rawBody}`)
      const parts = Object.fromEntries(sigHeader.split(",").map(kv => kv.split("=")));
      const t = parts.t, v1 = parts.v1;
      if (!t || !v1) return new Response("bad sig", { status: 400 });
      if (Math.abs(Math.floor(Date.now() / 1000) - parseInt(t, 10)) > 300) return new Response("stale", { status: 400 });
      const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.STRIPE_WEBHOOK_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
      const macBuf = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${t}.${raw}`));
      const expected = [...new Uint8Array(macBuf)].map(b => b.toString(16).padStart(2, "0")).join("");
      if (expected !== v1) return new Response("sig mismatch", { status: 400 });
      const event = JSON.parse(raw);
      if (event.type === "checkout.session.completed" || event.type === "payment_intent.succeeded") {
        const md = (event.data?.object?.metadata) || {};
        const tokens = parseInt(md.tokens || "0", 10);
        if (md.hash && tokens > 0) {
          const cur = parseInt((await env.AIXMOS_KV.get(`wallet:${md.hash}`)) || "0", 10);
          await env.AIXMOS_KV.put(`wallet:${md.hash}`, String(cur + tokens));
          // optional: a pack can also raise the model ceiling/agents
          if (md.maxTier || md.agents) {
            const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${md.hash}`)) || "{}");
            if (md.maxTier) c.maxTier = md.maxTier;
            if (md.agents) c.agents = md.agents.split(",").filter(Boolean);
            await env.AIXMOS_KV.put(`cust:${md.hash}`, JSON.stringify(c));
          }
        }
      }
      return Response.json({ received: true });
    }

    // ── PUBLIC: UNIVERSAL payment webhook — connect ANY US payment rail (cards, ACH, PayPal,
    //    Venmo, CashApp, Zelle, Square, crypto) via the provider's webhook OR a Zapier/Make zap.
    //    Auth = shared secret header `x-pay-secret`. Body: { email|secret|hash, tokens|amount_usd, maxTier?, agents? }.
    if (url.pathname === "/pay/webhook" && req.method === "POST") {
      if (!env.PAY_WEBHOOK_SECRET) return new Response("not configured", { status: 503 });
      if (req.headers.get("x-pay-secret") !== env.PAY_WEBHOOK_SECRET) return new Response("bad secret", { status: 401 });
      const b = await req.json().catch(() => ({}));
      let h = b.hash;
      if (!h && b.secret) {
        const hb = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(b.secret));
        h = [...new Uint8Array(hb)].map(x => x.toString(16).padStart(2, "0")).join("");
      }
      if (!h && b.email) h = await env.AIXMOS_KV.get(`emailidx:${b.email.toLowerCase()}`);   // signup account by email
      // amount_usd (dollars) maps to a PACK; or pass explicit tokens
      let tokens = parseInt(b.tokens || "0", 10), maxTier = b.maxTier;
      if (!tokens && b.amount_usd) {
        const cents = Math.round(parseFloat(b.amount_usd) * 100);
        const p = Object.values(PACKS).find(x => x.usd === cents);
        if (p) { tokens = p.tokens; maxTier = maxTier || p.maxTier; }
      }
      if (!h || !tokens) return Response.json({ error: "need {email|secret|hash} and {tokens|amount_usd}" }, { status: 400 });
      const cur = parseInt((await env.AIXMOS_KV.get(`wallet:${h}`)) || "0", 10);
      await env.AIXMOS_KV.put(`wallet:${h}`, String(cur + tokens));
      if (maxTier) { const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${h}`)) || "{}"); c.maxTier = maxTier; if (b.agents) c.agents = String(b.agents).split(",").filter(Boolean); await env.AIXMOS_KV.put(`cust:${h}`, JSON.stringify(c)); }
      return Response.json({ ok: true, wallet: cur + tokens });
    }

    // ── PUBLIC: Coinbase Commerce crypto webhook (HMAC over raw body w/ X-CC-Webhook-Signature). ──
    if (url.pathname === "/pay/coinbase" && req.method === "POST") {
      if (!env.COINBASE_WEBHOOK_SECRET) return new Response("not configured", { status: 503 });
      const raw = await req.text();
      const sig = req.headers.get("x-cc-webhook-signature") || "";
      const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.COINBASE_WEBHOOK_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
      const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(raw));
      const expected = [...new Uint8Array(mac)].map(x => x.toString(16).padStart(2, "0")).join("");
      if (expected !== sig) return new Response("sig mismatch", { status: 400 });
      const ev = JSON.parse(raw);
      if (ev.event?.type === "charge:confirmed" || ev.event?.type === "charge:resolved") {
        const md = ev.event?.data?.metadata || {};
        const tokens = parseInt(md.tokens || "0", 10);
        if (md.hash && tokens > 0) {
          const cur = parseInt((await env.AIXMOS_KV.get(`wallet:${md.hash}`)) || "0", 10);
          await env.AIXMOS_KV.put(`wallet:${md.hash}`, String(cur + tokens));
          if (md.maxTier) { const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${md.hash}`)) || "{}"); c.maxTier = md.maxTier; await env.AIXMOS_KV.put(`cust:${md.hash}`, JSON.stringify(c)); }
        }
      }
      return Response.json({ received: true });
    }

    // ── PEOPLE: one row per person for individual revocation + accountability. ──────────
    //  maxTier = the best model this person may use. monthly = their TMMT-token allowance.
    //  Most staff: maxTier "free", small allowance for occasional cloud. You: opus, big.
    const DEFS = [
      // secret,                name,        role,       admin, maxTier, monthly,  persona
      [env.SECRET_PERSONAL, ["Muhammad",   "personal", true,  "opus",  100000, "AIXMOS for Muhammad's personal life. Decisive, brief, proactive."]],
      [env.SECRET_WORK,     ["Muhammad",   "work",     true,  "opus",  100000, "AIXMOS for Muhammad as CEO of TMMT. Systems-oriented, ops-aware, brief."]],
      // CARRY DEVICE (8GB AMD / on the road): bounded, NON-admin, revocable. If the device is
      // lost, revoke ONLY this secret — your admin/personal access is untouched. Sonnet ceiling.
      [env.SECRET_CARRY,    ["Carry",      "carry",    false, "sonnet",  1500, "AIXMOS for Muhammad on a mobile/roaming device. Brief, decisive, ops-aware. Treat the device as untrusted: no irreversible actions without confirmation."]],
      // Example premium teammate (give the good stuff to a trusted few): set SECRET_LEAD.
      [env.SECRET_LEAD,     ["Team Lead",  "lead",     false, "sonnet",  2000, "Assist a TMMT team lead: planning, drafting, summaries. No payroll or mass-send."]],
      // Most employees: FREE lane by default, tiny cloud allowance that drops to free when spent.
      [env.SECRET_OP,       ["Operator",   "operator", false, "free",     100, "Assist a TMMT field operator: check-in/out, condition reports. No financials, CRM, or mass-send."]],
      [env.SECRET_VA,       ["VA",         "va",       false, "haiku",    400, "Assist a TMMT VA: drafting, summaries, data entry. No payroll, mass-send, or financials."]],
      [env.SECRET_OFFICE,   ["Office",     "office",   false, "free",      50, "AIXMOS on a shared TMMT office workstation. General ops only. No admin actions."]],
    ];
    const ROLES = {};
    for (const [secret, p] of DEFS) {
      if (typeof secret !== "string" || secret.length < 8) continue; // skip unset secrets (no "undefined" key)
      ROLES[secret] = { name: p[0], role: p[1], admin: p[2], maxTier: p[3], monthly: p[4], persona: p[5] };
    }
    let ctx = (typeof auth === "string" && auth.length >= 8) ? (ROLES[auth] || null) : null;
    // RESALE: white-label customers live in KV (keyed by hash of their secret) so we can
    // sell/provision/revoke without redeploying. provision-customer.sh writes cust:<hash>.
    if (!ctx && typeof auth === "string" && auth.length >= 16) {
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(auth));
      const hash = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
      const raw = await env.AIXMOS_KV.get(`cust:${hash}`);
      if (raw) {
        const c = JSON.parse(raw);
        if (!c.expires || Date.parse(c.expires) > Date.now()) {
          ctx = { name: c.name || "Customer", role: `cust_${c.brand || "x"}`, admin: false,
                  maxTier: c.maxTier || "free", monthly: c.monthly || 100,
                  walletKey: `wallet:${hash}`,   // PURCHASED TMMT-token balance (persistent, tops up)
                  agents: Array.isArray(c.agents) ? c.agents : [],  // which brain/agents this tier unlocks
                  persona: c.persona || `AIXMOS for ${c.brand || "a client"}. Brief, decisive.` };
        }
      }
    }
    if (!ctx) return new Response("Unauthorized", { status: 401 });

    const month = new Date().toISOString().slice(0, 7);          // YYYY-MM (credits reset monthly)
    const day   = new Date().toISOString().slice(0, 10);
    const credKey = `cred:${ctx.role}:${month}`;
    const getUsed = async () => parseInt((await env.AIXMOS_KV.get(credKey)) || "0", 10);

    // ── /usage : admin sees everyone's TMMT-token spend this month + remaining. ──────────
    if (url.pathname === "/usage" && ctx.admin && req.method === "GET") {
      const out = {};
      for (const [, p] of DEFS) {
        const used = parseInt((await env.AIXMOS_KV.get(`cred:${p[1]}:${month}`)) || "0", 10);
        out[p[1]] = { name: p[0], monthly: p[4], used, remaining: Math.max(0, p[4] - used), maxTier: p[3] };
      }
      return Response.json({ month, people: out });
    }

    // ── /buy : authed buyer picks a TMMT-token pack → Stripe Checkout URL. Webhook loads tokens on payment. ──
    if (url.pathname === "/buy" && req.method === "POST") {
      if (!env.STRIPE_SECRET_KEY) return Response.json({ error: "payments not configured yet" }, { status: 503 });
      const b = await req.json().catch(() => ({}));
      const pack = PACKS[b.pack];
      if (!pack) return Response.json({ error: "unknown pack", packs: Object.keys(PACKS) }, { status: 400 });
      const hbuf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(auth));
      const bhash = [...new Uint8Array(hbuf)].map(x => x.toString(16).padStart(2, "0")).join("");
      const f = new URLSearchParams();
      f.set("mode", "payment");
      f.set("success_url", `${url.origin}/?paid=1`);
      f.set("cancel_url", `${url.origin}/?canceled=1`);
      f.set("line_items[0][quantity]", "1");
      f.set("line_items[0][price_data][currency]", "usd");
      f.set("line_items[0][price_data][unit_amount]", String(pack.usd));
      f.set("line_items[0][price_data][product_data][name]", pack.label);
      f.set("metadata[hash]", bhash);
      f.set("metadata[tokens]", String(pack.tokens));
      f.set("metadata[maxTier]", pack.maxTier);
      const r = await fetch("https://api.stripe.com/v1/checkout/sessions", {
        method: "POST",
        headers: { Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`, "Content-Type": "application/x-www-form-urlencoded" },
        body: f.toString(),
      });
      const s = await r.json();
      return s.url ? Response.json({ url: s.url, pack: b.pack }) : Response.json({ error: s.error?.message || "stripe error" }, { status: 502 });
    }

    // ── /pay/crypto : authed buyer picks a pack → Coinbase Commerce hosted crypto checkout (BTC/ETH/USDC…). ──
    if (url.pathname === "/pay/crypto" && req.method === "POST") {
      if (!env.COINBASE_COMMERCE_KEY) return Response.json({ error: "crypto not configured yet" }, { status: 503 });
      const b = await req.json().catch(() => ({}));
      const pack = PACKS[b.pack];
      if (!pack) return Response.json({ error: "unknown pack", packs: Object.keys(PACKS) }, { status: 400 });
      const hb = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(auth));
      const bhash = [...new Uint8Array(hb)].map(x => x.toString(16).padStart(2, "0")).join("");
      const r = await fetch("https://api.commerce.coinbase.com/charges", {
        method: "POST",
        headers: { "X-CC-Api-Key": env.COINBASE_COMMERCE_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: pack.label, description: `${BRAND} TMMT tokens`, pricing_type: "fixed_price",
          local_price: { amount: (pack.usd / 100).toFixed(2), currency: "USD" },
          metadata: { hash: bhash, tokens: String(pack.tokens), maxTier: pack.maxTier },
          redirect_url: `${url.origin}/?paid=1`, cancel_url: `${url.origin}/?canceled=1`,
        }),
      });
      const c = await r.json();
      const hosted = c.data?.hosted_url;
      return hosted ? Response.json({ url: hosted, pack: b.pack }) : Response.json({ error: c.error?.message || "coinbase error" }, { status: 502 });
    }

    // ── /admin/topup : PROCESSOR-AGNOSTIC token loading (admin only). Works with ANY payment:
    //    manual, PayPal, crypto, Zelle, invoice — or a Zapier/Make automation that fires on payment.
    //    Body: { secret OR hash, tokens, maxTier?, agents? }. Use your admin secret in x-aixmos-auth.
    if (url.pathname === "/admin/topup" && req.method === "POST" && ctx.admin) {
      const b = await req.json().catch(() => ({}));
      let h = b.hash;
      if (!h && b.secret) {
        const hb = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(b.secret));
        h = [...new Uint8Array(hb)].map(x => x.toString(16).padStart(2, "0")).join("");
      }
      if (!h && b.email) h = await env.AIXMOS_KV.get(`emailidx:${b.email.toLowerCase()}`);   // load by email
      const add = parseInt(b.tokens || "0", 10);
      if (!h || !add) return Response.json({ error: "need {secret|hash, tokens}" }, { status: 400 });
      const cur = parseInt((await env.AIXMOS_KV.get(`wallet:${h}`)) || "0", 10);
      await env.AIXMOS_KV.put(`wallet:${h}`, String(cur + add));
      if (b.maxTier || b.agents) {
        const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${h}`)) || "{}");
        if (b.maxTier) c.maxTier = b.maxTier;
        if (b.agents) c.agents = Array.isArray(b.agents) ? b.agents : String(b.agents).split(",").filter(Boolean);
        await env.AIXMOS_KV.put(`cust:${h}`, JSON.stringify(c));
      }
      return Response.json({ ok: true, wallet: cur + add });
    }

    // ── /wallet : anyone checks their plan — TMMT tokens left, model ceiling, unlocked agents. ──
    if (url.pathname === "/wallet" && req.method === "GET") {
      const tokens = ctx.walletKey ? parseInt((await env.AIXMOS_KV.get(ctx.walletKey)) || "0", 10) : null;
      return Response.json({ name: ctx.name, plan_model_ceiling: ctx.maxTier,
        tmmt_tokens_left: tokens, agents_unlocked: ctx.agents || [], free_lane_always: true });
    }

    // ── /mem : shared memory, namespaced so team can't read your private context. ────────
    if (url.pathname === "/mem") {
      const scope = ctx.admin ? "" : ctx.role + ":";
      if (req.method === "GET") {
        const k = scope + url.searchParams.get("key");
        return Response.json({ key: k, value: await env.AIXMOS_KV.get(k) });
      }
      const { key, value } = await req.json();
      await env.AIXMOS_KV.put(scope + key, value);
      return Response.json({ ok: true });
    }

    // ── BRAIN ───────────────────────────────────────────────────────────────────────────
    if (req.method === "POST") {
      const incoming = await req.json().catch(() => null);
      if (!incoming || typeof incoming !== "object")
        return Response.json({ error: "Bad request" }, { status: 400 });

      // ABUSE GUARD: cap input size so nobody can run up token cost with a giant prompt.
      const inText = JSON.stringify(incoming.messages || incoming.prompt || "");
      if (inText.length > 24000)
        return Response.json({ error: "Input too large (max ~24k chars)." }, { status: 413 });

      // Decide the tier: requested (if any) but never above this person's maxTier.
      let want = incoming.tier && RANK[incoming.tier] !== undefined ? incoming.tier : ctx.maxTier;
      if (RANK[want] > RANK[ctx.maxTier]) want = ctx.maxTier;

      // ACCESS GATE: free for everyone; the brain/agents cost TMMT tokens.
      //  - Customers spend a PURCHASED wallet (persistent balance, tops up).
      //  - Staff spend a monthly allowance (auto-resets).
      // Out of tokens? DOWN-SHIFT to free (your Ollama) — the free floor is always there.
      const used = await getUsed();
      let tier = want, downgraded = false, walletBal = null;
      if (tier !== "free") {
        if (ctx.walletKey) {                                   // customer = purchased tokens
          walletBal = parseInt((await env.AIXMOS_KV.get(ctx.walletKey)) || "0", 10);
          if (walletBal < COST[tier]) { tier = "free"; downgraded = true; }
        } else if (used + COST[tier] > ctx.monthly) {          // staff = monthly allowance
          tier = "free"; downgraded = true;
        }
      }
      // Agent gating: a requested agent must be unlocked by this customer's tier.
      if (incoming.agent && ctx.walletKey && ctx.agents.length && !ctx.agents.includes(incoming.agent))
        return Response.json({ error: `Agent '${incoming.agent}' not in your plan. Upgrade tier to unlock.` }, { status: 403 });

      // ── FREE LANE — public free tier on Cloudflare Workers AI (scales, keeps home brain private).
      //    Staff/internal can route to private Ollama by setting OLLAMA_URL (Tailscale).
      if (tier === "free") {
        // ABUSE GUARD: bound free calls/account/day.
        const fKey = `free:${ctx.role}:${day}`;
        const fUsed = parseInt((await env.AIXMOS_KV.get(fKey)) || "0", 10);
        const FREE_DAILY = 100;
        if (fUsed >= FREE_DAILY)
          return Response.json({ error: "Daily free limit reached. Buy TMMT tokens to keep going." }, { status: 429 });
        await env.AIXMOS_KV.put(fKey, String(fUsed + 1), { expirationTtl: 172800 });
        const messages = [{ role: "system", content: ctx.persona }, ...(incoming.messages || [{ role: "user", content: incoming.prompt || "" }])];
        // 1) private Ollama (only if you wire OLLAMA_URL for internal/Tailscale)
        if (env.OLLAMA_URL) {
          const r = await fetch(`${env.OLLAMA_URL.replace(/\/$/, "")}/api/chat`, {
            method: "POST",
            headers: { "content-type": "application/json", ...(env.OLLAMA_AUTH ? { "x-aixmos-tunnel": env.OLLAMA_AUTH } : {}) },
            body: JSON.stringify({ model: env.OLLAMA_MODEL || "llama3.1", stream: false, messages }),
          });
          const data = await r.json().catch(() => ({}));
          return Response.json({ lane: "free", model: env.OLLAMA_MODEL || "llama3.1", downgraded, text: data?.message?.content ?? data?.response ?? "", raw: data }, { status: r.ok ? 200 : 502 });
        }
        // 2) public free tier → Cloudflare Workers AI
        if (env.AI) {
          const m = env.WORKERS_AI_MODEL || "@cf/meta/llama-3.1-8b-instruct";
          const a = await env.AI.run(m, { messages, max_tokens: 512 });
          return Response.json({ lane: "free", model: m, downgraded, text: a.response || "" });
        }
        return Response.json({ error: "Free lane not configured." }, { status: 503 });
      }

      // ── PAID LANE → Anthropic. Debit TMMT tokens first. ──
      if (ctx.walletKey) {           // customer: spend PURCHASED tokens (persistent, no reset)
        await env.AIXMOS_KV.put(ctx.walletKey, String(Math.max(0, walletBal - COST[tier])));
      } else {                        // staff: monthly allowance (auto-reset via TTL)
        await env.AIXMOS_KV.put(credKey, String(used + COST[tier]), { expirationTtl: 60 * 60 * 24 * 40 });
      }
      // light daily counter too (visibility)
      const dKey = `calls:${ctx.role}:${day}`;
      await env.AIXMOS_KV.put(dKey, String(parseInt((await env.AIXMOS_KV.get(dKey)) || "0", 10) + 1), { expirationTtl: 172800 });

      const payload = {
        model: TIERS[tier],
        max_tokens: Math.min(incoming.max_tokens || 1024, 2048),
        system: ctx.persona,
        messages: incoming.messages || [{ role: "user", content: incoming.prompt || "" }],
      };
      const r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "x-api-key": env.ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await r.text();
      // attach lane/token info via headers so clients can show "X tokens left"
      const hdrs = { "content-type": "application/json", "x-aixmos-lane": tier };
      if (ctx.walletKey) hdrs["x-aixmos-tokens-left"] = String(Math.max(0, walletBal - COST[tier]));
      else { hdrs["x-aixmos-credits-used"] = String(used + COST[tier]); hdrs["x-aixmos-credits-monthly"] = String(ctx.monthly); }
      return new Response(body, { status: r.status, headers: hdrs });
    }

    return new Response("Not found", { status: 404 });
  },
};
