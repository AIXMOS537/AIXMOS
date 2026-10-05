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

def check_reply(text, p=None):
    """-> (ok, problems, notes). problems = the draft must be rewritten (invented claims, banned phrases).
    notes = it may go to the owner, flagged (business rules such as "prices need your approval")."""
    p = p or profile()
    ok, probs = verify.grounded_reply(text, facts_text(p))
    low = (text or "").lower()
    for line in prohibited(p):
        if line.lower() in low:
            probs.append("uses a phrase the owner never wants: %s" % line)
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
