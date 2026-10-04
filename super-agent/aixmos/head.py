"""
head.py -- HTTP surface + boot for the head agent (skills, approvals inbox, scheduler, guard).

GET  /api/head                     overview: skills catalog, connectors, inbox + job counts, guard status
GET  /api/head/approvals?status=   inbox items (default: pending)
GET  /api/head/jobs?status=        scheduled work
GET  /api/head/events?kind=        audit trail
GET  /api/head/contacts            opt-outs / do-not-contact
GET  /api/head/skill?id=           one skill with its live status and full guide
POST /api/head/approvals/decide    {id, approve, note}
POST /api/head/approvals/retry     {id}
POST /api/head/optout              {contact, reason}       POST /api/head/optin {contact, source}
POST /api/head/autopilot           {skill, kinds: [..] | true | false}
POST /api/head/skills/reload

Everything here is local (the server binds 127.0.0.1 and _guard refuses cross-site requests).
"""
from . import settings, store, guard, approvals, scheduler, skillkit

def overview():
    return {"skills": skillkit.catalog(), "connectors": skillkit.connectors(),
            "approvals": {"counts": approvals.counts(), "pending": approvals.pending(20)},
            "jobs": {"counts": scheduler.counts(), "next": scheduler.jobs("pending", 10)},
            "guard": guard.status()}

def route_get(h, p, g):
    if p == "/api/head":
        h._json(overview())
    elif p == "/api/head/approvals":
        h._json({"items": approvals.items(g("status", "pending") or None, int(g("limit", 100)), g("skill") or None),
                 "counts": approvals.counts()})
    elif p == "/api/head/jobs":
        h._json({"items": scheduler.jobs(g("status") or None, int(g("limit", 100))), "counts": scheduler.counts()})
    elif p == "/api/head/events":
        h._json({"items": store.events(int(g("limit", 100)), g("kind") or None)})
    elif p == "/api/head/contacts":
        h._json({"items": guard.contacts()})
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
    elif p == "/api/head/skills/reload":
        h._json({"skills": skillkit.load(force=True)})
    else:
        return False
    return True

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
