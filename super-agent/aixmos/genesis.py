"""
genesis.py -- the first boot. AIXMOS introduces itself, finds out WHO it is working for (student,
employee, or a business owner / builder),
asks the questions that fit that person, shows everything it can do on this machine, and writes a
first plan they can start on today. The role also sets the guardrails the chat and agent follow.

State lives in memory/genesis.json (gitignored, local). The installer may pre-seed it with the
role chosen at install time. Intake answers that match business-profile fields are saved there
too, so every skill, the CRM and the agent see them immediately.

  state()                 -> current genesis record
  catalog(caps)           -> capability showcase with live status for this machine
  save_intake(role, ans)  -> store answers, fill the business profile
  plan()                  -> first plan (local model, deterministic fallback)
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
        "Your conversations, your files and your plans stay here. Nothing leaves unless you connect it.",
        "First I find out who you are: a student, an employee, or someone building a business or project.",
        "Then I learn what you are working on, plan it with you, and do the work alongside you.",
        "Project AIXMOS is a movement meant 4THEPEOPLE: serious AI capability on the hardware you already own, with no gatekeeper.",
    ],
    "principles": [
        ["Local first", "The brain runs on your device. The cloud is optional, never required."],
        ["You hold the keys", "Nothing is sent, posted, paid or deployed without your explicit go."],
        ["Proof over promises", "I show output, verify my work and never invent data."],
        ["Build to own", "Every plan ends with something you own: a skill, a system, an asset."],
    ],
}

ROLES = [
    {"id": "student", "icon": "\U0001F393", "title": "Student",
     "desc": "In school, a program, or teaching yourself. I help you understand faster, plan your coursework and build real projects. I explain and coach; I don't do graded work for you.",
     "intake_title": "Tell me about your studies.",
     "intake_sub": "Classes, deadlines, what you want to get good at. It stays on this machine."},
    {"id": "employee", "icon": "\U0001F4BC", "title": "Employee",
     "desc": "You work for a company. I help you get the job done faster: email, documents, research, planning and small automations, with your employer's data kept on this machine.",
     "intake_title": "Tell me about your work.",
     "intake_sub": "Your role and the tasks that eat your week. Leave out anything confidential; it stays on this machine either way."},
    {"id": "aixmos_member", "icon": "⚡", "title": "Business owner / builder",
     "desc": "You are building your own business, product or side project. I become your build partner.",
     "intake_title": "Tell me what you are building.",
     "intake_sub": "The more you give me, the sharper the plan. Everything stays on this machine."},
    {"id": "everything", "icon": "\U0001F310", "title": "Everything (full station)",
     "desc": "Every feature on: study partner, work helper and build partner in one station.",
     "intake_title": "Tell me what you run and what you are building.",
     "intake_sub": "Your operation, your projects and what is in the way. Everything stays on this machine."},
]
# Roles from installs before 2.1.1 that are no longer offered: they become aixmos_member.  # tmmt-retired
RETIRED_ROLES = ("tmmt_pathway", "tmmt_operator", "both")  # tmmt-retired
ROLE_IDS = {r["id"] for r in ROLES}
ALIASES = {"builder": "aixmos_member", "entrepreneur": "aixmos_member", "movement": "aixmos_member",
           "all": "everything", "full": "everything",
           **{r: "aixmos_member" for r in RETIRED_ROLES + ("pathway", "candidate", "operator")}}  # tmmt-retired

def normalize_role(role):
    r = str(role or "").strip().lower()
    r = ALIASES.get(r, r)
    return r if r in ROLE_IDS else ""

def role_title(role):
    return next((r["title"] for r in ROLES if r["id"] == role), "builder")

def _q(qid, label, ph="", profile=None, required=False, choices=None):
    q = {"id": qid, "label": label, "ph": ph, "profile": profile}
    if required: q["required"] = True
    if choices: q["choices"] = choices
    return q

OWNER = _q("owner", "What should I call you?", "First name is fine", "owner", True)
HOURS = _q("hours", "How many hours a week can you put in?", "e.g. 10")
LEVEL = _q("level", "How comfortable are you with tech?", choices=["Just starting", "Getting there", "I build things"])
VOICE = _q("voice", "How should I talk to you?", "Straight up, warm, professional, hype...", "voice")
BLOCKERS = _q("blockers", "What is in the way?", "Time, skills, money, focus, confidence... be honest")

BUSINESS = [
    OWNER,
    _q("name", "What is the business or project called?", "Working names welcome", "name"),
    _q("type", "What is it, in one line?", "e.g. mobile auto detailing in Houston; a budgeting app for students", "type"),
    _q("services", "What do you sell, or plan to?", "Services, products, offers, pricing if you have it", "services"),
    _q("customers", "Who is it for?", "Your ideal customer or user", "customers"),
    _q("area", "Where do you operate?", "City / region / online", "area"),
    _q("building", "What are you building or working on right now?", "The thing you want to move forward this week", required=True),
    _q("goal", "What does a win look like 90 days from now?", "Revenue, clients, a launched app, hours saved..."),
    BLOCKERS,
    _q("tools", "What tools and accounts do you already use?", "Gmail, Instagram, GoHighLevel, Shopify, Canva, GitHub..."),
    HOURS, LEVEL, VOICE,
]
STUDENT = [
    OWNER,
    _q("school", "Where do you study, and what program or grade?", "e.g. 11th grade; community college nursing; self-taught coding"),
    _q("subjects", "Which classes or subjects matter most right now?", "e.g. algebra, biology, intro to Python"),
    _q("building", "What are you working on right now?", "An assignment, a project, a skill, an application", required=True),
    _q("deadlines", "What deadlines are coming up?", "Exams, due dates, applications"),
    _q("goal", "What does a win look like 90 days from now?", "Grades, a skill, an internship, a finished project"),
    BLOCKERS,
    _q("tools", "What do you use for school?", "Google Docs, Canvas, Notion, GitHub, Quizlet..."),
    _q("hours", "How many hours a week can you study or build?", "e.g. 8"),
    LEVEL, VOICE,
]
EMPLOYEE = [
    OWNER,
    _q("job", "What is your job, and what kind of company is it?", "e.g. office manager at a dental practice. No confidential details needed"),
    _q("tasks", "Which tasks eat most of your week?", "Email, reports, scheduling, data entry, research...", required=True),
    _q("building", "What do you want to get done or improve right now?", "The one thing that would make this week easier", required=True),
    _q("goal", "What does a win look like 90 days from now?", "Hours saved, a promotion case, a process fixed..."),
    _q("policy", "Does your company have rules about AI tools or where work data can go?",
       choices=["Yes, strict rules", "Some rules", "No rules / not sure"]),
    _q("tools", "Which tools does your job run on?", "Outlook, Excel, Google Workspace, Slack, Salesforce..."),
    BLOCKERS,
    _q("hours", "How many hours a week do you want back?", "e.g. 5"),
    LEVEL, VOICE,
]
QUESTIONS_BY_ROLE = {"student": STUDENT, "employee": EMPLOYEE, "aixmos_member": BUSINESS, "everything": BUSINESS}
QUESTIONS = BUSINESS

def questions_for(role):
    return QUESTIONS_BY_ROLE.get(role) or QUESTIONS

# The showcase. `needs` names a capability key from the server's capabilities(); `try` goes into chat.
CATALOG = [
    {"group": "Think & plan", "items": [
        {"icon": "\U0001F9E0", "name": "Private chat brain", "what": "A local model with memory of every conversation. Works with the internet unplugged.", "needs": "ollama", "try": "What can you do for me this week?"},
        {"icon": "\U0001F4DA", "name": "Playbook vault", "what": "Hundreds of passages from business and engineering playbooks, cited automatically in answers.", "needs": "knowledge", "try": "/vault how do I qualify a lead"},
        {"icon": "\U0001F50E", "name": "Web research + fact-check", "what": "Searches the web, reads the top pages, cross-references them against the vault and reports agreements, conflicts and sources.", "needs": None, "try": "/research best way to get my first 10 customers for a local service business"},
        {"icon": "\U0001F3AD", "name": "Skills (playbook personas)", "what": "Switch me into receptionist, appointment setter, cold outreach, content engine, sales, agency OS and more.", "needs": "knowledge", "try": "/skill appointment-setter"},
    ]},
    {"group": "Build", "items": [
        {"icon": "\U0001F916", "name": "Super agent", "what": "Plans and executes multi-step work with real tools: files, commands, Python, web, CRM, media. Sandboxed to its workspace; asks before acting on anything it read online.", "needs": "ollama", "try": "/agent build me a simple landing page and save it in the workspace"},
        {"icon": "\U0001F50C", "name": "MCP + OpenAI-compatible API", "what": "Claude Code, Cursor or any OpenAI-speaking app on this machine can use me: /mcp and /v1 (read-only tools by default).", "needs": None, "try": "How do I connect Claude Code to you over MCP?"},
        {"icon": "\U0001F9E9", "name": "App & automation builder", "what": "Scripts, dashboards, storefronts, MCP servers, local automations, built step by step with proof.", "needs": "ollama", "try": "/agent write a python script that renames my photos by date"},
    ]},
    {"group": "Grow", "items": [
        {"icon": "\U0001F4C8", "name": "CRM + follow-ups", "what": "Leads, AI scoring, appointments, revenue, and follow-up sequences (cold outreach, missed call, no-show, review request).", "needs": None, "try": "/lead Maria Lopez, owns a 3-car rental fleet in Dallas, found on Instagram"},
        {"icon": "✉️", "name": "Email writer", "what": "Drafts, refines and (with your click) sends email from Gmail, Outlook or any SMTP account.", "needs": None, "try": "write an email thanking a new customer and asking for a review"},
        {"icon": "\U0001F5BC", "name": "Instagram carousels", "what": "Hook-driven carousel copy rendered into 1080x1350 slides in your brand colours.", "needs": None, "try": "/carousel 5 mistakes people make when renting a car"},
    ]},
    {"group": "Create", "items": [
        {"icon": "\U0001F3A8", "name": "Image lab", "what": "Image generation that learns your taste from your ratings. Needs a provider key, or the free public service switched on under Integrations.", "needs": "image", "try": "generate an image of a clean black SUV in a studio, product shot"},
        {"icon": "\U0001F3AC", "name": "Video lab", "what": "Text-to-video through providers you connect.", "needs": "video", "try": "make a video of a sunrise over a city skyline"},
        {"icon": "✂️", "name": "Plain-English video editing", "what": "Trim, cut, speed, captions (local speech-to-text) with ffmpeg, from one sentence.", "needs": "video_edit", "try": "trim the first 5 seconds and add captions"},
        {"icon": "\U0001F399", "name": "Voice", "what": "Talk to me and hear replies. Speech-to-text runs locally.", "needs": "captions", "try": None},
    ]},
]

STUDENT_ITEMS = [
    {"icon": "\U0001F9D1‍\U0001F3EB", "name": "Study partner", "what": "Explains any topic step by step, quizzes you and checks your understanding. It teaches; the work you hand in stays yours.", "needs": "ollama", "try": "Explain how compound interest works like I'm new to it, then quiz me with 3 questions"},
    {"icon": "\U0001F5D3", "name": "Assignment & exam planner", "what": "Turns your deadlines into a week-by-week plan saved in your workspace.", "needs": "ollama", "try": "/agent make a study schedule for the next 4 weeks as a markdown file in the workspace"},
    {"icon": "\U0001F4DD", "name": "Research with sources", "what": "Finds and reads sources and tells you where they agree and disagree, so you can cite properly.", "needs": None, "try": "/research how do students find their first internship"},
    {"icon": "\U0001F310", "name": "Portfolio builder", "what": "Build a real project you can show: a site, an app, a script.", "needs": "ollama", "try": "/agent build me a simple personal portfolio web page in the workspace"},
]
EMPLOYEE_ITEMS = [
    {"icon": "✉️", "name": "Email & document drafts", "what": "Drafts and rewrites in your voice. You review and send; nothing goes out on its own.", "needs": "ollama", "try": "write an email to my manager summarizing what I finished this week"},
    {"icon": "\U0001F4CB", "name": "Meeting notes to action items", "what": "Paste notes and get owners, deadlines and next steps.", "needs": "ollama", "try": "Turn these meeting notes into action items with owners and due dates:"},
    {"icon": "⚙️", "name": "Small automations", "what": "Scripts that take the repetitive part of your job off your plate.", "needs": "ollama", "try": "/agent write a python script that merges every CSV file in a folder into one"},
    {"icon": "\U0001F512", "name": "Work data stays here", "what": "What you paste stays on this machine. Cloud providers stay off unless you switch them on, so check your company's AI policy first.", "needs": None, "try": None},
]
ROLE_GROUPS = {
    "student": ("For your studies", STUDENT_ITEMS),
    "employee": ("For your job", EMPLOYEE_ITEMS),
}

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
    if d["role"] in RETIRED_ROLES:          # an install from before 2.1.1 picked a retired role
        d["role"] = "aixmos_member"
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
    if role in ROLE_GROUPS:
        name, items = ROLE_GROUPS[role]
        groups.insert(0, {"group": name, "items": [dict(i, status=_status(i["needs"], caps)) for i in items]})
    return groups

def view(caps=None):
    st = state()
    role = st.get("role")
    return {"state": st, "mission": MISSION, "roles": ROLES, "questions": questions_for(role),
            "questions_by_role": QUESTIONS_BY_ROLE,
            "catalog": catalog(caps, role), "profile": skills.profile(),
            "assistant": settings.pref("assistant_name") or "AIXMOS",
            "console": False}

def save_intake(role, answers):
    answers = {k: str(v or "").strip()[:1500] for k, v in (answers or {}).items() if isinstance(k, str)}
    role = normalize_role(role) or state().get("role") or ""
    prof = {}
    for q in questions_for(role):
        f = q.get("profile")
        if f and answers.get(q["id"]):
            prof[f] = answers[q["id"]]
    if answers.get("customers") and not skills.profile().get("audience"):
        prof["audience"] = answers["customers"]
    if prof:
        skills.save_profile(prof)
    with _LOCK:
        d = _read()
        if role:
            d["role"] = role
        d.setdefault("answers", {}).update(answers)
        d["intake_ts"] = time.time()
        _write(d)
    return state()

def _brief(st):
    a = st.get("answers", {})
    rows = [("Role", role_title(st.get("role")))] + [(q["label"], a.get(q["id"], "")) for q in questions_for(st.get("role"))]
    return "\n".join("- %s %s" % (k, v) for k, v in rows if v)

ROLE_SKILLS = {
    "student": ["prompt-vault", "app-builder", "claude-code-starter-kit", "side-hustle-vault"],
    "employee": ["business-prompt-vault", "local-automation", "dashboard-kit", "prompt-vault"],
    "everything": ["business-builder", "sales-pack", "appointment-setter", "app-builder"],
}

def _suggest_skills(st):
    out = [s for s in ROLE_SKILLS.get(st.get("role"), []) if skills.get(s)][:2]
    a = " ".join(str(v) for v in st.get("answers", {}).values()).lower()
    rules = [("appointment", "appointment-setter"), ("book", "appointment-setter"), ("call", "receptionist"),
             ("lead", "lead-gen"), ("customer", "lead-gen"), ("outreach", "cold-outreach"), ("instagram", "content-engine"),
             ("content", "content-engine"), ("tiktok", "viral-reel"), ("reel", "viral-reel"), ("app", "app-builder"),
             ("website", "app-builder"), ("store", "storefront-kit"), ("shop", "storefront-kit"), ("agency", "agency-os"),
             ("automat", "local-automation"), ("sales", "sales-pack"), ("side", "side-hustle-vault"), ("dashboard", "dashboard-kit")]
    for word, sid in rules:
        if word in a and sid not in out and skills.get(sid):
            out.append(sid)
    for fallback in ROLE_SKILLS.get(st.get("role"), []) + ["business-builder", "ai-building-kit"]:
        if len(out) < 3 and skills.get(fallback) and fallback not in out:
            out.append(fallback)
    return out[:4]

def _fallback_plan(st, picks):
    a, role = st.get("answers", {}), st.get("role")
    who = a.get("owner") or "you"
    building = a.get("building") or "your first step"
    goal = a.get("goal") or "a clear, measurable win in 90 days"
    hours = a.get("hours") or "a few"
    skills_md = ["- `/skill %s`" % p for p in picks] or ["- `/skill business-builder`"]
    if role == "student":
        lines = ["# Your first study plan", "", "**For:** %s  |  **Working on:** %s  |  **90-day win:** %s" % (who, building, goal), "",
                 "## This week (%s hours)" % hours,
                 "1. **Map your deadlines.** Type `/agent make a study schedule for the next 4 weeks as a markdown file in the workspace` and paste your due dates.",
                 "2. **Learn one hard topic properly.** Ask me to explain it step by step, then say `quiz me` and answer without looking.",
                 "3. **Find good sources.** Type `/research %s` and keep the links for your citations." % building, "",
                 "## Next 30 days",
                 "- One short review session per class each week: ask me to quiz you on last week's notes.",
                 "- Start one portfolio project you can show (`/agent build me a simple personal portfolio web page`).",
                 "- Honest rule: I explain, outline, quiz and give feedback. The work you hand in is written by you.", "",
                 "## Skills to switch on", ""] + skills_md
    elif role == "employee":
        lines = ["# Your first work plan", "", "**For:** %s  |  **Improving:** %s  |  **90-day win:** %s" % (who, building, goal), "",
                 "## This week (%s hours back is the target)" % hours,
                 "1. **Pick the task that eats the most time** (%s) and tell me exactly how you do it today." % (a.get("tasks") or "your biggest time sink"),
                 "2. **Turn it into a template or a script.** Type `/agent write a python script that ...` or ask me for a reusable email/report template.",
                 "3. **Check the rules first.** Your company's AI policy (%s) decides what you paste in. Everything here stays on this machine." % (a.get("policy") or "not sure yet"), "",
                 "## Next 30 days",
                 "- Every Friday, ask me to draft your weekly status update from your notes.",
                 "- Automate one more repetitive task a week, then measure the hours you got back.", "",
                 "## Skills to switch on", ""] + skills_md
    else:
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
                 "## Skills to switch on", ""] + skills_md
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

ROLE_BRIEFS = {
    "student": "The client is a STUDENT. Write a study plan: understanding, deadlines, sources, a portfolio project. "
               "Never offer to write graded work for them; offer to explain, outline, quiz and give feedback.",
    "employee": "The client is an EMPLOYEE. Write a work plan that saves them hours: templates, drafts, small automations. "
                "Remind them to follow their company's AI policy; their work data stays on this machine.",
    "everything": "The client runs the full station: study, work and their own business, products and apps. "
                  "Plan across their work and one build project.",
}

def plan(timeout=300):
    st = state()
    role = st.get("role")
    picks = _suggest_skills(st)
    brief = _brief(st)
    kb = ""
    try:
        kb = knowledge.context_for((st.get("answers", {}).get("building") or "") + " " + (st.get("answers", {}).get("goal") or ""),
                                   k=3, min_score=4.0, max_chars=1800)
    except Exception:
        kb = ""
    system = ("You are AIXMOS, a private local AI operator and partner, meeting your client for the first time. %s "
              "Write their first plan in markdown. Be concrete and honest, no hype, no invented facts or numbers. "
              "Structure: '# Your first plan' (one-line summary), '## This week' (3 numbered actions sized to their hours, "
              "each with an exact command they can type to you), "
              "'## Next 30 days' (3-5 bullets), '## Milestones to the 90-day win' (3 bullets), '## Skills to switch on' "
              "(use exactly these: %s), '## What I need from you' (2-3 bullets). Under 380 words."
              % (ROLE_BRIEFS.get(role, "The client is building their own business or project."), ", ".join(picks)))
    user = "Client intake:\n" + brief + (("\n\nRelevant playbook knowledge:\n" + kb) if kb else "")
    user += ("\n\nThe ONLY commands that exist: " + ", ".join(COMMANDS) +
             ". A skill is switched on with '/skill <name>'. Never write any other slash command."
             "\nExample action: 1. **Map your offer.** Type `/research how car rental companies in Dallas price weekly rentals` and I will bring back a cited report.")
    md = llm.text(system, user, temperature=0.3, num_ctx=4096, timeout=timeout) if llm.available() else ""
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
    role = normalize_role(role)
    with _LOCK:
        d = _read()
        if role and not d.get("role"):
            d["role"] = role
        d.setdefault("installed_ts", time.time())
        _write(d)

ROLE_RULES = {
    "student": ["Academic integrity: teach, explain, quiz, outline and give feedback. Do not write graded work for them to submit as "
                "their own; if asked, offer to coach them through it instead. Encourage citing sources."],
    "employee": ["Their employer's information stays on this machine. Do not suggest pasting confidential work into cloud tools.",
                 "Follow their company's AI policy (they said: %s). You draft; they review and send."],
}

def mission_context():
    st = state()
    if not st.get("answers"):
        return ""
    a, role = st["answers"], st.get("role")
    bits = ["CLIENT MISSION (learned at first boot; keep moving this forward):", "Role: " + role_title(role)]
    for k, label in (("owner", "Name"), ("school", "Studies"), ("job", "Job"), ("building", "Working on now"), ("goal", "90-day win"),
                     ("blockers", "Blockers"), ("tools", "Tools they use"), ("hours", "Hours/week"), ("level", "Tech comfort")):
        if a.get(k):
            bits.append("%s: %s" % (label, a[k][:300]))
    for rule in ROLE_RULES.get(role, []):
        bits.append(rule % (a.get("policy") or "not sure") if "%s" in rule else rule)
    bits.append("Serve the Project AIXMOS mission: local-first AI for the people. Tie suggestions back to their goal and 90-day win; "
                "suggest the next concrete step and the exact command when useful.")
    return "\n".join(bits)
