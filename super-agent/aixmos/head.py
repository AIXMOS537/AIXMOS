"""
head.py -- HTTP surface + boot for the head agent (skills, approvals inbox, scheduler, guard).

GET  /api/head                     overview: skills catalog, connectors, inbox + job counts, guard status
GET  /api/head/approvals?status=   inbox items (default: pending; status=all for every item)
GET  /api/head/jobs?status=        scheduled work
GET  /api/head/events?kind=        audit trail
GET  /api/head/contacts            opt-outs / do-not-contact
GET  /api/head/skill?id=           one skill with its live status and full guide
GET  /api/head/tools               every tool: risk, approval mode, limits      GET /api/head/models  providers + policy
GET  /api/head/memory?q=           remembered items with provenance             GET /api/head/machine RAM / model fit
POST /api/head/approvals/decide    {id, approve, note}
POST /api/head/approvals/retry     {id}
POST /api/head/optout              {contact, reason}       POST /api/head/optin {contact, source}
POST /api/head/autopilot           {skill, kinds: [..] | true | false}
POST /api/head/skills/reload
POST /api/head/tools/policy        {tool, mode: AUTO|SESSION|ALWAYS|BLOCKED|""}
POST /api/head/models/policy       {privacy_mode, cloud_allowed, prefer_cloud}
POST /api/head/memory/add|forget|promote   {text, klass, scope} | {id}

Everything here is local (the server binds 127.0.0.1 and _guard refuses cross-site requests). Owner decisions
(approve, autopilot, permissions, privacy, memory) also need the per-launch UI token that only the app page carries,
so a script or an agent tool calling the API cannot approve its own work.
"""
import hmac, secrets
from . import settings, store, guard, approvals, scheduler, skillkit

UI_TOKEN = secrets.token_urlsafe(24)      # new every launch; injected into the app page by the server
OWNER_ONLY = {"/api/head/approvals/decide", "/api/head/approvals/retry", "/api/head/autopilot", "/api/head/tools/policy",
              "/api/head/models/policy", "/api/head/memory/add", "/api/head/memory/forget", "/api/head/memory/promote"}

def ui_ok(h):
    hdrs = getattr(h, "headers", None)
    got = (hdrs.get("X-AIXMOS-UI") if hdrs is not None else "") or ""
    return hmac.compare_digest(str(got), UI_TOKEN)

def overview():
    return {"skills": skillkit.catalog(), "connectors": skillkit.connectors(),
            "approvals": {"counts": approvals.counts(), "pending": approvals.pending(20)},
            "jobs": {"counts": scheduler.counts(), "next": scheduler.jobs("pending", 10)},
            "guard": guard.status()}

def route_get(h, p, g):
    if p == "/api/head":
        h._json(overview())
    elif p == "/api/head/approvals":
        st = g("status", "pending")
        h._json({"items": approvals.items(None if st in ("all", "") else st, int(g("limit", 100)), g("skill") or None),
                 "counts": approvals.counts()})
    elif p == "/api/head/jobs":
        h._json({"items": scheduler.jobs(g("status") or None, int(g("limit", 100))), "counts": scheduler.counts()})
    elif p == "/api/head/events":
        h._json({"items": store.events(int(g("limit", 100)), g("kind") or None)})
    elif p == "/api/head/contacts":
        h._json({"items": guard.contacts()})
    elif p == "/api/head/tools":
        from . import agent
        h._json({"tools": agent.tool_table(), "modes": ["AUTO", "SESSION", "ALWAYS", "BLOCKED"]})
    elif p == "/api/head/models":
        from . import providers
        h._json(providers.status(fresh=g("fresh") == "1"))
    elif p == "/api/head/memory":
        from . import memory_store
        q = g("q", "")
        h._json({"items": memory_store.relevant(q, limit=100) if q else memory_store.recall("", limit=200),
                 "stats": memory_store.stats()})
    elif p == "/api/head/machine":
        from . import resources, providers
        snap = resources.snapshot()
        m = providers.pick_model(providers.get("ollama"))
        h._json({"snapshot": snap, "default_model": m, "admission": {k: v for k, v in resources.admit(m, snap).items() if k != "snapshot"}})
    elif p == "/api/head/skill":
        sid = g("id", "")
        sk = next((s for s in skillkit.catalog() if s["id"] == sid), None)
        if not sk:
            h._fail("no such skill", 404)
        else:
            h._json({**sk, "guide": skillkit.guide(sid)})
    else:
        return False
    return True

def route_post(h, p):
    if p in OWNER_ONLY and not ui_ok(h):
        try:
            h._body()                    # drain it: an unread body would corrupt the next request on this connection
        except Exception:
            pass
        store.audit("owner_action.refused", p, {"why": "missing app token"})
        h._fail("only the owner can do this, from the AIXMOS app", 403)
        return True
    if p == "/api/head/approvals/decide":
        b = h._body()
        h._json(approvals.decide(str(b.get("id") or ""), bool(b.get("approve")), by="owner", note=b.get("note") or ""))
    elif p == "/api/head/approvals/retry":
        h._json(approvals.retry(str(h._body().get("id") or "")))
    elif p == "/api/head/optout":
        b = h._body()
        h._json({"contact": guard.opt_out(b.get("contact"), reason=b.get("reason") or "", source="owner")})
    elif p == "/api/head/optin":
        b = h._body()
        h._json({"contact": guard.opt_in(b.get("contact"), source=b.get("source") or "owner")})
    elif p == "/api/head/autopilot":
        b = h._body()
        sid, kinds = str(b.get("skill") or ""), b.get("kinds")
        if not skillkit.get(sid):
            raise ValueError("unknown skill")
        ap = dict(settings.pref("autopilot") or {})
        if kinds in (False, None, [], ""):
            ap.pop(sid, None)
        else:
            ap[sid] = True if kinds is True else [str(k) for k in kinds]
        settings.update(prefs={"autopilot": ap})
        store.audit("autopilot.set", sid, {"kinds": ap.get(sid)})
        h._json({"autopilot": ap})
    elif p == "/api/head/tools/policy":
        from . import registry
        b = h._body()
        tool, mode = str(b.get("tool") or ""), str(b.get("mode") or "").upper()
        from . import agent
        if not agent._tool(tool):
            raise ValueError("unknown tool")
        if mode and mode not in registry.MODES:
            raise ValueError("mode must be one of " + ", ".join(registry.MODES))
        pol = dict(settings.pref("tool_policy") or {})
        if mode:
            pol[tool] = mode
        else:
            pol.pop(tool, None)
        settings.update(prefs={"tool_policy": pol})
        store.audit("tool_policy.set", tool, {"mode": mode or "default"})
        h._json({"tool_policy": pol})
    elif p == "/api/head/models/policy":
        from . import providers
        b, upd = h._body(), {}
        if b.get("privacy_mode") in providers.PRIVACY_MODES:
            upd["privacy_mode"] = b["privacy_mode"]
        for k in ("cloud_allowed", "prefer_cloud"):
            if k in b:
                upd[k] = bool(b[k])
        settings.update(prefs=upd)
        providers.forget_health()
        store.audit("model_policy.set", None, upd)
        h._json(providers.policy())
    elif p == "/api/head/memory/add":
        from . import memory_store
        b = h._body()
        klass = str(b.get("klass") or "USER_STATEMENT").upper()
        if klass not in ("USER_STATEMENT", "PREFERENCE", "DECISION", "PROCEDURE", "VERIFIED_FACT"):
            raise ValueError("unknown memory kind")
        rid = memory_store.remember(str(b.get("text") or "").strip() or _no_text(), klass, origin="user", source="owner (app)",
                                    topic=str(b.get("topic") or ""), scope="CLOUD_OK" if b.get("scope") == "CLOUD_OK" else "LOCAL_ONLY")
        store.audit("memory.add", rid, {"klass": klass})
        h._json({"id": rid})
    elif p == "/api/head/memory/forget":
        from . import memory_store
        rid = int(h._body().get("id") or 0)
        memory_store.forget(rid); store.audit("memory.forget", rid)
        h._json({"forgotten": rid})
    elif p == "/api/head/memory/promote":
        from . import memory_store
        rid = int(h._body().get("id") or 0)
        memory_store.promote(rid, "customer"); store.audit("memory.promote", rid)
        h._json({"confirmed": rid})
    elif p == "/api/head/skills/reload":
        h._json({"skills": skillkit.load(force=True)})
    else:
        return False
    return True

def _no_text():
    raise ValueError("text is required")

def boot(interval=30):
    """Load built-in skills, put their timers on the schedule, start the scheduler loop."""
    try:
        cat = skillkit.load()
        skillkit.ensure_triggers()
        scheduler.start(interval)
        bad = [s["id"] for s in cat if s.get("state") == "error"]
        print("  Skills  ->  %d built-in%s" % (len(cat) - len(bad), (" (failed: %s)" % ", ".join(bad)) if bad else ""))
    except Exception as e:
        print("  Skills  ->  head agent boot failed (%s)" % e)
