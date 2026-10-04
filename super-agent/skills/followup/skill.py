"""
followup -- follow-up sequences that actually run.

The CRM already stores sequences (cold outreach, missed call, no-show, review request) with due dates. This skill
makes them happen: every 15 minutes it finds steps that are due, writes the message in the owner's voice, and puts
it in the approval inbox (or sends it at once when the owner switched on autopilot for follow-ups). An approved
step goes out through channels.send_email, which re-checks opt-outs and caps at the moment of sending.
A contact who opted out has their sequences stopped. A rejected step is skipped and the sequence moves on.
"""
import re, time
from datetime import datetime
from aixmos import crm, guard, approvals, scheduler, store, channels

SID = "followup"
KIND = "followup.email"
MIN_GAP = 4 * 3600          # never two follow-ups to the same person within 4 hours

def _seq(seq_id):
    return next((s for s in crm.all_data()["sequences"] if s["id"] == seq_id), None)

def _step(seq, n):
    return next((st for st in seq["steps"] if st["n"] == int(n)), None)

def _dedupe(seq_id, n):
    return "followup:%s:%s" % (seq_id, n)

def _looks_unwritten(body, intent):
    """email_tools.draft falls back to pasting the instruction when the model fails. Never propose that."""
    b = (body or "").lower()
    return len(b.strip()) < 40 or (intent or "").lower()[:40] in b

LINK_FIELDS = ("booking_link", "review_link", "website")
NEEDS_LINK = {"review_request": "review_link", "no_show": "booking_link"}

def _links():
    from aixmos import skills
    p = skills.profile()
    return {f: (p.get(f) or "").strip() for f in LINK_FIELDS if (p.get(f) or "").strip()}

def _norm_url(u):
    u = (u or "").strip().rstrip(".,;:!?)]/").lower()
    u = re.sub(r"^https?://", "", u)
    return re.sub(r"^www\.", "", u)

def _bad_links(body):
    """Any URL in a draft must be one of the owner's own links (or a deeper page of one). A model-invented or
    look-alike link (bookme.com.evil.io) is a reason to reject the draft."""
    allowed = [_norm_url(u) for u in _links().values() if _norm_url(u)]
    found = re.findall(r"(?i)\b(?:https?://|www\.)[^\s<>()\"']+", body or "")
    def ok(u):
        n = _norm_url(u)
        return any(n == a or n.startswith(a + "/") or n.startswith(a + "?") for a in allowed)
    return [u for u in found if not ok(u)]

def _replied(contact, since_ts):
    """True when the person wrote back after the sequence started, False when not, None when the inbox can't be read."""
    from aixmos import email_tools
    want = guard.normalize(contact)
    since = datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d %H:%M")
    seen_any = False
    for a in email_tools.list_accounts():
        if not a.get("imap"):
            continue
        try:
            msgs = email_tools.inbox(a["id"], n=40)
            seen_any = True
        except Exception:
            continue
        for m in msgs:
            if guard.normalize(m.get("from")) == want and str(m.get("date") or "") >= since:
                return True
    return False if seen_any else None

def _stop_for_reply(seq, contact):
    crm.stop_sequence(seq["id"])
    crm.log("%s replied, follow-ups stopped. Your turn." % (seq.get("name") or contact), "sequence", seq["id"])
    store.audit("followup.replied", seq["id"], {"contact": guard.normalize(contact)})

# ------------------------------------------------------------- actions ----
def step(payload, job):
    seq = _seq(payload["seq"])
    if not seq or seq["status"] != "active":
        return {"skipped": "sequence not active"}
    st = _step(seq, payload["n"])
    if not st or st["status"] != "pending":
        return {"skipped": "step is %s" % (st or {}).get("status")}
    contact = seq.get("contact") or ""
    channel = guard.channel_of(contact)
    if channel != "email":
        crm.sequence_step(seq["id"], st["n"], status="skipped")
        crm.log("Follow-up step %d skipped for %s: texting arrives in Wave 1" % (st["n"], seq.get("name") or contact), "sequence", seq["id"])
        return {"skipped": "no email address"}
    d = guard.check_send("email", contact)
    if not d:
        if d.retry_at:
            raise scheduler.Later(d.retry_at, d.reason)
        crm.stop_sequence(seq["id"])
        crm.log("Stopped %s sequence for %s: %s" % (seq["kind"].replace("_", " "), seq.get("name") or contact, d.reason), "sequence", seq["id"])
        return {"stopped": d.reason}
    last = store.one("SELECT MAX(ts) AS t FROM sends WHERE skill=? AND contact=?", (SID, guard.normalize(contact)))["t"]
    if last and time.time() - last < MIN_GAP:
        raise scheduler.Later(last + MIN_GAP, "keeping at least 4 hours between follow-ups")
    if _replied(contact, seq.get("created") or 0):
        _stop_for_reply(seq, contact)
        return {"stopped": "they replied"}
    links = _links()
    need = NEEDS_LINK.get(seq["kind"])
    if need and not links.get(need):
        crm.sequence_step(seq["id"], st["n"], status="skipped")
        crm.log("Follow-up step %d skipped: add your %s in Business profile" % (st["n"], need.replace("_", " ")), "sequence", seq["id"])
        return {"skipped": "missing " + need}
    from aixmos import email_tools
    total = len(seq["steps"])
    link_note = (" Use exactly this link: %s." % links[need]) if need else " Do not include any links."
    intent = ("%s (message %d of %d in a %s follow-up to %s). Write it so it stands alone, shorter than the one before. "
              "Never invent facts, prices, availability or results; no pressure; make it easy to say no.%s"
              % (st["intent"], st["n"], total, seq["kind"].replace("_", " "), seq.get("name") or "this contact", link_note))
    dr = email_tools.draft(intent, to=[contact], tone="warm, professional")
    if _looks_unwritten(dr.get("body"), st["intent"]):
        raise RuntimeError("the local model could not write this message yet")
    if _bad_links(dr.get("body")):
        raise RuntimeError("the draft contained a link that is not yours; rewriting")
    item = approvals.propose(KIND, "Follow-up %d/%d to %s" % (st["n"], total, seq.get("name") or contact),
                             {"to": contact, "subject": dr["subject"], "body": dr["body"], "seq": seq["id"], "n": st["n"],
                              "skill": SID, "ref": _dedupe(seq["id"], st["n"])},
                             skill=SID, summary="%s sequence, step %d of %d" % (seq["kind"].replace("_", " "), st["n"], total),
                             risk="send", dedupe=_dedupe(seq["id"], st["n"]), auto=True)
    if item["status"] == "pending":
        crm.sequence_step(seq["id"], st["n"], status="awaiting_approval", draft=dr)
    return {"approval": item["id"], "status": item["status"]}

def sweep(payload, job, now=None):
    """Strictly in order, one step per sequence: queue the first unfinished step when it is due (incl. sequences
    started from the CRM screen); a step waiting for the owner blocks the steps after it; a rejected step is skipped."""
    now_iso = datetime.fromtimestamp(now or time.time()).isoformat(timespec="minutes")
    queued = settled = 0
    for seq in crm.all_data()["sequences"]:
        if seq["status"] != "active":
            continue
        st = next((x for x in seq["steps"] if x["status"] not in ("sent", "skipped")), None)
        if not st:
            continue
        if st["status"] == "awaiting_approval":
            row = store.one("SELECT status FROM approvals WHERE dedupe=?", (_dedupe(seq["id"], st["n"]),))
            if row and row["status"] == "rejected":
                crm.sequence_step(seq["id"], st["n"], status="skipped")
                settled += 1
        elif st["status"] == "pending" and st["due"] <= now_iso:
            scheduler.schedule("followup.step", {"seq": seq["id"], "n": st["n"]}, due=now, skill=SID,
                               dedupe=_dedupe(seq["id"], st["n"]))
            queued += 1
    return {"queued": queued, "settled": settled}

# ------------------------------------------------------------ executor ----
def send(payload):
    seq = _seq(payload["seq"])
    if not seq or seq["status"] != "active":
        raise PermissionError("not sent: the sequence was stopped (reply, opt-out or the owner)")
    if _replied(payload["to"], seq.get("created") or 0):
        _stop_for_reply(seq, payload["to"])
        raise PermissionError("not sent: they replied in the meantime")
    res = channels.send_email(payload)
    crm.sequence_step(seq["id"], payload["n"], status="sent")
    crm.log("Sent follow-up %s to %s" % (payload["n"], seq.get("name") or payload["to"]), "sequence", seq["id"])
    return res

# --------------------------------------------------------------- tools ----
def t_start(a, ctx):
    seq = crm.start_sequence(a.get("kind") or "", lead_id=a.get("lead_id"), contact=a.get("contact"), name=a.get("name"))
    sweep({}, None)
    first = seq["steps"][0]["due"] if seq["steps"] else ""
    return "Started %s sequence %s for %s: %d steps, first due %s. Each message waits in the approval inbox." % (
        seq["kind"], seq["id"], seq.get("name") or seq.get("contact"), len(seq["steps"]), first)

def t_status(a, ctx):
    rows = []
    for s in crm.all_data()["sequences"][:30]:
        nxt = next((st for st in s["steps"] if st["status"] in ("pending", "awaiting_approval")), None)
        rows.append("%s | %s | %s | %s | next: %s" % (s["id"], s["kind"], s.get("name") or s.get("contact"), s["status"],
                    ("step %d %s (due %s)" % (nxt["n"], nxt["status"], nxt["due"])) if nxt else "-"))
    return "\n".join(rows) or "No follow-up sequences yet."

def t_stop(a, ctx):
    crm.stop_sequence(a.get("sequence_id") or "")
    return "Stopped."

def status():
    seqs = crm.all_data()["sequences"]
    week = time.time() - 7 * 86400
    sent = store.one("SELECT COUNT(*) AS n FROM sends WHERE skill=? AND ts>=?", (SID, week))["n"]
    return {"active": sum(1 for s in seqs if s["status"] == "active"),
            "awaiting_approval": sum(1 for s in seqs for st in s["steps"] if st["status"] == "awaiting_approval"),
            "sent_7d": sent}

SKILL = {
    "id": SID, "name": "Follow-ups that run", "icon": "📨", "category": "customers",
    "summary": ("Runs your follow-up sequences on schedule: missed-call, no-show, cold outreach and review requests. "
                "Writes each message in your voice and puts it in your inbox to approve."),
    "needs": ["email", "local_model"],
    "tools": [
        ("followup_start", "Start a follow-up sequence for one contact: kind is cold_outreach, missed_call, no_show or "
         "review_request. Messages wait in the owner's approval inbox.",
         {"kind": "string", "contact": "string", "name": "string", "lead_id": "string"}, ["kind", "contact"], t_start, "builder"),
        ("followup_status", "List follow-up sequences with their next step.", {}, [], t_status, "safe"),
        ("followup_stop", "Stop a follow-up sequence (e.g. they replied or asked to stop).", {"sequence_id": "string"},
         ["sequence_id"], t_stop, "safe"),
    ],
    "actions": {"step": step, "sweep": sweep},
    "executors": {KIND: send},
    "triggers": [{"action": "sweep", "every_minutes": 15}],
    "status": status,
    "rules": [
        "Never message anyone who opted out or is marked do-not-contact. A STOP reply ends every sequence for that person.",
        "Never invent facts, prices, availability, results or urgency. If something is unknown, leave it out.",
        "Never promise income, savings or outcomes.",
        "One clear, low-pressure ask per message, and always an easy way to say no.",
        "Stop the sequence as soon as the person replies; a human takes over from there.",
    ],
}
