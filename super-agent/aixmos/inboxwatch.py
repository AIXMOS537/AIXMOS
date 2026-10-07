"""
inboxwatch.py -- notices new email so the owner hears about the ones that matter, without opening six apps.

READ-ONLY on the mailbox: it lists the newest messages through email_tools.inbox (IMAP is opened read-only with
BODY.PEEK, so nothing is marked as read; Gmail / Outlook are metadata reads). It never replies, moves, deletes or
labels anything.

  check(now=None, n=25) -> {"accounts", "new", "items"}     run by the chief_of_staff timer every 10 minutes

Per new message (seen once, by a hash of sender + subject + date, because IMAP sequence numbers shift):
  - bounce (mailer-daemon / "Undeliverable" ...) naming someone AIXMOS emailed -> important "send.bounced", and the
    outcome of that approved send is marked "mismatch": it did not arrive
  - "STOP" / "unsubscribe" as the subject or first words -> the sender is opted out (guard), never automatic opt-in
  - automated senders (no-reply, newsletters, notifications) -> background
  - someone AIXMOS has written to -> "lead.reply" (important; an away-mandate can ask to be alerted)
  - a known lead or GoHighLevel contact -> "customer.message" (routine; complaint / refund words raise it to important)
  - anyone else -> "email.unknown" (background; the same words raise it to important)
Every item is source "external:email": the text is data, it can reach at most "important", it never authorizes.
The first check of an account only records what is already there (no flood of old mail).
"""
import hashlib, re, time
from . import store, guard, attention

AUTOMATED = re.compile(r"(?i)(no-?reply|do-?not-?reply|newsletter|notifications?@|mailer@|marketing@|news@|updates@|"
                       r"billing@|receipts?@|support@.*(stripe|google|microsoft|apple|amazon))")
BOUNCE_FROM = re.compile(r"(?i)(mailer-daemon|postmaster|mail delivery)")
BOUNCE_SUBJECT = re.compile(r"(?i)(undeliverable|delivery status notification|mail delivery failed|returned mail|"
                            r"delivery has failed|could not be delivered)")
EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SEEN_CAP = 400

def _key(m):
    raw = "%s|%s|%s" % (guard.normalize(m.get("from")) or m.get("from"), m.get("subject") or "", m.get("date") or "")
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:16]

def _name(frm):
    m = re.match(r'\s*"?([^"<]+?)"?\s*<', str(frm or ""))
    return (m.group(1).strip() if m else str(frm or "").strip())[:60]

def _messaged(addr):
    return bool(addr) and bool(store.one("SELECT 1 AS x FROM sends WHERE contact=? LIMIT 1", (addr,)))

def _known(addr, budget):
    """A lead in the local CRM, or (when connected, within the lookup budget) a GoHighLevel contact."""
    if not addr:
        return False
    from . import crm
    if any(guard.normalize(l.get("contact")) == addr for l in crm.list_leads()):
        return True
    if budget[0] <= 0:
        return False
    try:
        from . import ghl
        if not ghl.connected():
            return False
        budget[0] -= 1
        bare = addr.split(":", 1)[1]
        return any((c.get("email") or "").lower() == bare for c in ghl.Client().find_contacts(bare, 5)["contacts"])
    except Exception:
        return False

def _bounced(m):
    if not (BOUNCE_FROM.search(m.get("from") or "") or BOUNCE_SUBJECT.search(m.get("subject") or "")):
        return None
    for e in EMAIL.findall((m.get("snippet") or "") + " " + (m.get("subject") or "")):
        n = guard.normalize(e)
        if _messaged(n):
            return n
    return "unknown"

def _mark_bounce(addr):
    """The newest executed send to addr did not arrive: record it on the outcome (it was only 'accepted')."""
    from . import approvals, outcomes
    bare = addr.split(":", 1)[1]
    for it in approvals.items("executed", 200):
        pl = it.get("payload") if isinstance(it.get("payload"), dict) else {}
        if str(pl.get("to") or "").strip().lower() == bare:
            outcomes.mark(it["id"], "mismatch", "the email to %s bounced" % bare)
            return it["id"]
    return None

def _handle(acc, m, budget, now):
    frm, subj = m.get("from") or "", (m.get("subject") or "(no subject)")[:120]
    addr = guard.normalize(frm)
    if addr and addr == guard.normalize(acc.get("email")):
        return None                                   # the owner's own mail
    snippet = (m.get("snippet") or "")[:500]
    key = "email:%s:%s" % (acc["id"], _key(m))
    b = _bounced(m)
    if b:
        if b == "unknown":
            return attention.observe("email.automated", "A delivery failure notice arrived", detail=snippet,
                                     source="external:email", dedupe=key, now=now)
        aid = _mark_bounce(b)
        store.audit("email.bounced", b, {"approval": aid})
        return attention.observe("send.bounced", "An email to %s bounced" % b.split(":", 1)[1], detail=snippet,
                                 source="external:email", ref=aid, dedupe=key, now=now)
    first = re.split(r"[\r\n.!]", snippet.strip(), maxsplit=1)[0] if snippet else ""
    if addr and (guard.is_stop(subj) or guard.is_stop(first)):
        if not guard.blocked(addr):
            guard.opt_out(addr, reason="asked to stop by email", source="email")
        return attention.observe("contact.opted_out", "%s asked to stop; they're opted out" % _name(frm),
                                 source="external:email", dedupe=key, now=now)
    if AUTOMATED.search(frm):
        return attention.observe("email.automated", "%s: %s" % (_name(frm), subj), detail=snippet,
                                 source="external:email", dedupe=key, now=now)
    if _messaged(addr):
        return attention.observe("lead.reply", "Reply from %s: %s" % (_name(frm), subj), detail=snippet,
                                 source="external:email", category="opportunity", dedupe=key, now=now)
    if _known(addr, budget):
        return attention.observe("customer.message", "Email from %s: %s" % (_name(frm), subj), detail=snippet,
                                 source="external:email", dedupe=key, now=now)
    # category "unknown_sender": a stranger's "refund!!" may reach the digest as important, but never trips an
    # away-mandate's customer-issue alert (that is for people the business actually knows)
    return attention.observe("email.unknown", "Email from %s: %s" % (_name(frm), subj), detail=snippet,
                             source="external:email", category="unknown_sender", dedupe=key, now=now)

def check(now=None, n=25):
    from . import email_tools
    now = float(now if now is not None else time.time())
    out = {"accounts": 0, "new": 0, "items": [], "errors": []}
    budget = [10]                                     # GoHighLevel lookups per run
    for acc in email_tools.list_accounts():
        if not acc.get("imap"):
            continue
        out["accounts"] += 1
        try:
            msgs = email_tools.inbox(acc["id"], n=n)
        except Exception as e:
            out["errors"].append("%s: %s" % (acc.get("label"), type(e).__name__))
            continue
        seen = store.state_get("inboxwatch", "seen:" + acc["id"])
        first = seen is None
        seen = list(seen or [])
        have = set(seen)
        for m in reversed(msgs):                      # oldest first, so items keep their order
            k = _key(m)
            if k in have:
                continue
            seen.append(k); have.add(k)
            if first:
                continue                              # baseline: what was already there is not news
            try:
                it = _handle(acc, m, budget, now)
            except Exception as e:                    # one odd message never stops the watch
                store.audit("inboxwatch.error", acc["id"], str(e)[:200])
                continue
            if it:
                out["new"] += 1
                out["items"].append({"kind": it["kind"], "level": it["level"], "title": it["title"]})
        store.state_set("inboxwatch", "seen:" + acc["id"], seen[-SEEN_CAP:])
    store.state_set("inboxwatch", "last", {"ts": now, "accounts": out["accounts"], "new": out["new"]})
    return out
