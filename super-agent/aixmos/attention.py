"""
attention.py -- protects the owner's attention. Everything AIXMOS notices becomes one item with a level; only a few
ever interrupt, the rest wait for the digest / briefing.

Levels (low -> high): background, routine, important, decision (owner decision required), urgent.

  observe(kind, title, detail=, source=, ref=, category=, level=, dedupe=, now=)  -> item
          the same dedupe key never makes a second item: it bumps `count` (no notification storms)
  classify(kind, category, text, source)      -> level
  resolve(dedupe=None, id=None, why=)         an item that no longer needs anyone (cancels a queued interrupt)
  ack(id)                                      the owner has seen it
  outbox() / delivered(id, channel)            interrupts waiting for a channel (desktop, Telegram) to deliver
  digest(since, now)                           what waited: counts per level + the top items
  sweep(now)                                   the observation loop: reads new audit events and turns the ones
                                               that matter into items (approvals waiting, failures, replies ...)

Who may raise what:
  - the level comes from the event KIND, which only AIXMOS's own code writes. The owner can re-rank kinds
    (prefs attention_rules = {kind: level});
  - external content (a lead's message, an email, a web page) can raise an item to 'important' at most, never
    to 'urgent'. A stranger writing "URGENT" cannot page the owner at 3 a.m., and content never grants authority.
Interrupt policy (configurable): urgent always; decision outside quiet hours; important only when an active
mandate asked for alerts on its category; at most one interrupt per kind per attention_kind_minutes (60) and
attention_max_per_hour (4) overall. Everything else is held for the digest.
"""
import json, re, time, uuid
from . import store, settings, guard

LEVELS = ("background", "routine", "important", "decision", "urgent")
RANK = {l: i for i, l in enumerate(LEVELS)}
DEFAULTS = {"attention_max_per_hour": 4, "attention_kind_minutes": 60, "attention_rules": {}}
for _k, _v in DEFAULTS.items():          # owner-editable prefs (fold into settings.DEFAULT_PREFS on merge)
    settings.DEFAULT_PREFS.setdefault(_k, _v)

KIND_LEVELS = {
    "approval.pending": "decision", "mandate.ending": "important",
    "action.failed": "important", "job.failed": "important", "system.error": "important",
    "spend.blocked": "important", "lead.reply": "important", "lead.new": "routine",
    "customer.message": "routine", "send.blocked": "routine", "brief.ready": "routine",
    "security.alert": "urgent", "system.outage": "urgent",
    "email.unknown": "background", "email.automated": "background", "send.bounced": "important",
    "contact.opted_out": "routine",
}
KIND_CATEGORY = {"security.alert": "security", "system.outage": "outage", "system.error": "outage",
                 "lead.reply": "opportunity"}
# Words in untrusted content that make an item worth a look sooner. They can raise to 'important', no further.
CONTENT_FLAGS = re.compile(r"(?i)\b(refund|chargeback|lawyer|attorney|legal action|sue|complain(t|ing)?|furious|angry|"
                           r"cancel(l?ed|ling)? (my|the) (order|contract|service|booking)|emergency|injur(y|ed))\b")

_DDL = """
CREATE TABLE IF NOT EXISTS attention (
  id TEXT PRIMARY KEY, ts REAL NOT NULL, first_ts REAL NOT NULL, kind TEXT NOT NULL, category TEXT, level TEXT NOT NULL,
  title TEXT NOT NULL, detail TEXT, source TEXT, ref TEXT, dedupe TEXT UNIQUE, count INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'open', interrupt TEXT NOT NULL DEFAULT 'none', interrupt_ts REAL, channel TEXT);
CREATE INDEX IF NOT EXISTS attention_open ON attention(status, ts);
CREATE INDEX IF NOT EXISTS attention_interrupt ON attention(interrupt, interrupt_ts);
"""
_ready = set()

def _ensure():
    from .mandate import ensure_table
    ensure_table(_DDL, _ready)

def _pref(name):
    v = settings.pref(name)
    return DEFAULTS.get(name) if v is None else v

def _row(r):
    return dict(r) if r else None

def get(iid):
    _ensure()
    return _row(store.one("SELECT * FROM attention WHERE id=?", (iid,)))

def classify(kind, category=None, text="", source="system"):
    rules = settings.pref("attention_rules") or {}
    lvl = rules.get(kind) if isinstance(rules, dict) and rules.get(kind) in RANK else KIND_LEVELS.get(kind, "routine")
    if text and CONTENT_FLAGS.search(str(text)) and RANK[lvl] < RANK["important"]:
        lvl = "important"                # content may raise to important, never higher
    return lvl

def _interrupt_for(item, now):
    lvl, cat = item["level"], item.get("category")
    if lvl == "urgent":
        return "queued"
    from . import mandate
    wanted = lvl == "decision" or (lvl == "important" and cat and mandate.alerting(cat, now))
    if not wanted or guard.quiet(now):
        return "none" if not wanted else "held"
    since_kind = now - 60 * float(_pref("attention_kind_minutes"))
    same = store.one("SELECT COUNT(*) AS n FROM attention WHERE kind=? AND id<>? AND interrupt IN ('queued','delivered') "
                     "AND interrupt_ts>=?", (item["kind"], item["id"], since_kind))["n"]
    total = store.one("SELECT COUNT(*) AS n FROM attention WHERE interrupt IN ('queued','delivered') AND interrupt_ts>=?",
                      (now - 3600,))["n"]
    return "held" if same or total >= int(_pref("attention_max_per_hour")) else "queued"

def observe(kind, title, detail="", source="system", ref=None, category=None, level=None, dedupe=None, now=None,
            push=False):
    """Record something AIXMOS noticed. `level` may only be passed by AIXMOS's own code; content-derived calls pass
    the text as `detail` and let classify() decide. push=True (own code only) delivers something the owner scheduled,
    such as the morning briefing, regardless of quiet hours and caps."""
    _ensure()
    now = float(now if now is not None else time.time())
    trusted = not str(source or "").startswith("external")
    lvl = level if (level in RANK and trusted) else classify(kind, category, detail, source)
    if not trusted and RANK[lvl] > RANK["important"]:
        lvl = "important"                # content-borne items never page the owner
    cat = category or KIND_CATEGORY.get(kind) or ("customer_issue" if CONTENT_FLAGS.search(str(detail or "")) else None)
    if dedupe:
        old = store.one("SELECT * FROM attention WHERE dedupe=?", (dedupe,))
        if old:
            with store.tx() as c:
                c.execute("UPDATE attention SET ts=?, count=count+1 WHERE id=?", (now, old["id"]))
            return get(old["id"])
    iid = uuid.uuid4().hex[:12]
    with store.tx() as c:
        c.execute("INSERT INTO attention(id, ts, first_ts, kind, category, level, title, detail, source, ref, dedupe) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (iid, now, now, kind, cat, lvl, str(title)[:200], str(detail or "")[:1000], str(source)[:60], ref, dedupe))
    item = get(iid)
    how = "queued" if (push and trusted) else _interrupt_for(item, now)
    if how != "none":
        with store.tx() as c:
            c.execute("UPDATE attention SET interrupt=?, interrupt_ts=? WHERE id=?", (how, now if how == "queued" else None, iid))
    return get(iid)

def resolve(dedupe=None, iid=None, why="done"):
    _ensure()
    key, val = ("dedupe", dedupe) if dedupe else ("id", iid)
    with store.tx() as c:
        n = c.execute("UPDATE attention SET status='resolved', detail=COALESCE(detail,'') || ? , "
                      "interrupt=CASE interrupt WHEN 'queued' THEN 'cancelled' WHEN 'held' THEN 'cancelled' ELSE interrupt END "
                      "WHERE %s=? AND status<>'resolved'" % key, ("\n[resolved: %s]" % str(why)[:80], val)).rowcount
    return n

def ack(iid):
    _ensure()
    with store.tx() as c:
        return c.execute("UPDATE attention SET status='seen' WHERE id=? AND status='open'", (iid,)).rowcount

def items(status="open", limit=100, min_level=None):
    _ensure()
    rows = store.q("SELECT * FROM attention" + (" WHERE status=?" if status else "") + " ORDER BY ts DESC LIMIT ?",
                   ((status, int(limit)) if status else (int(limit),)))
    if min_level:
        rows = [r for r in rows if RANK[r["level"]] >= RANK[min_level]]
    return rows

def outbox(limit=20):
    _ensure()
    return store.q("SELECT * FROM attention WHERE interrupt='queued' ORDER BY interrupt_ts LIMIT ?", (int(limit),))

def delivered(iid, channel):
    _ensure()
    with store.tx() as c:
        return c.execute("UPDATE attention SET interrupt='delivered', channel=? WHERE id=? AND interrupt='queued'",
                         (str(channel)[:30], iid)).rowcount

def digest(since, now=None):
    """What waited for the owner since `since`: open items per level, highest first, plus counts."""
    _ensure()
    rows = store.q("SELECT * FROM attention WHERE ts>=? AND status IN ('open','seen') ORDER BY ts DESC", (float(since),))
    out = {"since": since, "counts": {l: 0 for l in LEVELS}, "top": {}}
    for r in rows:
        out["counts"][r["level"]] += 1
        if r["level"] != "background":
            out["top"].setdefault(r["level"], [])
            if len(out["top"][r["level"]]) < 5:
                out["top"][r["level"]].append({"id": r["id"], "title": r["title"], "count": r["count"], "kind": r["kind"]})
    return out

# ------------------------------------------------------- observation loop ----
def _detail(ev):
    try:
        return json.loads(ev.get("detail") or "{}")
    except ValueError:
        return {}

def _on_event(ev):
    k, ref, d = ev["kind"], ev.get("ref"), _detail(ev)
    if k == "approval.proposed":
        observe("approval.pending", "Waiting for your OK: %s" % (d.get("title") or d.get("kind") or "an action"),
                ref=ref, dedupe="approval:%s" % ref, category="approval")
    elif k in ("approval.approved", "approval.rejected", "approval.executed"):
        if k != "approval.approved" or not str(d.get("by") or "").startswith(("autopilot:", "mandate:")):
            resolve(dedupe="held:%s" % ref, why=k.split(".")[1])   # an automatic approve may still be held
        resolve(dedupe="approval:%s" % ref, why=k.split(".")[1])
    elif k == "approval.held":
        observe("approval.pending", "Held for you: %s (%s)" % (d.get("title") or d.get("kind") or "an action",
                                                               (d.get("why") or "")[:140]),
                ref=ref, dedupe="held:%s" % ref, category="approval")
    elif k == "approval.failed":
        observe("action.failed", "An approved %s failed: %s" % (d.get("kind") or "action", (d.get("error") or "")[:120]),
                ref=ref, dedupe="failed:%s" % ref)
    elif k == "job.failed":
        observe("job.failed", "Scheduled work stopped after retries: %s" % (d.get("action") or ""), ref=ref,
                detail=(d.get("error") or "")[:300], dedupe="job:%s" % ref)
    elif k == "followup.replied":
        observe("lead.reply", "A lead replied, follow-ups stopped. Your turn.", ref=ref, dedupe="reply:%s" % ref)
    elif k == "guard.spend_blocked":
        observe("spend.blocked", "A paid %s call was held: daily budget reached" % (d.get("op") or "API"), ref=ref,
                dedupe="spend:%s:%s" % (ref, time.strftime("%Y-%m-%d")))
    elif k == "send.blocked":
        observe("send.blocked", "A message was not sent: %s" % (d.get("reason") or ""), ref=ref,
                dedupe="blocked:%s:%s" % (ref, d.get("ref")))
    elif k == "scheduler.error":
        observe("system.error", "The scheduler hit an error", detail=str(ev.get("detail") or "")[:300],
                dedupe="sched:%s" % time.strftime("%Y-%m-%d %H"))
    elif k == "mandate.expired":
        observe("mandate.ending", "Your away-mandate ended; I'm back to asking before each send", ref=ref,
                dedupe="mandate-end:%s" % ref)

def sweep(now=None, batch=500):
    """Read audit events written since the last sweep and turn the ones that matter into attention items."""
    _ensure()
    cur = int(store.state_get("attention", "cursor", 0) or 0)
    evs = store.q("SELECT * FROM events WHERE id>? ORDER BY id LIMIT ?", (cur, int(batch)))
    for ev in evs:
        try:
            _on_event(ev)
        except Exception as e:           # one bad event never stops the loop
            store.audit("attention.error", str(ev.get("id")), str(e)[:200])
        cur = ev["id"]
    store.state_set("attention", "cursor", cur)
    return {"read": len(evs), "cursor": cur}
