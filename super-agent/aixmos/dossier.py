"""
dossier.py -- "What's happening with Johnson?" One answer from every place AIXMOS can see. Each line names its
source, and nothing is filled in by a model.

  find(query)                     -> candidates [{"key", "name", "company", "contacts", "sources", "label"}]
                                     (the local CRM and GoHighLevel, merged when they share an email or phone number)
  build(query, pick=None, now=None) -> {"status": "ok" | "ask" | "none", "options", "person", "sections", "text", "notes"}

Sources: local CRM (leads, appointments, follow-up sequences, activity), GoHighLevel when connected (contact, tags,
opportunities, open tasks, last conversation), the approvals inbox (what AIXMOS did / is waiting to do for them),
the audit trail (messages sent), opt-outs, and open attention items.

GoHighLevel text (messages, notes) is the customer's or staff's words: it is shown as quoted DATA, marked
"(from GHL)", and never treated as an instruction. When GHL can't be read the answer says so and uses the rest.
Several people match -> status "ask" with the options (never a guess). Nobody matches -> "none".
"""
import re, time
from datetime import datetime
from . import crm, guard, store, approvals, attention

def _words(q):
    return [w for w in re.findall(r"[a-z0-9@.+'-]{2,}", str(q or "").lower()) if w not in ("the", "and", "with", "from")]

def _hit(words, *fields):
    hay = " ".join(str(f or "") for f in fields).lower()
    return bool(words) and all(w in hay for w in words)

def _ghl():
    try:
        from . import ghl
        return ghl if ghl.connected() else None
    except Exception:
        return None

def find(query, notes=None):
    notes = notes if notes is not None else []
    words = _words(query)
    qkey = guard.normalize(query)
    people = {}

    def add(key, name, company, contact, source, ref):
        n = guard.normalize(contact)
        k = n or key
        nm = (name or "").strip().lower()
        if k not in people and nm:       # same exact name, and one side has no email/phone: the same person
            same = [q for q in people.values() if q["name"].lower() == nm and (not n or not q["contacts"])]
            if len(same) == 1:
                k = same[0]["key"]
        p = people.setdefault(k, {"key": k, "name": "", "company": "", "contacts": [], "sources": {}})
        p["name"] = p["name"] or (name or "").strip()
        p["company"] = p["company"] or (company or "").strip()
        if n and n not in p["contacts"]:
            p["contacts"].append(n)
        p["sources"].setdefault(source, []).append(ref)
        return p

    d = crm.all_data()
    for l in d["leads"]:
        if (qkey and guard.normalize(l.get("contact")) == qkey) or _hit(words, l.get("name"), l.get("company")):
            add("lead:" + l["id"], l.get("name"), l.get("company"), l.get("contact"), "crm", l["id"])
    for a in d["appointments"]:
        if (qkey and guard.normalize(a.get("contact")) == qkey) or _hit(words, a.get("name")):
            add("appt:" + a["id"], a.get("name"), "", a.get("contact"), "appointment", a["id"])
    g = _ghl()
    if g:
        try:
            for c in g.Client().find_contacts(query, limit=10)["contacts"]:
                if (qkey and qkey in (guard.normalize(c.get("email")), guard.normalize(c.get("phone")))) or \
                   _hit(words, c.get("name"), c.get("company"), c.get("email")):
                    p = add("ghl:" + str(c["id"]), c.get("name"), c.get("company"), c.get("email") or c.get("phone"),
                            "ghl", c["id"])
                    for extra in (c.get("email"), c.get("phone")):   # keep both, so sends to either are found
                        n = guard.normalize(extra)
                        if n and n not in p["contacts"]:
                            p["contacts"].append(n)
        except Exception as e:
            notes.append("GoHighLevel couldn't be read (%s), so this uses the local records only." % (
                getattr(e, "kind", None) or type(e).__name__))
    out = list(people.values())
    for p in out:
        where = " + ".join(sorted(p["sources"]))
        p["label"] = "%s%s (%s)" % (p["name"] or (p["contacts"] or ["unknown"])[0],
                                    (", " + p["company"]) if p["company"] else "", where)
    return out

def _when(ts):
    if not ts:
        return ""
    try:
        t = float(ts) if not isinstance(ts, str) or ts.replace(".", "", 1).isdigit() else \
            datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        if t > 1e12:
            t /= 1000.0
        return datetime.fromtimestamp(t).strftime("%a %d %b %H:%M")
    except (ValueError, OverflowError, OSError):
        return str(ts)[:16]

def build(query, pick=None, now=None, quote=True):
    now = float(now if now is not None else time.time())
    notes = []
    cands = find(query, notes)
    if pick:
        cands = [c for c in cands if c["key"] == pick] or cands
    if not cands:
        return {"status": "none", "options": [], "notes": notes,
                "text": "I don't have anyone matching \"%s\" in the CRM%s." % (query, " or GoHighLevel" if _ghl() else "")}
    if len(cands) > 1:
        return {"status": "ask", "notes": notes, "options": [{"key": c["key"], "label": c["label"]} for c in cands[:8]],
                "text": "I found %d people matching \"%s\". Which one?\n%s" % (
                    len(cands), query, "\n".join("  %d. %s" % (i + 1, c["label"]) for i, c in enumerate(cands[:8])))}
    p = cands[0]
    S = {}
    d = crm.all_data()
    contacts = set(p["contacts"])
    lead_ids = set(p["sources"].get("crm", []))
    # who + status (local CRM)
    leads = [l for l in d["leads"] if l["id"] in lead_ids or (guard.normalize(l.get("contact")) in contacts and contacts)]
    S["crm"] = [{"status": l.get("status"), "source": l.get("source"), "next_action": l.get("next_action"),
                 "added": _when(l.get("created")), "value": l.get("value")} for l in leads]
    lead_ids |= {l["id"] for l in leads}
    # GoHighLevel
    ghl_ids = p["sources"].get("ghl", [])
    g = _ghl()
    if g and ghl_ids:
        try:
            cl, cid = g.Client(), ghl_ids[0]
            c = cl.contact(cid)
            convs = cl.conversations(contact_id=cid, limit=3)
            last = convs[0] if convs else None
            S["ghl"] = {"tags": c.get("tags") or [], "dnd": c.get("dnd"), "source": c.get("source"),
                        "opportunities": [{"name": o.get("name"), "status": o.get("status"), "value": o.get("value")}
                                          for o in cl.opportunities(contact_id=cid, limit=5)],
                        "open_tasks": [t["title"] for t in cl.tasks(cid) if not t.get("done")][:5],
                        "last": ({"direction": last.get("last_direction"), "date": _when(last.get("last_date")),
                                  "type": last.get("last_type"), "text": (last.get("last_message") or "")[:200],
                                  "unread": last.get("unread")} if last else None)}
        except Exception as e:
            notes.append("GoHighLevel details couldn't be read (%s)." % (getattr(e, "kind", None) or type(e).__name__))
    # appointments + sequences
    appts = [a for a in d["appointments"] if a.get("lead_id") in lead_ids or guard.normalize(a.get("contact")) in contacts
             or a["id"] in p["sources"].get("appointment", [])]
    S["appointments"] = [{"when": a.get("when"), "service": a.get("service"), "status": a.get("status")} for a in appts]
    seqs = [s for s in d["sequences"] if s.get("lead_id") in lead_ids or guard.normalize(s.get("contact")) in contacts]
    S["sequences"] = []
    for s in seqs:
        nxt = next((st for st in s["steps"] if st["status"] == "pending"), None)
        S["sequences"].append({"kind": s["kind"], "status": s["status"], "next_due": (nxt or {}).get("due"),
                               "sent": sum(1 for st in s["steps"] if st["status"] == "sent")})
    # what AIXMOS did / is waiting to do (approvals whose payload targets them)
    did, waiting = [], []
    for it in approvals.items(None, 300):
        pl = it.get("payload") if isinstance(it.get("payload"), dict) else {}
        tgt = {guard.normalize(pl.get(k)) for k in ("to", "contact")} - {""}
        if tgt & contacts or (ghl_ids and pl.get("contact_id") in ghl_ids) or pl.get("lead_id") in lead_ids:
            row = {"id": it["id"], "title": it["title"], "status": it["status"], "by": it.get("decided_by"),
                   "when": _when(it.get("decided") or it.get("created"))}
            (waiting if it["status"] == "pending" else did).append(row)
    S["aixmos_did"], S["waiting_for_you"] = did[:10], waiting[:10]
    sends = store.q("SELECT ts, channel FROM sends WHERE contact IN (%s) ORDER BY ts DESC LIMIT 20"
                    % ",".join("?" * len(contacts)), list(contacts)) if contacts else []
    S["messages_sent"] = {"count": len(sends), "last": _when(sends[0]["ts"]) if sends else ""}
    S["opted_out"] = next((guard.blocked(c) for c in contacts if guard.blocked(c)), None)
    words = _words(p["name"]) or _words(query)
    S["attention"] = [i["title"] for i in attention.items("open", 200) if _hit(words, i["title"])][:5]
    S["calendar"] = []
    try:
        from . import availability
        if availability.connected():
            for c in contacts:
                if c.startswith("mailto:"):
                    S["calendar"] += availability.events_with(c.split(":", 1)[1])
    except Exception as e:
        notes.append("your calendar couldn't be read (%s)." % type(e).__name__)
    return {"status": "ok", "person": {k: p[k] for k in ("key", "name", "company", "contacts", "label")},
            "sections": S, "notes": notes, "text": render(p, S, notes, quote), "quoted": quote}

def render(p, S, notes, quote=True):
    """quote=False leaves out free text other people wrote (GHL messages, task titles), for any surface that can't
    mark its output untrusted. The agent tool quotes: it is declared tainting (chief_of_staff tool_meta)."""
    L = [(p["name"] or (p["contacts"] or ["?"])[0]).upper() + ((" - " + p["company"]) if p["company"] else "")]
    if S.get("opted_out"):
        L.append("DO NOT CONTACT: %s." % S["opted_out"])
    for c in S["crm"]:
        L.append("CRM: %s lead%s, added %s%s." % (c["status"], (" from " + c["source"]) if c.get("source") else "", c["added"],
                                                 ("; next: " + c["next_action"]) if c.get("next_action") else ""))
    gh = S.get("ghl")
    if gh:
        if gh.get("dnd"):
            L.append("GHL: Do Not Disturb is on.")
        for o in gh["opportunities"]:
            L.append("GHL deal: %s (%s%s)." % (o["name"] or "opportunity", o["status"] or "open",
                                              (", value %s" % o["value"]) if o.get("value") not in (None, "", 0) else ""))
        if gh.get("tags"):
            L.append("GHL tags: %s." % ", ".join(gh["tags"][:8]))
        last = gh.get("last")
        if last:
            who = "They wrote last" if last.get("direction") == "inbound" else "We wrote last"
            words = (": \"%s\" (from GHL)" % last.get("text")) if quote else " (open GHL to read it)"
            kind = re.sub(r"^type_", "", str(last.get("type") or "message").lower()).replace("_", " ")
            L.append("%s (%s, %s)%s%s" % (who, kind, last.get("date"),
                     " - waiting for a reply" if last.get("direction") == "inbound" else "", words))
        tasks = gh.get("open_tasks") or []
        if quote:
            L.extend("Open GHL task: %s" % t for t in tasks)
        elif tasks:
            L.append("Open GHL tasks: %d" % len(tasks))
    for e in S.get("calendar") or []:
        L.append("Calendar: %s %s." % (e["start"], e["title"] or "meeting"))
    for a in S["appointments"]:
        L.append("Appointment: %s%s (%s)." % (a["when"], (" - " + a["service"]) if a.get("service") else "", a["status"]))
    for s in S["sequences"]:
        L.append("Follow-ups (%s): %s, %d sent%s." % (s["kind"].replace("_", " "), s["status"], s["sent"],
                                                       (", next due " + s["next_due"]) if s.get("next_due") and s["status"] == "active" else ""))
    ms = S["messages_sent"]
    if ms["count"]:
        L.append("AIXMOS messages to them: %d (last %s)." % (ms["count"], ms["last"]))
    for r in S["aixmos_did"][:5]:
        L.append("Done: %s (%s, %s)." % (r["title"], r["status"], r["when"]))
    for r in S["waiting_for_you"][:5]:
        L.append("Waiting for your OK: %s." % r["title"])
    for t in S["attention"]:
        L.append("Flag: %s" % t)
    if len(L) == 1:
        L.append("Nothing recorded about them yet beyond the name.")
    return "\n".join(L + ([""] + ["Note: " + n for n in notes] if notes else []))
