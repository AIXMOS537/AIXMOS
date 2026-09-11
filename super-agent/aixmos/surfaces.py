"""
surfaces.py -- everything the server exposes beyond plain chat, kept out of the handler class:

  run_intent(h, intent, req)  chat slash-commands / natural intents -> capability calls
  route_get / route_post       the /api routes for vault, skills, prompts, CRM, carousel, agent
  openai_chat / openai_models  OpenAI-compatible /v1 endpoints (use AIXMOS from any OpenAI-speaking app)
  mcp(h)                       Model Context Protocol server (streamable HTTP, JSON-RPC) on /mcp
  boot_index()                 index the kit at startup when the vault is empty or stale

Everything binds to 127.0.0.1 only; the agent's shell/file tools stay inside the allowed roots.
"""
import os, json, time, uuid, urllib.request
from . import settings, media, jobs, llm, intents, imagegen, videogen, videoedit, email_tools
from . import knowledge, skills, crm, carousel, agent

OLLAMA = "http://localhost:11434"
NUM_CTX = 8192

# ----------------------------------------------------------------- intents ----
def run_intent(h, intent, req):
    """Returns the final assistant text; streams tool events through h._event as it goes."""
    kind = intent["kind"]
    if kind == "image":
        h._event({"tool": {"kind": "image", "status": "working", "text": "Rendering image..."}})
        item = imagegen.generate(intent["prompt"], provider=req.get("image_provider"))
        h._event({"tool": {"kind": "image", "item": item}})
        return "Image ready -> %s\nPrompt used: %s%s\nRate it (thumbs on the card) so I learn your taste." % (
            item["url"], item["final_prompt"], ("\n(" + item["warning"] + ")") if item.get("warning") else "")
    if kind == "video":
        job = videogen.generate(intent["prompt"], provider=req.get("video_provider"), on_done=h.job_note("Video ready"))
        h._event({"tool": {"kind": "video", "job": job["id"], "status": "working"}})
        return "Video generation started (job %s via %s). It will appear here when rendered; the Video Lab shows live progress." % (job["id"], job["meta"]["provider"])
    if kind == "edit":
        src = req.get("current_video")
        if not src or not media.path_for(src):
            return "Load a video first: open the Video Lab, upload a clip or pick a generated one, then tell me the edit."
        job = videoedit.edit(src, intent["instruction"], on_done=h.job_note("Edited video ready"))
        h._event({"tool": {"kind": "edit", "job": job["id"], "status": "working"}})
        return "Editing: %s (job %s). Progress shows in the Video Lab; the result lands here when done." % (intent["instruction"], job["id"])
    if kind == "email":
        accounts = email_tools.list_accounts()
        h._event({"tool": {"kind": "email", "status": "working", "text": "Drafting email..."}})
        d = email_tools.draft(intent["intent"], to=intent.get("to"), account_id=(accounts[0]["id"] if accounts else None))
        if intent.get("subject"):
            d["subject"] = intent["subject"]
        draft = {"to": intent.get("to") or [], "subject": d["subject"], "body": d["body"]}
        h._event({"tool": {"kind": "email", "draft": draft}})
        return "Draft ready in the Mail panel:\nTo: %s\nSubject: %s\n\n%s\n\n%s" % (
            ", ".join(draft["to"]) or "(add a recipient)", draft["subject"], draft["body"],
            "Review it and press Send there; nothing goes out without your click." if accounts else "Connect an account in the Mail panel to send it.")
    if kind == "agent":
        goal = intent.get("goal") or ""
        if not goal:
            return "Give the agent a goal, e.g. /agent build a python script that renames my photos by date."
        recent = "\n".join("%s: %s" % (m["role"], m["content"][:300]) for m in h.load_mem()[-7:-1])
        job = agent.run(goal, autonomy=req.get("autonomy"), context=recent, on_done=h.agent_note)
        h._event({"tool": {"kind": "agent", "job": job["id"], "status": "working"}})
        return ("Super agent engaged (run %s, autonomy %s, model %s). Steps stream in the Agent panel; "
                "I will report here when it finishes or needs you." % (job["id"], job["meta"]["autonomy"], job["meta"]["model"]))
    if kind == "carousel":
        h._event({"tool": {"kind": "carousel", "status": "working", "text": "Writing and rendering slides..."}})
        c = carousel.build(intent.get("arg") or "")
        h._event({"tool": {"kind": "carousel", "item": c}})
        return "Carousel ready (%d slides):\n%s\n\nCaption:\n%s\n%s" % (
            len(c["slides"]), "\n".join(s["url"] for s in c["slides"]), c["caption"], " ".join(c["hashtags"]))
    if kind == "research":
        from . import research
        h._event({"tool": {"kind": "research", "status": "working", "text": "Scouring the web and cross-referencing the vault..."}})
        rep = research.run(intent.get("arg") or "", depth=(req or {}).get("depth") or "normal", cross=True,
                           progress=lambda m: h._event({"tool": {"kind": "research", "status": "working", "text": m}}))
        h._event({"tool": {"kind": "research", "item": rep}})
        return rep["markdown"]
    if kind == "vault":
        q = intent.get("arg") or ""
        hits = knowledge.search(q, k=5)
        if not hits:
            return "Nothing in the vault matched that."
        return "Vault results for \"%s\":\n\n" % q + "\n\n".join(
            "- %s / %s: %s\n  %s" % (x["pack"], x["file"].split("/")[-1], x["title"], x["snippet"]) for x in hits)
    if kind == "skill":
        arg = (intent.get("arg") or "").strip().lower()
        if arg in ("", "off", "none", "stop", "exit"):
            skills.activate(None)
            return "Skill mode off. Back to the general AIXMOS assistant."
        match = next((s for s in skills.list_skills() if s["id"] == arg or arg in s["id"] or arg in s["name"].lower()), None)
        if not match:
            return "No skill named '%s'. Available: %s" % (arg, ", ".join(s["id"] for s in skills.list_skills()))
        skills.activate(match["id"])
        return "Skill activated: %s %s. I now follow that playbook in every reply. Say /skill off to leave." % (match["icon"], match["name"])
    if kind == "lead":
        out = llm.json_call("Extract a CRM lead from the text. Return JSON with any of: name, company, role, contact (email or phone), "
                            "location, source, hook (personalisation observation), notes, next_action. Unknown fields empty.",
                            intent.get("arg") or "", num_ctx=2048, timeout=150) or {}
        out = {k: v for k, v in out.items() if k in ("name", "company", "role", "contact", "location", "source", "hook", "notes", "next_action") and v}
        if not out:
            raise ValueError("could not read a lead from that text")
        lead = crm.upsert_lead(out)
        return "Lead saved to the CRM (id %s): %s" % (lead["id"], ", ".join("%s=%s" % (k, v) for k, v in out.items()))
    if kind == "book":
        out = llm.json_call("Extract an appointment from the text. Return JSON: {name, contact, when (date and time as written), tz, service, notes}. Unknown fields empty.",
                            intent.get("arg") or "", num_ctx=2048, timeout=150) or {}
        ap = crm.book(out)
        return "Booked: %s on %s%s (%s). Confirm the time and timezone with them." % (
            ap["name"] or ap["contact"], ap["when"], (" " + ap["tz"]) if ap["tz"] else "", ap["service"] or "appointment")
    return "Unknown command."

# ------------------------------------------------------------------ routes ----
def settings_view(h):
    v = settings.public_view(); v["caps"] = h.capabilities(); v["tools"] = media.tools_status()
    v["email_presets"] = email_tools.PRESETS; v["business"] = skills.profile(); v["brand"] = carousel.brand()
    v["agent_roots"] = agent.roots(); v["workspace"] = agent.WORKSPACE
    return v

def route_get(h, p, g):
    """Handle a GET path; returns True when handled."""
    if p == "/api/knowledge/packs":
        h._json({"packs": knowledge.packs(), "stats": knowledge.stats()})
    elif p == "/api/knowledge/search":
        h._json({"hits": knowledge.search(g("q", ""), k=int(g("k", 8)), pack=g("pack") or None)})
    elif p == "/api/knowledge/file":
        txt = knowledge.read(g("path", ""))
        h._json({"path": g("path"), "text": txt}) if txt is not None else h._fail("no such file", 404)
    elif p == "/api/skills":
        h._json({"skills": skills.list_skills(), "active": settings.pref("active_skill") or "", "business": skills.profile()})
    elif p == "/api/skills/persona":
        h._json({"id": g("id"), "persona": skills.persona(g("id", ""))})
    elif p == "/api/prompts":
        h._json(skills.prompts(g("q") or None, g("pack") or None, int(g("limit", 80))))
    elif p == "/api/business":
        h._json({"business": skills.profile(), "fields": skills.PROFILE_FIELDS})
    elif p == "/api/crm":
        d = crm.all_data(); d["dashboard"] = crm.dashboard(); d["statuses"] = crm.STATUSES; d["sequence_types"] = list(crm.SEQUENCES)
        h._json(d)
    elif p == "/api/crm/dashboard":
        h._json(crm.dashboard())
    elif p == "/api/carousels":
        h._json({"items": carousel.history(), "brand": carousel.brand(), "layouts": carousel.LAYOUTS})
    elif p == "/api/research":
        from . import research
        h._json({"history": research.history(), "engines": research.engines()})
    elif p == "/api/agent/runs":
        live = [j for j in jobs.list_jobs(50) if j["kind"] == "agent"]
        h._json({"live": live, "history": agent.runs(), "tools": [t["function"]["name"] for t in agent.tool_schemas("full")],
                 "model": agent.pick_model(), "autonomy": settings.pref("agent_autonomy"), "workspace": agent.WORKSPACE, "roots": agent.roots()})
    elif p.startswith("/api/agent/run/"):
        j = jobs.get(p.rsplit("/", 1)[1])
        h._json(j) if j else h._fail("no such run", 404)
    elif p == "/api/agent/tools":
        h._json({"tools": agent.tool_schemas(g("autonomy") or "full")})
    elif p == "/v1/models":
        openai_models(h)
    elif p == "/mcp":
        h._send(405, "application/json", b'{"error":"POST JSON-RPC to /mcp"}')
    else:
        return False
    return True

def route_post(h, p):
    """Handle a POST path; returns True when handled."""
    if p == "/api/knowledge/ingest":
        b = h._body()
        if b.get("path"):
            settings.update(prefs={"kit_path": b["path"]})
        h._json(knowledge.ingest(b.get("path") or None))
    elif p == "/api/skills/activate":
        h._json({"active": skills.activate(h._body().get("id") or None)})
    elif p == "/api/business":
        h._json({"business": skills.save_profile(h._body())})
    elif p == "/api/brand":
        h._json({"brand": carousel.save_brand(h._body())})
    elif p == "/api/crm/lead":
        h._json(crm.upsert_lead(h._body()))
    elif p == "/api/crm/lead/delete":
        h._json({"ok": crm.delete_lead(h._body().get("id"))})
    elif p == "/api/crm/score":
        h._json({"leads": crm.score_leads(h._body().get("ids"))})
    elif p == "/api/crm/appointment":
        h._json(crm.book(h._body()))
    elif p == "/api/crm/appointment/update":
        b = h._body(); h._json({"ok": crm.set_appointment(b.get("id"), b.get("status"), b.get("notes"))})
    elif p == "/api/crm/appointment/delete":
        h._json({"ok": crm.delete_appointment(h._body().get("id"))})
    elif p == "/api/crm/revenue":
        b = h._body(); h._json({"ok": crm.add_revenue(b.get("period"), b.get("value"), b.get("source", ""))})
    elif p == "/api/crm/revenue/delete":
        h._json({"ok": crm.delete_revenue(h._body().get("ts"))})
    elif p == "/api/crm/activity":
        crm.log(h._body().get("desc") or "", "note"); h._json({"ok": True})
    elif p == "/api/crm/review":
        h._json(crm.weekly_review(h._body().get("notes") or ""))
    elif p == "/api/crm/sequence":
        b = h._body()
        h._json(crm.start_sequence(b.get("kind"), lead_id=b.get("lead_id"), contact=b.get("contact"), name=b.get("name"), start=b.get("start")))
    elif p == "/api/crm/sequence/step":
        b = h._body(); h._json({"ok": crm.sequence_step(b.get("id"), b.get("n"), b.get("status"), b.get("draft"))})
    elif p == "/api/crm/sequence/stop":
        h._json({"ok": crm.stop_sequence(h._body().get("id"))})
    elif p == "/api/crm/sequence/draft":
        b = h._body()
        seq = next((s for s in crm.all_data()["sequences"] if s["id"] == b.get("id")), None)
        if not seq:
            raise ValueError("unknown sequence")
        st = next((s for s in seq["steps"] if s["n"] == int(b.get("n") or 1)), None)
        if not st:
            raise ValueError("unknown step")
        accs = email_tools.list_accounts()
        d = email_tools.draft("%s follow-up, touch %d of %d: %s. Recipient: %s." % (
                seq["kind"].replace("_", " "), st["n"], len(seq["steps"]), st["intent"], seq.get("name") or seq.get("contact")),
            to=[seq["contact"]] if seq.get("contact") else None, tone=b.get("tone") or "friendly",
            account_id=(accs[0]["id"] if accs else None), length="short")
        crm.sequence_step(seq["id"], st["n"], "drafted", d)
        h._json({"draft": {"to": [seq["contact"]] if seq.get("contact") else [], **d}, "seq": seq["id"], "n": st["n"]})
    elif p == "/api/research":
        from . import research
        b = h._body()
        rep = research.run(b.get("question") or "", depth=b.get("depth") or "normal", cross=b.get("cross", True))
        h.remember("user", "/research " + rep["question"]); h.remember("assistant", rep["markdown"])
        h._json(rep)
    elif p == "/api/carousel":
        b = h._body()
        c = carousel.build(b.get("topic"), b.get("audience") or "", b.get("layout") or "B_list", b.get("slides") or 6, b.get("extra") or "", b.get("brand"))
        h.remember("assistant", "Carousel ready -> " + " ".join(s["url"] for s in c["slides"]))
        h._json(c)
    elif p == "/api/agent/run":
        b = h._body()
        job = agent.run(b.get("goal"), autonomy=b.get("autonomy"), extra_roots=b.get("roots"), model=b.get("model"),
                        max_steps=b.get("max_steps"), context=b.get("context"), on_done=h.agent_note)
        h.remember("user", "/agent " + (b.get("goal") or ""))
        h._json(job)
    elif p == "/api/agent/answer":
        b = h._body(); h._json({"ok": agent.answer(b.get("id"), b.get("answer") or "")})
    elif p == "/api/agent/cancel":
        h._json({"ok": agent.cancel(h._body().get("id"))})
    elif p == "/v1/chat/completions":
        openai_chat(h)
    elif p == "/mcp":
        mcp(h)
    else:
        return False
    return True

# ------------------------------------------------------------------ OpenAI ----
def openai_models(h):
    now = int(time.time())
    h._json({"object": "list", "data": [{"id": m, "object": "model", "created": now, "owned_by": "aixmos"} for m in ("aixmos", "aixmos-agent", "aixmos-raw")]})

def _text_of(m):
    c = m.get("content")
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
    return str(c or "")

def openai_chat(h):
    b = h._body()
    msgs = [m for m in (b.get("messages") or []) if isinstance(m, dict)]
    model = str(b.get("model") or "aixmos")
    stream = bool(b.get("stream"))
    user = next((_text_of(m) for m in reversed(msgs) if m.get("role") == "user"), "").strip()
    rid = "chatcmpl-" + uuid.uuid4().hex[:12]; created = int(time.time())
    def chunk(delta, finish=None):
        return ("data: " + json.dumps({"id": rid, "object": "chat.completion.chunk", "created": created, "model": model,
                "choices": [{"index": 0, "delta": ({"content": delta} if delta else {}), "finish_reason": finish}]}) + "\n\n").encode()
    parts = []
    if stream:
        h._start_stream("text/event-stream")
    def emit(t):
        if not t:
            return
        parts.append(t)
        if stream:
            h._chunk(chunk(t))
    port = settings.RUNTIME.get("port", 8770)
    try:
        if model.endswith("agent"):
            job = agent.run_sync(user, autonomy=settings.pref("mcp_autonomy") or "builder", max_steps=int(b.get("max_steps") or 10),
                                 on_progress=lambda s: emit("> %s %s\n" % (s.get("tool") or "plan", str(s.get("args") or s.get("text") or "")[:160])) if stream else None)
            res = job.get("result") or {}
            emit("\n" + (res.get("final") or job.get("error") or "no result"))
        else:
            intent = intents.detect(user) if model != "aixmos-raw" else None
            if intent and intent["kind"] == "image":
                it = imagegen.generate(intent["prompt"])
                emit("![%s](http://localhost:%d%s)\n\nPrompt used: %s" % (intent["prompt"][:60], port, it["url"], it["final_prompt"]))
            elif intent and intent["kind"] in ("vault", "skill", "lead", "book"):
                emit(run_intent(h, intent, {}))
            else:
                sysmsg = h.build_system(user) if model != "aixmos-raw" else h.SYSTEM
                convo = [{"role": m["role"], "content": _text_of(m)} for m in msgs if m.get("role") in ("user", "assistant")][-30:]
                payload = json.dumps({"model": llm.pick_model(), "messages": [{"role": "system", "content": sysmsg}] + convo, "stream": True,
                                      "options": {"num_ctx": NUM_CTX, "temperature": float(b.get("temperature") or 0.7)}}).encode()
                r = urllib.request.Request(OLLAMA + "/api/chat", data=payload, headers={"Content-Type": "application/json"}, method="POST")
                resp = urllib.request.urlopen(r, timeout=600); buf = b""
                while True:
                    c = resp.read(512)
                    if not c:
                        break
                    buf += c
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            emit((json.loads(line).get("message") or {}).get("content") or "")
                        except ValueError:
                            pass
    except Exception as e:
        emit("\n[AIXMOS error: %s]" % e)
    full = "".join(parts)
    if stream:
        h._chunk(chunk("", "stop")); h._chunk(b"data: [DONE]\n\n"); h._chunk(b"")
    else:
        h._json({"id": rid, "object": "chat.completion", "created": created, "model": model,
                 "choices": [{"index": 0, "message": {"role": "assistant", "content": full}, "finish_reason": "stop"}],
                 "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})

# --------------------------------------------------------------------- MCP ----
def mcp(h):
    b = h._body()
    mid, method, params = b.get("id"), b.get("method") or "", b.get("params") or {}
    def reply(result=None, error=None):
        obj = {"jsonrpc": "2.0", "id": mid}
        if error:
            obj["error"] = error
        else:
            obj["result"] = result
        h._json(obj, 200)
    if method == "initialize":
        reply({"protocolVersion": params.get("protocolVersion") or "2025-03-26", "capabilities": {"tools": {"listChanged": False}},
               "serverInfo": {"name": "aixmos", "version": "2.0"},
               "instructions": "AIXMOS super agent tools: files, shell and python inside a sandboxed workspace, web fetch/search, the AI Building Kit vault, image/video generation, CRM, mail drafting."})
    elif method.startswith("notifications/"):
        h._send(202, "application/json", b"")
    elif method == "ping":
        reply({})
    elif method == "tools/list":
        tools = [{"name": t["function"]["name"], "description": t["function"]["description"], "inputSchema": t["function"]["parameters"]}
                 for t in agent.tool_schemas(settings.pref("mcp_autonomy") or "builder") if t["function"]["name"] not in ("ask_user", "finish")]
        reply({"tools": tools})
    elif method == "tools/call":
        name, args = params.get("name") or "", params.get("arguments") or {}
        out = agent.call_tool(name, args, agent.mcp_ctx())
        reply({"content": [{"type": "text", "text": out}], "isError": out.startswith("ERROR")})
    else:
        reply(error={"code": -32601, "message": "method not found: " + method})

# -------------------------------------------------------------------- boot ----
def boot_index():
    try:
        st = knowledge.stats()
        root = settings.pref("kit_path") or knowledge.DEFAULT_ROOT
        newest = max((os.path.getmtime(os.path.join(dp, f)) for dp, dn, fn in os.walk(root) for f in fn), default=0) if os.path.isdir(root) else 0
        if not st["chunks"] or newest > float(st.get("built") or 0):
            print("  Vault   ->  indexing %s" % root)
            print("  Vault   ->  %s" % knowledge.ingest(root))
    except Exception as e:
        print("  Vault   ->  index skipped (%s)" % e)
