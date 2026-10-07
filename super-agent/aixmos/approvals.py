"""
approvals.py -- the owner's inbox: anything that talks to a customer, posts publicly or spends money is
proposed here first and only runs after an explicit approve (or a per-skill autopilot the owner switched on).

  register(kind, fn)               an executor: fn(payload) -> result (dict or str); raises on failure
  propose(kind, title, payload, skill=, summary=, risk=, dedupe=, auto=False)
                                   -> item. auto=True executes at once ONLY if the skill's autopilot is on or an
                                   active owner mandate lists this kind (mandate.py), and AIXMOS is not locked.
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
    store.audit("approval.proposed", aid, {"kind": kind, "skill": skill, "title": title, "risk": risk})
    if auto:
        from . import mandate        # an active owner mandate counts as approval; LOCK stops both
        by = "autopilot:" + (skill or kind) if autopilot(skill, kind) else None
        mid = None if by else mandate.covers(kind, risk)
        if mid:
            by = "mandate:" + mid
        if by and not mandate.locked():
            return decide(aid, True, by=by)
    return get(aid)

def decide(aid, approve, by="owner", note=""):
    if approve:
        from . import mandate
        if mandate.locked() and by not in mandate.LOCAL_OWNER:
            raise PermissionError("AIXMOS is locked: only the owner on this computer can approve actions")
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
    from . import outcomes               # requested -> authorized -> verified -> executed -> successful
    try:
        outcomes.before(item)
        res = EXECUTORS[item["kind"]](item["payload"])
        with store.tx() as c:
            c.execute("UPDATE approvals SET status='executed', result=? WHERE id=?",
                      (json.dumps(res, ensure_ascii=False, default=str)[:4000], aid))
        store.audit("approval.executed", aid, {"kind": item["kind"]})
        outcomes.after(item, res)
    except outcomes.Blocked as e:        # an automatic approval that fails a check goes back to the owner, not to failed
        with store.tx() as c:
            c.execute("UPDATE approvals SET status='pending', decided=NULL, decided_by=NULL, note=? WHERE id=?",
                      (str(e)[:500], aid))
        store.audit("approval.held", aid, {"kind": item["kind"], "title": item.get("title"), "why": str(e)[:300]})
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

EDITABLE = ("subject", "body", "description", "text", "caption", "title")

def edit(aid, fields, by="owner"):
    """The owner rewrites a pending item's text before approving it. Only text fields, only while pending; the
    recipient, the target record and the action stay as proposed. Any card already sent for the old text (Telegram)
    no longer matches and is refused."""
    item = get(aid)
    if not item:
        raise KeyError("no such approval")
    if item["status"] != "pending":
        raise ValueError("only a waiting item can be edited (this one is %s)" % item["status"])
    p = dict(item["payload"] or {})
    changed = [k for k, v in (fields or {}).items() if k in EDITABLE and k in p and isinstance(v, str) and v != p[k]]
    if not changed:
        return item
    for k in changed:
        p[k] = fields[k][:20000]
    with store.tx() as c:
        n = c.execute("UPDATE approvals SET payload=? WHERE id=? AND status='pending'",
                      (json.dumps(p, ensure_ascii=False, default=str), aid)).rowcount
    if not n:
        raise ValueError("it was decided while you were editing")
    store.audit("approval.edited", aid, {"by": by, "fields": changed})
    return get(aid)

def decide_many(ids, approve, by="owner", note=""):
    """Approve or reject several items in one go; each runs (or not) exactly as if decided alone."""
    out = []
    for aid in list(dict.fromkeys(str(i) for i in ids or []))[:100]:
        try:
            r = decide(aid, approve, by=by, note=note)
            out.append({"id": aid, "status": r["status"], "error": r.get("error")})
        except (KeyError, PermissionError) as e:
            out.append({"id": aid, "status": "refused", "error": str(e)})
    return out

def counts():
    return {r["status"]: r["n"] for r in store.q("SELECT status, COUNT(*) AS n FROM approvals GROUP BY status")}
