"""
skills.py -- turns every kit pack into an activatable AIXMOS skill (persona + playbook),
and mines every blockquote prompt in the kit into a searchable prompt library.

A skill = system-prompt persona built from the pack's START-HERE, core prompt file and
templates, with [BRACKET] placeholders filled from the business profile in settings.
"""
import os, re, json
from . import settings, knowledge

# Packs whose "core prompt" file carries the operational persona (receptionist etc.)
CORE_FILES = {
    "receptionist": "02-the-system-prompt.md", "appointment-setter": "02-the-qualifying-prompt.md",
    "missed-call": "04-message-packs.md", "cold-outreach": "02-personalization-engine.md",
    "sales-pack": "03-lead-scoring.md", "content-engine": "01-the-hook-engine.md",
    "carousel-system": "03-writing-framework.md", "lead-gen": "01-define-your-lead.md",
    "prompt-vault": "guides/prompt-anatomy.md", "ai-building-kit": "03-the-build-loop.md",
}
ICONS = {"receptionist": "☎", "appointment-setter": "📅", "missed-call": "📲", "cold-outreach": "✉", "sales-pack": "💼",
         "content-engine": "🎬", "carousel-system": "🖼", "creator-prompt-vault": "✨", "business-prompt-vault": "🏢",
         "lead-gen": "🎯", "local-marketing": "📍", "marketing-system": "📈", "agency-os": "🏛", "app-builder": "🧩",
         "business-builder": "🏗", "ai-building-kit": "🛠", "prompt-vault": "📚", "claude-code-starter-kit": "⌨",
         "dashboard-kit": "📊", "local-automation": "⚙", "mcp-starter": "🔌", "side-hustle-vault": "💡",
         "storefront-kit": "🛒", "viral-reel": "📱"}

PROFILE_FIELDS = ["name", "type", "services", "customers", "area", "hours", "voice", "booking_link", "phone", "email",
                  "owner", "qualified", "nurture", "not_fit", "faq", "offer", "audience", "pricing"]
PLACEHOLDERS = {  # bracket token (lowercased) -> profile field
    "business": "name", "business name": "name", "company": "name", "type": "type", "services": "services",
    "service": "services", "customers": "customers", "audience": "audience", "area": "area", "location": "area",
    "hours": "hours", "voice": "voice", "warm/professional/friendly — describe": "voice", "booking link": "booking_link",
    "qualification criteria": "qualified", "what i do": "offer", "topic": None, "your name": "owner",
}

def profile():
    d = settings.load()
    b = d.get("business") or {}
    return {k: b.get(k, "") for k in PROFILE_FIELDS}

def save_profile(fields):
    with settings._LOCK:
        d = settings._read()
        b = d.setdefault("business", {})
        for k, v in (fields or {}).items():
            if k in PROFILE_FIELDS:
                b[k] = str(v or "").strip()[:2000]
        settings._write(d)
    return profile()

def profile_text():
    p = profile()
    lines = [("%s: %s" % (k.replace("_", " "), v)) for k, v in p.items() if v]
    return ("Business profile:\n" + "\n".join(lines)) if lines else ""

def fill(text, p=None):
    p = p or profile()
    def rep(m):
        key = m.group(1).strip().lower()
        f = PLACEHOLDERS.get(key)
        if f and p.get(f):
            return p[f]
        for cand in PROFILE_FIELDS:
            if cand.replace("_", " ") == key and p.get(cand):
                return p[cand]
        return m.group(0)
    return re.sub(r"\[([^\[\]\n]{2,60})\]", rep, text or "")

def _quotes(text):
    """Blockquote paragraphs in a markdown file -> list of (heading, prompt)."""
    out, head, buf = [], "", []
    for line in (text or "").splitlines():
        if re.match(r"^#{1,4}\s", line):
            head = line.strip("# ").strip()
        if line.startswith(">"):
            buf.append(line.lstrip("> ").rstrip())
        else:
            if buf:
                q = " ".join(x for x in buf).strip()
                if len(q) >= 60:
                    out.append((head, q))
                buf = []
    if buf:
        q = " ".join(buf).strip()
        if len(q) >= 60:
            out.append((head, q))
    return out

def list_skills():
    out = []
    for p in knowledge.packs():
        pid = p["id"]
        out.append({"id": pid, "name": p["title"], "summary": p["summary"], "icon": ICONS.get(pid, "◆"),
                    "files": len(p["files"]), "core": CORE_FILES.get(pid, ""), "active": settings.pref("active_skill") == pid})
    return out

def get(pid):
    return next((s for s in list_skills() if s["id"] == pid), None)

def persona(pid, max_chars=7000):
    """Compose the system prompt for a pack: role framing + start-here + core prompt + templates, placeholders filled."""
    pack = next((p for p in knowledge.packs() if p["id"] == pid), None)
    if not pack:
        return ""
    files = pack["files"]
    def grab(pred, limit):
        for f in files:
            if pred(f):
                t = knowledge.read(f) or ""
                return t[:limit]
        return ""
    start = grab(lambda f: f.endswith("00-START-HERE.md") or f.lower().endswith("readme.md"), 2200)
    core = grab(lambda f: f.endswith(CORE_FILES.get(pid, "\x00")), 2600)
    templates = ""
    for f in files:
        if "/templates/" in f and len(templates) < 1800:
            templates += "\n--- %s ---\n%s" % (f.split("/")[-1], (knowledge.read(f) or "")[:700])
    prof = profile_text()
    head = ("You are AIXMOS operating in the '%s' skill. Apply this playbook faithfully: follow its rules, "
            "use its templates, keep its guardrails (never invent facts, escalate what you cannot verify, "
            "confirm details before committing). Speak as the business when the playbook says to; otherwise "
            "coach the owner concisely and concretely.\n" % pack["title"])
    body = "\n\n".join(x for x in ["PLAYBOOK OVERVIEW:\n" + start if start else "", "CORE PROMPT:\n" + core if core else "",
                                     "TEMPLATES:" + templates if templates else "", prof] if x)
    return fill(head + "\n" + body, profile())[:max_chars]

def activate(pid):
    if pid and not get(pid):
        raise ValueError("unknown skill")
    settings.update(prefs={"active_skill": pid or ""})
    return pid or ""

def active_persona():
    pid = settings.pref("active_skill")
    return persona(pid) if pid else ""

_PROMPTS = {"built": 0, "items": []}
def prompts(q=None, pack=None, limit=80):
    st = knowledge.stats()
    if _PROMPTS["built"] != st.get("built"):
        items = []
        for p in knowledge.packs():
            for f in p["files"]:
                if not f.endswith(".md"):
                    continue
                for head, quote in _quotes(knowledge.read(f) or ""):
                    items.append({"id": "%s#%d" % (f, len(items)), "pack": p["id"], "file": f, "title": head or f.split("/")[-1],
                                  "text": quote})
        _PROMPTS["items"], _PROMPTS["built"] = items, st.get("built")
    items = _PROMPTS["items"]
    if pack:
        items = [i for i in items if i["pack"] == pack]
    if q:
        ql = [w for w in q.lower().split() if w]
        items = [i for i in items if all(w in (i["title"] + " " + i["text"] + " " + i["pack"]).lower() for w in ql)]
    return {"total": len(_PROMPTS["items"]), "items": items[:limit]}
