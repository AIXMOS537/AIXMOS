"""
crm.py -- the local business operating layer built from the kit's lead-gen, sales,
appointment-setter, missed-call, cold-outreach and dashboard packs.

memory/business.json holds leads, appointments, activity, revenue entries, follow-up
sequences and weekly reviews. No sample data anywhere: empty states stay honest.
"""
import os, json, time, threading, uuid, re
from datetime import datetime, timedelta
from . import settings, llm, skills

FILE = os.path.join(settings.MEMDIR, "business.json")
_LOCK = threading.Lock()
STATUSES = ["new", "enriched", "contacted", "replied", "booked", "not-a-fit", "do-not-contact"]
SEQUENCES = {   # day offsets + the intent handed to the email drafter
    "cold_outreach": [(0, "opener: one personalised line, one sentence on why us, one low-friction ask, under 90 words"),
                      (3, "value add: share one genuinely useful idea or resource for them, no pitch, no 'bumping this'"),
                      (7, "short friendly nudge with an easy out"),
                      (12, "graceful breakup: close the loop, leave the door open")],
    "missed_call":   [(0, "sorry we missed your call, one-line invite to reply with what they need, include 'Reply STOP to opt out'"),
                      (0.3, "same-day follow-up if no reply: short, friendly, offer a time to talk"),
                      (1, "next-day follow-up: last gentle check-in, easy out")],
    "no_show":       [(0, "we missed you at the appointment, no guilt, offer two new times"),
                      (2, "second chance: one more offer to rebook with the booking link"),
                      (5, "final: door stays open, easy way to reach us")],
    "review_request": [(0, "thank them for their visit and ask for a Google review with the link, one warm sentence"),
                       (3, "gentle reminder for the review, thank them regardless")],
}

def _load():
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    for k in ("leads", "appointments", "activity", "revenue", "sequences", "reviews"):
        d.setdefault(k, [])
    return d

def _save(d):
    os.makedirs(settings.MEMDIR, exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FILE)

def _id():
    return uuid.uuid4().hex[:8]

def log(desc, kind="note", ref=None):
    with _LOCK:
        d = _load()
        d["activity"].insert(0, {"ts": time.time(), "kind": kind, "desc": str(desc)[:300], "ref": ref})
        d["activity"] = d["activity"][:300]
        _save(d)

def all_data():
    with _LOCK:
        return _load()

# ---------------------------------------------------------------- leads ----
def upsert_lead(fields):
    with _LOCK:
        d = _load()
        lid = fields.get("id")
        lead = next((l for l in d["leads"] if l["id"] == lid), None) if lid else None
        if not lead:
            lead = {"id": _id(), "created": time.time(), "status": "new", "score": None, "notes": ""}
            d["leads"].insert(0, lead)
        for k in ("company", "name", "role", "contact", "location", "source", "hook", "status", "next_action", "date", "notes", "value"):
            if k in fields and fields[k] is not None:
                lead[k] = str(fields[k]).strip()[:500]
        if lead.get("status") not in STATUSES:
            lead["status"] = "new"
        lead["updated"] = time.time()
        _save(d)
    log("Lead %s: %s (%s)" % ("updated" if lid else "added", lead.get("name") or lead.get("company") or lead["id"], lead["status"]), "lead", lead["id"])
    return lead

def delete_lead(lid):
    with _LOCK:
        d = _load(); d["leads"] = [l for l in d["leads"] if l["id"] != lid]; _save(d)
    return True

def list_leads(status=None):
    d = all_data()
    return [l for l in d["leads"] if not status or l.get("status") == status]

def dnc_check(contact):
    c = (contact or "").strip().lower()
    return any(l.get("status") == "do-not-contact" and c and c in (l.get("contact", "").lower()) for l in list_leads())

def score_leads(ids=None):
    """Sales-pack 3-axis scoring (fit / intent / reach, 1-5 each) via the local model."""
    leads = [l for l in list_leads() if (not ids or l["id"] in ids) and l.get("status") not in ("do-not-contact",)][:25]
    if not leads:
        return []
    prof = skills.profile_text()
    listing = "\n".join("- id=%s | %s, %s at %s | source=%s | status=%s | hook=%s | notes=%s" % (
        l["id"], l.get("name", "?"), l.get("role", ""), l.get("company", ""), l.get("source", ""), l.get("status", ""),
        l.get("hook", ""), (l.get("notes") or "")[:200]) for l in leads)
    out = llm.json_call(
        "You score sales leads for a small business using the 3-axis method: Fit (match to ideal client), Intent (readiness to act), "
        "Reach (can we actually move it forward). Rate each 1-5 from the notes only; never invent facts. Total 12-15 = call today, "
        "8-11 = nurture, under 8 = park. Return JSON: {\"scores\":[{\"id\":\"..\",\"fit\":n,\"intent\":n,\"reach\":n,\"next_action\":\"one concrete step\",\"talking_point\":\"..\",\"disqualify\":false}]}"
        + ("\n" + prof if prof else ""), listing, temperature=0.1, num_ctx=6144, timeout=300)
    scores = (out or {}).get("scores") or []
    with _LOCK:
        d = _load()
        for s in scores:
            l = next((x for x in d["leads"] if x["id"] == s.get("id")), None)
            if not l:
                continue
            try:
                fit, intent, reach = [max(1, min(5, int(s.get(k, 3)))) for k in ("fit", "intent", "reach")]
            except (TypeError, ValueError):
                continue
            total = fit + intent + reach
            l["score"] = {"fit": fit, "intent": intent, "reach": reach, "total": total,
                          "bucket": "call today" if total >= 12 else ("nurture" if total >= 8 else "park"),
                          "talking_point": str(s.get("talking_point") or "")[:300], "disqualify": bool(s.get("disqualify"))}
            if s.get("next_action"):
                l["next_action"] = str(s["next_action"])[:300]
        _save(d)
    log("Scored %d leads" % len(scores), "score")
    return list_leads()

# --------------------------------------------------------- appointments ----
def book(fields):
    when = str(fields.get("when") or "").strip()
    if not when:
        raise ValueError("appointment time is required")
    with _LOCK:
        d = _load()
        ap = {"id": _id(), "created": time.time(), "name": str(fields.get("name") or "")[:120], "contact": str(fields.get("contact") or "")[:120],
              "when": when[:60], "tz": str(fields.get("tz") or "")[:40], "service": str(fields.get("service") or "")[:120],
              "notes": str(fields.get("notes") or "")[:500], "lead_id": fields.get("lead_id"), "status": "booked"}
        d["appointments"].insert(0, ap)
        if ap["lead_id"]:
            for l in d["leads"]:
                if l["id"] == ap["lead_id"]:
                    l["status"] = "booked"
        _save(d)
    log("Booked %s for %s (%s)" % (ap["name"] or ap["contact"], ap["when"], ap["service"]), "appointment", ap["id"])
    return ap

def set_appointment(aid, status=None, notes=None):
    with _LOCK:
        d = _load()
        for a in d["appointments"]:
            if a["id"] == aid:
                if status: a["status"] = status
                if notes is not None: a["notes"] = str(notes)[:500]
        _save(d)
    return True

def delete_appointment(aid):
    with _LOCK:
        d = _load(); d["appointments"] = [a for a in d["appointments"] if a["id"] != aid]; _save(d)
    return True

# --------------------------------------------------------------- revenue ----
def add_revenue(period, value, source=""):
    with _LOCK:
        d = _load()
        d["revenue"].append({"ts": time.time(), "period": str(period)[:20], "value": float(value), "source": str(source)[:60]})
        d["revenue"] = d["revenue"][-400:]
        _save(d)
    log("Revenue %s: %.2f %s" % (period, float(value), source), "revenue")
    return True

def delete_revenue(ts):
    with _LOCK:
        d = _load(); d["revenue"] = [r for r in d["revenue"] if r["ts"] != ts]; _save(d)
    return True

# ------------------------------------------------------------- sequences ----
def start_sequence(kind, lead_id=None, contact=None, name=None, start=None):
    if kind not in SEQUENCES:
        raise ValueError("unknown sequence type")
    if dnc_check(contact):
        raise ValueError("contact is on the do-not-contact list")
    base = datetime.now() if not start else datetime.fromisoformat(start)
    steps = [{"n": i + 1, "due": (base + timedelta(days=off)).isoformat(timespec="minutes"), "intent": intent, "status": "pending", "draft": None}
             for i, (off, intent) in enumerate(SEQUENCES[kind])]
    seq = {"id": _id(), "kind": kind, "lead_id": lead_id, "contact": (contact or "")[:120], "name": (name or "")[:120],
           "created": time.time(), "steps": steps, "status": "active"}
    with _LOCK:
        d = _load(); d["sequences"].insert(0, seq); _save(d)
    log("Started %s sequence for %s" % (kind.replace("_", " "), name or contact or lead_id), "sequence", seq["id"])
    return seq

def sequence_step(seq_id, n, status=None, draft=None):
    with _LOCK:
        d = _load()
        for s in d["sequences"]:
            if s["id"] == seq_id:
                for st in s["steps"]:
                    if st["n"] == int(n):
                        if status: st["status"] = status
                        if draft is not None: st["draft"] = draft
                if all(st["status"] in ("sent", "skipped") for st in s["steps"]):
                    s["status"] = "complete"
        _save(d)
    return True

def stop_sequence(seq_id):
    with _LOCK:
        d = _load()
        for s in d["sequences"]:
            if s["id"] == seq_id:
                s["status"] = "stopped"
                for st in s["steps"]:
                    if st["status"] == "pending": st["status"] = "skipped"
        _save(d)
    return True

def due_steps():
    now = datetime.now().isoformat(timespec="minutes")
    out = []
    for s in all_data()["sequences"]:
        if s["status"] != "active":
            continue
        for st in s["steps"]:
            if st["status"] == "pending" and st["due"] <= now:
                out.append({"seq": s["id"], "kind": s["kind"], "contact": s["contact"], "name": s["name"], "lead_id": s.get("lead_id"), **st})
                break   # one step at a time per sequence
    return out

# ------------------------------------------------------------ dashboard ----
def _week(ts):
    return datetime.fromtimestamp(ts).strftime("%G-W%V")

def dashboard():
    d = all_data()
    now = time.time(); wk, lastwk = _week(now), _week(now - 7 * 86400)
    leads = d["leads"]
    def cnt(pred): return sum(1 for l in leads if pred(l))
    new_wk, new_last = cnt(lambda l: _week(l["created"]) == wk), cnt(lambda l: _week(l["created"]) == lastwk)
    contacted = cnt(lambda l: l.get("status") in ("contacted", "replied", "booked"))
    booked = cnt(lambda l: l.get("status") == "booked")
    conv = (booked / contacted * 100) if contacted else None
    rev = {}
    for r in d["revenue"]:
        rev[r["period"]] = rev.get(r["period"], 0) + r["value"]
    trend = [{"label": k, "value": v} for k, v in sorted(rev.items())[-8:]]
    src = {}
    for r in d["revenue"]:
        src[r["source"] or "unattributed"] = src.get(r["source"] or "unattributed", 0) + r["value"]
    upcoming = [a for a in d["appointments"] if a.get("status") == "booked"][:8]
    def pct(a, b): return None if not b else round((a - b) / b * 100, 1)
    metrics = [
        {"label": "Revenue (latest period)", "value": (trend[-1]["value"] if trend else None), "change": pct(trend[-1]["value"], trend[-2]["value"]) if len(trend) > 1 else None, "fmt": "money"},
        {"label": "New leads this week", "value": new_wk, "change": pct(new_wk, new_last), "fmt": "int"},
        {"label": "Contacted → booked", "value": conv, "change": None, "fmt": "pct"},
        {"label": "Booked appointments", "value": len(upcoming), "change": None, "fmt": "int"},
    ]
    return {"metrics": metrics, "trend": trend, "breakdown": [{"category": k, "value": v} for k, v in sorted(src.items(), key=lambda x: -x[1])],
            "activity": d["activity"][:12], "upcoming": upcoming, "leads_total": len(leads),
            "by_status": {s: cnt(lambda l, s=s: l.get("status") == s) for s in STATUSES},
            "due": due_steps(), "last_review": (d["reviews"][0] if d["reviews"] else None)}

def weekly_review(extra_notes=""):
    """The kit's 15-minute weekly review, answered from real data by the local model."""
    dash = dashboard()
    facts = json.dumps({"metrics": dash["metrics"], "trend": dash["trend"][-6:], "by_status": dash["by_status"],
                        "breakdown": dash["breakdown"][:6], "recent_activity": [a["desc"] for a in dash["activity"][:10]],
                        "upcoming_appointments": len(dash["upcoming"]), "previous_review": (dash["last_review"] or {}).get("one_action")},
                       ensure_ascii=False)
    out = llm.json_call(
        "You run a small business owner's 15-minute weekly review from REAL numbers only. Never invent data; if a number is "
        "missing say so. Answer four things: what changed, why (best hypothesis), the single bottleneck, and ONE specific action "
        "for this week. Return JSON: {\"what_changed\":\"..\",\"why\":\"..\",\"bottleneck\":\"..\",\"one_action\":\"..\",\"check_last_week\":\"did they do last week's action? what happened?\"}"
        + ("\n" + skills.profile_text()), "Data: " + facts + ("\nOwner notes: " + extra_notes if extra_notes else ""),
        temperature=0.3, num_ctx=6144, timeout=300)
    if not out or not out.get("one_action"):
        raise RuntimeError("the local model could not produce a review; try again or add more data")
    rev = {"ts": time.time(), "week": _week(time.time()), **{k: str(out.get(k) or "")[:600] for k in ("what_changed", "why", "bottleneck", "one_action", "check_last_week")}}
    with _LOCK:
        d = _load(); d["reviews"].insert(0, rev); d["reviews"] = d["reviews"][:60]; _save(d)
    log("Weekly review: " + rev["one_action"][:120], "review")
    return rev
