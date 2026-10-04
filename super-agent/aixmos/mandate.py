"""
mandate.py -- delegated authority with an end date ("I'm away until Monday. Keep things moving.").

A mandate is a written, time-boxed grant the OWNER switches on. It never gives AIXMOS a capability it does not
already have: it only lets the approval-inbox actions the owner listed run without a tap per item, until it ends.

  draft(title, until, will=[kinds], ask=[..], alert=[..], note="", by="agent", now=None)
                       -> mandate in status 'draft'. Nothing is covered until the owner activates it.
  plan(m)              -> the WHILE YOU'RE AWAY text: what AIXMOS will do / ask first / alert at once
  activate(id, by)     owner channels only (LOCAL_OWNER + "owner:telegram" once paired) -> 'active'
  revoke(id, by, why)  -> 'revoked' (immediate)
  covers(kind, risk)   -> id of the active mandate that lets this inbox item run now, else None
  alerting(category)   -> True when an active mandate asked for an immediate alert on this category
  active(now) / items(limit) / get(id)
  lock(by, why) / unlock(by) / locked() -> LOCK AIXMOS: every active mandate is revoked and nothing runs
                       automatically (autopilot included) until the owner unlocks from this computer.

Hard limits live in code, not in a prompt:
  - money, contracts, signatures, pricing, refunds, deletes, settings, security, credentials and mandates
    themselves are never delegable (NEVER_SEGMENTS), and neither is anything rated 'spend' or 'post';
  - at most MAX_DAYS long; a mandate cannot be extended or edited once active (revoke it, draft a new one);
  - only actions with a registered executor can be listed, so a mandate can't name a power that doesn't exist;
  - unlocking never brings a revoked mandate back.
"""
import json, re, time, uuid
from datetime import datetime
from . import store, approvals

MAX_DAYS = 14
OWNER = ("owner", "owner:desktop", "owner:telegram")
LOCAL_OWNER = ("owner", "owner:desktop")
NEVER_SEGMENTS = {"payment", "pay", "money", "refund", "invoice", "charge", "contract", "sign", "signature", "price",
                  "pricing", "discount", "delete", "purge", "security", "settings", "permission", "mandate",
                  "credential", "secret", "licence", "license"}
NEVER_RISKS = ("spend", "post")

DEFAULT_ASK = ["custom pricing or discounts", "contracts or anything signed", "refunds or money", "unusual commitments",
               "sensitive customer issues"]
DEFAULT_ALERT = ["customer_issue", "security", "outage", "opportunity"]
ALERT_LABELS = {"customer_issue": "a critical customer issue", "security": "a security problem",
                "outage": "a system outage", "opportunity": "a high-value opportunity that needs your decision"}
KIND_LABELS = {"followup.email": "send the due steps of follow-up sequences you already started",
               "email.send": "send emails AIXMOS drafted for you"}

_DDL = """
CREATE TABLE IF NOT EXISTS mandates (
  id TEXT PRIMARY KEY, created REAL NOT NULL, created_by TEXT, title TEXT NOT NULL, starts REAL NOT NULL,
  until REAL NOT NULL, will TEXT NOT NULL, ask TEXT NOT NULL, alert TEXT NOT NULL, note TEXT,
  status TEXT NOT NULL DEFAULT 'draft', activated REAL, activated_by TEXT, ended REAL, ended_by TEXT, end_reason TEXT);
CREATE INDEX IF NOT EXISTS mandates_status ON mandates(status, until);
"""
_ready = set()

def ensure_table(ddl, done):
    """Create this module's tables once per database (kept out of store.SCHEMA so the rails stay untouched)."""
    if store.DB not in done:
        c = store._open()
        try:
            c.executescript(ddl)
        finally:
            c.close()
        done.add(store.DB)

def _ensure():
    ensure_table(_DDL, _ready)

def _ts(v, now):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").strip()
    if not s:
        raise ValueError("a mandate needs an end time")
    try:
        return datetime.fromisoformat(s.replace("Z", "")).timestamp()
    except ValueError:
        raise ValueError("end time must be a date like 2026-10-12T09:00")

def delegable(kind, risk="send"):
    """Why a kind can't be delegated, or '' when it can."""
    k = str(kind or "")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", k):
        return "not an action name"
    hit = NEVER_SEGMENTS.intersection(re.split(r"[._]", k))
    if hit:
        return "%s always needs your own approval" % sorted(hit)[0]
    if risk in NEVER_RISKS:
        return "anything that %s always needs your own approval" % ("spends money" if risk == "spend" else "posts publicly")
    return ""

def _row(r):
    if not r:
        return None
    for k in ("will", "ask", "alert"):
        try:
            r[k] = json.loads(r[k] or "[]")
        except ValueError:
            r[k] = []
    return r

def get(mid):
    _ensure()
    return _row(store.one("SELECT * FROM mandates WHERE id=?", (mid,)))

def items(limit=50):
    _ensure()
    _expire()
    return [_row(r) for r in store.q("SELECT * FROM mandates ORDER BY created DESC LIMIT ?", (int(limit),))]

def draft(title, until, will=(), ask=None, alert=None, note="", by="agent", now=None):
    _ensure()
    now = float(now if now is not None else time.time())
    end = _ts(until, now)
    if end <= now:
        raise ValueError("the end time has already passed")
    if end - now > MAX_DAYS * 86400:
        raise ValueError("a mandate can last at most %d days" % MAX_DAYS)
    kinds = []
    for k in will or ():
        k = str(k).strip()
        why = delegable(k)
        if why:
            raise ValueError("%s: %s" % (k, why))
        if k not in approvals.EXECUTORS:
            raise ValueError("AIXMOS has no action called %s" % k)
        if k not in kinds:
            kinds.append(k)
    alerts = [a for a in (DEFAULT_ALERT if alert is None else alert) if a in ALERT_LABELS]
    mid = uuid.uuid4().hex[:10]
    with store.tx() as c:
        c.execute("INSERT INTO mandates(id, created, created_by, title, starts, until, will, ask, alert, note, status) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?, 'draft')",
                  (mid, now, str(by)[:60], str(title or "While you're away")[:120], now, end, json.dumps(kinds),
                   json.dumps([str(a)[:120] for a in (DEFAULT_ASK if ask is None else ask)][:12]), json.dumps(alerts),
                   str(note or "")[:500]))
    store.audit("mandate.drafted", mid, {"by": by, "until": end, "will": kinds})
    return get(mid)

def plan(m):
    """The operating plan the owner reads before switching a mandate on."""
    end = datetime.fromtimestamp(m["until"]).strftime("%a %d %b %H:%M")
    will = [KIND_LABELS.get(k, k) for k in m["will"]] + ["prepare drafts and organise incoming requests (nothing sent)"]
    alert = [ALERT_LABELS[a] for a in m["alert"] if a in ALERT_LABELS]
    return {"title": m["title"], "until": m["until"], "until_text": end, "will": will, "ask": m["ask"], "alert": alert,
            "text": "WHILE YOU'RE AWAY (until %s)\n\nI WILL:\n%s\n\nI WILL ASK BEFORE:\n%s\n\nI WILL ALERT YOU AT ONCE FOR:\n%s"
                    % (end, "\n".join("  + " + w for w in will),
                       "\n".join("  - " + a for a in m["ask"]) or "  - everything else",
                       "\n".join("  ! " + a for a in alert) or "  ! nothing")}

def activate(mid, by, now=None):
    _ensure()
    if by not in OWNER:
        raise PermissionError("only the owner can switch on a mandate")
    if locked():
        raise PermissionError("AIXMOS is locked; unlock it on this computer first")
    now = float(now if now is not None else time.time())
    with store.tx() as c:
        n = c.execute("UPDATE mandates SET status='active', activated=?, activated_by=?, starts=? "
                      "WHERE id=? AND status='draft' AND until>?", (now, by, now, mid, now)).rowcount
    if not n:
        m = get(mid)
        if not m:
            raise KeyError("no such mandate")
        raise ValueError("this mandate is %s and can't be switched on" % ("expired" if m["until"] <= now else m["status"]))
    store.audit("mandate.activated", mid, {"by": by})
    return get(mid)

def revoke(mid, by="owner", why="revoked", now=None):
    _ensure()
    with store.tx() as c:
        n = c.execute("UPDATE mandates SET status='revoked', ended=?, ended_by=?, end_reason=? "
                      "WHERE id=? AND status IN ('draft','active')",
                      (float(now if now is not None else time.time()), str(by)[:60], str(why)[:200], mid)).rowcount
    if n:
        store.audit("mandate.revoked", mid, {"by": by, "why": why})
    return get(mid)

def _expire(now=None):
    now = float(now if now is not None else time.time())
    with store.tx() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM mandates WHERE status='active' AND until<=?", (now,)).fetchall()]
        for mid in ids:
            c.execute("UPDATE mandates SET status='expired', ended=?, ended_by='clock', end_reason='time is up' WHERE id=?", (now, mid))
    for mid in ids:
        store.audit("mandate.expired", mid, None)

def active(now=None):
    _ensure()
    now = float(now if now is not None else time.time())
    _expire(now)
    if locked():
        return []
    return [_row(r) for r in store.q("SELECT * FROM mandates WHERE status='active' AND starts<=? AND until>? "
                                     "ORDER BY activated", (now, now))]

def covers(kind, risk="send", now=None):
    if delegable(kind, risk):
        return None
    for m in active(now):
        if kind in m["will"]:
            return m["id"]
    return None

def alerting(category, now=None):
    return any(category in m["alert"] for m in active(now))

# ------------------------------------------------------------------ lock ----
def locked():
    return bool((store.state_get("authority", "lock") or {}).get("on"))

def lock(by="owner", why="", now=None):
    """LOCK AIXMOS. Any owner channel may lock; only this computer may unlock."""
    if by not in OWNER:
        raise PermissionError("only the owner can lock AIXMOS")
    _ensure()
    now = float(now if now is not None else time.time())
    store.state_set("authority", "lock", {"on": True, "since": now, "by": by, "why": str(why or "")[:200]})
    for r in store.q("SELECT id FROM mandates WHERE status IN ('draft','active')"):
        revoke(r["id"], by=by, why="AIXMOS locked", now=now)
    store.audit("authority.locked", by, {"why": why})
    return lock_state()

def unlock(by="owner"):
    if by not in LOCAL_OWNER:
        raise PermissionError("AIXMOS can only be unlocked on this computer")
    store.state_set("authority", "lock", {"on": False, "since": time.time(), "by": by})
    store.audit("authority.unlocked", by, None)
    return lock_state()

def lock_state():
    return store.state_get("authority", "lock") or {"on": False}
