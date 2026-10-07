"""
brand.py -- the Brand Profile: the business's own facts and voice, kept apart from raw documents.

It lives in the business profile (skills.PROFILE_FIELDS, edited in Vault & Skills -> Business profile). This module
turns it into the three things every customer-facing draft needs:

  facts_text()        what a reply MAY state: services, prices, hours, area, offer, FAQ, policies, links.
                      Anything not in here is unknown -> the draft asks or says the team will confirm.
  voice_brief(query)  how it should sound: voice, preferred phrases, the owner's example messages (most relevant
                      first, within a size budget), and what it must never say
  check_reply(text)   the Verifier for outgoing text -> (ok, [problems], [notes]): problems = unsupported
                      prices/guarantees/policies (verify.grounded_reply) or the owner's "never say" lines; notes = business
                      rules the owner should see (judgment.rule_conflicts when that layer is installed)
  missing()           the key fields still empty, so AIXMOS asks the owner instead of guessing
"""
import re
from . import skills, verify

FACT_FIELDS = ("name", "type", "services", "pricing", "hours", "area", "offer", "faq", "policies", "differentiators",
               "booking_link", "website", "review_link", "phone", "email")
KEY_FIELDS = ("name", "services", "hours", "voice", "booking_link")

def profile():
    return skills.profile()

def _lines(v):
    return [x.strip(" -*\t") for x in str(v or "").splitlines() if x.strip(" -*\t")]

def facts_text(p=None):
    p = p or profile()
    return "\n".join("%s: %s" % (k.replace("_", " "), p[k]) for k in FACT_FIELDS if p.get(k))

def prohibited(p=None):
    return _lines((p or profile()).get("prohibited_claims"))

def voice_brief(query="", budget=1500, p=None):
    p = p or profile()
    parts = []
    if p.get("voice"):
        parts.append("Voice: " + p["voice"])
    if p.get("preferred_phrases"):
        parts.append("Phrases the owner likes: " + "; ".join(_lines(p["preferred_phrases"])[:12]))
    never = prohibited(p)
    if never:
        parts.append("Never say: " + "; ".join(never[:12]))
    ex = [e for e in re.split(r"\n\s*\n|\n-{3,}\n", str(p.get("examples") or "")) if e.strip()]
    if ex and query:
        words = {w for w in re.findall(r"[a-z]{4,}", query.lower())}
        ex.sort(key=lambda e: -len(words & set(re.findall(r"[a-z]{4,}", e.lower()))))
    out = "\n".join(parts)
    for e in ex:
        add = "\nExample the owner was happy with:\n" + e.strip()
        if len(out) + len(add) > budget:
            break
        out += add
    return out[:budget]

# A reply must not commit the business to a time, a slot or a delivery the owner never offered (measured 2026-10-05:
# a local model wrote "yes, we're available next Tuesday afternoon" and "I'll send an overview by end of day").
_WHEN = (r"(today|tonight|tomorrow|this (morning|afternoon|evening|week|weekend)|next (week|month|"
         r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)|(on )?(monday|tuesday|wednesday|thursday|friday|"
         r"saturday|sunday)|by (the )?end of (the )?(day|week)|within (the|an|\d+) (hour|hours|minutes|days)|"
         r"\d{1,2}(:\d\d)?\s?(am|pm))")
COMMITMENT = re.compile(r"(?i)\b(we('| a)?re (available|free|open)|we (can|will|'ll) (come|be there|do it|fit you in|have it)|"
                        r"i('| wi)?ll (send|call|get back|have|email)|we('| wi)?ll (send|call|get back|email)|"
                        r"see you|you('re| are) booked|booked (you|for))\b[^.!?\n]{0,60}\b" + _WHEN)

# A concrete slot written like "Tue 13 Oct 9:00" / "Tuesday, 13 October at 9:00". Allowed only when it is one of the
# calendar's verified free slots (availability.free_slots), never otherwise.
SLOTLIKE = re.compile(r"(?i)\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+(\d{1,2})\s+([a-z]{3})[a-z]*\.?,?\s+(?:at\s+)?(\d{1,2}:\d\d)\b")

def _slot_key(m):
    return (int(m.group(2)), m.group(3).lower(), m.group(4).lstrip("0") or "0")

def slot_problems(text, slots=None):
    """-> (problems, offered_verified). Every concrete day+time in the text must be a verified free slot."""
    allowed = set()
    for s in slots or []:
        m = SLOTLIKE.search(str(s.get("text") if isinstance(s, dict) else s))
        if m:
            allowed.add(_slot_key(m))
    probs, ok = [], False
    for m in SLOTLIKE.finditer(text or ""):
        if _slot_key(m) in allowed:
            ok = True
        else:
            probs.append("offers a time that is not a free slot in your calendar (\"%s\")" % m.group(0))
    return probs, ok

def check_reply(text, p=None, slots=None):
    """-> (ok, problems, notes). problems = the draft must be rewritten (invented claims, banned phrases).
    notes = it may go to the owner, flagged (business rules such as "prices need your approval")."""
    p = p or profile()
    ok, probs = verify.grounded_reply(text, facts_text(p))
    low = (text or "").lower()
    for line in prohibited(p):
        if line.lower() in low:
            probs.append("uses a phrase the owner never wants: %s" % line)
    sp, offered = slot_problems(text, slots)
    probs += sp
    m = COMMITMENT.search(text or "")
    if m and not (offered and not sp):            # offering verified free slots is fine; anything else is a promise
        probs.append("promises a time or delivery nobody offered (\"%s\"): offer the booking link or say the team "
                     "will confirm" % m.group(0)[:60])
    notes = []
    try:
        from .judgment import rule_conflicts
        notes = list(rule_conflicts(text or ""))
    except ImportError:
        pass
    return not probs, probs, notes

def missing(p=None):
    p = p or profile()
    return [k for k in KEY_FIELDS if not p.get(k)]
