"""
guard.py -- the rails every outbound message and every paid call passes through.

Contact policy
  normalize(contact)           -> "mailto:a@b.c" / "tel:+15551234567" / "" (one key per person)
  opt_out(contact, ...)        -> record an opt-out (STOP reply, unsubscribe, owner action); permanent until opt_in
  blocked(contact)             -> reason string when the contact must not be messaged, else None
  is_stop(text)                -> True when an inbound reply is an opt-out (STOP, UNSUBSCRIBE, ...)
Sending
  check_send(channel, contact) -> Decision(ok, reason, retry_at): opt-out / do-not-contact, quiet hours,
                                  daily caps per channel and per contact
  record_send(...)             -> ledger row used by the caps
Spending
  charge(provider, op, ...)    -> logs the estimated cost of a paid API call; raises SpendBlocked when an
                                  automated caller would pass the owner's daily budget (prefs spend_daily_usd)

Nothing here sends or spends by itself. Prices are conservative estimates, not invoices.
"""
import re, time
from datetime import datetime, timedelta
from . import store, settings

STOP_WORDS = {"stop", "stopall", "stop all", "unsubscribe", "cancel", "end", "quit", "revoke", "optout",
              "opt out", "opt-out", "remove me", "do not contact", "dont contact me", "don't contact me"}

DEFAULTS = {"quiet_start": 21, "quiet_end": 8, "send_cap_email": 200, "send_cap_sms": 100,
            "send_cap_per_contact": 3, "spend_daily_usd": 2.0}

# Rough per-call cost in USD for providers that bill. Free/local engines cost 0. Unknown paid ops use FALLBACK.
PRICES = {("openai", "image"): 0.08, ("openai", "video"): 1.50, ("stability", "image"): 0.04,
          ("replicate", "image"): 0.01, ("replicate", "video"): 0.60, ("fal", "image"): 0.01, ("fal", "video"): 0.60,
          ("gemini", "image"): 0.04, ("gemini", "video"): 2.00, ("runway", "video"): 1.25, ("runway", "video_edit"): 1.25,
          ("luma", "video"): 1.00, ("google_search", "search"): 0.005, ("serpapi", "search"): 0.015,
          ("anthropic", "chat"): 0.02, ("openai", "chat"): 0.01}
FREE = {"pollinations", "duckduckgo", "ollama", "lmstudio", "local", "storyboard"}
FALLBACK = 0.25

class SpendBlocked(PermissionError):
    pass

class Decision:
    def __init__(self, ok, reason="", retry_at=None):
        self.ok, self.reason, self.retry_at = ok, reason, retry_at
    def __bool__(self):
        return self.ok
    def __repr__(self):
        return "Decision(ok=%s, reason=%r, retry_at=%r)" % (self.ok, self.reason, self.retry_at)

def _pref(name):
    v = settings.pref(name)
    return DEFAULTS.get(name) if v is None else v

# ------------------------------------------------------------ contacts ----
_EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def normalize(contact):
    c = str(contact or "").strip()
    if not c:
        return ""
    m = _EMAIL.search(c)
    if m:
        return "mailto:" + m.group(0).lower()
    digits = re.sub(r"\D", "", c)
    if len(digits) == 10:
        digits = "1" + digits
    if 11 <= len(digits) <= 15:
        return "tel:+" + digits
    return ""

def channel_of(contact):
    n = normalize(contact)
    return "email" if n.startswith("mailto:") else "sms" if n.startswith("tel:") else ""

def opt_out(contact, reason="", source="owner", kind="opt_out"):
    n = normalize(contact)
    if not n:
        raise ValueError("not a phone number or email address")
    with store.tx() as c:
        c.execute("INSERT INTO contact_policy(contact, kind, reason, source, created) VALUES (?,?,?,?,?) "
                  "ON CONFLICT(contact) DO UPDATE SET kind=excluded.kind, reason=excluded.reason, source=excluded.source",
                  (n, kind, (reason or "")[:300], source, time.time()))
    store.audit("guard.opt_out", n, {"kind": kind, "source": source, "reason": reason})
    return n

def opt_in(contact, source="owner"):
    """Only on the person's own clear request (e.g. they texted START). Never automatic."""
    n = normalize(contact)
    with store.tx() as c:
        c.execute("DELETE FROM contact_policy WHERE contact=?", (n,))
    store.audit("guard.opt_in", n, {"source": source})
    return n

def blocked(contact):
    n = normalize(contact)
    if not n:
        return "no valid phone number or email address"
    r = store.one("SELECT kind, reason FROM contact_policy WHERE contact=?", (n,))
    if r:
        return "%s%s" % ("opted out" if r["kind"] == "opt_out" else "on the do-not-contact list",
                         (": " + r["reason"]) if r.get("reason") else "")
    try:
        from . import crm            # leads marked do-not-contact in the CRM count too
        bare = n.split(":", 1)[1]
        for l in crm.list_leads("do-not-contact"):
            if normalize(l.get("contact")) == n or (bare and bare in str(l.get("contact", "")).lower()):
                return "marked do-not-contact in the CRM"
    except Exception:
        pass
    return None

def is_stop(text):
    t = re.sub(r"[^a-z' -]", " ", str(text or "").lower()).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        return False
    return t in STOP_WORDS or t.split(" ")[0] in {"stop", "stopall", "unsubscribe", "optout"}

def contacts(limit=500):
    return store.q("SELECT * FROM contact_policy ORDER BY created DESC LIMIT ?", (int(limit),))

# --------------------------------------------------------------- timing ----
def _now(now):
    return datetime.fromtimestamp(now) if isinstance(now, (int, float)) else (now or datetime.now())

def quiet(now=None):
    """Quiet hours run from quiet_start to quiet_end in the business's local time (default 21:00-08:00)."""
    h = _now(now).hour
    s, e = int(_pref("quiet_start")), int(_pref("quiet_end"))
    return (h >= s or h < e) if s > e else (s <= h < e)

def next_window(now=None):
    t = _now(now)
    if not quiet(t):
        return t.timestamp()
    e = int(_pref("quiet_end"))
    cand = t.replace(hour=e, minute=0, second=0, microsecond=0)
    if cand <= t:
        cand += timedelta(days=1)
    return cand.timestamp()

def _day_start(now):
    return _now(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

# -------------------------------------------------------------- sending ----
def check_send(channel, contact, now=None, respect_quiet=True):
    why = blocked(contact)
    if why:
        return Decision(False, why)
    if channel_of(contact) and channel_of(contact) != channel:
        return Decision(False, "address does not match the %s channel" % channel)
    if respect_quiet and channel == "sms" and quiet(now):
        return Decision(False, "quiet hours", next_window(now))
    start = _day_start(now)
    n = normalize(contact)
    per_channel = store.one("SELECT COUNT(*) AS n FROM sends WHERE channel=? AND ts>=?", (channel, start))["n"]
    cap = int(_pref("send_cap_" + channel) or 0)
    if cap and per_channel >= cap:
        return Decision(False, "daily %s limit reached (%d)" % (channel, cap), start + 86400 + 9 * 3600)
    per_contact = store.one("SELECT COUNT(*) AS n FROM sends WHERE contact=? AND ts>=?", (n, start))["n"]
    pcap = int(_pref("send_cap_per_contact") or 0)
    if pcap and per_contact >= pcap:
        return Decision(False, "already messaged this person %d times today" % pcap, start + 86400 + 9 * 3600)
    return Decision(True, "ok")

def record_send(channel, contact, skill="", ref=None, now=None):
    ts = now if isinstance(now, (int, float)) else time.time()
    with store.tx() as c:
        c.execute("INSERT INTO sends(ts, channel, contact, skill, ref) VALUES (?,?,?,?,?)",
                  (ts, channel, normalize(contact), skill, ref))

# ------------------------------------------------------------- spending ----
def price(provider, op, units=1):
    if provider in FREE:
        return 0.0
    return round(PRICES.get((provider, op), FALLBACK) * max(1, units), 4)

def spent_today(now=None, automated_only=False):
    sql = "SELECT COALESCE(SUM(usd), 0) AS s FROM spend WHERE ts>=?" + (" AND interactive=0" if automated_only else "")
    return round(store.one(sql, (_day_start(now),))["s"], 4)

def budget():
    return float(_pref("spend_daily_usd") or 0)

def charge(provider, op, units=1, interactive=False, ref=None, now=None):
    """Call BEFORE a paid API call. Interactive (a person clicked) is logged but never blocked;
    automated callers (agent, scheduler, MCP, /v1) are held to the daily budget."""
    usd = price(provider, op, units)
    if usd and not interactive:
        if spent_today(now, automated_only=True) + usd > budget():
            store.audit("guard.spend_blocked", provider, {"op": op, "usd": usd, "budget": budget()})
            raise SpendBlocked("daily automatic spend budget ($%.2f) would be passed by %s %s (~$%.2f); "
                               "raise it in Settings or run it yourself" % (budget(), provider, op, usd))
    if usd:
        with store.tx() as c:
            c.execute("INSERT INTO spend(ts, provider, op, usd, interactive, ref) VALUES (?,?,?,?,?,?)",
                      (now if isinstance(now, (int, float)) else time.time(), provider, op, usd, 1 if interactive else 0, ref))
    return usd

def status(now=None):
    return {"quiet_now": quiet(now), "next_window": next_window(now), "spent_today": spent_today(now),
            "spent_today_automatic": spent_today(now, automated_only=True), "budget": budget(),
            "opted_out": store.one("SELECT COUNT(*) AS n FROM contact_policy")["n"],
            "caps": {k: _pref(k) for k in ("send_cap_email", "send_cap_sms", "send_cap_per_contact")},
            "quiet_hours": [int(_pref("quiet_start")), int(_pref("quiet_end"))]}
