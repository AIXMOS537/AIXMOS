"""
skillkit.py -- the head agent's skill runtime.

A skill is CODE shipped inside the product (skills/<id>/skill.py + guide.md), not a playbook the user has to
copy and paste. Each skill.py defines

  SKILL = {
    "id": "followup", "name": "Follow-ups that run", "summary": "...", "category": "customers",
    "needs":     ["email"],                                   # connector ids (CONNECTORS below)
    "tools":     [(name, description, params, required, fn(args, ctx), level), ...],  # agent/MCP tools
    "actions":   {"step": fn(payload, job)},                  # scheduler handlers -> "followup.step"
    "executors": {"followup.email": fn(payload)},             # approval executors (run only after approve)
    "triggers":  [{"action": "sweep", "every_minutes": 15}, {"action": "brief", "daily": "07:00"}],
    "status":    fn() -> dict,                                # live numbers for the dashboard (optional)
    "rules":     ["Never ...", ...],                          # always in the skill's prompt, never trimmed
  }

Tool names must start with "<id>_" so skills never collide with the core tools or each other.
A broken skill is reported in the catalog and skipped; it never takes the head agent down.

  load(force=False) -> catalog()    tools()    tool(name)    persona(id, query="")
  ensure_triggers(now=None)         connectors()
"""
import os, re, time, importlib.util, threading
from datetime import datetime, timedelta
from . import settings, scheduler, approvals, store

SKILLS_DIR = os.environ.get("AIXMOS_SKILLS_DIR") or os.path.join(settings.ROOT, "skills")
LEVELS = ("safe", "builder", "full")
_LOCK = threading.RLock()
_REG = {"loaded": False, "skills": {}, "errors": {}, "tools": {}}

# ------------------------------------------------------------ connectors ----
def _email_ok():
    from . import email_tools
    return bool(email_tools.list_accounts())

def _model_ok():
    from . import llm
    return llm.available()

def _profile(field):
    from . import skills
    return bool((skills.profile() or {}).get(field))

CONNECTORS = {
    "local_model": ("Local AI model (Ollama)", _model_ok, "Install Ollama and a model (Settings > AI engine)."),
    "email":       ("A connected email account", _email_ok, "Mail > Connect account (Gmail, Outlook or any SMTP)."),
    "booking_link":("Your booking link", lambda: _profile("booking_link"), "Business profile > booking link (Calendly, Cal.com, Google)."),
    "calendar":    ("Calendar sync (Google / Cal.com)", lambda: False, "Coming in Wave 1."),
    "sms":         ("Business texting number", lambda: False, "Coming in Wave 1 (Twilio, with US 10DLC registration)."),
    "payments":    ("Stripe account", lambda: False, "Coming in Wave 2."),
}

def connectors():
    out = {}
    for cid, (label, check, hint) in CONNECTORS.items():
        try:
            ok = bool(check())
        except Exception:
            ok = False
        out[cid] = {"label": label, "ok": ok, "hint": hint}
    return out

# --------------------------------------------------------------- loading ----
def _validate(sk, folder):
    sid = sk.get("id")
    if not sid or not re.fullmatch(r"[a-z][a-z0-9_]{1,30}", sid):
        raise ValueError("skill id must be lowercase letters/digits/_")
    if os.path.basename(folder) != sid:
        raise ValueError("folder name must equal the skill id")
    for k in ("name", "summary"):
        if not sk.get(k):
            raise ValueError("missing %s" % k)
    for t in sk.get("tools", []):
        name, desc, params, req, fn, level = t
        if not name.startswith(sid + "_"):
            raise ValueError("tool %s must start with %s_" % (name, sid))
        if level not in LEVELS or not callable(fn):
            raise ValueError("tool %s: bad level or function" % name)
    for need in sk.get("needs", []):
        if need not in CONNECTORS:
            raise ValueError("unknown connector %r" % need)

def _daily_next(hhmm, now):
    h, m = [int(x) for x in hhmm.split(":")]
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return (t if t > now else t + timedelta(days=1)).timestamp()

def _wrap_trigger(sid, trig, fn):
    """A triggered action re-schedules itself after every run (even a failed one), so it never stops ticking."""
    def run(payload, job):
        try:
            return fn(payload, job)
        finally:
            if job:                      # this run still holds the timer's dedupe key: release it, or the next
                with store.tx() as c:    # booking would see a live job and the timer would stop after one tick
                    c.execute("UPDATE jobs SET dedupe=NULL WHERE id=?", (job["id"],))
            _schedule_trigger(sid, trig, datetime.now())
    return run

def _schedule_trigger(sid, trig, now):
    action = "%s.%s" % (sid, trig["action"])
    if trig.get("daily"):
        due = _daily_next(trig["daily"], now)
    else:
        due = now.timestamp() + 60 * max(1, int(trig.get("every_minutes", 60)))
    scheduler.schedule(action, {"trigger": True}, due=due, skill=sid, dedupe="trigger:" + action, max_attempts=1)

def load(force=False):
    with _LOCK:
        if _REG["loaded"] and not force:
            return catalog()
        skills, errors, tools = {}, {}, {}
        if os.path.isdir(SKILLS_DIR):
            for sid in sorted(os.listdir(SKILLS_DIR)):
                folder = os.path.join(SKILLS_DIR, sid)
                path = os.path.join(folder, "skill.py")
                if not os.path.isfile(path):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location("aixmos_skill_" + sid, path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    sk = dict(getattr(mod, "SKILL"))
                    _validate(sk, folder)
                    sk["_dir"] = folder
                    need = sk.get("requires_feature")
                    if need:
                        from . import licence
                        if not licence.has_feature(need):
                            sk["_locked"] = "needs a licence with the '%s' feature" % need
                            skills[sid] = sk           # listed as locked; none of its tools, timers or executors run
                            continue
                    trig_actions = {t["action"]: t for t in sk.get("triggers", [])}
                    for name, fn in (sk.get("actions") or {}).items():
                        t = trig_actions.get(name)
                        scheduler.handler("%s.%s" % (sid, name))(_wrap_trigger(sid, t, fn) if t else fn)
                    for kind, fn in (sk.get("executors") or {}).items():
                        approvals.register(kind, fn)
                    for t in sk.get("tools", []):
                        tools[t[0]] = t
                    skills[sid] = sk
                except Exception as e:
                    errors[sid] = "%s: %s" % (type(e).__name__, str(e)[:300])
        _REG.update(loaded=True, skills=skills, errors=errors, tools=tools)
    return catalog()

def _ensure():
    if not _REG["loaded"]:
        load()

def get(sid):
    _ensure()
    return _REG["skills"].get(sid)

def tools():
    _ensure()
    return list(_REG["tools"].values())

def tool(name):
    _ensure()
    return _REG["tools"].get(name)

def ensure_triggers(now=None):
    _ensure()
    now = now or datetime.now()
    for sid, sk in _REG["skills"].items():
        if sk.get("_locked"):
            continue
        for t in sk.get("triggers", []):
            _schedule_trigger(sid, t, now)

def _autopilot_on(sid):
    ap = settings.pref("autopilot") or {}
    return bool(isinstance(ap, dict) and ap.get(sid))

def catalog():
    _ensure()
    conn = connectors()
    out = []
    for sid, sk in _REG["skills"].items():
        missing = [n for n in sk.get("needs", []) if not conn.get(n, {}).get("ok")]
        live = {}
        if callable(sk.get("status")) and not sk.get("_locked"):
            try:
                live = sk["status"]() or {}
            except Exception as e:
                live = {"error": str(e)[:200]}
        state = "locked" if sk.get("_locked") else "ready" if not missing else "needs_setup"
        out.append({"id": sid, "name": sk["name"], "summary": sk["summary"], "category": sk.get("category", "general"),
                    "icon": sk.get("icon", "◆"), "state": state, "locked": sk.get("_locked", ""),
                    "missing": [{"id": m, **conn[m]} for m in missing], "needs": sk.get("needs", []),
                    "tools": [t[0] for t in sk.get("tools", [])], "autopilot": _autopilot_on(sid),
                    "live": live, "builtin": True})
    for sid, err in _REG["errors"].items():
        out.append({"id": sid, "name": sid, "summary": "This skill failed to load.", "state": "error", "error": err,
                    "builtin": True, "tools": [], "missing": [], "needs": []})
    return out

# ---------------------------------------------------------------- guides ----
def _sections(md):
    parts, title, buf = [], "Overview", []
    for line in (md or "").splitlines():
        m = re.match(r"^##\s+(.+)", line)
        if m:
            if buf:
                parts.append((title, "\n".join(buf).strip()))
            title, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if buf:
        parts.append((title, "\n".join(buf).strip()))
    return [(t, b) for t, b in parts if b]

def guide(sid):
    sk = get(sid)
    if not sk:
        return ""
    p = os.path.join(sk["_dir"], sk.get("guide", "guide.md"))
    try:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""

def persona(sid, query="", budget=None):
    """The skill's working brief for the model: who it is, its hard rules (never trimmed), the business profile
    (never dropped) and the guide sections most relevant to the request, within the character budget."""
    from . import skills
    sk = get(sid)
    if not sk:
        return ""
    budget = int(budget or settings.pref("skill_prompt_chars") or 4000)
    head = ("You are AIXMOS running the '%s' skill. %s\nUse the skill's tools to do the work; never claim an action "
            "happened unless a tool result shows it. Anything that messages a customer goes to the owner's approval "
            "inbox unless the owner switched on autopilot." % (sk["name"], sk["summary"]))
    rules = "\n".join("- " + r for r in sk.get("rules", []))
    prof = skills.profile_text()
    fixed = "\n\n".join(x for x in [head, ("HARD RULES:\n" + rules) if rules else "", prof] if x)
    room = max(0, budget - len(fixed) - 40)
    words = set(w for w in re.findall(r"[a-z]{4,}", (query or "").lower()))
    secs = _sections(guide(sid))
    def score(i_t):
        i, (t, b) = i_t
        hit = sum(1 for w in words if w in (t + " " + b).lower())
        must = 1000 if re.search(r"(?i)\b(rule|never|always|how it works)\b", t) else 0
        return (must + hit * 10 - i)
    picked, used = [], 0
    for i, (t, b) in sorted(enumerate(secs), key=score, reverse=True):
        block = "### %s\n%s" % (t, b)
        if used + len(block) > room:
            continue
        picked.append((i, block)); used += len(block)
    body = "\n\n".join(b for _, b in sorted(picked))
    return skills.fill(fixed + ("\n\nGUIDE:\n" + body if body else ""))
