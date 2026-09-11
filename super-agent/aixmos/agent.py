"""
agent.py -- the AIXMOS super agent: a tool-using loop on the local model that can read and
write files, run commands and Python in a sandboxed workspace, browse the web, search the
knowledge vault, generate media, work the CRM, draft mail, remember things, and ask you
when it is unsure. Doctrine comes straight from the kit: plan before acting, small steps,
prove with real output, never fabricate, leave the human a veto.

Autonomy levels:
  safe     read-only tools + knowledge + media generation, no shell, no writes outside workspace
  builder  + write files and run commands/python inside the allowed roots (default)
  full     + send email (needs a connected account and agent_allow_send)
"""
import os, re, sys, json, time, glob, shutil, threading, subprocess, urllib.parse
from . import settings, llm, jobs, media, knowledge, skills, crm, imagegen, videogen, videoedit, email_tools

WORKSPACE = os.path.join(settings.MEMDIR, "workspace")
NOTES = os.path.join(settings.MEMDIR, "agent_notes.json")
RUNS = os.path.join(settings.MEMDIR, "agent_runs.json")
_LOCK = threading.Lock()
LEVELS = ("safe", "builder", "full")
TOOL_OUT_CAP = 5000

# ------------------------------------------------------------- helpers ----
def roots(extra=None):
    out = [os.path.abspath(WORKSPACE)]
    for r in re.split(r"[;\n]+", (settings.pref("agent_roots") or "") + ";" + (extra or "")):
        r = r.strip().strip('"')
        if r and os.path.isdir(r):
            out.append(os.path.abspath(r))
    return out

def _safe(path, ctx):
    p = os.path.abspath(os.path.join(WORKSPACE, path) if not os.path.isabs(path) else path)
    for r in ctx["roots"]:
        if p == r or p.startswith(r + os.sep):
            return p
    raise PermissionError("path outside the allowed roots (%s)" % ", ".join(ctx["roots"]))

def _cap(s, n=TOOL_OUT_CAP):
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "\n…[truncated %d chars]" % (len(s) - n)

def _needs(level, ctx):
    if LEVELS.index(ctx["autonomy"]) < LEVELS.index(level):
        raise PermissionError("this tool needs autonomy '%s' (current: %s)" % (level, ctx["autonomy"]))

def _notes():
    try:
        with open(NOTES, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []

# --------------------------------------------------------------- tools ----
def t_list_dir(a, ctx):
    p = _safe(a.get("path") or ".", ctx)
    if not os.path.isdir(p):
        return "not a directory: " + p
    rows = []
    for name in sorted(os.listdir(p))[:300]:
        fp = os.path.join(p, name)
        rows.append(("%s/" % name) if os.path.isdir(fp) else "%s (%d bytes)" % (name, os.path.getsize(fp)))
    return "\n".join(rows) or "(empty)"

def t_read_file(a, ctx):
    p = _safe(a["path"], ctx)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read(int(a.get("max_chars") or 12000))

def t_write_file(a, ctx):
    _needs("builder", ctx)
    p = _safe(a["path"], ctx)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    mode = "a" if a.get("append") else "w"
    with open(p, mode, encoding="utf-8") as f:
        f.write(a.get("content") or "")
    ctx["artifacts"].append(p)
    return "wrote %d chars to %s" % (len(a.get("content") or ""), p)

def t_search_files(a, ctx):
    p = _safe(a.get("path") or ".", ctx)
    pat = re.compile(a["pattern"], re.I)
    hits = []
    for dp, dn, fn in os.walk(p):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git", "__pycache__", "vendor")]
        for f in fn:
            fp = os.path.join(dp, f)
            if os.path.getsize(fp) > 2_000_000:
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if pat.search(line):
                            hits.append("%s:%d: %s" % (os.path.relpath(fp, p), i, line.strip()[:160]))
                            if len(hits) >= 80:
                                return "\n".join(hits)
            except OSError:
                pass
    return "\n".join(hits) or "no matches"

def _run(cmdlist, cwd, timeout, shell=False):
    proc = subprocess.run(cmdlist, cwd=cwd, capture_output=True, timeout=timeout, shell=shell, **media._no_window())
    out = proc.stdout.decode("utf-8", "replace") + (("\n[stderr]\n" + proc.stderr.decode("utf-8", "replace")) if proc.stderr.strip() else "")
    return "exit code %d\n%s" % (proc.returncode, out.strip() or "(no output)")

def t_run_command(a, ctx):
    _needs("builder", ctx)
    cwd = _safe(a.get("cwd") or ".", ctx)
    cmd = str(a["command"])
    if re.search(r"\b(format|diskpart|shutdown|restart-computer|rm\s+-rf\s+/|del\s+/s\s+/q\s+c:\\|remove-item\s+-recurse.*c:\\\s*$)", cmd, re.I):
        raise PermissionError("refused: destructive system command")
    shell_cmd = (["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd]
                 if os.name == "nt" else ["/bin/bash", "-lc", cmd])
    try:
        return _run(shell_cmd, cwd, int(a.get("timeout") or 180))
    except subprocess.TimeoutExpired:
        return "command timed out"

def t_run_python(a, ctx):
    _needs("builder", ctx)
    cwd = _safe(a.get("cwd") or ".", ctx)
    tmp = os.path.join(cwd, "_agent_%d.py" % int(time.time() * 1000))
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(a["code"])
    try:
        py = sys.executable or shutil.which("python3") or shutil.which("python") or "python"
        return _run([py, tmp], cwd, int(a.get("timeout") or 180))
    except subprocess.TimeoutExpired:
        return "python timed out"
    finally:
        try: os.remove(tmp)
        except OSError: pass

def t_web_fetch(a, ctx):
    from . import research
    page = research.fetch(a["url"], max_chars=int(a.get("max_chars") or 8000))
    return "HTTP %d %s%s\n%s" % (page["status"], page["url"], (" — " + page["title"]) if page["title"] else "", page["text"])

def t_web_search(a, ctx):
    from . import research
    hits, errors = research.search(a["query"], n=int(a.get("max_results") or 8))
    out = ["- %s\n  %s\n  %s" % (h["title"], h["url"], h["snippet"][:200]) for h in hits]
    if errors and not hits:
        return "no results (" + "; ".join(errors) + ")"
    return "\n".join(out) + ("\n(engine: %s)" % (hits[0]["engine"] if hits else "")) if out else "no results"

def t_research(a, ctx):
    from . import research
    rep = research.run(a["question"], depth=a.get("depth") or "normal", cross=bool(a.get("cross_reference", True)))
    return rep["markdown"]

def t_knowledge_search(a, ctx):
    hits = knowledge.search(a["query"], k=int(a.get("k") or 5), pack=a.get("pack"))
    return "\n\n".join("[%s / %s — %s] (score %s)\n%s" % (h["pack"], h["file"], h["title"], h["score"], h["text"][:900]) for h in hits) or "nothing relevant in the vault"

def t_remember(a, ctx):
    notes = _notes()
    notes.append({"ts": time.time(), "note": str(a["note"])[:1000], "tags": a.get("tags") or []})
    with open(NOTES, "w", encoding="utf-8") as f:
        json.dump(notes[-500:], f, ensure_ascii=False, indent=1)
    return "remembered"

def t_recall(a, ctx):
    q = str(a.get("query") or "").lower().split()
    notes = [n for n in _notes() if all(w in (n["note"] + " " + " ".join(n.get("tags") or [])).lower() for w in q)]
    return "\n".join("- %s" % n["note"] for n in notes[-20:]) or "no matching notes"

def t_generate_image(a, ctx):
    it = imagegen.generate(a["prompt"], style=a.get("style"), size=a.get("size"))
    ctx["artifacts"].append(it["url"])
    return "image saved: %s (prompt used: %s)" % (it["url"], it["final_prompt"][:200])

def t_generate_video(a, ctx):
    job = videogen.generate(a["prompt"], provider=a.get("provider"), image_url=a.get("image_url"), seconds=a.get("seconds"), aspect=a.get("aspect"))
    return "video job started: id=%s provider=%s. It renders in the background (minutes); do not wait for it, tell the user it is in the Video Lab." % (job["id"], job["meta"]["provider"])

def t_edit_video(a, ctx):
    job = videoedit.edit(a["source"], a["instruction"])
    return "edit job started: id=%s. Result appears in the Video Lab when done." % job["id"]

def t_crm_add_lead(a, ctx):
    lead = crm.upsert_lead(a)
    return "lead saved: id=%s status=%s" % (lead["id"], lead["status"])

def t_crm_list_leads(a, ctx):
    leads = crm.list_leads(a.get("status"))
    return "\n".join("- id=%s %s / %s / %s / status=%s / next=%s" % (l["id"], l.get("name", ""), l.get("company", ""), l.get("contact", ""), l.get("status"), l.get("next_action", "")) for l in leads[:60]) or "no leads"

def t_crm_book(a, ctx):
    ap = crm.book(a)
    return "appointment booked: id=%s %s at %s" % (ap["id"], ap["name"] or ap["contact"], ap["when"])

def t_crm_sequence(a, ctx):
    s = crm.start_sequence(a["kind"], lead_id=a.get("lead_id"), contact=a.get("contact"), name=a.get("name"))
    return "sequence %s started (%d steps, first due %s)" % (s["id"], len(s["steps"]), s["steps"][0]["due"])

def t_draft_email(a, ctx):
    accs = email_tools.list_accounts()
    d = email_tools.draft(a["intent"], to=[a["to"]] if a.get("to") else None, tone=a.get("tone") or "professional", account_id=(accs[0]["id"] if accs else None))
    ctx["drafts"].append({"to": a.get("to"), **d})
    return "DRAFT (not sent)\nSubject: %s\n\n%s" % (d["subject"], d["body"])

def t_send_email(a, ctx):
    _needs("full", ctx)
    if not settings.pref("agent_allow_send"):
        raise PermissionError("sending is disabled (Integrations → agent → allow send)")
    accs = email_tools.list_accounts()
    if not accs:
        raise RuntimeError("no email account connected")
    acc = next((x["id"] for x in accs if x["email"] == a.get("from")), accs[0]["id"])
    res = email_tools.send(acc, a["to"], a["subject"], a["body"])
    return "sent to %s from %s" % (", ".join(res["to"]), res["from"])

def t_ask_user(a, ctx):
    job = ctx.get("job")
    if not job:
        return "ask_user is not available on this surface; choose the safest reasonable option and state the assumption."
    job["question"], job["status"], job["progress"] = str(a["question"])[:1000], "waiting", "waiting for your answer"
    ev = ctx["event"]; ev.clear()
    ev.wait(timeout=6 * 3600)
    job["status"] = "running"
    ans = job.pop("answer", None)
    job["question"] = None
    if ans is None:
        raise RuntimeError("no answer received")
    return "USER ANSWER: " + str(ans)

def t_finish(a, ctx):
    ctx["final"] = str(a.get("summary") or "done")
    return "finished"

TOOLS = [
    ("list_dir", "List files in a directory inside the workspace / allowed roots.", {"path": "string"}, [], t_list_dir, "safe"),
    ("read_file", "Read a text file.", {"path": "string", "max_chars": "integer"}, ["path"], t_read_file, "safe"),
    ("write_file", "Create or overwrite (or append to) a text file. Use for code, docs, data.", {"path": "string", "content": "string", "append": "boolean"}, ["path", "content"], t_write_file, "builder"),
    ("search_files", "Regex search across files under a path.", {"pattern": "string", "path": "string"}, ["pattern"], t_search_files, "safe"),
    ("run_command", "Run a PowerShell command inside the workspace (build, test, git, install). Returns exit code and output.", {"command": "string", "cwd": "string", "timeout": "integer"}, ["command"], t_run_command, "builder"),
    ("run_python", "Execute a Python snippet in the workspace and return its output.", {"code": "string", "cwd": "string", "timeout": "integer"}, ["code"], t_run_python, "builder"),
    ("web_fetch", "Fetch a URL and return its readable text.", {"url": "string", "max_chars": "integer"}, ["url"], t_web_fetch, "safe"),
    ("web_search", "Search the web (Google when a key is configured, otherwise DuckDuckGo) and return titles, links, snippets.", {"query": "string", "max_results": "integer"}, ["query"], t_web_search, "safe"),
    ("research", "Deep web research: search, read the top pages, and cross-reference the findings against the built-in vault. Returns a cited report with agreements, conflicts and gaps. Use for anything current, factual or contested.", {"question": "string", "depth": "string", "cross_reference": "boolean"}, ["question"], t_research, "safe"),
    ("knowledge_search", "Search the AI Building Kit vault (playbooks on agencies, outreach, content, sales, receptionist, apps, MCP, shipping).", {"query": "string", "k": "integer", "pack": "string"}, ["query"], t_knowledge_search, "safe"),
    ("remember", "Store a durable note for future runs.", {"note": "string", "tags": "array"}, ["note"], t_remember, "safe"),
    ("recall", "Search stored notes.", {"query": "string"}, ["query"], t_recall, "safe"),
    ("generate_image", "Generate an image from a prompt (returns a /media URL).", {"prompt": "string", "style": "string", "size": "string"}, ["prompt"], t_generate_image, "safe"),
    ("generate_video", "Start a background video generation job.", {"prompt": "string", "provider": "string", "image_url": "string", "seconds": "integer", "aspect": "string"}, ["prompt"], t_generate_video, "safe"),
    ("edit_video", "Start a background prompt-driven edit of a /media video.", {"source": "string", "instruction": "string"}, ["source", "instruction"], t_edit_video, "safe"),
    ("crm_add_lead", "Add or update a lead in the CRM.", {"id": "string", "name": "string", "company": "string", "role": "string", "contact": "string", "location": "string", "source": "string", "hook": "string", "status": "string", "next_action": "string", "notes": "string"}, [], t_crm_add_lead, "safe"),
    ("crm_list_leads", "List CRM leads, optionally by status (new, enriched, contacted, replied, booked, not-a-fit).", {"status": "string"}, [], t_crm_list_leads, "safe"),
    ("crm_book_appointment", "Book an appointment (confirm time + timezone with the user first).", {"name": "string", "contact": "string", "when": "string", "tz": "string", "service": "string", "notes": "string", "lead_id": "string"}, ["when"], t_crm_book, "safe"),
    ("crm_start_sequence", "Start a follow-up sequence: cold_outreach, missed_call, no_show or review_request.", {"kind": "string", "lead_id": "string", "contact": "string", "name": "string"}, ["kind"], t_crm_sequence, "safe"),
    ("draft_email", "Draft an email (never sends). Returns subject and body for the user to review in Mail.", {"intent": "string", "to": "string", "tone": "string"}, ["intent"], t_draft_email, "safe"),
    ("send_email", "Send an email from a connected account. Only when the user explicitly asked to send.", {"to": "string", "subject": "string", "body": "string", "from": "string"}, ["to", "subject", "body"], t_send_email, "full"),
    ("ask_user", "Pause and ask the user a question when a decision is theirs or information is missing.", {"question": "string"}, ["question"], t_ask_user, "safe"),
    ("finish", "Call when the goal is complete (or truly blocked) with a clear summary of what was done, verified, and what remains.", {"summary": "string"}, ["summary"], t_finish, "safe"),
]
TOOL_MAP = {t[0]: t for t in TOOLS}

def tool_schemas(autonomy="builder"):
    out = []
    for name, desc, params, req, fn, level in TOOLS:
        if LEVELS.index(level) > LEVELS.index(autonomy):
            continue
        props = {}
        for k, typ in params.items():
            props[k] = {"type": "array", "items": {"type": "string"}} if typ == "array" else {"type": typ}
        out.append({"type": "function", "function": {"name": name, "description": desc,
                    "parameters": {"type": "object", "properties": props, "required": req}}})
    return out

def call_tool(name, args, ctx):
    if name not in TOOL_MAP:
        return "unknown tool: " + name
    fn, level = TOOL_MAP[name][4], TOOL_MAP[name][5]
    try:
        _needs(level, ctx)
        return _cap(fn(args or {}, ctx))
    except Exception as e:
        return "ERROR: %s" % (str(e) or e.__class__.__name__)

# ---------------------------------------------------------------- loop ----
DOCTRINE = (
    "You are AIXMOS in super-agent mode: a careful, capable operator working on the user's own machine with real tools.\n"
    "Doctrine (from the AI Building Kit):\n"
    "1. PLAN FIRST: your first reply is a short numbered plan (files/tools you will touch, blast radius). Then act.\n"
    "2. SMALL STEPS: one logical change per tool call; keep the workspace working after each.\n"
    "3. PROVE IT: verify with real command output (run_command / run_python / read_file) before claiming done. Never say 'should work'.\n"
    "4. NEVER FABRICATE: no invented numbers, files, results or placeholder data presented as real. If unknown, say so or ask_user.\n"
    "5. HUMAN VETO: use ask_user for decisions that are the user's (spending, sending, deleting, ambiguous scope).\n"
    "6. STOP CLEANLY: when done or blocked, call finish with what was done, how it was verified, and what remains.\n"
    "Only call tools that exist. Put file paths relative to the workspace unless the user gave an absolute allowed path. "
    "Keep messages concise; results speak."
)

def _persist(job):
    with _LOCK:
        try:
            with open(RUNS, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except (OSError, ValueError):
            runs = []
        runs = [r for r in runs if r["id"] != job["id"]]
        runs.insert(0, {"id": job["id"], "goal": job["meta"]["goal"], "status": job["status"], "created": job["created"],
                        "updated": job["updated"], "final": (job.get("result") or {}).get("final") if isinstance(job.get("result"), dict) else None,
                        "steps": job["meta"].get("steps", [])[-60:], "artifacts": job["meta"].get("artifacts", []), "error": job.get("error")})
        with open(RUNS, "w", encoding="utf-8") as f:
            json.dump(runs[:50], f, ensure_ascii=False, indent=1)

def runs(limit=30):
    try:
        with open(RUNS, "r", encoding="utf-8") as f:
            return json.load(f)[:limit]
    except (OSError, ValueError):
        return []

def pick_model():
    # The 7B model is opt-in (Integrations -> agent model): on this 2-core box it can stall Ollama
    # with tool schemas + an 8k context. The 3B model finishes a tool step in ~20 s.
    pref = settings.pref("agent_model")
    models = llm.list_models()
    if pref and pref in models:
        return pref
    for cand in ("qwen2.5:3b", "qwen3b-max:latest"):
        if cand in models:
            return cand
    return llm.pick_model()

def run(goal, autonomy=None, extra_roots=None, model=None, max_steps=None, context=None, on_done=None):
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("goal is required")
    autonomy = autonomy if autonomy in LEVELS else (settings.pref("agent_autonomy") or "builder")
    max_steps = int(max_steps or settings.pref("agent_max_steps") or 24)
    os.makedirs(WORKSPACE, exist_ok=True)
    mdl = model or pick_model()
    ctx = {"autonomy": autonomy, "roots": roots(extra_roots), "artifacts": [], "drafts": [], "final": None, "event": threading.Event(), "job": None}

    def loop(progress):
        while ctx["job"] is None:          # jobs.create starts the thread before run() can store the handle
            time.sleep(0.02)
        job = ctx["job"]
        steps = job["meta"]["steps"]
        kb = knowledge.context_for(goal, k=3, min_score=5.0, max_chars=2200) if settings.pref("use_knowledge") else ""
        persona = skills.active_persona()
        sysmsg = DOCTRINE + "\nWorkspace: %s\nAllowed roots: %s\nAutonomy: %s\nDate: %s" % (
            WORKSPACE, "; ".join(ctx["roots"]), autonomy, time.strftime("%Y-%m-%d %H:%M"))
        if persona: sysmsg += "\n\nACTIVE SKILL PERSONA:\n" + persona[:3000]
        if kb: sysmsg += "\n\nRELEVANT VAULT KNOWLEDGE:\n" + kb
        prof = skills.profile_text()
        if prof: sysmsg += "\n\n" + prof
        from . import genesis
        mission = genesis.mission_context()
        if mission: sysmsg += "\n\n" + mission
        msgs = [{"role": "system", "content": sysmsg}]
        if context: msgs.append({"role": "user", "content": "Context from the conversation:\n" + str(context)[:4000]})
        msgs.append({"role": "user", "content": "GOAL: " + goal})
        tools = tool_schemas(autonomy)
        idle_text = 0
        for step in range(1, max_steps + 1):
            if job["meta"].get("cancel"):
                ctx["final"] = "cancelled by user"; break
            progress("step %d/%d: thinking" % (step, max_steps))
            try:
                resp = llm.chat_raw(msgs, model=mdl, tools=tools, temperature=0.2, num_ctx=6144, timeout=900)
            except Exception as e:
                steps.append({"n": step, "kind": "error", "text": "model error: %s" % e}); _persist(job); raise
            m = resp.get("message") or {}
            calls = m.get("tool_calls") or []
            text = (m.get("content") or "").strip()
            msgs.append({"role": "assistant", "content": text, **({"tool_calls": calls} if calls else {})})
            if text:
                steps.append({"n": step, "kind": "assistant", "text": text[:3000]})
            if not calls:
                idle_text += 1
                if step == 1 and not ctx["final"]:
                    msgs.append({"role": "user", "content": "Good. Now execute the plan with tools. Call finish when complete."}); continue
                if idle_text >= 2 or ctx["final"] is not None:
                    ctx["final"] = ctx["final"] or text; break
                msgs.append({"role": "user", "content": "Continue with tools, or call finish(summary) if the goal is complete."}); continue
            idle_text = 0
            for c in calls:
                fnm = (c.get("function") or {}).get("name") or ""
                args = (c.get("function") or {}).get("arguments") or {}
                if isinstance(args, str):
                    args = llm.parse_json(args) or {}
                progress("step %d: %s" % (step, fnm))
                t0 = time.time()
                res = call_tool(fnm, args, ctx)
                steps.append({"n": step, "kind": "tool", "tool": fnm, "args": _cap(args, 800), "result": _cap(res, 2500), "ms": int((time.time() - t0) * 1000)})
                msgs.append({"role": "tool", "content": res, "tool_name": fnm})
                job["meta"]["artifacts"] = ctx["artifacts"][:]; job["updated"] = time.time(); _persist(job)
                if ctx["final"] is not None:
                    break
            if ctx["final"] is not None:
                break
        else:
            ctx["final"] = "stopped: reached the step limit (%d). Progress so far is in the log." % max_steps
        # trim very long transcripts to keep the model responsive on later steps
        result = {"final": ctx["final"] or "no summary", "artifacts": ctx["artifacts"], "drafts": ctx["drafts"], "steps": len(steps), "model": mdl}
        job["result"] = result; _persist(job)
        return result

    def done(j):
        _persist(j)
        if on_done:
            on_done(j)
    job = jobs.create("agent", loop, {"goal": goal, "autonomy": autonomy, "model": mdl, "steps": [], "artifacts": [], "cancel": False},
                      on_done=done)
    ctx["job"] = job
    job["meta"]["ctx_event"] = None
    _CTX[job["id"]] = ctx
    return job

_CTX = {}

def mcp_ctx(autonomy=None):
    """Tool context for non-interactive callers (no job to pause on)."""
    autonomy = autonomy if autonomy in LEVELS else (settings.pref("mcp_autonomy") or "builder")
    os.makedirs(WORKSPACE, exist_ok=True)
    return {"autonomy": autonomy, "roots": roots(), "artifacts": [], "drafts": [], "final": None, "event": threading.Event(), "job": None}

def answer(job_id, text):
    ctx = _CTX.get(job_id)
    job = jobs.get(job_id)
    if not ctx or not job or job.get("status") != "waiting":
        raise ValueError("that run is not waiting for an answer")
    job["answer"] = str(text)
    ctx["event"].set()
    return True

def cancel(job_id):
    job = jobs.get(job_id)
    if not job:
        raise ValueError("unknown run")
    job["meta"]["cancel"] = True
    ctx = _CTX.get(job_id)
    if ctx and job.get("status") == "waiting":
        job["answer"] = "cancel"; ctx["event"].set()
    return True

def run_sync(goal, autonomy="builder", max_steps=8, on_progress=None):
    """Blocking variant for the OpenAI-compatible / MCP surfaces."""
    job = run(goal, autonomy=autonomy, max_steps=max_steps)
    last = 0
    while job["status"] in ("queued", "running", "waiting"):
        steps = job["meta"]["steps"]
        if on_progress and len(steps) > last:
            for s in steps[last:]:
                on_progress(s)
            last = len(steps)
        if job["status"] == "waiting":
            answer(job["id"], "Decide yourself using the safest reasonable option; I cannot answer interactively here.")
        time.sleep(1)
    return job
