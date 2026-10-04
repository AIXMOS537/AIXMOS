"""
head.py -- HTTP surface + boot for the head agent (skills, approvals inbox, scheduler, guard).

GET  /api/head                     overview: skills catalog, connectors, inbox + job counts, guard status
GET  /api/head/approvals?status=   inbox items (default: pending; status=all for every item)
GET  /api/head/jobs?status=        scheduled work
GET  /api/head/events?kind=        audit trail
GET  /api/head/contacts            opt-outs / do-not-contact
GET  /api/head/skill?id=           one skill with its live status and full guide
POST /api/head/approvals/decide    {id, approve, note}
POST /api/head/approvals/retry     {id}
POST /api/head/optout              {contact, reason}       POST /api/head/optin {contact, source}
POST /api/head/autopilot           {skill, kinds: [..] | true | false}
POST /api/head/skills/reload

Right hand (authority, attention, briefings):
GET  /api/head/mandates            every mandate + the active one + lock state
GET  /api/head/attention?status=   attention items (default open) + digest of the last 24 h
GET  /api/head/brief?kind=         morning (default) or evening, built from evidence only
POST /api/head/mandates/draft      {title, until, will: [kinds], ask, alert, note}   -> draft + plan (grants nothing)
POST /api/head/mandates/activate   {id}       POST /api/head/mandates/revoke {id, why}
POST /api/head/lock                {why}      POST /api/head/unlock  (this computer only)
POST /api/head/attention/ack       {id}
POST /api/head/judge               {action}   dry-run of the pre-action check, nothing runs

Everything here is local (the server binds 127.0.0.1 and _guard refuses cross-site requests).
"""
import time
from . import settings, store, guard, approvals, scheduler, skillkit, mandate, attention, briefing, judgment

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
    elif p == "/api/head/brief":
        h._json(briefing.end_of_day() if g("kind", "morning") == "evening" else briefing.morning())
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
