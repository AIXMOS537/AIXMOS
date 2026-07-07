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
// Allowlist for the maxTier setting (any other value is rejected at write time).
const VALID_TIERS = new Set(["free", "haiku", "sonnet", "opus"]);
// TMMT TOKEN PACKS (buy with Stripe → auto-loaded into wallet). usd in cents. Bonus scales up.
// Bumps maxTier so buying tokens also unlocks premium models. Adjust pricing freely.
const PACKS = {
  starter: { usd: 2500,  tokens: 600,   maxTier: "haiku",  label: "Starter — 600 TMMT tokens" },
  pro:     { usd: 10000, tokens: 3000,  maxTier: "sonnet", label: "Pro — 3,000 TMMT tokens" },
  scale:   { usd: 50000, tokens: 18000, maxTier: "opus",   label: "Scale — 18,000 TMMT tokens" },
};

// Free tokens expire 90 days from issue if never recharged. Paid token packs
// extend expiry by another 90 days (set on the next topup). This stops a
// stolen secret from being usable indefinitely.
const FREE_EXPIRY_MS = 90 * 24 * 60 * 60 * 1000;
const PAID_EXPIRY_MS = 365 * 24 * 60 * 60 * 1000;

// Agent / KV-key sanitizer. ALL identifiers that get concatenated into a KV
// key — and that may later be rendered in HTML on the founder dashboard —
// MUST pass through this. Closes the XSS chain where a staff user POSTs
// `{agent: "<script>...</script>"}` → bump('stat:agent:<script>...')` →
// founder page renders that key via innerHTML.
function sanitizeId(s) {
  if (typeof s !== "string") return "";
  // Only [a-zA-Z0-9_-], max 64 chars.
  const m = s.match(/^[a-zA-Z0-9_-]{1,64}$/);
  return m ? m[0] : "";
}

// Constant-time string compare for shared secrets passed in headers.
async function constantEq(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  // Web Crypto has no built-in constant-time compare. Hash both sides and
  // bytewise-compare the digests — gives O(constant) compare time relative
  // to the input.
  const enc = new TextEncoder();
  const [da, db] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(a)),
    crypto.subtle.digest("SHA-256", enc.encode(b)),
  ]);
  const ua = new Uint8Array(da), ub = new Uint8Array(db);
  let diff = 0;
  for (let i = 0; i < ua.length; i++) diff |= ua[i] ^ ub[i];
  return diff === 0;
}

function safeHtmlEscape(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

// Strict default response headers. CSP blocks inline-script injection in
// pages where we still use inline JS (the gateway is mostly self-contained)
// and frame-ancestors blocks clickjacking.
function htmlHeaders(extra) {
  return {
    "content-type": "text/html;charset=utf-8",
    // CSP: scripts/styles from self + inline (we use nonceless inline JS in
    // the pages below). Connect to self only. img: self + data: + Stripe.
    "content-security-policy":
      "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    ...(extra || {}),
  };
}

// lightweight metric counter (founder dashboard)
async function bump(env, k, by = 1) {
  const v = parseInt((await env.AIXMOS_KV.get(k)) || "0", 10) + by;
  await env.AIXMOS_KV.put(k, String(v));
}

// ── STRONGLY-CONSISTENT LEDGER (Durable Object) ──────────────────────────────────────
// Cloudflare KV is eventually consistent + non-atomic, so read-modify-write on a wallet
// races under concurrency (20 parallel calls all read "100", all write "95" → 1 debit
// instead of 20 = double-spend + quota-bypass). The DO serializes every op per account
// (one single-threaded instance per name, input-gated storage) → atomic, no leak.
function ledgerOp(env, name, body) {
  const stub = env.LEDGER.get(env.LEDGER.idFromName(name));
  return stub.fetch("https://ledger/op", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  }).then(r => r.json());
}

export class Ledger {
  constructor(state) { this.state = state; }
  async fetch(req) {
    const b = await req.json().catch(() => ({}));
    const s = this.state.storage;
    switch (b.op) {
      case "balance":
        return Response.json({ balance: (await s.get("bal")) || 0 });
      case "topup": {                                   // add purchased tokens
        const bal = ((await s.get("bal")) || 0) + (b.amount || 0);
        await s.put("bal", bal); return Response.json({ balance: bal });
      }
      case "charge": {                                  // atomic wallet debit (customer)
        let bal = (await s.get("bal")) || 0;
        if (bal < b.cost) return Response.json({ ok: false, balance: bal });
        bal -= b.cost; await s.put("bal", bal); return Response.json({ ok: true, balance: bal });
      }
      case "freecap": {                                 // per-account daily free-call limit
        const k = "free:" + b.day, used = (await s.get(k)) || 0;
        if (used >= b.limit) return Response.json({ ok: false, used });
        await s.put(k, used + 1); return Response.json({ ok: true, used: used + 1 });
      }
      case "allowance": {                               // atomic monthly allowance debit (staff)
        const k = "cred:" + b.month, used = (await s.get(k)) || 0;
        if (used + b.cost > b.monthly) return Response.json({ ok: false, used });
        await s.put(k, used + b.cost); return Response.json({ ok: true, used: used + b.cost });
      }
      case "used":                                      // read monthly allowance spent (admin view)
        return Response.json({ used: (await s.get("cred:" + b.month)) || 0 });
      default:
        return Response.json({ error: "unknown op" }, { status: 400 });
    }
  }
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const auth = req.headers.get("x-aixmos-auth");
    const BRAND = env.BRAND_NAME || "AIXMOS";

    // ── PUBLIC: landing page (top of funnel) — no auth. ──
    if ((url.pathname === "/" || url.pathname === "/join") && req.method === "GET") {
      const TS_KEY = env.TURNSTILE_SITEKEY || "";   // when set, renders the bot-check widget on signup
      const tsScript = TS_KEY ? '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>' : '';
      const tsWidget = TS_KEY ? `<div class="cf-turnstile" data-sitekey="${TS_KEY}" style="margin:8px auto"></div>` : '';
      const html = `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">
<title>${safeHtmlEscape(BRAND)} — your AI operating brain</title>${tsScript}<style>
body{font-family:system-ui,sans-serif;background:#0b0b0f;color:#eee;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center}
.card{max-width:520px;padding:40px;text-align:center}h1{font-size:2rem;margin:.2em 0}p{color:#aaa;line-height:1.5}
input,button{font-size:1rem;padding:12px 14px;border-radius:10px;border:1px solid #333;margin:6px}
input{background:#15151c;color:#fff;width:60%}button{background:#5b8cff;color:#fff;border:0;cursor:pointer;font-weight:600}
#out{margin-top:18px;text-align:left;background:#15151c;padding:14px;border-radius:10px;display:none;white-space:pre-wrap;font-size:.85rem}
small{color:#777}</style></head><body><div class=card>
<h1>${safeHtmlEscape(BRAND)}</h1><p>Your AI operating brain — runs your ops, agents, and automations. <b>Free to start.</b> Add TMMT tokens to unlock premium models &amp; agents.</p>
<div><input id=email type=email placeholder="you@email.com"><button id=goBtn>Get free access</button></div>
${tsWidget}
<div id=out></div><small>Free tier runs on our edge AI. No card required.</small>
<script>let SEC='';
function el(t,attrs,kids){const n=document.createElement(t);if(attrs)for(const k in attrs)n.setAttribute(k,attrs[k]);if(kids)for(const c of kids)n.appendChild(typeof c==='string'?document.createTextNode(c):c);return n;}
async function go(){const e=document.getElementById('email').value;const o=document.getElementById('out');o.style.display='block';o.textContent='Creating your free account…';
const tk=(window.turnstile&&turnstile.getResponse)?turnstile.getResponse():'';
const r=await fetch('/signup',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email:e,turnstile:tk})});const d=await r.json();
o.textContent='';
if(d.secret){SEC=d.secret;
o.appendChild(document.createTextNode('✅ You\\'re in! Save your key:'));o.appendChild(el('br'));
const code=el('code',{style:'color:#5b8cff'},[d.secret]);o.appendChild(code);o.appendChild(el('br'));o.appendChild(el('br'));
o.appendChild(document.createTextNode('Unlock premium models + agents with TMMT tokens:'));o.appendChild(el('br'));
for(const p of ['starter','pro','scale']){const b=el('button',null,['Card '+({starter:'$25',pro:'$100',scale:'$500'})[p]]);b.onclick=()=>buy(p);o.appendChild(b);o.appendChild(document.createTextNode(' '));}
o.appendChild(el('br'));const cb=el('button',null,['₿ Pay with crypto']);cb.onclick=()=>buyCrypto('pro');o.appendChild(cb);
} else { o.textContent='Error: '+(d.error||'try again'); } }
document.getElementById('goBtn').addEventListener('click',go);
async function buy(p){const r=await fetch('/buy',{method:'POST',headers:{'content-type':'application/json','x-aixmos-auth':SEC},body:JSON.stringify({pack:p})});const d=await r.json();if(d.url){location.href=d.url;}else{alert(d.error||'card payments not live yet — use crypto or contact us');}}
async function buyCrypto(p){const r=await fetch('/pay/crypto',{method:'POST',headers:{'content-type':'application/json','x-aixmos-auth':SEC},body:JSON.stringify({pack:p})});const d=await r.json();if(d.url){location.href=d.url;}else{alert(d.error||'crypto not live yet');}}</script>
</div></body></html>`;
      return new Response(html, { headers: htmlHeaders() });
    }

    // ── /me : customer portal — log in with key, see TMMT tokens + agents, chat, buy more. ──
    if (url.pathname === "/me" && req.method === "GET") {
      const html = `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">
<title>${safeHtmlEscape(BRAND)}</title><style>
body{font-family:system-ui,sans-serif;background:#0b0b0f;color:#eee;margin:0;padding:20px;max-width:640px;margin:auto}
h2{margin:.2em 0}.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;background:#15151c;padding:12px;border-radius:12px;margin:12px 0}
.pill{background:#1f1f2b;padding:6px 12px;border-radius:20px;font-size:.85rem}.pill b{color:#5b8cff}
input,select,textarea,button{font-size:1rem;padding:11px;border-radius:10px;border:1px solid #333;background:#15151c;color:#fff;box-sizing:border-box}
textarea{width:100%;min-height:80px}button{background:#5b8cff;border:0;font-weight:700;cursor:pointer}
#chat{background:#15151c;border-radius:12px;padding:14px;margin:12px 0;white-space:pre-wrap;min-height:60px}
.row{display:flex;gap:8px;margin:8px 0}small{color:#777}.buy button{margin:4px}</style></head>
<body><h2>${safeHtmlEscape(BRAND)}</h2>
<div class=bar><input id=key type=password placeholder="your access key" style="flex:1"><button id=connectBtn>Connect</button></div>
<div id=panel style=display:none>
 <div class=bar><span class=pill>TMMT tokens: <b id=tok>–</b></span><span class=pill>Model: <b id=tier>–</b></span><span class=pill>Agents: <b id=agents>–</b></span></div>
 <div class=row><select id=agent style="flex:1"></select></div>
 <textarea id=prompt placeholder="Ask AIXMOS…"></textarea>
 <div class=row><button id=sendBtn style="flex:1">Send</button></div>
 <div id=chat>Connect and ask anything. Free runs on edge AI; premium agents use TMMT tokens.</div>
 <div class=buy><small>Need more tokens?</small><br>
  <button data-pack=starter>Card $25</button><button data-pack=pro>Card $100</button><button data-pack=scale>Card $500</button>
  <button id=cryptoBtn>₿ Crypto</button></div>
</div>
<script>
// Customer key uses sessionStorage (clears on tab close) instead of
// localStorage so a phishing/XSS in another tab can't steal it across
// sessions. Lower convenience, much lower blast radius if any future
// pages on the same origin pick up an inline-script issue.
let K=sessionStorage.getItem('aixkey')||'';
if(K){document.getElementById('key').value=K;login();}
async function api(path,opt){opt=opt||{};opt.headers=Object.assign({'x-aixmos-auth':K,'content-type':'application/json'},opt.headers||{});return (await fetch(path,opt)).json();}
async function login(){K=document.getElementById('key').value;sessionStorage.setItem('aixkey',K);const w=await api('/wallet');if(w.name===undefined){alert('invalid key');return;}
document.getElementById('panel').style.display='block';document.getElementById('tok').textContent=w.tmmt_tokens_left??'free';document.getElementById('tier').textContent=w.plan_model_ceiling;
const ag=Array.isArray(w.agents_unlocked)?w.agents_unlocked:[];
document.getElementById('agents').textContent=ag.length?ag.join(', '):'tmmt-brain';
const sel=document.getElementById('agent');
while(sel.firstChild)sel.removeChild(sel.firstChild);
const autoOpt=document.createElement('option');autoOpt.value='';autoOpt.textContent='auto';sel.appendChild(autoOpt);
for(const a of ag){const o=document.createElement('option');o.value=a;o.textContent=a;sel.appendChild(o);}}
async function send(){const p=document.getElementById('prompt').value;const c=document.getElementById('chat');c.textContent='…';
const body={prompt:p};const a=document.getElementById('agent').value;if(a)body.agent=a;
const d=await api('/',{method:'POST',body:JSON.stringify(body)});
c.textContent=(d.text)||(d.content&&d.content[0]&&d.content[0].text)||(d.error||JSON.stringify(d));
const w=await api('/wallet');document.getElementById('tok').textContent=w.tmmt_tokens_left??'free';}
async function buy(p){const d=await api('/buy',{method:'POST',body:JSON.stringify({pack:p})});if(d.url)location.href=d.url;else alert(d.error||'card not live yet — try crypto');}
async function buyCrypto(p){const d=await api('/pay/crypto',{method:'POST',body:JSON.stringify({pack:p})});if(d.url)location.href=d.url;else alert(d.error||'crypto not live yet');}
document.getElementById('connectBtn').addEventListener('click',login);
document.getElementById('sendBtn').addEventListener('click',send);
for(const b of document.querySelectorAll('button[data-pack]'))b.addEventListener('click',()=>buy(b.dataset.pack));
document.getElementById('cryptoBtn').addEventListener('click',()=>buyCrypto('pro'));
</script>
</body></html>`;
      return new Response(html, { headers: htmlHeaders() });
    }

    // ── ADMIN console (phone-friendly): load TMMT tokens after ANY payment. Needs your admin key (entered here). ──
    if (url.pathname === "/admin" && req.method === "GET") {
      const html = `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">
<title>${safeHtmlEscape(BRAND)} — Load Tokens</title><style>
body{font-family:system-ui,sans-serif;background:#0b0b0f;color:#eee;margin:0;padding:24px;max-width:460px;margin:auto}
h2{margin-top:0}label{display:block;margin:14px 0 4px;color:#aaa;font-size:.85rem}
input,select,button{width:100%;font-size:1rem;padding:12px;border-radius:10px;border:1px solid #333;background:#15151c;color:#fff;box-sizing:border-box}
button{background:#5b8cff;border:0;font-weight:700;margin-top:18px;cursor:pointer}#msg{margin-top:14px;white-space:pre-wrap}small{color:#777}</style></head>
<body><h2>${safeHtmlEscape(BRAND)} · Load Tokens</h2><small>After a Zelle/CashApp/PayPal/crypto/cash payment, load the customer's TMMT tokens.</small>
<label>Your admin key (NOT remembered — enter each session)</label><input id=adm type=password placeholder="admin secret">
<label>Customer email</label><input id=email type=email placeholder="customer@email.com">
<label>TMMT tokens to add</label><input id=tok type=number value=3000>
<label>Unlock model up to</label><select id=tier><option>free</option><option>haiku</option><option selected>sonnet</option><option>opus</option></select>
<button id=loadBtn>Load tokens</button><div id=msg></div>
<script>
// Admin key was previously cached in localStorage. That made an XSS
// anywhere on this origin a one-shot admin theft. Now: admin enters
// the key every session. sessionStorage would survive page reloads
// within the tab, but for the admin console the safer default is no
// persistence at all.
async function load(){const adm=document.getElementById('adm').value;
const m=document.getElementById('msg');m.textContent='Loading…';
const r=await fetch('/admin/topup',{method:'POST',headers:{'content-type':'application/json','x-aixmos-auth':adm},
body:JSON.stringify({email:document.getElementById('email').value,tokens:parseInt(document.getElementById('tok').value),maxTier:document.getElementById('tier').value})});
const d=await r.json();m.textContent=d.ok?('✅ Loaded. New balance: '+d.wallet+' tokens'):('❌ '+(d.error||'failed — check admin key / that the customer signed up'));}
document.getElementById('loadBtn').addEventListener('click',load);
</script>
</body></html>`;
      return new Response(html, { headers: htmlHeaders() });
    }

    // ── /founder : your business at a glance (page prompts admin key, reads /founder/data). ──
    if (url.pathname === "/founder" && req.method === "GET") {
      const html = `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">
<title>${safeHtmlEscape(BRAND)} · Founder</title><style>
body{font-family:system-ui,sans-serif;background:#0b0b0f;color:#eee;margin:0;padding:22px;max-width:640px;margin:auto}
h2{margin:.2em 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}
.kpi{background:#15151c;border-radius:14px;padding:18px}.kpi b{font-size:1.8rem;color:#5b8cff;display:block}.kpi span{color:#aaa;font-size:.8rem}
input,button{font-size:1rem;padding:11px;border-radius:10px;border:1px solid #333;background:#15151c;color:#fff}
button{background:#5b8cff;border:0;font-weight:700;cursor:pointer}#ag{background:#15151c;border-radius:14px;padding:14px;margin-top:12px}</style></head>
<body><h2>${safeHtmlEscape(BRAND)} · Founder</h2>
<div><input id=adm type=password placeholder="admin key (enter each session)" style="width:60%"><button id=viewBtn>View</button></div>
<div id=dash style=display:none><div class=grid>
<div class=kpi><b id=signups>–</b><span>Free signups</span></div>
<div class=kpi><b id=cust>–</b><span>Accounts</span></div>
<div class=kpi><b id=tok>–</b><span>TMMT tokens sold</span></div>
<div class=kpi><b id=calls>–</b><span>Premium calls</span></div></div>
<div id=ag></div></div>
<script>
async function go(){const a=document.getElementById('adm').value;
const r=await fetch('/founder/data',{headers:{'x-aixmos-auth':a}});if(!r.ok){alert('bad admin key');return;}const d=await r.json();
document.getElementById('dash').style.display='block';
document.getElementById('signups').textContent=d.signups;
document.getElementById('cust').textContent=d.customers;
document.getElementById('tok').textContent=Number(d.tmmt_tokens_sold||0).toLocaleString();
document.getElementById('calls').textContent=d.paid_calls;
const e=Object.entries(d.agents_used||{}).sort((a,b)=>b[1]-a[1]);
const wrap=document.getElementById('ag');
while(wrap.firstChild)wrap.removeChild(wrap.firstChild);
const h=document.createElement('b');h.textContent='Top agents/models';wrap.appendChild(h);wrap.appendChild(document.createElement('br'));
if(e.length){
  for(const [name,n] of e){
    // textContent (not innerHTML) — the agent name was historically a server-
    // recorded label that we now sanitize at write time, but defense in depth
    // says never trust the rendering side either.
    const row=document.createElement('div');row.textContent=name+': '+n;wrap.appendChild(row);
  }
}else{wrap.appendChild(document.createTextNode('none yet'));}}
document.getElementById('viewBtn').addEventListener('click',go);
</script></body></html>`;
      return new Response(html, { headers: htmlHeaders() });
    }

    // ── PUBLIC: self-serve free signup — issues a free account on the spot. ──
    if (url.pathname === "/signup" && req.method === "POST") {
      const b = await req.json().catch(() => ({}));
      const email = (b.email || "").toString().slice(0, 120);
      if (!email || !email.includes("@")) return Response.json({ error: "valid email required" }, { status: 400 });
      const ip = req.headers.get("cf-connecting-ip") || "unknown";
      // BOT GUARD: Cloudflare Turnstile (free). Activates when you set TURNSTILE_SECRET (+ TURNSTILE_SITEKEY
      // makes the widget render). Until then signup still works, protected by the per-IP + global caps below.
      if (env.TURNSTILE_SECRET) {
        const tv = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
          method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: (b.turnstile || "").toString(), remoteip: ip }),
        }).then(r => r.json()).catch(() => ({ success: false }));
        if (!tv.success) return Response.json({ error: "bot check failed — refresh and try again" }, { status: 403 });
      }
      // ABUSE GUARD: per-IP daily cap stops one network flooding fake accounts (each costs you Workers-AI calls).
      const ipk = `sigip:${ip}:${new Date().toISOString().slice(0,10)}`;
      const ipc = parseInt((await env.AIXMOS_KV.get(ipk)) || "0", 10);
      if (ipc >= 10) return Response.json({ error: "too many signups from this network today" }, { status: 429 });
      await env.AIXMOS_KV.put(ipk, String(ipc + 1), { expirationTtl: 172800 });
      // light abuse guard: cap signups/day globally
      const sd = `signups:${new Date().toISOString().slice(0,10)}`;
      const sc = parseInt((await env.AIXMOS_KV.get(sd)) || "0", 10);
      if (sc > 500) return Response.json({ error: "signups paused, try later" }, { status: 429 });
      await env.AIXMOS_KV.put(sd, String(sc + 1), { expirationTtl: 172800 });
      const secret = "ax_free_" + crypto.randomUUID().replace(/-/g, "");
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(secret));
      const hash = [...new Uint8Array(buf)].map(x => x.toString(16).padStart(2, "0")).join("");
      const now = Date.now();
      const cfg = {
        name: email, brand: "free", maxTier: "free", monthly: 0,
        agents: ["tmmt-brain"], persona: `${BRAND} free assistant. Helpful, brief.`, tier: "free_signup",
        // Expiry: 90 days from issue. Renews on any token topup to 1 year out.
        // Stops a leaked/copied secret from being valid forever.
        iat: now,
        expires_at: new Date(now + FREE_EXPIRY_MS).toISOString(),
      };
      await env.AIXMOS_KV.put(`cust:${hash}`, JSON.stringify(cfg));
      await env.AIXMOS_KV.put(`wallet:${hash}`, "0");
      await env.AIXMOS_KV.put(`emailidx:${email.toLowerCase()}`, hash);   // load tokens later by email
      await bump(env, "stat:signups");
      return Response.json({ ok: true, secret, plan: "free", expires_at: cfg.expires_at, note: "Free edge AI. Buy TMMT tokens to unlock premium models + agents." });
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
      if (!(await constantEq(expected, v1))) return new Response("sig mismatch", { status: 400 });
      const event = JSON.parse(raw);
      if (event.type === "checkout.session.completed" || event.type === "payment_intent.succeeded") {
        const md = (event.data?.object?.metadata) || {};
        const tokens = parseInt(md.tokens || "0", 10);
        if (md.hash && tokens > 0) {
          await ledgerOp(env, md.hash, { op: "topup", amount: tokens });
          // optional: a pack can also raise the model ceiling/agents
          if (md.maxTier || md.agents) {
            const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${md.hash}`)) || "{}");
            if (md.maxTier && VALID_TIERS.has(md.maxTier)) c.maxTier = md.maxTier;
            if (md.agents) {
              c.agents = md.agents.split(",").map((a) => sanitizeId(a)).filter(Boolean);
            }
            // Extend expiry on every paid topup.
            c.expires_at = new Date(Date.now() + PAID_EXPIRY_MS).toISOString();
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
      const provided = req.headers.get("x-pay-secret") || "";
      if (!(await constantEq(provided, env.PAY_WEBHOOK_SECRET))) {
        return new Response("bad secret", { status: 401 });
      }
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
      // Validate maxTier against the allowlist BEFORE persisting (remote lockdown).
      if (maxTier && !VALID_TIERS.has(maxTier)) {
        return Response.json({ error: "invalid maxTier" }, { status: 400 });
      }
      // Atomic topup via the per-account Durable Object ledger (no KV race → no double-spend).
      const { balance } = await ledgerOp(env, h, { op: "topup", amount: tokens });
      await bump(env, "stat:tokens_sold", tokens);
      if (maxTier || b.agents) {
        const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${h}`)) || "{}");
        if (maxTier) c.maxTier = maxTier;
        if (b.agents) c.agents = String(b.agents).split(",").map((a) => sanitizeId(a)).filter(Boolean);
        // Extend expiry on paid topup.
        c.expires_at = new Date(Date.now() + PAID_EXPIRY_MS).toISOString();
        await env.AIXMOS_KV.put(`cust:${h}`, JSON.stringify(c));
      }
      return Response.json({ ok: true, wallet: balance });
    }

    // ── PUBLIC: Coinbase Commerce crypto webhook (HMAC over raw body w/ X-CC-Webhook-Signature). ──
    if (url.pathname === "/pay/coinbase" && req.method === "POST") {
      if (!env.COINBASE_WEBHOOK_SECRET) return new Response("not configured", { status: 503 });
      const raw = await req.text();
      const sig = req.headers.get("x-cc-webhook-signature") || "";
      const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.COINBASE_WEBHOOK_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
      const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(raw));
      const expected = [...new Uint8Array(mac)].map(x => x.toString(16).padStart(2, "0")).join("");
      if (!(await constantEq(expected, sig))) return new Response("sig mismatch", { status: 400 });
      const ev = JSON.parse(raw);
      if (ev.event?.type === "charge:confirmed" || ev.event?.type === "charge:resolved") {
        const md = ev.event?.data?.metadata || {};
        const tokens = parseInt(md.tokens || "0", 10);
        if (md.hash && tokens > 0) {
          // Atomic topup via the DO ledger (no KV race → no double-spend).
          await ledgerOp(env, md.hash, { op: "topup", amount: tokens });
          if (md.maxTier && VALID_TIERS.has(md.maxTier)) {
            const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${md.hash}`)) || "{}");
            c.maxTier = md.maxTier;
            c.expires_at = new Date(Date.now() + PAID_EXPIRY_MS).toISOString();
            await env.AIXMOS_KV.put(`cust:${md.hash}`, JSON.stringify(c));
          }
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
        const stillValid = !c.expires_at || Date.parse(c.expires_at) > Date.now();
        if (!stillValid && c.expires_at) {
          // Expired token → 401 (same status as unknown so a caller can't enumerate live vs expired).
          return new Response("Unauthorized (expired)", { status: 401 });
        }
        if (stillValid) {
          ctx = {
            name: c.name || "Customer",
            role: `cust_${sanitizeId(c.brand) || "x"}`,
            admin: false,
            maxTier: VALID_TIERS.has(c.maxTier) ? c.maxTier : "free",
            monthly: typeof c.monthly === "number" ? c.monthly : 100,
            hash,                          // ledger key: PURCHASED TMMT-token balance (DO-backed, atomic)
            agents: Array.isArray(c.agents) ? c.agents.map((a) => sanitizeId(a)).filter(Boolean) : [],
            persona: c.persona || `AIXMOS for ${c.brand || "a client"}. Brief, decisive.`,
          };
        }
      }
    }
    if (!ctx) return new Response("Unauthorized", { status: 401 });

    const month = new Date().toISOString().slice(0, 7);          // YYYY-MM (credits reset monthly)
    const day   = new Date().toISOString().slice(0, 10);

    // ── /usage : admin sees everyone's TMMT-token spend this month + remaining. ──────────
    if (url.pathname === "/usage" && ctx.admin && req.method === "GET") {
      const out = {};
      for (const [, p] of DEFS) {
        const { used } = await ledgerOp(env, `staff:${p[1]}`, { op: "used", month });
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
      // Validate maxTier against the allowlist BEFORE persisting (remote lockdown).
      if (b.maxTier && !VALID_TIERS.has(b.maxTier)) {
        return Response.json({ error: "invalid maxTier" }, { status: 400 });
      }
      // Atomic topup via the DO ledger (no KV race → no double-spend).
      const { balance } = await ledgerOp(env, h, { op: "topup", amount: add });
      await bump(env, "stat:tokens_sold", add);
      if (b.maxTier || b.agents) {
        const c = JSON.parse((await env.AIXMOS_KV.get(`cust:${h}`)) || "{}");
        if (b.maxTier) c.maxTier = b.maxTier;
        if (b.agents) {
          const incoming = Array.isArray(b.agents) ? b.agents : String(b.agents).split(",");
          c.agents = incoming.map((a) => sanitizeId(a)).filter(Boolean);
        }
        c.expires_at = new Date(Date.now() + PAID_EXPIRY_MS).toISOString();
        await env.AIXMOS_KV.put(`cust:${h}`, JSON.stringify(c));
      }
      return Response.json({ ok: true, wallet: balance });
    }

    // ── /wallet : anyone checks their plan — TMMT tokens left, model ceiling, unlocked agents. ──
    if (url.pathname === "/wallet" && req.method === "GET") {
      const tokens = ctx.hash ? (await ledgerOp(env, ctx.hash, { op: "balance" })).balance : null;
      return Response.json({ name: ctx.name, plan_model_ceiling: ctx.maxTier,
        tmmt_tokens_left: tokens, agents_unlocked: ctx.agents || [], free_lane_always: true });
    }

    // ── /founder/data : your live business numbers (admin only, JSON). ──
    if (url.pathname === "/founder/data" && req.method === "GET" && ctx.admin) {
      const g = async k => parseInt((await env.AIXMOS_KV.get(k)) || "0", 10);
      const custList = await env.AIXMOS_KV.list({ prefix: "cust:", limit: 1000 });
      const agList = await env.AIXMOS_KV.list({ prefix: "stat:agent:", limit: 100 });
      const agents = {};
      for (const k of agList.keys) {
        // Defense in depth: even though we sanitize the agent name at write
        // time, defensively re-sanitize on read so a pre-fix value already
        // sitting in KV can't ride through to the HTML dashboard.
        const clean = sanitizeId(k.name.replace("stat:agent:", ""));
        if (clean) agents[clean] = await g(k.name);
      }
      return Response.json({
        signups: await g("stat:signups"),
        tmmt_tokens_sold: await g("stat:tokens_sold"),
        paid_calls: await g("stat:paid_calls"),
        customers: custList.keys.length + (custList.list_complete ? 0 : 1000),
        agents_used: agents,
      });
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

      // Sanitize the requested agent name BEFORE any use — defense against the
      // XSS-into-founder-dashboard chain (used here for gating and below for the stat key).
      const requestedAgent = sanitizeId(incoming.agent || "");
      // Agent gating FIRST (before any debit): requested agent must be unlocked by this tier.
      if (requestedAgent && ctx.hash && ctx.agents.length && !ctx.agents.includes(requestedAgent))
        return Response.json({ error: `Agent not in your plan. Upgrade tier to unlock.` }, { status: 403 });

      // ACCESS GATE: free for everyone; the brain/agents cost TMMT tokens. The debit is ATOMIC
      // via the per-account Durable Object (no KV race → no double-spend, no quota bypass).
      //  - Customers spend a PURCHASED wallet (persistent balance, tops up).
      //  - Staff spend a monthly allowance (auto-resets).
      // Out of tokens? DOWN-SHIFT to free (your Ollama) — the free floor is always there.
      const meter = ctx.hash || `staff:${ctx.role}`;
      let tier = want, downgraded = false, walletBal = null, staffUsed = null;
      if (tier !== "free") {
        if (ctx.hash) {                                        // customer = purchased tokens
          const res = await ledgerOp(env, meter, { op: "charge", cost: COST[tier] });
          if (res.ok) walletBal = res.balance; else { tier = "free"; downgraded = true; }
        } else {                                               // staff = monthly allowance
          const res = await ledgerOp(env, meter, { op: "allowance", cost: COST[tier], monthly: ctx.monthly, month });
          if (res.ok) staffUsed = res.used; else { tier = "free"; downgraded = true; }
        }
      }
      // (Requested-agent sanitize + gating already enforced above, before the debit, via ctx.hash.)

      // ── FREE LANE — public free tier on Cloudflare Workers AI (scales, keeps home brain private).
      //    Staff/internal can route to private Ollama by setting OLLAMA_URL (Tailscale).
      if (tier === "free") {
        // ABUSE GUARD: bound free calls PER-ACCOUNT/day (atomic; was a shared role counter before).
        const FREE_DAILY = 100;
        const cap = await ledgerOp(env, meter, { op: "freecap", day, limit: FREE_DAILY });
        if (!cap.ok)
          return Response.json({ error: "Daily free limit reached. Buy TMMT tokens to keep going." }, { status: 429 });
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
        // 2) public free tier → Cloudflare Workers AI (fall back to your Claude Haiku if it errors)
        if (env.AI) {
          try {
            const m = env.WORKERS_AI_MODEL || "@cf/meta/llama-3.1-8b-instruct";
            const a = await env.AI.run(m, { messages, max_tokens: 512 });
            if (a && a.response) return Response.json({ lane: "free", model: m, downgraded, text: a.response });
          } catch (e) { /* Workers AI unavailable on this account → fall through to Claude Haiku */ }
        }
        // fallback free brain → your own Claude Haiku (cheap; bounded by the daily free cap above) = your leash
        if (env.ANTHROPIC_KEY) {
          const r = await fetch("https://api.anthropic.com/v1/messages", {
            method: "POST",
            headers: { "x-api-key": env.ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
            body: JSON.stringify({ model: TIERS.haiku, max_tokens: 512, system: ctx.persona, messages: messages.filter((m) => m.role !== "system") }),
          });
          const j = await r.json().catch(() => ({}));
          const text = (j.content && j.content[0] && j.content[0].text) || (j.error && j.error.message) || "";
          return Response.json({ lane: "free", model: "haiku", downgraded, text }, { status: r.ok ? 200 : 502 });
        }
        return Response.json({ error: "Free lane not configured." }, { status: 503 });
      }

      // ── PAID LANE → Anthropic. TMMT tokens already debited ATOMICALLY at the access gate above. ──
      await bump(env, "stat:paid_calls");
      // Use the SANITIZED agent name (or fall back to tier) for the KV key.
      // Without this, the unsafe incoming string ends up in `stat:agent:<...>`
      // and renders into the founder dashboard.
      await bump(env, `stat:agent:${requestedAgent || tier}`);

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
      if (ctx.hash) hdrs["x-aixmos-tokens-left"] = String(walletBal);
      else { hdrs["x-aixmos-credits-used"] = String(staffUsed); hdrs["x-aixmos-credits-monthly"] = String(ctx.monthly); }
      return new Response(body, { status: r.status, headers: hdrs });
    }

    return new Response("Not found", { status: 404 });
  },
};
