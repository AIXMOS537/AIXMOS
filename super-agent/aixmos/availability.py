"""
availability.py -- when the owner is actually free (calendar reading; not named calendar.py so it can never
shadow the standard library module). READ-ONLY: AIXMOS never creates, moves or deletes an event here.

Sources (any or all):
  - iCal / ICS feeds: the owner's private "secret address in iCal format" (Google Calendar), a published Outlook
    calendar, Apple / Cal.com / any CalDAV export. The URL is a password, so it lives in secret_store
    ("calendar.ics.<n>"), never in settings.json or the audit trail. Events become busy blocks.
  - GoHighLevel booking calendar (prefs calendar_ghl_id): GET /calendars/{id}/free-slots, the bookable times the
    owner configured in GHL (documented API v2; date range <= 31 days). NOT yet checked against a live calendar: the
    test sub-account has none, so status() says so.

  add_feed(url) -> name    remove_feed(name)    feeds() -> [{name, host}]      (the URL itself is never returned)
  status()                 -> {"connected", "sources", "notes"}
  busy(start, end)         -> [{"start", "end", "title", "source"}]     events that block time (cancelled/free skipped)
  agenda(day=None)         -> that day's events, sorted
  free_slots(days=7, minutes=30, limit=8, now=None) -> [{"start", "end", "text"}]   inside business hours, minus busy,
                              intersected with GHL's bookable slots when a GHL calendar is set; never in the past or
                              inside the minimum notice
  events_with(email, days=30) -> upcoming events where that address is an attendee

Business hours: prefs business_hours {"days": [0..6] (Mon=0), "start": "09:00", "end": "17:00"}, calendar_min_notice_hours
(default 2). Repeating events: DAILY / WEEKLY (BYDAY) / MONTHLY (by date) / YEARLY with INTERVAL, COUNT, UNTIL,
EXDATE and moved instances (RECURRENCE-ID). A rule it can't expand is NOT dropped silently: free_slots() reports it
in `notes`, so nobody is offered a time that might clash. All-day events count as busy unless marked free.
"""
import re, time, urllib.request, urllib.parse
from datetime import datetime, date, timedelta, timezone
from . import settings, store

DEFAULTS = {"business_hours": {"days": [0, 1, 2, 3, 4], "start": "09:00", "end": "17:00"},
            "calendar_min_notice_hours": 2, "calendar_ghl_id": ""}
for _k, _v in DEFAULTS.items():          # owner-editable (fold into settings.DEFAULT_PREFS on merge)
    settings.DEFAULT_PREFS.setdefault(_k, _v)

MAX_FEED = 5 * 1024 * 1024
CACHE_SECONDS = 300
_cache = {}                               # name -> (fetched_at, events, notes)
WIN_TZ = {"eastern standard time": "America/New_York", "central standard time": "America/Chicago",
          "mountain standard time": "America/Denver", "pacific standard time": "America/Los_Angeles",
          "gmt standard time": "Europe/London", "utc": "UTC"}

def _pref(k):
    v = settings.pref(k)
    return DEFAULTS[k] if v in (None, "") else v

# ------------------------------------------------------------------ feeds ----
def _names():
    from . import secret_store
    return sorted(n for n in secret_store.names() if n.startswith("calendar.ics."))

def feeds():
    from . import secret_store
    out = []
    for n in _names():
        u = secret_store.get(n) or ""
        out.append({"name": n, "host": urllib.parse.urlparse(u).hostname or "?"})
    return out

def add_feed(url):
    u = str(url or "").strip()
    if u.startswith("webcal://"):
        u = "https://" + u[len("webcal://"):]
    p = urllib.parse.urlparse(u)
    if p.scheme != "https" or not p.hostname:
        raise ValueError("use the https (or webcal) address of the calendar's iCal feed")
    from . import secret_store
    n = "calendar.ics.%d" % (max([int(x.rsplit(".", 1)[1]) for x in _names()] or [0]) + 1)
    secret_store.put(n, u)
    store.audit("calendar.feed_added", n, {"host": p.hostname})
    _cache.clear()
    return n

def remove_feed(name):
    from . import secret_store
    if name not in _names():
        raise KeyError("no such calendar feed")
    secret_store.delete(name)
    store.audit("calendar.feed_removed", name, None)
    _cache.clear()

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AIXMOS-calendar/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(MAX_FEED + 1)
    if len(data) > MAX_FEED:
        raise ValueError("calendar feed is larger than 5 MB")
    return data.decode("utf-8", "replace")

# ------------------------------------------------------------- ICS parsing ----
def _tz(name, notes):
    if not name:
        return None
    n = name.strip().strip('"')
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(WIN_TZ.get(n.lower(), n))
    except Exception:
        notes.add("time zone %s not known on this computer: its events are read as local time" % n)
        return None

def _dt(value, params, notes):
    """-> (datetime naive local, all_day)"""
    v = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", v):
        return datetime.strptime(v[:8], "%Y%m%d"), True
    utc = v.endswith("Z")
    d = datetime.strptime(v.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
    if utc:
        return d.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None), False
    tz = _tz(params.get("TZID"), notes)
    if tz is not None:
        return d.replace(tzinfo=tz).astimezone().replace(tzinfo=None), False
    return d, False

def _duration(v):
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", v.strip())
    if not m:
        return timedelta(0)
    w, d, h, mi, s = (int(x or 0) for x in m.groups()[1:])
    return timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)

def parse_ics(text, notes=None):
    """-> list of raw events {uid, start, end, all_day, title, attendees, rrule, exdates, recurrence_id, free}"""
    notes = notes if notes is not None else set()
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    out, ev, depth = [], None, 0
    for line in lines:
        if line == "BEGIN:VEVENT":
            ev, depth = {"attendees": [], "exdates": [], "free": False, "title": ""}, 0
            continue
        if ev is None:
            continue
        if line.startswith("BEGIN:"):
            depth += 1                      # VALARM etc.: skip its properties
            continue
        if line.startswith("END:") and line != "END:VEVENT":
            depth = max(0, depth - 1)
            continue
        if line == "END:VEVENT":
            if ev.get("start") and ev.get("status") != "CANCELLED" and not ev["free"]:
                if not ev.get("end"):
                    ev["end"] = ev["start"] + (ev.pop("dur", None) or (timedelta(days=1) if ev["all_day"] else timedelta(0)))
                out.append(ev)
            ev = None
            continue
        if depth or ":" not in line:
            continue
        head, value = line.split(":", 1)
        parts = head.split(";")
        name = parts[0].upper()
        params = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        params = {k.upper(): v for k, v in params.items()}
        try:
            if name == "DTSTART":
                ev["start"], ev["all_day"] = _dt(value, params, notes)
            elif name == "DTEND":
                ev["end"], _ = _dt(value, params, notes)
            elif name == "DURATION":
                ev["dur"] = _duration(value)
            elif name == "SUMMARY":
                ev["title"] = value.replace("\\,", ",").replace("\\;", ";").replace("\\n", " ")[:200]
            elif name == "UID":
                ev["uid"] = value
            elif name == "STATUS":
                ev["status"] = value.upper()
            elif name == "TRANSP":
                ev["free"] = value.upper() == "TRANSPARENT"
            elif name == "RRULE":
                ev["rrule"] = dict(p.split("=", 1) for p in value.split(";") if "=" in p)
            elif name == "EXDATE":
                ev["exdates"] += [_dt(x, params, notes)[0] for x in value.split(",") if x.strip()]
            elif name == "RECURRENCE-ID":
                ev["recurrence_id"] = _dt(value, params, notes)[0]
            elif name == "ATTENDEE":
                m = re.search(r"(?i)mailto:(.+)$", value)
                if m:
                    ev["attendees"].append(m.group(1).strip().lower())
        except ValueError:
            notes.add("one event had a date I couldn't read and was skipped")
    return out

DAYCODE = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

def _expand(ev, start, end, notes):
    """Instances of ev that overlap [start, end)."""
    length = ev["end"] - ev["start"]
    r = ev.get("rrule")
    if not r:
        return [(ev["start"], ev["end"])] if ev["start"] < end and ev["end"] > start else []
    freq = r.get("FREQ", "").upper()
    interval = max(1, int(r.get("INTERVAL", 1) or 1))
    count = int(r["COUNT"]) if r.get("COUNT", "").isdigit() else None
    until = None
    if r.get("UNTIL"):
        try:
            until = _dt(r["UNTIL"], {}, notes)[0]
        except ValueError:
            pass
    unsupported = [k for k in ("BYSETPOS", "BYWEEKNO", "BYYEARDAY", "BYHOUR", "BYMINUTE") if k in r] or \
                  (freq in ("MONTHLY", "YEARLY") and ("BYDAY" in r or "BYMONTHDAY" in r and "," in r["BYMONTHDAY"])) or \
                  freq not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY")
    if unsupported:
        notes.add("a repeating event (\"%s\") uses a pattern I can't expand; check those times yourself" % ev["title"][:60])
        return [(ev["start"], ev["end"])] if ev["start"] < end and ev["end"] > start else []
    byday = [DAYCODE[d[-2:]] for d in r.get("BYDAY", "").split(",") if d[-2:] in DAYCODE] if freq == "WEEKLY" else []
    out, n, cur, guard_n = [], 0, ev["start"], 0
    exd = set(ev["exdates"])

    def emit(s):
        nonlocal n
        if until and s > until:
            return False
        n += 1
        if count and n > count:
            return False
        if s not in exd and s < end and s + length > start:
            out.append((s, s + length))
        return True

    while guard_n < 5000 and cur < end:
        guard_n += 1
        if freq == "WEEKLY" and byday:
            week0 = cur - timedelta(days=cur.weekday())
            for wd in sorted(byday):
                s = week0 + timedelta(days=wd)
                if s < ev["start"]:
                    continue
                if not emit(s):
                    return out
            cur = week0 + timedelta(weeks=interval)
            cur = cur.replace(hour=ev["start"].hour, minute=ev["start"].minute, second=ev["start"].second)
            continue
        if not emit(cur):
            return out
        if freq == "DAILY":
            cur += timedelta(days=interval)
        elif freq == "WEEKLY":
            cur += timedelta(weeks=interval)
        elif freq == "MONTHLY":
            nxt = None
            for step in range(1, 13):           # skip months without that day (31st)
                yy, mm = divmod(cur.month - 1 + interval * step, 12)
                try:
                    nxt = cur.replace(year=cur.year + yy, month=mm + 1, day=ev["start"].day)
                    break
                except ValueError:
                    continue
            if nxt is None:
                return out
            cur = nxt
        else:
            try:
                cur = cur.replace(year=cur.year + interval)
            except ValueError:
                cur = cur.replace(year=cur.year + interval, day=28)
    return out

def _feed_events(name, notes):
    hit = _cache.get(name)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        notes.update(hit[2])
        return hit[1]
    from . import secret_store
    local = set()
    evs = parse_ics(_fetch(secret_store.get(name) or ""), local)
    _cache[name] = (time.time(), evs, local)
    notes.update(local)
    return evs

def busy(start, end, notes=None):
    notes = notes if notes is not None else set()
    out = []
    for name in _names():
        try:
            evs = _feed_events(name, notes)
        except Exception as e:
            notes.add("calendar %s couldn't be read (%s), so its busy times are unknown" % (name.rsplit(".", 1)[1],
                                                                                          type(e).__name__))
            continue
        moved = {(e.get("uid"), e["recurrence_id"]) for e in evs if e.get("recurrence_id")}
        for e in evs:
            if e.get("recurrence_id"):
                inst = [(e["start"], e["end"])] if e["start"] < end and e["end"] > start else []
            else:
                inst = [(s, f) for s, f in _expand(e, start, end, notes) if (e.get("uid"), s) not in moved]
            out += [{"start": s, "end": f, "title": e["title"], "source": "ical", "all_day": e["all_day"],
                     "attendees": e["attendees"]} for s, f in inst]
    return sorted(out, key=lambda x: x["start"])

# ------------------------------------------------------------------ GHL ----
def _ghl_slots(start, end, notes):
    cid = str(_pref("calendar_ghl_id") or "").strip()
    if not cid:
        return None
    try:
        from . import ghl
        if not ghl.connected():
            return None
        c = ghl.Client()
        d = c.req("GET", "/calendars/%s/free-slots" % ghl._id(cid),
                  {"startDate": int(start.timestamp() * 1000), "endDate": int(min(end, start + timedelta(days=31)).timestamp() * 1000)},
                  version=ghl.V_CALENDARS)
    except Exception as e:
        notes.add("the GoHighLevel calendar couldn't be read (%s)" % (getattr(e, "kind", None) or type(e).__name__))
        return None
    out = set()
    for k, v in (d or {}).items():
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(k)):
            continue
        for s in (v.get("slots") if isinstance(v, dict) else v) or []:
            try:
                t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
                out.add((t.astimezone().replace(tzinfo=None) if t.tzinfo else t).replace(second=0, microsecond=0))
            except ValueError:
                continue
    return out

# ------------------------------------------------------------- answers ----
def status():
    notes = []
    srcs = ["ical:%s" % f["host"] for f in feeds()]
    if str(_pref("calendar_ghl_id") or "").strip():
        srcs.append("ghl")
        notes.append("GoHighLevel free-slots is built to the documented API but not yet checked on a live calendar")
    return {"connected": bool(srcs), "sources": srcs, "notes": notes, "business_hours": _pref("business_hours")}

def connected():
    return status()["connected"]

def _hm(s):
    h, m = [int(x) for x in str(s).split(":")]
    return h, m

def agenda(day=None):
    d = day if isinstance(day, (datetime, date)) else datetime.now()
    start = datetime(d.year, d.month, d.day)
    notes = set()
    evs = busy(start, start + timedelta(days=1), notes)
    return {"day": start.strftime("%Y-%m-%d"), "events": [{"start": e["start"].strftime("%H:%M") if not e["all_day"] else "all day",
            "end": e["end"].strftime("%H:%M"), "title": e["title"]} for e in evs], "notes": sorted(notes)}

def free_slots(days=7, minutes=30, limit=8, now=None, per_day=2):
    now = now if isinstance(now, datetime) else datetime.fromtimestamp(now) if now else datetime.now()
    notes = set()
    if not connected():
        return {"slots": [], "notes": ["no calendar connected, so I can't offer times"], "connected": False}
    bh = _pref("business_hours")
    open_days = set(bh.get("days", [0, 1, 2, 3, 4]))
    (sh, sm), (eh, em) = _hm(bh.get("start", "09:00")), _hm(bh.get("end", "17:00"))
    earliest = now + timedelta(hours=float(_pref("calendar_min_notice_hours") or 0))
    horizon = now + timedelta(days=int(days))
    blocks = busy(now, horizon, notes)
    ghl = _ghl_slots(now, horizon, notes)
    step, length, out = timedelta(minutes=30), timedelta(minutes=int(minutes)), []
    day = datetime(now.year, now.month, now.day)
    while day < horizon and len(out) < limit:
        if day.weekday() in open_days:
            t, close, taken = day.replace(hour=sh, minute=sm), day.replace(hour=eh, minute=em), 0
            while t + length <= close and taken < per_day and len(out) < limit:
                ok = t >= earliest and not any(b["start"] < t + length and b["end"] > t for b in blocks)
                if ok and ghl is not None:
                    ok = t in ghl
                if ok:
                    out.append({"start": t.isoformat(timespec="minutes"), "end": (t + length).isoformat(timespec="minutes"),
                                "text": t.strftime("%a %d %b %H:%M").replace(" 0", " ")})
                    taken += 1
                    t += timedelta(hours=2)        # spread the offers out
                else:
                    t += step
        day += timedelta(days=1)
    return {"slots": out, "notes": sorted(notes) + status()["notes"], "connected": True}

def events_with(email, days=30, now=None):
    e = str(email or "").strip().lower()
    if not e:
        return []
    now = now if isinstance(now, datetime) else datetime.now()
    notes = set()
    return [{"start": x["start"].strftime("%a %d %b %H:%M"), "title": x["title"]}
            for x in busy(now, now + timedelta(days=days), notes) if e in x["attendees"]]
