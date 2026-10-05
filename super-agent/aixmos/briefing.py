"""
briefing.py -- the morning briefing and the end-of-day report, built only from evidence.

Every number comes from the audit trail (events), the approvals inbox, the scheduler, the CRM or the attention
items, and each section carries the ids it was counted from (`evidence`). If a source has nothing, the briefing
says so; it never estimates, rounds up or fills a gap with a guess.

  morning(now=None, health=True) -> {"kind": "morning", "since", "sections": {...}, "text"}
  end_of_day(now=None, health=True)
  build(kind, since, now, health)  the shared builder
"""
import time
from datetime import datetime
from . import store, approvals, scheduler, crm, attention, mandate, outcomes

def _events(kinds, since, now):
    marks = ",".join("?" * len(kinds))
    return store.q("SELECT id, ts, kind, ref FROM events WHERE kind IN (%s) AND ts>=? AND ts<? ORDER BY id" % marks,
                   list(kinds) + [since, now])

def _handled(since, now):
    """Actions AIXMOS carried out without a per-item tap: executed approvals decided by autopilot or a mandate."""
    rows = store.q("SELECT id, kind, title, decided_by FROM approvals WHERE status='executed' AND decided>=? AND decided<? "
                   "AND (decided_by LIKE 'autopilot:%' OR decided_by LIKE 'mandate:%')", (since, now))
    by_owner = store.q("SELECT id FROM approvals WHERE status='executed' AND decided>=? AND decided<? "
                       "AND decided_by NOT LIKE 'autopilot:%' AND decided_by NOT LIKE 'mandate:%'", (since, now))
    return rows, by_owner

def _today_iso(now):
    return datetime.fromtimestamp(now).strftime("%Y-%m-%d")

def build(kind, since, now, health=True):
    d = crm.all_data()
    s, ev = {}, {}
    # SINCE: what happened (evidence-backed)
    new_leads = [l for l in d["leads"] if since <= float(l.get("created") or 0) < now]
    replies = _events(["followup.replied"], since, now)
    sent = _events(["send.email"], since, now)
    failed = _events(["approval.failed", "job.failed", "send.blocked", "guard.spend_blocked"], since, now)
    handled, by_owner = _handled(since, now)
    held = _events(["approval.held"], since, now)
    s["happened"] = {"new_leads": len(new_leads), "replies": len(replies), "messages_sent": len(sent),
                     "handled_by_aixmos": len(handled), "approved_by_you": len(by_owner), "problems": len(failed),
                     "held_for_rules": len(held), "results": outcomes.summary(since, now)}
    ev["happened"] = {"new_leads": [l["id"] for l in new_leads], "replies": [e["id"] for e in replies],
                      "messages_sent": [e["id"] for e in sent], "handled_by_aixmos": [r["id"] for r in handled],
                      "approved_by_you": [r["id"] for r in by_owner], "problems": [e["id"] for e in failed],
                      "held_for_rules": [e["ref"] for e in held]}
    # TODAY / NEXT: what is scheduled
    day = _today_iso(now if kind == "morning" else now + 86400)
    appts = [a for a in d["appointments"] if a.get("status") == "booked" and str(a.get("when", "")).startswith(day)]
    undated = [a for a in d["appointments"] if a.get("status") == "booked" and not str(a.get("when", ""))[:4].isdigit()]
    due = [st for st in crm.due_steps()] if kind == "morning" else []
    end_of_day = datetime.fromtimestamp(now).replace(hour=23, minute=59, second=59).timestamp()
    jobs = [j for j in scheduler.jobs("pending", 500) if j["due"] <= end_of_day + (86400 if kind != "morning" else 0)
            and not str(j.get("dedupe") or "").startswith("trigger:")]
    s["schedule"] = {"day": day, "appointments": [{"when": a["when"], "name": a.get("name") or a.get("contact"),
                                                   "service": a.get("service")} for a in appts],
                     "appointments_time_unclear": len(undated), "follow_ups_due": len(due), "scheduled_work": len(jobs)}
    ev["schedule"] = {"appointments": [a["id"] for a in appts], "follow_ups_due": [x["seq"] for x in due],
                      "scheduled_work": [j["id"] for j in jobs]}
    # NEEDS YOU
    pend = approvals.pending(50)
    decisions = attention.items("open", 50, min_level="decision")
    decisions = [i for i in decisions if i["kind"] != "approval.pending"]       # approvals are listed once, above
    top = (pend[-1]["title"] if pend else None) or (decisions[0]["title"] if decisions else None)
    s["needs_you"] = {"approvals": len(pend), "approval_titles": [p["title"] for p in pend[:5]],
                      "decisions": [i["title"] for i in decisions[:5]], "top": top}
    ev["needs_you"] = {"approvals": [p["id"] for p in pend], "decisions": [i["id"] for i in decisions]}
    s["waited"] = attention.digest(since, now)["counts"]
    # AUTHORITY + HEALTH
    act = mandate.active(now)
    s["authority"] = {"locked": mandate.locked(), "mandate": ({"title": act[0]["title"], "until": act[0]["until"]}
                                                              if act else None)}
    if health:
        h = {"failed_jobs": scheduler.counts().get("failed", 0), "failed_actions": approvals.counts().get("failed", 0)}
        try:
            from . import skillkit
            h["connectors"] = {k: v["ok"] for k, v in skillkit.connectors().items()}
        except Exception as e:
            h["connectors_error"] = str(e)[:120]
        s["health"] = h
    return {"kind": kind, "since": since, "now": now, "sections": s, "evidence": ev, "text": render(kind, s, now)}

def morning(now=None, health=True):
    now = float(now if now is not None else time.time())
    last = store.state_get("briefing", "last_morning")
    since = float(last) if last and now - float(last) < 3 * 86400 else now - 86400
    return build("morning", since, now, health)

def end_of_day(now=None, health=True):
    now = float(now if now is not None else time.time())
    start = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return build("evening", start, now, health)

def _n(v, one, many):
    return "%d %s" % (v, one if v == 1 else many)

def render(kind, s, now):
    h, sc, nd, au = s["happened"], s["schedule"], s["needs_you"], s["authority"]
    L = ["GOOD MORNING." if kind == "morning" else "END OF DAY.", ""]
    if au["locked"]:
        L += ["AIXMOS IS LOCKED: nothing runs on its own until you unlock it on your computer.", ""]
    L.append("SINCE YESTERDAY:" if kind == "morning" else "TODAY:")
    lines = [(h["new_leads"], "new lead", "new leads"), (h["replies"], "reply", "replies"),
             (h["messages_sent"], "message accepted by your mail provider", "messages accepted by your mail provider"), (h["approved_by_you"], "action you approved", "actions you approved")]
    got = ["  %s" % _n(v, a, b) for v, a, b in lines if v]
    L += got or ["  Nothing new recorded."]
    if h["problems"]:
        L.append("  %s (see Activity)" % _n(h["problems"], "problem", "problems"))
    if h["results"]["successful"]:
        L.append("  %s confirmed done" % _n(h["results"]["successful"], "action", "actions"))
    if h["held_for_rules"]:
        L.append("  I held %s back for you: %s your business rules." % (
            _n(h["held_for_rules"], "automatic message", "automatic messages"),
            "it broke" if h["held_for_rules"] == 1 else "they broke"))
    if h["handled_by_aixmos"]:
        L.append("  I handled %s under your standing permissions." % _n(h["handled_by_aixmos"], "routine action", "routine actions"))
    L += ["", ("TODAY (%s):" if kind == "morning" else "TOMORROW (%s):") % sc["day"]]
    plan = ["  %s %s%s" % (a["when"][11:16] or a["when"], a["name"] or "appointment", (" - " + a["service"]) if a.get("service") else "")
            for a in sc["appointments"]]
    if sc["follow_ups_due"]:
        plan.append("  %s due" % _n(sc["follow_ups_due"], "follow-up", "follow-ups"))
    if sc["appointments_time_unclear"]:
        plan.append("  %s booked without a clear date" % _n(sc["appointments_time_unclear"], "appointment", "appointments"))
    L += plan or ["  Nothing on the books."]
    L += ["", "NEEDS YOU:"]
    need = (["  %s waiting for your OK" % _n(nd["approvals"], "item", "items")] if nd["approvals"] else []) + \
           ["  " + t for t in nd["decisions"]]
    L += need or ["  Nothing. You're clear."]
    if nd["top"]:
        L += ["", "Most important: %s" % nd["top"]]
    if au["mandate"]:
        L += ["", "Away-mandate active until %s." % datetime.fromtimestamp(au["mandate"]["until"]).strftime("%a %H:%M")]
    hl = s.get("health")
    if hl:
        down = [k for k, ok in (hl.get("connectors") or {}).items() if not ok]
        bad = hl["failed_jobs"] + hl["failed_actions"]
        L += ["", "SYSTEM: " + ("all good" if not bad else "%s need a look" % _n(bad, "failed task", "failed tasks"))
              + ("" if not down else "; not set up: " + ", ".join(down))]
    return "\n".join(L)
