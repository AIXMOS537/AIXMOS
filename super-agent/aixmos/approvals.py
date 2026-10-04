"""
approvals.py -- the owner's inbox: anything that talks to a customer, posts publicly or spends money is
proposed here first and only runs after an explicit approve (or a per-skill autopilot the owner switched on).

  register(kind, fn)               an executor: fn(payload) -> result (dict or str); raises on failure
  propose(kind, title, payload, skill=, summary=, risk=, dedupe=, auto=False)
                                   -> item. auto=True executes at once ONLY if the skill's autopilot is on.
  decide(id, approve, by=, note=)  approve -> runs the executor once; reject -> never runs
  pending() / items(status) / get(id)

Executions are idempotent: an item moves approved -> executing -> executed|failed exactly once.
"""
import json, time, uuid
from . import store, settings

EXECUTORS = {}
RISKS = ("send", "post", "spend", "change", "info")

def register(kind, fn):
    EXECUTORS[kind] = fn
    return fn

def executor(kind):
    def deco(fn):
        return register(kind, fn)
    return deco

def _row(r):
    if not r:
        return None
    for k in ("payload", "result"):
        if r.get(k):
            try:
                r[k] = json.loads(r[k])
            except ValueError:
                pass
    return r

def get(aid):
    return _row(store.one("SELECT * FROM approvals WHERE id=?", (aid,)))

def items(status=None, limit=100, skill=None):
    sql, args = "SELECT * FROM approvals", []
    conds = []
    if status:
        conds.append("status=?"); args.append(status)
    if skill:
        conds.append("skill=?"); args.append(skill)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY created DESC LIMIT ?"
    args.append(int(limit))
    return [_row(r) for r in store.q(sql, args)]

def pending(limit=100):
    return items("pending", limit)

def autopilot(skill, kind=None):
    """Autopilot is OFF unless the owner turned it on for this skill (prefs autopilot = {skill: [kinds] | true})."""
    ap = settings.pref("autopilot") or {}
    v = ap.get(skill) if isinstance(ap, dict) else None
    return bool(v is True or (isinstance(v, list) and kind in v))

def propose(kind, title, payload, skill="", summary="", risk="send", dedupe=None, auto=False):
    if kind not in EXECUTORS:
        raise ValueError("no executor registered for %r" % kind)
    if risk not in RISKS:
        raise ValueError("risk must be one of %s" % ", ".join(RISKS))
    if dedupe:
        old = store.one("SELECT id FROM approvals WHERE dedupe=?", (dedupe,))
        if old:
            return get(old["id"])
    aid = uuid.uuid4().hex[:12]
    with store.tx() as c:
        c.execute("INSERT INTO approvals(id, created, kind, skill, title, summary, payload, risk, status, dedupe) "
                  "VALUES (?,?,?,?,?,?,?,?, 'pending', ?)",
                  (aid, time.time(), kind, skill, str(title)[:200], str(summary or "")[:2000],
                   json.dumps(payload, ensure_ascii=False, default=str), risk, dedupe))
    store.audit("approval.proposed", aid, {"kind": kind, "skill": skill, "title": title})
    if auto and autopilot(skill, kind):
        return decide(aid, True, by="autopilot:" + (skill or kind))
    return get(aid)

def decide(aid, approve, by="owner", note=""):
    with store.tx() as c:
        n = c.execute("UPDATE approvals SET status=?, decided=?, decided_by=?, note=? WHERE id=? AND status='pending'",
                      ("approved" if approve else "rejected", time.time(), by, str(note or "")[:500], aid)).rowcount
    if not n:
        item = get(aid)
        if not item:
            raise KeyError("no such approval")
        return item                      # already decided: deciding twice never runs anything twice
    store.audit("approval." + ("approved" if approve else "rejected"), aid, {"by": by, "note": note})
    return execute(aid) if approve else get(aid)

def execute(aid):
    with store.tx() as c:
        n = c.execute("UPDATE approvals SET status='executing' WHERE id=? AND status='approved'", (aid,)).rowcount
    item = get(aid)
    if not n:
        return item
    try:
        res = EXECUTORS[item["kind"]](item["payload"])
        with store.tx() as c:
            c.execute("UPDATE approvals SET status='executed', result=? WHERE id=?",
                      (json.dumps(res, ensure_ascii=False, default=str)[:4000], aid))
        store.audit("approval.executed", aid, {"kind": item["kind"]})
    except Exception as e:
        with store.tx() as c:
            c.execute("UPDATE approvals SET status='failed', error=? WHERE id=?", ((str(e) or type(e).__name__)[:1000], aid))
        store.audit("approval.failed", aid, {"kind": item["kind"], "error": str(e)[:300]})
    return get(aid)

def retry(aid, by="owner"):
    """A failed item can be put back in front of the owner; it never re-runs on its own."""
    with store.tx() as c:
        c.execute("UPDATE approvals SET status='pending', error=NULL WHERE id=? AND status='failed'", (aid,))
    store.audit("approval.retry", aid, {"by": by})
    return get(aid)

def counts():
    return {r["status"]: r["n"] for r in store.q("SELECT status, COUNT(*) AS n FROM approvals GROUP BY status")}
