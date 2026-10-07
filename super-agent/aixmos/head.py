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

Right hand (authority, attention, briefings):
GET  /api/head/mandates            every mandate + the active one + lock state
GET  /api/head/attention?status=   attention items (default open) + digest of the last 24 h
GET  /api/head/brief?kind=         morning (default) or evening, built from evidence only
GET  /api/head/outcome?id=         one action's execution state: requested/authorized/verified/executed/successful
GET  /api/head/dossier?q=&pick=    "what's happening with X": one person across CRM, GHL, inbox and audit
GET  /api/head/calendar            calendar sources (hosts only, never the secret URL), hours, inbox-watch status
GET  /api/head/calendar/free?days=&minutes=   free times from the real calendar
POST /api/head/calendar/feeds/add {url}   POST /api/head/calendar/feeds/remove {name}
POST /api/head/calendar/settings  {business_hours, min_notice_hours, ghl_calendar_id}
POST /api/head/inbox/check         read connected inboxes now (read-only) -> new attention items
POST /api/head/mandates/understand {text}   plain words -> proposed plan + questions (saves nothing)
POST /api/head/mandates/draft      {title, until, will: [kinds], ask, alert, note}   -> draft + plan (grants nothing)
POST /api/head/mandates/activate   {id}       POST /api/head/mandates/revoke {id, why}
POST /api/head/lock                {why}      POST /api/head/unlock  (this computer only)
POST /api/head/attention/ack       {id}
POST /api/head/judge               {action}   dry-run of the pre-action check, nothing runs

Everything here is local (the server binds 127.0.0.1 and _guard refuses cross-site requests). Owner decisions
(approve, autopilot, permissions, privacy, memory, mandates, lock/unlock) also need the per-launch UI token that only
the app page carries, so a script or an agent tool calling the API cannot approve its own work or grant itself a mandate.
"""
import hmac, re, secrets, time
from . import settings, store, guard, approvals, scheduler, skillkit, mandate, attention, briefing, judgment

UI_TOKEN = secrets.token_urlsafe(24)      # new every launch; injected into the app page by the server
OWNER_ONLY = {"/api/head/approvals/decide", "/api/head/approvals/retry", "/api/head/approvals/edit",
              "/api/head/approvals/decide_many", "/api/head/autopilot", "/api/head/tools/policy",
              "/api/head/models/policy", "/api/head/memory/add", "/api/head/memory/forget", "/api/head/memory/promote",
              "/api/head/mandates/draft", "/api/head/mandates/activate", "/api/head/mandates/revoke",
              "/api/head/lock", "/api/head/unlock", "/api/head/attention/ack",
              "/api/head/telegram/pair", "/api/head/telegram/revoke",
              "/api/head/calendar/feeds/add", "/api/head/calendar/feeds/remove", "/api/head/calendar/settings"}

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
    elif p == "/api/head/telegram":
        from . import telegram
        h._json(telegram.status())
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
    elif p == "/api/head/mandates":
        h._json({"items": [{**m, "plan": mandate.plan(m)} for m in mandate.items()],
                 "active": [m["id"] for m in mandate.active()], "lock": mandate.lock_state()})
    elif p == "/api/head/attention":
        st = g("status", "open")
        h._json({"items": attention.items(None if st in ("all", "") else st, int(g("limit", 100))),
                 "digest": attention.digest(time.time() - 86400), "outbox": attention.outbox()})
    elif p == "/api/head/calendar":
        from . import availability
        h._json({**availability.status(), "feeds": availability.feeds(),
                 "min_notice_hours": settings.pref("calendar_min_notice_hours"),
                 "ghl_calendar_id": settings.pref("calendar_ghl_id"),
                 "inbox_watch": store.state_get("inboxwatch", "last")})
    elif p == "/api/head/calendar/free":
        from . import availability
        h._json(availability.free_slots(days=int(g("days", 7)), minutes=int(g("minutes", 30))))
    elif p == "/api/head/dossier":
        from . import dossier
        h._json(dossier.build(g("q", ""), pick=g("pick") or None))
    elif p == "/api/head/outcome":
        from . import outcomes
        st = outcomes.state(g("id", ""))
        if not st:
            h._fail("no such action", 404)
        else:
            h._json(st)
    elif p == "/api/head/brief":
        h._json(briefing.end_of_day() if g("kind", "morning") == "evening" else briefing.morning())
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
    elif p == "/api/head/approvals/edit":
        b = h._body()
        h._json(approvals.edit(str(b.get("id") or ""), b.get("fields") or {}, by="owner"))
    elif p == "/api/head/approvals/decide_many":
        b = h._body()
        h._json({"results": approvals.decide_many(b.get("ids") or [], bool(b.get("approve")), by="owner", note=b.get("note") or "")})
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
    elif p == "/api/head/telegram/pair":
        from . import telegram
        if not telegram.configured():
            raise ValueError("add the bot token first (Integrations -> Telegram)")
        if telegram.owner():
            raise ValueError("a phone is already paired: disconnect it first")
        h._json(telegram.start_pairing())
    elif p == "/api/head/telegram/revoke":
        from . import telegram
        h._json(telegram.revoke(by="owner:desktop"))
    elif p == "/api/head/skills/reload":
        h._json({"skills": skillkit.load(force=True)})
    elif p == "/api/head/calendar/feeds/add":
        from . import availability
        h._json({"name": availability.add_feed(h._body().get("url")), "feeds": availability.feeds()})
    elif p == "/api/head/calendar/feeds/remove":
        from . import availability
        availability.remove_feed(str(h._body().get("name") or ""))
        h._json({"feeds": availability.feeds()})
    elif p == "/api/head/calendar/settings":
        from . import availability       # noqa: F401  registers the calendar prefs, or settings.update ignores them
        b, upd = h._body(), {}
        bh = b.get("business_hours")
        if isinstance(bh, dict):
            days = sorted({int(x) for x in bh.get("days", []) if str(x).isdigit() and 0 <= int(x) <= 6})
            for k in ("start", "end"):
                if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(bh.get(k) or "")):
                    raise ValueError("business hours must look like 09:00")
            if bh["start"] >= bh["end"]:
                raise ValueError("business hours must end after they start")
            upd["business_hours"] = {"days": days, "start": bh["start"], "end": bh["end"]}
        if "min_notice_hours" in b:
            upd["calendar_min_notice_hours"] = max(0.0, min(168.0, float(b["min_notice_hours"])))
        if "ghl_calendar_id" in b:
            cid = str(b["ghl_calendar_id"] or "").strip()
            if cid and not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", cid):
                raise ValueError("that doesn't look like a GoHighLevel calendar ID")
            upd["calendar_ghl_id"] = cid
        settings.update(prefs=upd)
        store.audit("calendar.settings", None, {k: v for k, v in upd.items()})
        h._json({"saved": sorted(upd)})
    elif p == "/api/head/inbox/check":
        from . import inboxwatch
        h._json(inboxwatch.check())
    elif p == "/api/head/mandates/understand":
        from . import delegate
        h._json(delegate.understand(str(h._body().get("text") or "")))
    elif p == "/api/head/mandates/draft":
        b = h._body()
        m = mandate.draft(b.get("title"), b.get("until"), will=b.get("will") or [], ask=b.get("ask"),
                          alert=b.get("alert"), note=b.get("note") or "", by="owner")
        h._json({**m, "plan": mandate.plan(m)})
    elif p == "/api/head/mandates/activate":
        h._json(mandate.activate(str(h._body().get("id") or ""), by="owner"))
    elif p == "/api/head/mandates/revoke":
        b = h._body()
        h._json(mandate.revoke(str(b.get("id") or ""), by="owner", why=b.get("why") or "revoked by the owner"))
    elif p == "/api/head/lock":
        h._json(mandate.lock(by="owner", why=h._body().get("why") or ""))
    elif p == "/api/head/unlock":
        h._json(mandate.unlock(by="owner"))
    elif p == "/api/head/attention/ack":
        h._json({"acked": attention.ack(str(h._body().get("id") or ""))})
    elif p == "/api/head/judge":
        act = dict(h._body().get("action") or {})
        act.setdefault("requested_by", "owner")      # the local, guarded desktop is the owner's own channel
        h._json(judgment.evaluate(act))
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
