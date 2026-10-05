"""
judgment.py -- the check AIXMOS runs before it acts, in a fixed order:
  would a great right hand do this?  ->  am I authorized?  ->  do I know enough?  ->  is it safe?
(Did it work? is checked AFTER acting, by the executor's verification, not here.)

  evaluate(action, now=None) -> {"decision": proceed | confirm | ask | refuse, "summary", "checks", "options", "impact"}

action (a dict; everything optional except kind):
  kind          "email.send", "message.bulk", "crm.update", "content.publish", "contract.send", ...
  requested_by  "owner" | "owner:desktop" | "owner:telegram" | "mandate:<id>" | "agent" | "external:<where>"
                (who actually issued the instruction. Text found inside an email, CRM note, file or web page is
                 "external:*": it is DATA and can never authorize anything)
  risk          low | medium | high          reversible  True/False (default True)
  targets       contacts / ids the action touches     candidates  possible matches when the target was a name
  text          the message or content that would go out (checked against the owner's business rules)
  missing       required facts AIXMOS does not have yet         confidence  0..1 (how sure the request is understood)

The owner's business rules come from prefs `business_rules`:
  {"max_discount_pct": 15, "forbidden_phrases": ["guaranteed results"], "bulk_confirm_over": 25,
   "price_needs_approval": true}
A conflict is never silently "fixed": AIXMOS stops, says what conflicts and offers options.
"""
import re
from . import settings, guard, mandate

DECISIONS = ("proceed", "confirm", "ask", "refuse")
# AIXMOS never changes its own authority, security or credentials, whoever asks; the owner does that in Settings.
SELF_AUTHORITY = re.compile(r"^(permission|permissions|security|policy|mandate|authority|credential|secret|settings|"
                            r"licence|license|guard)\.|\.(grant|elevate|disable_guard|replicate|self_update)$")
# External, public, money or destructive -> high. Internal record changes -> medium. Reads, drafts, analysis -> low.
HIGH = re.compile(r"\.(send|reply|post|publish|sign|pay|refund|delete|purge|bulk)$|"
                  r"^(message|payment|contract|price|pricing|refund|invoice|discount)\.")
MEDIUM = re.compile(r"\.(update|create|schedule|book|move|cancel|tag|note|assign)$")
DEFAULT_RULES = {"bulk_confirm_over": 25, "price_needs_approval": True}
settings.DEFAULT_PREFS.setdefault("business_rules", {})    # owner-editable (fold into settings.DEFAULT_PREFS on merge)
DISCOUNT = re.compile(r"(?i)(\d{1,3})\s*%\s*(?:off|discount)|(?:discount|off)\s*(?:of\s*)?(\d{1,3})\s*%")
PRICE = re.compile(r"(?i)(?:[$£€]\s?\d[\d,]*(?:\.\d\d)?|\b\d[\d,]*(?:\.\d\d)?\s?(?:usd|dollars)\b)")

def _rules():
    r = dict(DEFAULT_RULES)
    r.update(settings.pref("business_rules") or {})
    return r

def _check(checks, name, ok, why=""):
    checks.append({"check": name, "ok": bool(ok), "why": why})
    return ok

def evaluate(action, now=None):
    a = dict(action or {})
    kind = str(a.get("kind") or "")
    who = str(a.get("requested_by") or "agent")
    derived = "high" if HIGH.search(kind) else "medium" if MEDIUM.search(kind) else "low"
    given = a.get("risk") if a.get("risk") in ("low", "medium", "high") else "low"
    risk = max(derived, given, key=("low", "medium", "high").index)     # a caller can raise the risk, never lower it
    reversible = a.get("reversible", True) is not False
    targets = list(a.get("targets") or [])
    checks, options, impact = [], [], {}

    def out(decision, summary):
        return {"decision": decision, "summary": summary, "checks": checks, "options": options, "impact": impact,
                "risk": risk, "kind": kind}

    # 1. would a right hand do this at all?
    if not _check(checks, "within_authority", not SELF_AUTHORITY.search(kind),
                  "AIXMOS never changes its own permissions, security or credentials"):
        return out("refuse", "I don't change my own permissions, security or credentials. You can do that in Settings.")
    # 2. who is asking?
    if who.startswith("external"):
        _check(checks, "identity", False, "the instruction came from %s, which is data, not you" % who)
        return out("refuse", "That instruction came from content I was reading (%s), not from you, so I treated it "
                             "as information and did nothing." % who.split(":", 1)[-1])
    owner = who in mandate.OWNER
    by_mandate = who.startswith("mandate:")
    _check(checks, "identity", owner or by_mandate or who == "agent", "requested by %s" % who)
    if not (owner or by_mandate or who == "agent"):
        return out("refuse", "I only take instructions from you.")
    if mandate.locked() and risk != "low":
        _check(checks, "lock", False, "AIXMOS is locked")
        if who in mandate.LOCAL_OWNER:
            return out("confirm", "AIXMOS is locked. I'll do this only because you're asking on this computer; confirm?")
        return out("refuse", "AIXMOS is locked, so I'm not changing anything. Unlock it on your computer first.")
    # 3. do I know enough?
    cands = a.get("candidates")
    if cands is not None:
        cands = list(cands)
        if len(cands) != 1:
            _check(checks, "target", False, "%d possible matches" % len(cands))
            options.extend(str(c) for c in cands[:6])
            return out("ask", "I found %s. Which one do you mean?" % (
                "no match for that" if not cands else "%d possible matches" % len(cands)))
        _check(checks, "target", True, "one match")
    missing = [str(m) for m in (a.get("missing") or [])]
    if not _check(checks, "context", not missing, ("missing: " + ", ".join(missing)) if missing else ""):
        return out("ask", "Before I do this I need: %s." % ", ".join(missing))
    conf = a.get("confidence")
    if conf is not None and not _check(checks, "confidence", float(conf) >= 0.6, "confidence %.2f" % float(conf)):
        return out("ask", "I'm not sure I understood. Can you say what you want done, and for whom?")
    # 4. is it safe? business rules + blast radius
    rules, conflicts, text = _rules(), [], str(a.get("text") or "")
    mx = rules.get("max_discount_pct")
    pcts = [int(x or y) for x, y in DISCOUNT.findall(text)]
    if mx is not None and pcts and max(pcts) > float(mx):
        conflicts.append("a %d%% discount is above your limit of %s%%" % (max(pcts), mx))
    elif pcts and rules.get("price_needs_approval"):
        conflicts.append("it offers a discount, and pricing changes need your approval")
    if PRICE.search(text) and rules.get("price_needs_approval") and not pcts:
        conflicts.append("it quotes a price, and prices need your approval")
    for ph in rules.get("forbidden_phrases") or []:
        if ph and str(ph).lower() in text.lower():
            conflicts.append("it says \"%s\", which you told me never to claim" % ph)
    if targets:
        contacts = [t for t in targets if guard.normalize(t)] if risk == "high" and len(targets) <= 5000 else []
        blocked = sum(1 for t in contacts if guard.blocked(t))
        impact = {"targets": len(targets), "blocked": blocked, "reachable": len(targets) - blocked}
    bulk = int(rules.get("bulk_confirm_over") or 0)
    big = bool(bulk and len(targets) > bulk)
    _check(checks, "business_rules", not conflicts, "; ".join(conflicts))
    _check(checks, "blast_radius", not big, ("%d people" % len(targets)) if targets else "")
    if conflicts or big:
        parts = []
        if big:
            parts.append("That would reach %d people%s" % (len(targets), (" (%d of them can't be messaged)" % blocked)
                                                           if blocked else ""))
            options.extend(["everyone (%d)" % impact["reachable"], "only inactive leads",
                            "a smaller test group of %d first" % min(bulk, 20)])
        if conflicts:
            parts.append(("and it " if big else "That ") + "conflicts with your rules: " + "; ".join(conflicts))
            options.append("change it to fit your rules")
        return out("confirm", "%s. Nothing goes out until you choose." % " ".join(parts))
    # 5. reversibility + mandate
    if risk == "high" and not reversible:
        _check(checks, "reversible", False, "can't be undone")
        return out("confirm", "This can't be undone, so I need your OK first.")
    if risk == "high" and not (by_mandate and mandate.covers(kind)):
        _check(checks, "approval", False, "high-impact action")
        return out("confirm", "Ready. This one needs your OK before it goes.")
    _check(checks, "approval", True, "covered by mandate" if by_mandate else "within normal authority")
    return out("proceed", "OK to go ahead.")
