"""
verify.py -- the Verifier: model output is never accepted as truth. Check it against an output contract first.

accept(output, contract) -> (accepted, [problems], parsed)
contract keys (all optional):
  format          "json" -> output must parse (code fences allowed)
  required_keys   keys the JSON object must have
  min_items       {key: n} lists that need at least n items
  claim_terms     words that are claims about the business (pricing, insurance, guarantee ...): a reply may use one
                  only when the business's own facts contain it
  _facts          the business's facts as text (profile, brand profile, CRM record) used for grounding
  must_not_contain / must_not_match   forbidden text / regexes
  max_chars       length cap (default 20000)

Ported from the private line (provisioner/agents.accept). The rule it enforces: a model may not invent offerings,
prices, policies or guarantees. Missing facts are a question for the owner, not a guess.
"""
import json, re

# Claims a lead reply must never make unless the business's own facts say so.
CLAIM_TERMS = ("$", "price", "pricing", "discount", "% off", "for free", "free of charge", "guarantee", "warranty", "refund",
               "insurance", "insured", "licensed", "certified", "same day", "same-day", "24/7", "in stock", "deposit",
               "financing", "promotion", "coupon")

def _items(parsed, contract):
    out = []
    if isinstance(parsed, dict):
        for k in contract.get("min_items") or {}:
            out += [x for x in (parsed.get(k) or []) if isinstance(x, dict)]
    return out

def accept(output, contract):
    probs, parsed = [], None
    text = output or ""
    if contract.get("format") == "json":
        try:
            parsed = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()))
        except ValueError:
            return False, ["output is not valid JSON"], None
        for k in contract.get("required_keys", []):
            if not isinstance(parsed, dict) or k not in parsed:
                probs.append("missing key: " + k)
        for k, n in (contract.get("min_items") or {}).items():
            v = parsed.get(k) if isinstance(parsed, dict) else None
            if not isinstance(v, list) or len(v) < n:
                probs.append("%s needs at least %d items" % (k, n))
    facts = (contract.get("_facts") or "").lower()
    items = _items(parsed, contract)
    answers = [str(x.get("a", "")) for x in items] if items else ([text] if contract.get("format") != "json" else [])
    for term in contract.get("claim_terms", []):
        for a in answers:
            if term in a.lower() and term not in facts:
                probs.append("unsupported claim about '%s' (not in the business's facts)" % term)
                break
    for a in answers:
        if re.match(r"(?i)^\s*yes\b", a) and not any(w in facts for w in re.findall(r"[a-z]{5,}", a.lower())[1:]):
            probs.append("unsupported yes-claim: " + a[:60])
    norm = [re.sub(r"\W+", " ", a.lower()).strip() for a in answers]
    if len(set(norm)) < len(norm):
        probs.append("duplicate answers")
    for s in contract.get("must_not_contain", []):
        if s.lower() in text.lower():
            probs.append("contains forbidden text: " + s)
    for rx in contract.get("must_not_match", []):
        if re.search(rx, text):
            probs.append("matches forbidden pattern")
    if len(text) > contract.get("max_chars", 20000):
        probs.append("output too long")
    return not probs, probs, parsed

def grounded_reply(text, facts, extra_terms=()):
    """A customer-facing reply: no claim terms the business's facts do not support. -> (ok, problems)"""
    ok, probs, _ = accept(text, {"claim_terms": list(CLAIM_TERMS) + list(extra_terms), "_facts": facts or ""})
    return ok, probs
