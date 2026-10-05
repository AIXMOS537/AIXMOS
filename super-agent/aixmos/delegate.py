"""
delegate.py -- "I'm away until Monday. Keep things moving." -> a DRAFT away-mandate the owner can switch on.

  understand(text, now=None) -> {"until", "until_text", "title", "will", "declined", "questions", "plan"}
                                pure: reads the words, saves nothing
  draft_from(text, by="agent", now=None) -> understand(...) + {"mandate": draft or None}
                                saves a draft only when nothing is unclear; it NEVER activates one

How words become authority (deterministic, no model guesses):
  - the end time must be stated ("until Monday", "till 5pm", "for 3 days", "this weekend", "until Oct 12"). No end
    time -> a question, no draft. Longer than mandate.MAX_DAYS -> a question;
  - work maps to actions AIXMOS really has (registered executors only): follow-ups -> followup.email, CRM notes /
    tasks / tags -> ghl.write, "send/reply to emails" -> email.send. "Keep things moving" = follow-ups + CRM upkeep;
  - money, pricing, contracts, refunds, publishing and deleting are named back as "still yours", never drafted;
  - anything else it can't map comes back as a question, not a guess.
"""
import re
from datetime import datetime, timedelta
from . import mandate, approvals, settings

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
UNITS = {"hour": 3600, "hr": 3600, "day": 86400, "week": 7 * 86400}

WORK = [   # (pattern, kind, label)
    (r"follow[- ]?ups?|sequences?|nudges?|chase", "followup.email", "follow-ups"),
    (r"\bcrm\b|\bnotes?\b|\btasks?\b|\btags?\b|records?|pipeline", "ghl.write", "CRM notes, tasks and tags"),
    (r"(send|answer|reply to|respond to)\s+(my\s+|the\s+)?e-?mails?", "email.send", "sending emails I drafted"),
]
ROUTINE = re.compile(r"(?i)keep (things|it|everything|the business) (moving|going|running)|handle (the )?(routine|easy|usual)"
                     r"|take care of (things|everything|the business)|run things|routine (stuff|work)")
STILL_YOURS = [
    (r"pric(e|es|ing)|discounts?|quotes?|deals?", "pricing and discounts"),
    (r"contracts?|agreements?|sign(ing|atures?)?\b|proposals?", "contracts and anything signed"),
    (r"refunds?|payments?|invoices?|pay\b|money|billing","money: payments, refunds and invoices"),
    (r"\bpost(ing)?\b|publish|social|instagram|facebook|linkedin|tiktok", "publishing posts"),
    (r"delet(e|ing)|remove contacts|purge", "deleting anything"),
]
LEADS = re.compile(r"(?i)\b(new )?leads?\b|inquir(y|ies)|enquir(y|ies)")

def _start_hour():
    try:
        return int(settings.pref("quiet_end") or 8)
    except (TypeError, ValueError):
        return 8

def _clock(s):
    """'5pm' / '5:30 pm' / '17:00' / 'noon' -> (h, m) or None."""
    s = (s or "").strip().lower()
    if s in ("noon", "midday"):
        return 12, 0
    if s == "midnight":
        return 23, 59
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return (h, mi) if h < 24 and mi < 60 else None

TIME = r"(?:\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight))?"

def parse_until(text, now):
    """End time from plain words, or None. 'until X' = start of business that day; 'through X' = end of that day."""
    t = (text or "").lower()
    m = re.search(r"\b(?:for|next|the next)\s+(\d{1,3}|a|an|one|two|three|four|five|six|seven)\s+(hours?|hrs?|days?|weeks?)\b", t)
    if m:
        n = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}.get(m.group(1))
        n = n or int(m.group(1))
        unit = m.group(2).rstrip("s")
        return now + timedelta(seconds=n * UNITS["hr" if unit == "hr" else unit])
    if re.search(r"\b(this|the|over the) weekend\b", t):
        ahead = (0 - now.weekday()) % 7 or 7
        return (now + timedelta(days=ahead)).replace(hour=_start_hour(), minute=0, second=0, microsecond=0)
    if re.search(r"\b(rest of the day|for today|until tonight|till tonight)\b", t):
        return now.replace(hour=21, minute=0, second=0, microsecond=0) if now.hour < 21 else None
    kw = r"(until|till|til|through|thru|back on|back)"       # never bare "to": "reply to 3 leads" is not a date
    m = re.search(r"\b" + kw + r"\s+(tomorrow|" + "|".join(DAYS) + r")\b" + TIME, t)
    if m:
        through = m.group(1) in ("through", "thru")
        if m.group(2) == "tomorrow":
            day = now + timedelta(days=1)
        else:
            ahead = (DAYS.index(m.group(2)) - now.weekday()) % 7 or 7
            day = now + timedelta(days=ahead)
        return _at(day, m.group(3), through)
    # a clock time before any date: "till 5pm" is today at 17:00, not the 5th
    m = re.search(r"\b(?:until|till|til)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2}|noon|midnight)\b", t)
    if m:
        hm = _clock(m.group(1))
        if hm:
            end = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            return end if end > now else end + timedelta(days=1)
    # groups: 1 keyword, 2 ISO date, 3+4 "oct 12", 5+6 "the 12th (of oct)", 7 clock
    m = re.search(r"\b" + kw + r"\s+(?:the\s+)?(?:(\d{4}-\d{2}-\d{2})|(" + "|".join(MONTHS) + r")[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?"
                  r"|(\d{1,2})(?:st|nd|rd|th)?(?!\s*(?:am|pm|:|\d))(?:\s+of\s+(" + "|".join(MONTHS) + r")[a-z]*)?)" + TIME, t)
    if m:
        through = m.group(1) in ("through", "thru")
        if m.group(2):
            day = datetime.fromisoformat(m.group(2))
        else:
            mon = m.group(3) or m.group(6)
            dnum = int(m.group(4) or m.group(5))
            month = MONTHS.index(mon) + 1 if mon else now.month
            try:
                day = now.replace(month=month, day=dnum)
            except ValueError:
                return None
            if day.date() < now.date():
                day = day.replace(year=day.year + 1) if mon else (day + timedelta(days=32)).replace(day=dnum)
        return _at(day, m.group(7), through)
    return None

def _at(day, clock, through):
    hm = _clock(clock) if clock else None
    if hm:
        return day.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
    if through:
        return day.replace(hour=23, minute=59, second=0, microsecond=0)
    return day.replace(hour=_start_hour(), minute=0, second=0, microsecond=0)

def understand(text, now=None):
    now = now if isinstance(now, datetime) else datetime.fromtimestamp(now) if now else datetime.now()
    t = str(text or "")
    low = t.lower()
    have = set(approvals.EXECUTORS)
    will, labels, questions, declined, notes = [], [], [], [], []
    for pat, kind, label in WORK:
        if re.search(pat, low) and kind not in will:
            if kind in have and not mandate.delegable(kind):
                will.append(kind); labels.append(label)
            else:
                notes.append("I can't do %s on my own yet, so I'll prepare it and hold it for you." % label)
    if ROUTINE.search(low):
        for kind, label in (("followup.email", "follow-ups"), ("ghl.write", "CRM notes, tasks and tags")):
            if kind in have and kind not in will:
                will.append(kind); labels.append(label)
    for pat, what in STILL_YOURS:
        if re.search(r"\b(" + pat + r")", low):
            declined.append(what)
    if LEADS.search(low) and not any(k.startswith("lead") for k in will):
        lead_kinds = sorted(k for k in have if k.startswith("lead.") and not mandate.delegable(k))
        if lead_kinds:
            will.extend(lead_kinds); labels.append("replies to new leads")
        else:
            notes.append("Replying to new leads on my own isn't switched on yet, so I'll draft each reply and keep it "
                         "for you to send.")
    end = parse_until(t, now)
    if end is None:
        questions.insert(0, "Until when? (for example: until Monday, till 5pm, for 3 days)")
    elif (end - now).total_seconds() > mandate.MAX_DAYS * 86400:
        questions.insert(0, "That's longer than %d days. Shall I draft it until %s instead?"
                         % (mandate.MAX_DAYS, (now + timedelta(days=mandate.MAX_DAYS)).strftime("%a %d %b")))
        end = None
    elif end <= now:
        questions.insert(0, "That time has already passed. Until when?")
        end = None
    if not will and not questions and not notes:
        questions.append("What should I keep doing while you're away? (for example: follow-ups, CRM notes and tasks)")
    out = {"until": end.timestamp() if end else None, "until_text": end.strftime("%a %d %b %H:%M") if end else "",
           "title": ("Away until %s" % end.strftime("%a %d %b")) if end else "Away", "will": will, "will_labels": labels,
           "declined": declined, "questions": questions, "notes": notes}
    if end:
        preview = {"title": out["title"], "until": out["until"], "will": will, "ask": list(mandate.DEFAULT_ASK),
                   "alert": list(mandate.DEFAULT_ALERT)}
        p = mandate.plan(preview)
        if declined:
            p["text"] += "\n\nSTILL YOURS (I won't touch these):\n" + "\n".join("  - " + d for d in declined)
        if notes:
            p["text"] += "\n\nNOTE:\n" + "\n".join("  * " + n for n in notes)
        out["plan"] = p["text"]
    return out

def draft_from(text, by="agent", now=None):
    u = understand(text, now)
    ts = now.timestamp() if isinstance(now, datetime) else now
    u["mandate"] = None
    if u["until"] and not u["questions"]:
        u["mandate"] = mandate.draft(u["title"], u["until"], will=u["will"], note=str(text or "")[:500], by=by, now=ts)
    return u
