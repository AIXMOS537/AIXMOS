#!/usr/bin/env python3
"""
Project AIXMOS -- local JARVIS-style assistant server with persistent memory
and media / email capabilities.

Serves index.html at "/" and talks to the local Ollama daemon (http://localhost:11434).
Every chat turn is saved to memory/conversation.json.

Endpoints (all bound to 127.0.0.1 only):
  GET  /                      chat UI
  GET  /media/<kind>/<file>   generated / uploaded media
  GET  /api/tags              Ollama model list (proxied)
  GET  /api/memory            saved conversation
  GET  /api/telemetry         cpu / ram / disk / tool status for the HUD
  GET  /api/settings          providers (keys masked) + prefs      POST to update
  GET  /api/jobs[/<id>]       background job status
  GET  /api/images            image history + learning profile     POST /api/image/generate|rate|refine
  GET  /api/videos            generated video history              POST /api/video/generate|upload|plan|edit
  GET  /api/email/accounts    connected accounts                   POST /api/email/accounts|remove|draft|refine|send
  GET  /api/email/inbox       recent inbox for an account          GET  /api/email/read
  GET  /api/email/oauth/start?provider=google|microsoft, /oauth/google, /oauth/microsoft (callbacks)
  GET  /api/tags              every usable chat model + the routed default; GET /api/models provider status + policy
  POST /api/chat              streams the reply; recognises image / video / edit / email intents
  POST /api/stt               local whisper.cpp speech-to-text
  POST /api/forget            wipe the saved conversation
"""
import os, sys, json, threading, subprocess, tempfile, time, urllib.request, urllib.error, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
sys.path.insert(1, os.path.join(DIR, "vendor"))   # pure-python deps (requests) vendored next to the server
import context_tools  # safe live-context layer: time / location / weather / system stats
from aixmos import settings, media, jobs, llm, intents, imagegen, videogen, videoedit, email_tools
from aixmos import knowledge, skills, crm, carousel, agent, surfaces, research, providers
from aixmos import VERSION
from aixmos import channels, ghl  # noqa: F401  (register the inbox executors email.send / ghl.write at start)

MEMDIR   = settings.MEMDIR          # honours AIXMOS_MEMDIR, same folder every module uses
MEMFILE  = os.path.join(MEMDIR, "conversation.json")
LOCK     = threading.Lock()
WHISPER_CLI   = os.path.join(DIR, "whisper", "bin", "Release", "whisper-cli.exe")
WHISPER_MODEL = os.path.join(DIR, "whisper", "models", "ggml-base.en.bin")
STT_LOCK      = threading.Lock()
MAX_CTX_MSGS = 40
NUM_CTX      = 8192
MAX_UPLOAD   = 800 * 1024 * 1024

_MEM_CACHE = {"mtime": None, "data": None}

def load_mem():
    try:
        mtime = os.path.getmtime(MEMFILE)
        if _MEM_CACHE["mtime"] == mtime and _MEM_CACHE["data"] is not None:
            return _MEM_CACHE["data"]
        with open(MEMFILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _MEM_CACHE["mtime"], _MEM_CACHE["data"] = mtime, data
        return data
    except (OSError, ValueError):
        return []

def save_mem(msgs):
    os.makedirs(MEMDIR, exist_ok=True)
    tmp = MEMFILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MEMFILE)
    _MEM_CACHE["mtime"], _MEM_CACHE["data"] = os.path.getmtime(MEMFILE), msgs

def remember(role, content):
    with LOCK:
        mem = load_mem()
        mem.append({"role": role, "content": content})
        save_mem(mem)

def _err(e):
    return json.dumps({"error": str(e) or e.__class__.__name__}).encode()

SYSTEM = ("You are AIXMOS, a private JARVIS-style AI assistant running locally on the user's own machine. "
          "You retain persistent memory of previous conversations with this user; use that history for continuity. "
          "Be concise, precise and calm, with a light touch of wit.\n"
          "You have built-in capabilities the user can trigger by simply asking in chat: generating images "
          "(\"generate an image of ...\", learns from the user's ratings), generating videos (\"make a video of ...\"), "
          "editing a loaded video with plain language (\"trim the first 5 seconds and add captions\"), and writing, "
          "refining and sending email through the user's connected accounts (\"write an email to ... about ...\"). "
          "When the user asks for one of these, the system runs it automatically; you never need to say you cannot.\n"
          "You also have a super-agent mode (\"/agent <goal>\" or \"build me a ...\") that plans and executes multi-step work "
          "with real tools (files, shell, python, web, CRM, media, mail drafts), an AI Building Kit knowledge vault (24 business "
          "and engineering playbooks, searched automatically), activatable skills (receptionist, appointment setter, cold outreach, "
          "content engine, sales, agency OS, ...), a CRM with leads / appointments / follow-up sequences / weekly review, and an "
          "Instagram carousel generator. Mention the right capability when it would help.")

def stable_system():
    """The part of the prompt that does NOT change from turn to turn: base prompt, active skill
    persona, business profile, mission. Keeping it byte-identical lets Ollama reuse its cached
    prompt prefix, so a turn only pays prompt-processing for what is new (about 20 tok/s here)."""
    parts = [SYSTEM]
    persona = skills.active_persona()
    if persona:
        parts.append("ACTIVE SKILL (stay in this role until the user switches it off):\n" + persona)
    prof = skills.profile_text()
    if prof and not persona:
        parts.append(prof)
    from aixmos import genesis
    mission = genesis.mission_context()
    if mission:
        parts.append(mission)
    return "\n\n".join(parts)

def turn_context(content):
    """The volatile part: vault passages for THIS message plus a light time/place line. Appended to
    the user's turn instead of the system prompt so the cached prefix stays valid."""
    parts = []
    if settings.pref("use_knowledge"):
        kb = knowledge.context_for(content, k=2, min_score=6.0, max_chars=1200)
        if kb:
            parts.append("Relevant playbook passages (from the user's AI Building Kit; cite the pack when used):\n" + kb)
    try:
        parts.append(context_tools.build_context(light=True))
    except Exception:
        pass
    return "\n\n".join(parts)

def build_system(content):
    """Compatibility: full prompt in one block (used by the OpenAI-compatible surface)."""
    tc = turn_context(content)
    return stable_system() + (("\n\n" + tc) if tc else "")

def _clip(text, n=1200):
    text = text or ""
    return text if len(text) <= n else text[:n] + " …[trimmed]"

def capabilities():
    return {"image": settings.providers_for("image"), "video": settings.providers_for("video") + ["local"],
            "video_edit": media.tools_status()["ffmpeg"], "captions": media.whisper_ok(),
            "email_accounts": len(email_tools.list_accounts()), "ollama": bool(llm.list_models()), "model_ready": llm.available(),
            "knowledge": knowledge.stats(), "active_skill": settings.pref("active_skill") or "",
            "agent_model": agent.pick_model(), "port": settings.RUNTIME.get("port", 8770)}

def _job_note(prefix):
    return lambda j: remember("assistant", ("%s -> %s" % (prefix, j["result"]["url"])) if j["status"] == "done"
                              else ("%s failed: %s" % (prefix, j["error"])))

def _agent_note(j):
    if j["status"] == "done":
        remember("assistant", "Agent finished: %s" % ((j.get("result") or {}).get("final") or "")[:3000])
    else:
        remember("assistant", "Agent run failed: %s" % j.get("error"))

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------------------------------------------------------- helpers ----
    def _send(self, code, ctype, data=b""):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, "application/json; charset=utf-8", json.dumps(obj, ensure_ascii=False, default=str).encode())

    def _fail(self, e, code=400):
        self._send(code, "application/json", _err(e))

    def _guard(self, post):
        """Refuse anything that is not this machine talking to itself.

        The server has no login and exposes run_command / run_python through /mcp and the agent,
        so a web page must never be able to drive it: Host pins the request to localhost (blocks
        DNS rebinding), Origin and Sec-Fetch-Site block cross-site fetches (CSRF). Claude Code,
        curl and OpenAI clients send no Origin and a localhost Host, so they pass."""
        port = settings.RUNTIME.get("port", 8770)
        hosts = {"%s:%d" % (h, port) for h in ("localhost", "127.0.0.1", "[::1]")}
        origin = self.headers.get("Origin")
        reason = None
        if (self.headers.get("Host") or "").strip().lower() not in hosts:
            reason = "forbidden host"
        elif origin is not None and origin.strip().lower() not in {"http://" + h for h in hosts}:
            reason = "cross-origin request refused"
        elif post and (self.headers.get("Sec-Fetch-Site") or "").lower() == "cross-site":
            reason = "cross-site request refused"
        if reason:
            self.close_connection = True   # the refused body stays unread; never reuse this socket
            self._send(403, "application/json", json.dumps({"error": reason}).encode())
            return False
        return True

    # shared with aixmos.surfaces (the extra API surfaces live outside this class)
    SYSTEM = SYSTEM
    build_system = staticmethod(build_system)
    load_mem = staticmethod(load_mem)
    remember = staticmethod(remember)
    capabilities = staticmethod(capabilities)
    job_note = staticmethod(_job_note)
    agent_note = staticmethod(lambda j: remember("assistant", ("Agent finished: %s" % ((j.get("result") or {}).get("final") or "")[:3000]) if j["status"] == "done" else ("Agent run failed: %s" % j.get("error"))))

    def _start_stream(self, ctype="application/x-ndjson"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}

    def _index(self):
        try:
            with open(os.path.join(DIR, "index.html"), "rb") as f:
                page = f.read()
            from aixmos import head          # owner actions need this per-launch token; only the app page carries it
            page = page.replace(b"</head>", b'<meta name="aixmos-ui" content="%s"></head>' % head.UI_TOKEN.encode(), 1)
            self._send(200, "text/html; charset=utf-8", page)
        except OSError:
            self._send(500, "text/plain", b"index.html missing")

    def _media(self):
        path = media.path_for(urllib.parse.unquote(self.path.split("?")[0]))
        if not path:
            self.send_error(404); return
        size = os.path.getsize(path)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a or 0); end = int(b) if b else size - 1
            end = min(end, size - 1)
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", media.mime_for(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start); left = end - start + 1
            while left > 0:
                chunk = f.read(min(256 * 1024, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                left -= len(chunk)

    def _proxy_get(self):
        try:
            resp = urllib.request.urlopen(llm.ollama_url() + self.path, timeout=30)
            self._send(200, resp.headers.get("Content-Type", "application/json"), resp.read())
        except urllib.error.URLError as e:
            self._send(502, "application/json", _err(e))

    # ------------------------------------------------------------- chat ----
    def _chat(self):
        req = self._body()
        model = req.get("model") or llm.pick_model()
        content = (req.get("content") or "").strip()
        if not content:
            self._fail("empty message"); return
        remember("user", content)
        intent = intents.detect(content, has_video=bool(req.get("current_video")))
        if intent:
            self._chat_tool(intent, req); return
        mem = load_mem()
        n_hist = int(settings.pref("chat_history") or 12)
        history = [{"role": m["role"], "content": _clip(m["content"])} for m in mem[-(n_hist + 1):-1]]
        tc = turn_context(content)
        last = {"role": "user", "content": content + (("\n\n[context for this turn]\n" + tc) if tc else "")}
        ctx = [{"role": "system", "content": stable_system()}] + history + [last]
        gen = providers.stream(ctx, model=model, temperature=0.7, interactive=True)
        try:
            first = next(gen, "")          # provider errors surface here, before any bytes are sent
        except Exception as e:
            self._send(502, "application/json", _err(e)); return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        acc = first
        try:
            if first and self._event({"message": {"role": "assistant", "content": first}, "done": False}):
                for piece in gen:
                    acc += piece
                    if not self._event({"message": {"role": "assistant", "content": piece}, "done": False}):
                        break
        except Exception as e:
            self._event({"message": {"role": "assistant", "content": "\n[model error: %s]" % e}, "done": False})
        self._event({"done": True})
        self._chunk(b"")
        if acc:
            remember("assistant", acc)

    def _chunk(self, data):
        try:
            self.wfile.write(b"%x\r\n%s\r\n" % (len(data), data)); self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return False

    def _event(self, obj):
        return self._chunk((json.dumps(obj, ensure_ascii=False) + "\n").encode())

    def _chat_tool(self, intent, req):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        kind = intent["kind"]
        final = ""
        try:
            if kind == "image":
                self._event({"tool": {"kind": "image", "status": "working", "text": "Rendering image..."}})
                item = imagegen.generate(intent["prompt"], provider=req.get("image_provider"))
                self._event({"tool": {"kind": "image", "item": item}})
                final = "Image ready -> %s\nPrompt used: %s%s\nRate it (thumbs on the card) so I learn your taste." % (
                    item["url"], item["final_prompt"], ("\n(" + item["warning"] + ")") if item.get("warning") else "")
            elif kind == "video":
                job = videogen.generate(intent["prompt"], provider=req.get("video_provider"), on_done=_job_note("Video ready"))
                self._event({"tool": {"kind": "video", "job": job["id"], "status": "working"}})
                final = "Video generation started (job %s via %s). It will appear here when rendered; the Video Lab shows live progress." % (job["id"], job["meta"]["provider"])
            elif kind == "edit":
                src = req.get("current_video")
                if not src or not media.path_for(src):
                    final = "Load a video first: open the Video Lab, upload a clip or pick a generated one, then tell me the edit."
                else:
                    job = videoedit.edit(src, intent["instruction"], on_done=_job_note("Edited video ready"))
                    self._event({"tool": {"kind": "edit", "job": job["id"], "status": "working"}})
                    final = "Editing: %s (job %s). Progress shows in the Video Lab; the result lands here when done." % (intent["instruction"], job["id"])
            elif kind == "email":
                accounts = email_tools.list_accounts()
                self._event({"tool": {"kind": "email", "status": "working", "text": "Drafting email..."}})
                d = email_tools.draft(intent["intent"], to=intent.get("to"), account_id=(accounts[0]["id"] if accounts else None))
                if intent.get("subject"):
                    d["subject"] = intent["subject"]
                draft = {"to": intent.get("to") or [], "subject": d["subject"], "body": d["body"]}
                self._event({"tool": {"kind": "email", "draft": draft}})
                final = "Draft ready in the Mail panel:\nTo: %s\nSubject: %s\n\n%s\n\n%s" % (
                    ", ".join(draft["to"]) or "(add a recipient)", draft["subject"], draft["body"],
                    "Review it and press Send there; nothing goes out without your click." if accounts
                    else "Connect an account in the Mail panel to send it.")
            elif kind == "agent":
                goal = intent.get("goal") or ""
                if not goal:
                    final = "Give the agent a goal, e.g. /agent build a python script that renames my photos by date."
                else:
                    recent = "\n".join("%s: %s" % (m["role"], m["content"][:300]) for m in load_mem()[-6:-1])
                    job = agent.run(goal, autonomy=req.get("autonomy"), context=recent,
                                    on_done=lambda j: remember("assistant", ("Agent finished: %s" % (j["result"] or {}).get("final", "")) if j["status"] == "done" else ("Agent run failed: %s" % j["error"])))
                    self._event({"tool": {"kind": "agent", "job": job["id"], "status": "working"}})
                    final = "Super agent engaged (run %s, autonomy %s, model %s). Watch the steps in the Agent panel; I will answer here when it finishes or needs you." % (job["id"], job["meta"]["autonomy"], job["meta"]["model"])
            elif kind == "carousel":
                self._event({"tool": {"kind": "carousel", "status": "working", "text": "Writing and rendering slides..."}})
                c = carousel.build(intent.get("arg") or "")
                self._event({"tool": {"kind": "carousel", "item": c}})
                final = "Carousel ready (%d slides):\n%s\n\nCaption:\n%s\n%s" % (len(c["slides"]), "\n".join(s["url"] for s in c["slides"]), c["caption"], " ".join(c["hashtags"]))
            elif kind == "vault":
                hits = knowledge.search(intent.get("arg") or "", k=5)
                final = ("Vault results for \"%s\":\n\n" % intent.get("arg") + "\n\n".join("• %s / %s — %s\n  %s" % (h["pack"], h["file"].split("/")[-1], h["title"], h["snippet"]) for h in hits)) if hits else "Nothing in the vault matched that."
            elif kind == "skill":
                arg = (intent.get("arg") or "").strip().lower()
                if arg in ("", "off", "none", "stop"):
                    skills.activate(None); final = "Skill mode off. Back to the general AIXMOS assistant."
                else:
                    match = next((s for s in skills.list_skills() if s["id"] == arg or arg in s["id"] or arg in s["name"].lower()), None)
                    if not match:
                        final = "No skill named '%s'. Available: %s" % (arg, ", ".join(s["id"] for s in skills.list_skills()))
                    else:
                        skills.activate(match["id"]); final = "Skill activated: %s %s. I now follow that playbook in every reply. Say /skill off to leave." % (match["icon"], match["name"])
            elif kind == "lead":
                out = llm.json_call("Extract a CRM lead from the text. Return JSON with any of: name, company, role, contact (email or phone), location, source, hook (personalisation observation), notes, next_action. Unknown fields empty.", intent.get("arg") or "", num_ctx=2048, timeout=120) or {}
                out = {k: v for k, v in out.items() if k in ("name", "company", "role", "contact", "location", "source", "hook", "notes", "next_action") and v}
                if not out: raise ValueError("could not read a lead from that text")
                lead = crm.upsert_lead(out)
                final = "Lead saved to the CRM (id %s): %s" % (lead["id"], ", ".join("%s=%s" % (k, v) for k, v in out.items()))
            elif kind == "research":
                self._event({"tool": {"kind": "research", "status": "working", "text": "Scouring the web and cross-referencing the vault..."}})
                rep = research.run(intent.get("arg") or "", depth=req.get("depth") or "normal", cross=True,
                                   progress=lambda m: self._event({"tool": {"kind": "research", "status": "working", "text": m}}))
                self._event({"tool": {"kind": "research", "item": rep}})
                final = rep["markdown"]
            elif kind == "book":
                out = llm.json_call("Extract an appointment from the text. Return JSON: {name, contact, when (ISO-like date and time as written), tz, service, notes}. Unknown fields empty.", intent.get("arg") or "", num_ctx=2048, timeout=120) or {}
                ap = crm.book(out)
                final = "Booked: %s on %s%s (%s). Please confirm the time and timezone with them." % (ap["name"] or ap["contact"], ap["when"], (" " + ap["tz"]) if ap["tz"] else "", ap["service"] or "appointment")
            else:
                final = surfaces.run_intent(self, intent, req)   # e.g. /vault: one implementation, shared with /v1
        except Exception as e:
            final = "That capability hit an error: %s" % (str(e) or e.__class__.__name__)
        self._event({"message": {"role": "assistant", "content": final}, "done": True})
        self._chunk(b"")
        remember("assistant", final)

    # -------------------------------------------------------------- stt ----
    def _stt(self):
        cli, model = media.whisper_cli(), media.whisper_model()
        if not (cli and model):
            self._fail("whisper not installed", 503); return
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > 25 * 1024 * 1024:
            self._fail("bad audio size"); return
        audio = self.rfile.read(length)
        tmpdir = tempfile.mkdtemp(prefix="cs_stt_")
        wav = os.path.join(tmpdir, "in.wav"); base = os.path.join(tmpdir, "out")
        text = ""
        try:
            with open(wav, "wb") as f:
                f.write(audio)
            with STT_LOCK:
                subprocess.run([cli, "-m", model, "-f", wav, "-nt", "-np", "-otxt", "-of", base],
                               capture_output=True, timeout=180, cwd=os.path.dirname(cli), **media._no_window())
            try:
                with open(base + ".txt", "r", encoding="utf-8") as f:
                    text = f.read().strip()
            except OSError:
                text = ""
        except (subprocess.TimeoutExpired, OSError) as e:
            self._fail(e, 500); return
        finally:
            for p in (wav, base + ".txt"):
                try: os.remove(p)
                except OSError: pass
            try: os.rmdir(tmpdir)
            except OSError: pass
        self._json({"text": text})

    def _forget(self):
        with LOCK:
            try:
                os.remove(MEMFILE)
            except OSError:
                pass
            _MEM_CACHE["mtime"], _MEM_CACHE["data"] = None, None
        self._json({"ok": True})

    def _upload(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_UPLOAD:
            self._fail("file is empty or larger than 800 MB"); return
        name = urllib.parse.unquote(self.headers.get("X-Filename", "upload.mp4"))
        ext = os.path.splitext(name)[1].lower() or ".mp4"
        if ext not in media.EXT_MIME:
            self._fail("unsupported file type " + ext); return
        kind = "audio" if ext in (".mp3", ".wav", ".m4a") else ("images" if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif") else "uploads")
        media.ensure_dirs()
        path = os.path.join(media.MEDIA, kind, media.new_id() + ext)
        left = length
        with open(path, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(1024 * 1024, left))
                if not chunk:
                    break
                f.write(chunk); left -= len(chunk)
        info = media.probe(path) if kind != "images" else {}
        self._json({"url": media.url_for(path), "name": name, "kind": kind, "info": info})

    # ----------------------------------------------------------- routes ----
    def do_GET(self):
        if not self._guard(False):
            return
        p, _, q = self.path.partition("?")
        qs = urllib.parse.parse_qs(q)
        g = lambda k, d=None: (qs.get(k) or [d])[0]
        try:
            if p == "/api/health":
                from aixmos.local_cli import identity
                self._json({"app": "AIXMOS", "version": VERSION, "installation": identity(),
                            "pid": os.getpid(), "running": True})
            elif p in ("/", "/index.html"):
                self._index()
            elif p.startswith("/media/"):
                self._media()
            elif p == "/api/tags":
                ui = providers.models_for_ui()       # every usable model (Ollama, LM Studio, allowed cloud) + the default
                self._json(ui) if ui["models"] else self._fail(providers.route("chat")[1], 502)
            elif p == "/api/models":
                self._json(providers.status(fresh=g("fresh") == "1"))
            elif p == "/api/memory":
                self._json({"messages": load_mem()})
            elif p == "/api/telemetry":
                try: sysinfo = context_tools.get_system()
                except Exception: sysinfo = {}
                self._json({"system": sysinfo, "tools": media.tools_status(), "caps": capabilities(),
                            "models": llm.list_models(), "time": time.strftime("%H:%M:%S")})
            elif p == "/api/settings":
                self._json(surfaces.settings_view(self))
            elif p == "/api/jobs":
                self._json({"jobs": jobs.list_jobs()})
            elif p.startswith("/api/jobs/"):
                j = jobs.get(p.rsplit("/", 1)[1])
                self._json(j) if j else self._fail("no such job", 404)
            elif p == "/api/images":
                self._json({"items": imagegen.list_items(int(g("limit", 60))), "profile": imagegen.profile(),
                            "providers": settings.providers_for("image")})
            elif p == "/api/videos":
                self._json({"items": videogen.list_items(), "providers": settings.providers_for("video") + ["local"],
                            "ops": videoedit.OPS})
            elif p == "/api/email/accounts":
                self._json({"accounts": email_tools.list_accounts(), "presets": email_tools.PRESETS,
                            "oauth": {"google": settings.configured("google_oauth"), "microsoft": settings.configured("microsoft_oauth")},
                            "sent": email_tools.sent_log(10)})
            elif p == "/api/email/inbox":
                self._json({"messages": email_tools.inbox(g("account"), int(g("n", 12)))})
            elif p == "/api/email/read":
                self._json(email_tools.read(g("account"), g("id")))
            elif p == "/api/email/oauth/start":
                url = email_tools.oauth_start(g("provider"))
                self.send_response(302); self.send_header("Location", url); self.send_header("Content-Length", "0"); self.end_headers()
            elif p in ("/oauth/google", "/oauth/microsoft"):
                prov = p.rsplit("/", 1)[1]
                if g("error"):
                    self._oauth_page("Sign-in cancelled: " + (g("error_description") or g("error")), False); return
                try:
                    res = email_tools.oauth_finish(prov, g("code"), g("state"))
                    self._oauth_page("Connected " + res["email"] + ". You can close this tab.", True)
                except Exception as e:
                    self._oauth_page("Sign-in failed: " + str(e), False)
            elif surfaces.route_get(self, p, g):
                pass
            elif p.startswith("/api/"):
                self._proxy_get()
            else:
                self.send_error(404)
        except (ValueError, KeyError, PermissionError) as e:
            self._fail(e, 400)
        except Exception as e:
            self._fail(e, 500)

    def _oauth_page(self, msg, ok):
        html = ("<!doctype html><meta charset=utf-8><title>AIXMOS</title><body style='background:#030810;color:%s;"
                "font-family:Segoe UI,sans-serif;display:grid;place-items:center;height:100vh;margin:0'><div style='text-align:center'>"
                "<div style='font-size:42px'>%s</div><p style='font-size:16px'>%s</p></div>"
                "<script>try{window.opener&&window.opener.postMessage({aixmos:'oauth',ok:%s},'*')}catch(e){}"
                "setTimeout(function(){window.close()},2500)</script></body>"
                % ("#7ff3ff" if ok else "#ff6b6b", "&#10003;" if ok else "&#9888;", msg.replace("<", "&lt;"), "true" if ok else "false"))
        self._send(200, "text/html; charset=utf-8", html.encode())

    def do_POST(self):
        if not self._guard(True):
            return
        p = self.path.split("?")[0]
        try:
            if p == "/api/runtime/stop":
                import secrets
                token = os.environ.get("AIXMOS_CONTROL_TOKEN", "")
                supplied = self.headers.get("X-AIXMOS-Control", "")
                if not token or not secrets.compare_digest(token, supplied):
                    self._fail("Runtime control token required", 403)
                    return
                self._json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            elif p == "/api/chat":       self._chat()
            elif p == "/api/stt":      self._stt()
            elif p == "/api/forget":   self._forget()
            elif p in ("/api/upload", "/api/video/upload"):
                self._upload()
            elif p == "/api/settings":
                b = self._body()
                settings.update(b.get("providers"), b.get("prefs"))
                if b.get("business"): skills.save_profile(b["business"])
                if b.get("brand"): carousel.save_brand(b["brand"])
                self._json(surfaces.settings_view(self))
            elif p == "/api/image/generate":
                b = self._body()
                item = imagegen.generate(b.get("prompt"), provider=b.get("provider"), model=b.get("model"), size=b.get("size"),
                                         enhance=b.get("enhance"), style=b.get("style"))
                remember("assistant", "Image ready -> %s\nPrompt used: %s" % (item["url"], item["final_prompt"]))
                self._json(item)
            elif p == "/api/image/rate":
                b = self._body()
                self._json(imagegen.rate(b.get("id"), b.get("rating"), b.get("note", "")))
            elif p == "/api/image/refine":
                b = self._body()
                self._json(imagegen.refine(b.get("id"), b.get("instruction"), mode=b.get("mode", "prompt"), provider=b.get("provider")))
            elif p == "/api/video/generate":
                b = self._body()
                self._json(videogen.generate(b.get("prompt"), provider=b.get("provider"), model=b.get("model"), image_url=b.get("image_url"),
                                             seconds=b.get("seconds"), aspect=b.get("aspect"), on_done=_job_note("Video ready")))
            elif p == "/api/video/plan":
                b = self._body()
                src = media.path_for(b.get("source"))
                if not src:
                    raise ValueError("source video not found")
                self._json(videoedit.plan(src, b.get("instruction") or "", b.get("extras"), use_llm=b.get("use_llm", True)))
            elif p == "/api/video/edit":
                b = self._body()
                self._json(videoedit.edit(b.get("source"), b.get("instruction"), extras=b.get("extras"), ops=b.get("ops"),
                                          use_llm=b.get("use_llm", True), on_done=_job_note("Edited video ready")))
            elif p == "/api/email/accounts":
                self._json(email_tools.add_smtp(self._body()))
            elif p == "/api/email/accounts/remove":
                self._json({"ok": email_tools.remove_account(self._body().get("id"))})
            elif p == "/api/email/draft":
                b = self._body()
                self._json(email_tools.draft(b.get("intent") or "", to=b.get("to"), tone=b.get("tone") or "professional",
                                             account_id=b.get("account"), reply_to=b.get("reply_to"), length=b.get("length") or "medium"))
            elif p == "/api/email/refine":
                b = self._body()
                self._json(email_tools.refine(b.get("subject") or "", b.get("body") or "", b.get("instruction") or "", b.get("account")))
            elif p == "/api/email/send":
                # Every send is an approvals item. The owner clicking Send in the app IS the approval (recorded as
                # such); any other caller (scripts, agents, MCP clients) only queues it for the owner.
                from aixmos import approvals, channels, head
                b = self._body()
                owner = head.ui_ok(self)
                payload = {k: b.get(k) for k in ("to", "subject", "body", "cc", "bcc", "attachments", "reply_to", "account")}
                payload.update(skill="mail", manual=owner)
                if not channels.recipients(payload["to"]):
                    raise ValueError("at least one valid recipient is required")
                item = approvals.propose("email.send", "Email to %s: %s" % (payload["to"], str(payload["subject"] or "")[:80]),
                                         payload, skill="mail", summary=str(payload["body"] or "")[:1500], risk="send")
                if not owner:
                    self._json({"queued": True, "approval": item["id"],
                                "note": "Waiting for the owner's approval in the AIXMOS Command Center"}, 202)
                else:
                    item = approvals.decide(item["id"], True, by="owner (Mail)")
                    if item["status"] != "executed":
                        raise ValueError(item.get("error") or "not sent")
                    res = item["result"] or {}
                    remember("assistant", "Email sent from %s to %s: \"%s\"" % (res.get("from"), ", ".join(res.get("to") or []), res.get("subject")))
                    self._json(dict(res, ok=True))
            elif surfaces.route_post(self, p):
                pass
            else:
                self.send_error(404)
        except (ValueError, KeyError, PermissionError) as e:
            self._fail(e, 400)
        except Exception as e:
            self._fail(e, 500)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    settings.RUNTIME["port"] = port
    media.ensure_dirs()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    try:   # storage hygiene: storyboard clips and edit scratch older than a day
        tmpdir = os.path.join(media.MEDIA, "tmp"); cutoff = time.time() - 86400
        for dp, dn, fn in os.walk(tmpdir, topdown=False):
            for f in fn:
                p = os.path.join(dp, f)
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
            for d in dn:
                try: os.rmdir(os.path.join(dp, d))
                except OSError: pass
    except Exception:
        pass
    os.makedirs(agent.WORKSPACE, exist_ok=True)
    if os.environ.get("AIXMOS_NO_PREWARM") != "1":
        threading.Thread(target=context_tools.prewarm, daemon=True).start()
    threading.Thread(target=surfaces.boot_index, daemon=True).start()
    from aixmos import head
    threading.Thread(target=head.boot, daemon=True).start()     # built-in skills + their timers + the scheduler
    from aixmos import telegram
    telegram.start()          # the owner's phone door; idles until a bot token is saved and a phone is paired
    n = len(load_mem())
    print("=" * 56)
    print("  PROJECT AIXMOS  //  JARVIS super agent online")
    print("  UI      ->  http://localhost:%d" % port)
    print("  OpenAI  ->  http://localhost:%d/v1  (models: aixmos, aixmos-agent)" % port)
    print("  MCP     ->  http://localhost:%d/mcp" % port)
    print("  Memory  ->  %s  (%d msgs)" % (MEMFILE, n))
    print("  ffmpeg  ->  %s" % (media.ffmpeg() or "NOT FOUND"))
    print("  (Ctrl+C to stop)")
    print("=" * 56)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Project AIXMOS stopped.")
    finally:
        srv.server_close()
