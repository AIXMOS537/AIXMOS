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

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const auth = req.headers.get("x-aixmos-auth");

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
    const ctx = (typeof auth === "string" && auth.length >= 8) ? (ROLES[auth] || null) : null;
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

      // Credit check. If a paid tier would exceed the monthly allowance, DOWN-SHIFT to free
      // (your Ollama) instead of blocking — work never stops, premium just pauses.
      const used = await getUsed();
      let tier = want, downgraded = false;
      if (tier !== "free" && used + COST[tier] > ctx.monthly) {
        tier = "free"; downgraded = true;
      }

      // ── FREE LANE → your own Ollama via Cloudflare Tunnel ($0, private). ──
      if (tier === "free") {
        if (!env.OLLAMA_URL) {
          return Response.json({ error: "Free lane not configured (set OLLAMA_URL to your tunnel)." }, { status: 503 });
        }
        // ABUSE GUARD: bound free-lane calls/person/day so nobody can hammer the brain PC.
        const fKey = `free:${ctx.role}:${day}`;
        const fUsed = parseInt((await env.AIXMOS_KV.get(fKey)) || "0", 10);
        const FREE_DAILY = 500;
        if (fUsed >= FREE_DAILY)
          return Response.json({ error: `Daily free-lane limit reached for ${ctx.role}` }, { status: 429 });
        await env.AIXMOS_KV.put(fKey, String(fUsed + 1), { expirationTtl: 172800 });
        const messages = incoming.messages || [{ role: "user", content: incoming.prompt || "" }];
        const r = await fetch(`${env.OLLAMA_URL.replace(/\/$/, "")}/api/chat`, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            ...(env.OLLAMA_AUTH ? { "x-aixmos-tunnel": env.OLLAMA_AUTH } : {}),
          },
          body: JSON.stringify({
            model: env.OLLAMA_MODEL || "llama3.1",
            stream: false,
            messages: [{ role: "system", content: ctx.persona }, ...messages],
          }),
        });
        const data = await r.json().catch(() => ({}));
        const text = data?.message?.content ?? data?.response ?? "";
        return Response.json({ lane: "free", model: env.OLLAMA_MODEL || "llama3.1", downgraded, text, raw: data }, { status: r.ok ? 200 : 502 });
      }

      // ── PAID LANE → Anthropic. Debit TMMT tokens first (monthly auto-reset via TTL). ──
      await env.AIXMOS_KV.put(credKey, String(used + COST[tier]), { expirationTtl: 60 * 60 * 24 * 40 });
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
      // attach lane/credit info via headers so clients can show "X tokens left"
      return new Response(body, { status: r.status, headers: {
        "content-type": "application/json",
        "x-aixmos-lane": tier,
        "x-aixmos-credits-used": String(used + COST[tier]),
        "x-aixmos-credits-monthly": String(ctx.monthly),
      }});
    }

    return new Response("Not found", { status: 404 });
  },
};
