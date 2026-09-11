"""
genesis.py -- the first boot. AIXMOS introduces itself, states the mission, learns who it is
working for (role, business, goals, what they are building, what blocks them), shows everything
it can do on this machine, and writes a first build plan the client can start on today.

State lives in memory/genesis.json (gitignored, local). The installer may pre-seed it with the
role chosen at install time. Intake answers that match business-profile fields are saved there
too, so every skill, the CRM and the agent see them immediately.

  state()                 -> current genesis record
  catalog(caps)           -> capability showcase with live status for this machine
  save_intake(role, ans)  -> store answers, fill the business profile
  plan()                  -> first build plan (local model, deterministic fallback)
  complete() / reset()
  mission_context()       -> short block the chat + agent system prompts carry after intake
"""
import os, json, time, threading
from . import settings, skills, knowledge, llm

FILE = os.path.join(settings.MEMDIR, "genesis.json")
_LOCK = threading.Lock()

MISSION = {
    "name": "PROJECT AIXMOS",
    "tagline": "AI for the people. Owned by the people who use it.",
    "lines": [
        "I am AIXMOS: a private AI operator that lives on this machine, not in someone else's cloud.",
        "Your conversations, your leads, your files and your plans stay here. Nothing leaves unless you connect it.",
        "My job is to move your builds forward: learn what you are building, plan it with you, then do the work alongside you.",
        "I carry a vault of business and engineering playbooks, a super agent with real tools, and a CRM, and I learn your voice as we go.",
        "Project AIXMOS is a movement meant 4THEPEOPLE: serious AI capability on the hardware you already own, with no gatekeeper.",
    ],
    "principles": [
        ["Local first", "The brain runs on your device. The cloud is optional, never required."],
        ["You hold the keys", "Nothing is sent, posted, paid or deployed without your explicit go."],
        ["Proof over promises", "I show output, verify my work and never invent data."],
        ["Build to own", "Every plan ends with something you own: a system, a skill, an asset."],
    ],
}

ROLES = [
    {"id": "tmmt_operator", "icon": "\U0001F697", "title": "TMMT Operator",
     "desc": "You run rentals, detailing, dispatch or sales inside the TMMT network. I load the operator playbooks, scorecards and your console."},
    {"id": "aixmos_member", "icon": "⚡", "title": "AIXMOS Movement",
     "desc": "You are here to build with AI: your own business, product or side project. I become your build partner."},
    {"id": "both", "icon": "\U0001F6E1", "title": "Both",
     "desc": "Operator by day, builder always. You get the TMMT playbooks and the full build partner."},
]

QUESTIONS = [
    {"id": "owner", "label": "What should I call you?", "ph": "First name is fine", "profile": "owner", "required": True},
    {"id": "name", "label": "What is the business or project called?", "ph": "Working names welcome", "profile": "name"},
    {"id": "type", "label": "What is it, in one line?", "ph": "e.g. mobile auto detailing in Houston; a budgeting app for students", "profile": "type"},
    {"id": "services", "label": "What do you sell, or plan to?", "ph": "Services, products, offers, pricing if you have it", "profile": "services"},
    {"id": "customers", "label": "Who is it for?", "ph": "Your ideal customer or user", "profile": "customers"},
    {"id": "area", "label": "Where do you operate?", "ph": "City / region / online", "profile": "area"},
    {"id": "building", "label": "What are you building or working on right now?", "ph": "The thing you want to move forward this week", "required": True},
    {"id": "goal", "label": "What does a win look like 90 days from now?", "ph": "Revenue, clients, a launched app, hours saved..."},
    {"id": "blockers", "label": "What is in the way?", "ph": "Time, skills, leads, money, tech, focus... be honest"},
    {"id": "tools", "label": "What tools and accounts do you already use?", "ph": "Gmail, Instagram, GoHighLevel, Shopify, Canva, GitHub..."},
    {"id": "hours", "label": "How many hours a week can you put in?", "ph": "e.g. 10", "profile": None},
    {"id": "level", "label": "How comfortable are you with tech?", "choices": ["Just starting", "Getting there", "I build things"]},
    {"id": "voice", "label": "How should I talk to you (and write as your brand)?", "ph": "Straight up, warm, professional, hype...", "profile": "voice"},
]

# The showcase. `needs` names a capability key from the server's capabilities(); `try` goes into chat.
CATALOG = [
    {"group": "Think & plan", "items": [
        {"icon": "\U0001F9E0", "name": "Private chat brain", "what": "A local model with memory of every conversation. Works with the internet unplugged.", "needs": "ollama", "try": "What can you do for my business this week?"},
        {"icon": "\U0001F4DA", "name": "Playbook vault", "what": "Hundreds of passages from business and engineering playbooks, cited automatically in answers.", "needs": "knowledge", "try": "/vault how do I qualify a lead"},
        {"icon": "\U0001F50E", "name": "Web research + fact-check", "what": "Searches the web, reads the top pages, cross-references them against the vault and reports agreements, conflicts and sources.", "needs": None, "try": "/research best way to get my first 10 customers for a local service business"},
        {"icon": "\U0001F3AD", "name": "Skills (24 playbook personas)", "what": "Switch me into receptionist, appointment setter, cold outreach, content engine, sales, agency OS and more.", "needs": "knowledge", "try": "/skill appointment-setter"},
    ]},
    {"group": "Build", "items": [
        {"icon": "\U0001F916", "name": "Super agent", "what": "Plans and executes multi-step work with real tools: files, commands, Python, web, CRM, media. Sandboxed to its workspace.", "needs": "ollama", "try": "/agent build me a simple landing page for my business and save it in the workspace"},
        {"icon": "\U0001F50C", "name": "MCP + OpenAI-compatible API", "what": "Claude Code, Cursor or any OpenAI-speaking app can drive me: /mcp and /v1 on this machine.", "needs": None, "try": "How do I connect Claude Code to you over MCP?"},
        {"icon": "\U0001F9E9", "name": "App & automation builder", "what": "Scripts, dashboards, storefronts, MCP servers, local automations, built step by step with proof.", "needs": "ollama", "try": "/agent write a python script that renames my photos by date"},
    ]},
    {"group": "Grow the business", "items": [
        {"icon": "\U0001F4C8", "name": "CRM + follow-ups", "what": "Leads, AI scoring, appointments, revenue, and follow-up sequences (cold outreach, missed call, no-show, review request).", "needs": None, "try": "/lead Maria Lopez, owns a 3-car rental fleet in Dallas, found on Instagram"},
        {"icon": "✉️", "name": "Email writer", "what": "Drafts, refines and (with your click) sends email from Gmail, Outlook or any SMTP account.", "needs": None, "try": "write an email to a new customer thanking them and asking for a review"},
        {"icon": "\U0001F5BC", "name": "Instagram carousels", "what": "Hook-driven carousel copy rendered into 1080x1350 slides in your brand colours.", "needs": None, "try": "/carousel 5 mistakes people make when renting a car"},
    ]},
    {"group": "Create", "items": [
        {"icon": "\U0001F3A8", "name": "Image lab", "what": "Image generation that learns your taste from your ratings. Free provider works with no key.", "needs": "image", "try": "generate an image of a clean black SUV in a studio, product shot"},
        {"icon": "\U0001F3AC", "name": "Video lab", "what": "Text-to-video through providers, plus a zero-key local storyboard fallback.", "needs": "video", "try": "make a video of a sunrise over a city skyline"},
        {"icon": "✂️", "name": "Plain-English video editing", "what": "Trim, cut, speed, captions (local speech-to-text) with ffmpeg, from one sentence.", "needs": "video_edit", "try": "trim the first 5 seconds and add captions"},
        {"icon": "\U0001F399", "name": "Voice", "what": "Talk to me and hear replies. Speech-to-text runs locally.", "needs": "captions", "try": None},
    ]},
]

TMMT_ITEMS = [
    {"icon": "\U0001F697", "name": "TMMT operator playbooks", "what": "Rentals, detailing, dispatch/fleet and sales-leasing playbooks, the operator scorecard and onboarding SOPs, all in the vault.", "needs": "knowledge", "try": "/vault operator scorecard"},
    {"icon": "\U0001F39B", "name": "Operator console", "what": "Your role-locked TMMT console: briefing, dispatch, cases, calendar, assistant. Voice and Ctrl+K.", "needs": None, "try": None},
]

def _read():
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}

def _write(d):
    os.makedirs(settings.MEMDIR, exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, FILE)

def state():
    with _LOCK:
        d = _read()
    d.setdefault("done", False)
    d.setdefault("role", "")
    d.setdefault("answers", {})
    return d

def _status(needs, caps):
    if not needs:
        return "ready"
    v = (caps or {}).get(needs)
    if needs == "knowledge":
        return "ready" if (v or {}).get("chunks") else "indexing"
    return "ready" if v else "setup"

def catalog(caps=None, role=None):
    role = role or state().get("role")
    groups = [dict(g, items=[dict(i, status=_status(i["needs"], caps)) for i in g["items"]]) for g in CATALOG]
    if role in ("tmmt_operator", "both"):
        groups.insert(0, {"group": "TMMT operator", "items": [dict(i, status=_status(i["needs"], caps)) for i in TMMT_ITEMS]})
    return groups

def operator_console():
    """Path of the TMMT operator console the installer drops next to the app, if present."""
    p = os.path.join(settings.ROOT, "operator", "TMMT-Operator-Console.html")
    return p if os.path.isfile(p) else ""

def view(caps=None):
    st = state()
    return {"state": st, "mission": MISSION, "roles": ROLES, "questions": QUESTIONS,
            "catalog": catalog(caps, st.get("role")), "profile": skills.profile(),
            "assistant": settings.pref("assistant_name") or "AIXMOS", "console": bool(operator_console())}

def save_intake(role, answers):
    answers = {k: str(v or "").strip()[:1500] for k, v in (answers or {}).items() if isinstance(k, str)}
    prof = {}
    for q in QUESTIONS:
        f = q.get("profile")
        if f and answers.get(q["id"]):
            prof[f] = answers[q["id"]]
    if answers.get("customers") and not skills.profile().get("audience"):
        prof["audience"] = answers["customers"]
    if prof:
        skills.save_profile(prof)
    with _LOCK:
        d = _read()
        if role in {r["id"] for r in ROLES}:
            d["role"] = role
        d.setdefault("answers", {}).update(answers)
        d["intake_ts"] = time.time()
        _write(d)
    return state()

def _brief(st):
    a = st.get("answers", {})
    role = next((r["title"] for r in ROLES if r["id"] == st.get("role")), "builder")
    rows = [("Role", role)] + [(q["label"], a.get(q["id"], "")) for q in QUESTIONS]
    return "\n".join("- %s %s" % (k, v) for k, v in rows if v)

def _suggest_skills(st):
    a = " ".join(str(v) for v in st.get("answers", {}).values()).lower()
    rules = [("appointment", "appointment-setter"), ("book", "appointment-setter"), ("call", "receptionist"),
             ("lead", "lead-gen"), ("customer", "lead-gen"), ("outreach", "cold-outreach"), ("instagram", "content-engine"),
             ("content", "content-engine"), ("tiktok", "viral-reel"), ("reel", "viral-reel"), ("app", "app-builder"),
             ("website", "app-builder"), ("store", "storefront-kit"), ("shop", "storefront-kit"), ("agency", "agency-os"),
             ("automat", "local-automation"), ("sales", "sales-pack"), ("side", "side-hustle-vault"), ("dashboard", "dashboard-kit")]
    out = []
    for word, sid in rules:
        if word in a and sid not in out and skills.get(sid):
            out.append(sid)
    if st.get("role") in ("tmmt_operator", "both") and skills.get("sales-pack") and "sales-pack" not in out:
        out.append("sales-pack")
    for fallback in ("business-builder", "ai-building-kit"):
        if len(out) < 3 and skills.get(fallback) and fallback not in out:
            out.append(fallback)
    return out[:4]

def _fallback_plan(st, picks):
    a = st.get("answers", {})
    who = a.get("owner") or "you"
    building = a.get("building") or "your first build"
    goal = a.get("goal") or "a clear, measurable win in 90 days"
    hours = a.get("hours") or "a few"
    lines = ["# Your first build plan", "",
             "**For:** %s  |  **Building:** %s  |  **90-day win:** %s" % (who, building, goal), "",
             "## This week (%s hours)" % hours,
             "1. **Define the win.** One sentence, one number. Ask me: `turn my 90-day goal into weekly targets`.",
             "2. **Ship the smallest useful piece of %s.** Ask the agent: `/agent break %s into the smallest shippable step and build it`." % (building, building),
             "3. **Get it in front of one real person.** Ask me to draft the message: `write an email to a potential customer about %s`." % building, "",
             "## Next 30 days",
             "- Put every lead in the CRM (`/lead ...`) and let the follow-up sequences carry the chasing.",
             "- Post two carousels a week (`/carousel ...`) in your brand voice.",
             "- Run the 15-minute weekly review every Friday in Ops & CRM.", "",
             "## Skills to switch on", ""]
    lines += ["- `/skill %s`" % p for p in picks] or ["- `/skill business-builder`"]
    if a.get("blockers"):
        lines += ["", "## What is in the way, and the first move on it", "- %s: tell me about it and I will research options with `/research`." % a["blockers"]]
    return "\n".join(lines)

COMMANDS = ["/agent <goal>", "/research <question>", "/vault <question>", "/skill <name>", "/lead <details>",
            "/book <details>", "/carousel <topic>", "/image <prompt>", "/video <prompt>", "/email <request>"]
_VERBS = {c.split()[0][1:] for c in COMMANDS}

def _clean_commands(md):
    """Small local models invent slash commands (/lead-gen, /app-builder). Rewrite them to real ones."""
    import re
    ids = {s["id"] for s in skills.list_skills()}
    def fix(m):
        word = m.group(2)
        if word in _VERBS:
            return m.group(0)
        if word in ids:
            return m.group(1) + "/skill " + word
        return m.group(1) + word.replace("-", " ")
    md = re.sub(r"(^|[\s`(:])/([a-z][a-z0-9-]*)\b", fix, md, flags=re.M)
    return re.sub(r"/skill (/?skill )+", "/skill ", md)

def plan(timeout=300):
    st = state()
    picks = _suggest_skills(st)
    brief = _brief(st)
    kb = ""
    try:
        kb = knowledge.context_for((st.get("answers", {}).get("building") or "") + " " + (st.get("answers", {}).get("goal") or ""),
                                   k=3, min_score=4.0, max_chars=1800)
    except Exception:
        kb = ""
    system = ("You are AIXMOS, a private local AI operator and build partner, meeting your client for the first time. "
              "Write their first build plan in markdown. Be concrete and honest, no hype, no invented facts or numbers. "
              "Structure: '# Your first build plan' (one-line summary), '## This week' (3 numbered actions sized to their hours, "
              "each with an exact command they can type to you, such as /agent ..., /research ..., /lead ..., /carousel ..., /skill ...), "
              "'## Next 30 days' (3-5 bullets), '## Milestones to the 90-day win' (3 bullets), '## Skills to switch on' "
              "(use exactly these: %s), '## What I need from you' (2-3 bullets). Under 380 words." % ", ".join(picks))
    user = "Client intake:\n" + brief + (("\n\nRelevant playbook knowledge:\n" + kb) if kb else "")
    user += ("\n\nThe ONLY commands that exist: " + ", ".join(COMMANDS) +
             ". A skill is switched on with '/skill <name>'. Never write any other slash command."
             "\nExample action: 1. **Map your offer.** Type `/research how car rental companies in Dallas price weekly rentals` and I will bring back a cited report.")
    md = llm.text(system, user, temperature=0.3, num_ctx=4096, timeout=timeout) if llm.list_models() else ""
    source = "model"
    if len(md) < 200:
        md, source = _fallback_plan(st, picks), "template"
    else:
        md = _clean_commands(md)
    with _LOCK:
        d = _read()
        d["plan"] = md; d["plan_source"] = source; d["plan_ts"] = time.time(); d["skills"] = picks
        _write(d)
    return {"plan": md, "source": source, "skills": picks}

def complete(activate_skill=None):
    if activate_skill:
        try:
            skills.activate(activate_skill)
        except ValueError:
            pass
    with _LOCK:
        d = _read(); d["done"] = True; d["done_ts"] = time.time(); _write(d)
    return state()

def reset():
    with _LOCK:
        d = _read(); d["done"] = False; _write(d)
    return state()

def seed(role):
    """Called by the installer: remember the role picked at install time, without touching anything else."""
    with _LOCK:
        d = _read()
        if role in {r["id"] for r in ROLES} and not d.get("role"):
            d["role"] = role
        d.setdefault("installed_ts", time.time())
        _write(d)

def mission_context():
    st = state()
    if not st.get("answers"):
        return ""
    a = st["answers"]
    role = next((r["title"] for r in ROLES if r["id"] == st.get("role")), "builder")
    bits = ["CLIENT MISSION (learned at first boot; keep moving this forward):", "Role: " + role]
    for k, label in (("owner", "Name"), ("building", "Building now"), ("goal", "90-day win"), ("blockers", "Blockers"),
                     ("tools", "Tools they use"), ("hours", "Hours/week"), ("level", "Tech comfort")):
        if a.get(k):
            bits.append("%s: %s" % (label, a[k][:300]))
    bits.append("Serve the Project AIXMOS mission: local-first AI for the people. Tie suggestions back to their build and 90-day win; "
                "suggest the next concrete step and the exact command when useful.")
    return "\n".join(bits)
