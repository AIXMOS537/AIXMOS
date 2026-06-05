// AIXMOS Gateway — one brain, scoped access, cost-controlled.
// Holds your API key server-side. Each person/device sends a prompt + their secret.

const TIERS = {
  haiku:  "claude-haiku-4-5-20251001",  // cheapest — team + high-frequency jobs
  sonnet: "claude-sonnet-4-6",          // balanced — drafting
  opus:   "claude-opus-4-8",            // premium — your strategic work only
};

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const auth = req.headers.get("x-aixmos-auth");

    // One entry per role today; add one per PERSON later for individual revocation.
    const ROLES = {
      [env.SECRET_PERSONAL]: { role: "personal", tier: "sonnet", admin: true,  cap: 200,
        persona: "AIXMOS for Muhammad's personal life. Decisive, brief, proactive." },
      [env.SECRET_WORK]:     { role: "work",     tier: "sonnet", admin: true,  cap: 300,
        persona: "AIXMOS for Muhammad as CEO of TMMT. Systems-oriented, ops-aware, brief." },
      [env.SECRET_OP]:       { role: "operator", tier: "haiku",  admin: false, cap: 150,
        persona: "Assist a TMMT field operator: check-in/out, condition reports. No financials, CRM, or mass-send." },
      [env.SECRET_VA]:       { role: "va",       tier: "sonnet", admin: false, cap: 200,
        persona: "Assist a TMMT VA: drafting, summaries, data entry. No payroll, mass-send, or financials." },
      [env.SECRET_OFFICE]:   { role: "office",   tier: "haiku",  admin: false, cap: 100,
        persona: "AIXMOS on a shared TMMT office workstation. General ops only. No admin actions." },
    };
    const ctx = auth ? ROLES[auth] : null;
    if (!ctx) return new Response("Unauthorized", { status: 401 });

    // CONTROL: admin usage readout — GET /usage shows today's calls per role.
    if (url.pathname === "/usage" && ctx.admin && req.method === "GET") {
      const day = new Date().toISOString().slice(0, 10), out = {};
      for (const r of ["personal", "work", "operator", "va", "office"])
        out[r] = parseInt((await env.AIXMOS_KV.get(`usage:${r}:${day}`)) || "0", 10);
      return Response.json({ day, usage: out });
    }

    // Shared memory, namespaced so team roles can't read your private context.
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

    // BRAIN
    if (req.method === "POST") {
      // Cost / runaway control: per-role daily cap (approximate; free KV; auto-expires).
      const day = new Date().toISOString().slice(0, 10);
      const ukey = `usage:${ctx.role}:${day}`;
      const used = parseInt((await env.AIXMOS_KV.get(ukey)) || "0", 10);
      if (used >= ctx.cap)
        return Response.json({ error: `Daily AIXMOS limit reached for ${ctx.role}` }, { status: 429 });
      await env.AIXMOS_KV.put(ukey, String(used + 1), { expirationTtl: 172800 });

      const incoming = await req.json();
      // Admins may bump tier (e.g. opus for the brief); team is locked to its role tier.
      const tier = (ctx.admin && incoming.tier && TIERS[incoming.tier]) ? incoming.tier : ctx.tier;
      const payload = {
        model: TIERS[tier],
        max_tokens: Math.min(incoming.max_tokens || 1024, 2048),
        system: ctx.persona,
        messages: incoming.messages || [{ role: "user", content: incoming.prompt || "" }],
      };
      const r = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": env.ANTHROPIC_KEY,
          "anthropic-version": "2023-06-01",
          "content-type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json" } });
    }

    return new Response("Not found", { status: 404 });
  },
};
