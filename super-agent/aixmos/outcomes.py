"""
outcomes.py -- the five execution states, kept apart and never reported as each other:

  REQUESTED   an action was proposed (an approvals item exists)
  AUTHORIZED  the owner, a skill's autopilot or an owner mandate approved it
  VERIFIED    the checks that run just BEFORE it executes passed (prechecks below)
  EXECUTED    the executor returned without error: the outside system accepted the call
  SUCCESSFUL  a postcondition check confirmed the intended result actually exists

plus BLOCKED (a precheck stopped it), FAILED (the executor raised) and NOT CONFIRMED (it executed, but nothing
could confirm the result, or the check found a mismatch). An email the mail provider accepted is EXECUTED with
post="accepted": AIXMOS cannot see delivery or bounces, so it never calls that SUCCESSFUL.

  precheck(kind)(fn(item) -> (ok, detail))         extra checks for one kind ("*" = every kind)
  verifier(kind)(fn(item, result) -> (post, detail)) post: "confirmed" | "accepted" | "mismatch"
  before(item)        approvals.execute calls it first; raises Blocked when a check fails
  after(item, result) approvals.execute calls it after a clean run; never raises
  state(aid) -> {"state", "ladder", "pre", "post", "detail"}      summary(since, until) -> {state: count}

Built-in precheck for every kind whose payload carries text that goes out (body / text / message): the owner's
business rules (judgment.rule_conflicts). An item the owner approved by hand passes with the conflict noted (they
saw the text); an item approved by autopilot or a mandate is BLOCKED, so a model-written message can never slip a
price, a discount or a forbidden claim past the owner.
"""
import json, time
from . import store

PRE, POST = {}, {}
STATES = ("requested", "authorized", "verified", "executed", "successful")

class Blocked(PermissionError):
    pass

_DDL = """
CREATE TABLE IF NOT EXISTS outcomes (
  aid TEXT PRIMARY KEY, kind TEXT, pre TEXT, pre_detail TEXT, pre_ts REAL, post TEXT, post_detail TEXT, post_ts REAL);
"""
_ready = set()

def _ensure():
    from .mandate import ensure_table
    ensure_table(_DDL, _ready)

def precheck(kind):
    def deco(fn):
        PRE.setdefault(kind, []).append(fn)
        return fn
    return deco

def verifier(kind):
    def deco(fn):
        POST[kind] = fn
        return fn
    return deco

def _save(aid, kind, **cols):
    _ensure()
    keys = ["aid", "kind"] + list(cols)
    with store.tx() as c:
        c.execute("INSERT INTO outcomes(%s) VALUES (%s) ON CONFLICT(aid) DO UPDATE SET %s"
                  % (", ".join(keys), ",".join("?" * len(keys)), ", ".join("%s=excluded.%s" % (k, k) for k in cols)),
                  [aid, kind] + list(cols.values()))

def _owner_decided(item):
    from .mandate import LOCAL_OWNER, OWNER
    return (item.get("decided_by") or "") in OWNER + LOCAL_OWNER

def before(item):
    notes = []
    for fn in PRE.get("*", []) + PRE.get(item["kind"], []):
        ok, detail = fn(item)
        if not ok:
            _save(item["id"], item["kind"], pre="blocked", pre_detail=str(detail)[:500], pre_ts=time.time())
            store.audit("outcome.blocked", item["id"], {"kind": item["kind"], "why": str(detail)[:300]})
            raise Blocked("not verified: %s" % detail)
        if detail:
            notes.append(str(detail))
    _save(item["id"], item["kind"], pre="passed", pre_detail="; ".join(notes)[:500], pre_ts=time.time())

def after(item, result):
    fn = POST.get(item["kind"])
    try:
        post, detail = fn(item, result) if fn else ("unconfirmed", "no way to confirm this kind of action yet")
    except Exception as e:                       # a broken check never turns a done action into a failure
        post, detail = "unconfirmed", "the confirmation check failed: %s" % str(e)[:200]
    _save(item["id"], item["kind"], post=post, post_detail=str(detail)[:500], post_ts=time.time())
    store.audit("outcome." + post, item["id"], {"kind": item["kind"]})
    return post

def mark(aid, post, detail=""):
    """Later evidence about an executed action (e.g. a bounce notice): replaces the post state, never upgrades it to
    'confirmed' (only a verifier can do that)."""
    from . import approvals
    item = approvals.get(aid)
    if not item or post == "confirmed":
        return None
    _save(aid, item["kind"], post=post, post_detail=str(detail)[:500], post_ts=time.time())
    store.audit("outcome." + post, aid, {"kind": item["kind"], "why": str(detail)[:200]})
    return post

def state(aid):
    from . import approvals
    item = approvals.get(aid)
    if not item:
        return None
    _ensure()
    o = store.one("SELECT * FROM outcomes WHERE aid=?", (aid,)) or {}
    st = item["status"]
    ladder = {"requested": True,
              "authorized": st in ("approved", "executing", "executed", "failed") and bool(item.get("decided_by")),
              "verified": o.get("pre") == "passed",
              "executed": st == "executed",
              "successful": st == "executed" and o.get("post") == "confirmed"}
    if o.get("pre") == "blocked":
        name = "blocked"
    elif st == "failed":
        name = "failed"
    elif st == "rejected":
        name = "rejected"
    elif ladder["successful"]:
        name = "successful"
    elif ladder["executed"]:
        name = "executed" if o.get("post") == "accepted" else "not confirmed"
    else:
        name = [s for s in STATES if ladder[s]][-1]
    return {"state": name, "ladder": ladder, "pre": o.get("pre"), "post": o.get("post"),
            "detail": o.get("post_detail") or o.get("pre_detail") or item.get("error") or ""}

def summary(since, until=None):
    """Counts of what actually happened to approved actions decided in the window."""
    _ensure()
    until = float(until if until is not None else time.time())
    rows = store.q("SELECT a.status, o.pre, o.post FROM approvals a LEFT JOIN outcomes o ON o.aid=a.id "
                   "WHERE a.decided>=? AND a.decided<? AND a.status IN ('executed','failed')", (float(since), until))
    out = {"successful": 0, "accepted": 0, "unconfirmed": 0, "mismatch": 0, "blocked": 0, "failed": 0}
    for r in rows:
        if r["pre"] == "blocked":
            out["blocked"] += 1
        elif r["status"] == "failed":
            out["failed"] += 1
        elif r["post"] == "confirmed":
            out["successful"] += 1
        elif r["post"] in out:
            out[r["post"]] += 1
        else:
            out["unconfirmed"] += 1
    return out

# ---------------------------------------------------------- built-in checks ----
OUTGOING_TEXT = ("body", "text", "message", "caption")

@precheck("*")
def _business_rules(item):
    p = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    text = " ".join(str(p.get(k) or "") for k in ("subject",) + OUTGOING_TEXT).strip()
    if not text:
        return True, ""
    from .judgment import rule_conflicts
    bad = rule_conflicts(text)
    if not bad:
        return True, ""
    if _owner_decided(item):
        return True, "owner approved despite: " + "; ".join(bad)
    return False, "; ".join(bad) + " (approved automatically, so it waits for you instead)"

def _email_accepted(item, result):
    r = result if isinstance(result, dict) else {}
    if not r.get("sent_to"):
        return "mismatch", "the mail step returned no recipient"
    return "accepted", "accepted by your mail provider for %s (delivery and bounces are not visible)" % r["sent_to"]

verifier("email.send")(_email_accepted)
verifier("followup.email")(_email_accepted)
