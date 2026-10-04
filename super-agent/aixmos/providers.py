"""
providers.py -- the model layer. AIXMOS owns the work; a provider only reasons inside it.

One interface for every model provider (ported from the private line's engines.py):
  info()                    id, kind (local | cloud | coding_agent), privacy (PRIVATE-LOCAL | CLOUD), cost,
                            capabilities (chat, json, tools, stream, code, vision), context_limit
  health() / list_models()  availability is probed, never assumed (cached a few seconds)
  chat(messages, model=None, json_mode=False, tools=None, temperature=0.3, timeout=240)
        -> {"content", "tool_calls": [{"function": {"name", "arguments"}}], "model", "provider", "done_reason"}
  stream(messages, ...)     -> yields text pieces (chat providers)

Adapters: Ollama, LM Studio and any OpenAI-compatible local server, OpenAI (customer's key), Anthropic (customer's
key), Claude Code and Codex CLIs (coding agents on the customer's own login). A new provider is a new class, not a
redesign. No UI scraping, no borrowed sessions: supported HTTP APIs and official CLIs only.

route(task, need) picks a provider and NEVER breaks the owner's policy:
  privacy_mode PRIVATE-LOCAL      nothing leaves the machine
  cloud_allowed False (default)   cloud providers are never chosen, even when a key is saved
  no credentials                  a provider without its key/login is not available
Local first. Cloud only when allowed AND connected AND (the task needs it or nothing local is up). Automatic cloud
calls are charged against the daily spend budget (guard.charge) before they run.
"""
import json, os, shutil, subprocess, threading, time, urllib.error, urllib.request

from . import settings

PRIVACY_MODES = ("PRIVATE-LOCAL", "LOCAL-PREFERRED", "CLOUD-OK")
# Commercial-use licences first: qwen3 instruct (Apache-2.0), llama3.x (Llama community licence). qwen2.5:3b is
# research-only. Plain "qwen3:4b" is a thinking-only build: it talks to itself and makes no tool calls (measured
# 2026-10-04), so the instruct build is the default.
PREFERRED_LOCAL = ("qwen3:4b-instruct", "qwen3:8b", "llama3.1:8b", "llama3.2:3b", "qwen2.5:3b")
KEEP_ALIVE = "30m"
_HEALTH_TTL = 8.0

class ProviderError(RuntimeError):
    """kind: offline | auth | bad_request | timeout | rate_limited | server | policy"""
    def __init__(self, msg, kind="server", provider=""):
        super().__init__(msg)
        self.kind, self.provider = kind, provider

def _classify(e):
    if isinstance(e, ProviderError):
        return e.kind
    if isinstance(e, PermissionError):          # SpendBlocked and policy refusals; PermissionError is an OSError
        return "policy"
    if isinstance(e, urllib.error.HTTPError):
        return {401: "auth", 403: "auth", 400: "bad_request", 404: "bad_request", 422: "bad_request",
                429: "rate_limited"}.get(e.code, "server")
    if isinstance(e, (TimeoutError, subprocess.TimeoutExpired)) or "timed out" in str(e).lower():
        return "timeout"
    if isinstance(e, (urllib.error.URLError, ConnectionError, OSError)):
        return "offline"
    return "server"

def _http(url, body=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers=dict({"Content-Type": "application/json"}, **(headers or {})),
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")

def _open(url, body, headers=None, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers=dict({"Content-Type": "application/json"}, **(headers or {})))
    return urllib.request.urlopen(req, timeout=timeout)

def ollama_url():
    return (settings.pref("ollama_url") or "http://127.0.0.1:11434").rstrip("/")

# ----------------------------------------------------------------- base ----
class Provider:
    id = "base"; kind = "local"; privacy = "PRIVATE-LOCAL"; cost = "local"; context_limit = 4096
    capabilities = ("chat",)
    def info(self):
        return {"id": self.id, "kind": self.kind, "privacy": self.privacy, "cost": self.cost,
                "capabilities": list(self.capabilities), "context_limit": self.context_limit}
    def list_models(self):
        return []
    def health(self):
        try:
            m = self.list_models()
            return {"ok": bool(m), "models": m[:40], "error": "" if m else "no models installed"}
        except Exception as e:
            return {"ok": False, "models": [], "error": "%s: %s" % (_classify(e), str(e)[:120])}
    def chat(self, messages, model=None, **kw):
        raise ProviderError("%s cannot chat" % self.id, "bad_request", self.id)
    def stream(self, messages, model=None, **kw):
        yield self.chat(messages, model=model, **kw)["content"]

# --------------------------------------------------------------- ollama ----
class Ollama(Provider):
    id = "ollama"; capabilities = ("chat", "json", "tools", "stream", "code", "vision", "embeddings")
    def __init__(self, url=None):
        self.url = (url or ollama_url()).rstrip("/")
    def list_models(self):
        return [m["name"] for m in _http(self.url + "/api/tags", timeout=4).get("models", [])]
    def options(self, temperature):
        # ONE context size for every caller: Ollama reloads the model runner when num_ctx changes
        return {"temperature": temperature, "num_ctx": int(settings.pref("llm_ctx") or 4096),
                "num_thread": int(settings.pref("llm_threads") or 3)}
    def _payload(self, messages, model, stream, temperature, json_mode=False, tools=None):
        p = {"model": model or pick_model(self), "messages": messages, "stream": stream, "think": False,
             "keep_alive": KEEP_ALIVE, "options": self.options(temperature)}
        if json_mode:
            p["format"] = "json"
        if tools:
            p["tools"] = tools
        return p
    def chat(self, messages, model=None, json_mode=False, tools=None, temperature=0.3, timeout=240, **kw):
        p = self._payload(messages, model, False, temperature, json_mode, tools)
        try:
            d = _http(self.url + "/api/chat", p, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 400 and "think" in (e.read() or b"").decode("utf-8", "replace"):
                p.pop("think", None)            # older Ollama without the think switch
                d = _http(self.url + "/api/chat", p, timeout=timeout)
            else:
                raise
        m = d.get("message") or {}
        return {"content": m.get("content") or "", "tool_calls": m.get("tool_calls") or [], "model": p["model"],
                "provider": self.id, "done_reason": d.get("done_reason", "")}
    def stream(self, messages, model=None, temperature=0.7, timeout=600, **kw):
        resp = _open(self.url + "/api/chat", self._payload(messages, model, True, temperature), timeout=timeout)
        buf = b""
        with resp:
            while True:
                chunk = resp.read(512)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        piece = (json.loads(line).get("message") or {}).get("content") or ""
                    except ValueError:
                        continue
                    if piece:
                        yield piece

# ------------------------------------------------------ OpenAI-compatible ----
def _openai_messages(messages):
    """Our transcript (Ollama shape: tool messages carry tool_name) -> OpenAI shape with tool_call ids."""
    out, pending = [], []
    for i, m in enumerate(messages):
        m = dict(m)
        if m.get("role") == "assistant" and m.get("tool_calls"):
            calls = []
            for j, c in enumerate(m["tool_calls"]):
                f = c.get("function") or {}
                cid = c.get("id") or "call_%d_%d" % (i, j)
                args = f.get("arguments")
                calls.append({"id": cid, "type": "function",
                              "function": {"name": f.get("name", ""), "arguments": args if isinstance(args, str) else json.dumps(args or {})}})
                pending.append(cid)
            m["tool_calls"] = calls
            m["content"] = m.get("content") or None
        elif m.get("role") == "tool":
            m["tool_call_id"] = m.get("tool_call_id") or (pending.pop(0) if pending else "call_%d" % i)
            m.pop("tool_name", None)
        out.append(m)
    return out

class OpenAICompat(Provider):
    """LM Studio, llama.cpp server, vLLM, LocalAI ... or api.openai.com with the customer's key."""
    capabilities = ("chat", "json", "tools", "stream", "code")
    def __init__(self, id_="lmstudio", url=None, key_ref=None, kind="local"):
        self.id, self.kind = id_, kind
        self.url = (url or settings.pref("lmstudio_url") or "http://127.0.0.1:1234/v1").rstrip("/")
        self.key_ref = key_ref                   # (provider, field) in settings/secret_store, cloud only
        if kind == "cloud":
            self.privacy, self.cost, self.context_limit = "CLOUD", "metered (customer account)", 128000
        else:
            self.context_limit = 8192
    def _headers(self):
        if not self.key_ref:
            return {}
        key = settings.get(*self.key_ref)
        if not key:
            raise ProviderError("%s is not connected on this computer" % self.id, "auth", self.id)
        return {"Authorization": "Bearer " + key}
    def list_models(self):
        if self.kind == "cloud":
            self._headers()                      # raises when no key: not available
            return [settings.get("openai", "chat_model") or "gpt-4.1-mini"]
        return [m["id"] for m in _http(self.url + "/models", timeout=4).get("data", []) if "embed" not in m["id"].lower()]
    def _body(self, messages, model, temperature, json_mode=False, tools=None, stream=False):
        b = {"model": model or (self.list_models() or [""])[0], "messages": _openai_messages(messages),
             "temperature": temperature, "stream": stream}
        if json_mode and self.kind == "cloud":
            b["response_format"] = {"type": "json_object"}       # local servers differ; parse_json copes with prose
        if tools:
            b["tools"] = tools
        return b
    def chat(self, messages, model=None, json_mode=False, tools=None, temperature=0.3, timeout=240, **kw):
        b = self._body(messages, model, temperature, json_mode, tools)
        d = _http(self.url + "/chat/completions", b, headers=self._headers(), timeout=timeout)
        ch = (d.get("choices") or [{}])[0]
        m = ch.get("message") or {}
        calls = []
        for c in m.get("tool_calls") or []:
            f = c.get("function") or {}
            args = f.get("arguments") or "{}"
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except ValueError:
                args = {}
            calls.append({"id": c.get("id"), "function": {"name": f.get("name", ""), "arguments": args}})
        return {"content": m.get("content") or "", "tool_calls": calls, "model": b["model"], "provider": self.id,
                "done_reason": ch.get("finish_reason", "")}
    def stream(self, messages, model=None, temperature=0.7, timeout=600, **kw):
        resp = _open(self.url + "/chat/completions", self._body(messages, model, temperature, stream=True),
                     headers=self._headers(), timeout=timeout)
        buf = b""
        with resp:
            while True:
                chunk = resp.read(512)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if not line.startswith(b"data:") or line == b"data: [DONE]":
                        continue
                    try:
                        piece = ((json.loads(line[5:]).get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                    except ValueError:
                        continue
                    if piece:
                        yield piece

# ------------------------------------------------------------ anthropic ----
class Anthropic(Provider):
    """The customer's own Anthropic API key (Integrations -> Claude). Never bundled, never logged."""
    id = "anthropic"; kind = "cloud"; privacy = "CLOUD"; cost = "metered (customer account)"
    capabilities = ("chat", "json", "code", "vision"); context_limit = 200000
    URL = "https://api.anthropic.com/v1/messages"
    def _key(self):
        key = settings.get("anthropic", "api_key")
        if not key:
            raise ProviderError("Claude is not connected on this computer", "auth", self.id)
        return key
    def list_models(self):
        self._key()
        return [settings.get("anthropic", "chat_model") or "claude-sonnet-5-5"]
    def chat(self, messages, model=None, json_mode=False, tools=None, temperature=0.3, timeout=240, max_tokens=2048, **kw):
        if tools:
            raise ProviderError("tool calling runs on a local model in this version", "bad_request", self.id)
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        turns = []
        for m in messages:                       # roles must alternate, starting with the user
            if m.get("role") not in ("user", "assistant", "tool"):
                continue
            role, text = ("assistant" if m["role"] == "assistant" else "user"), str(m.get("content") or "")
            if turns and turns[-1]["role"] == role:
                turns[-1]["content"] += "\n\n" + text
            elif turns or role == "user":
                turns.append({"role": role, "content": text})
        if json_mode:
            system += "\n\nReply with one JSON object only."
        mdl = model or self.list_models()[0]
        d = _http(self.URL, {"model": mdl, "max_tokens": int(max_tokens), "system": system, "temperature": temperature,
                             "messages": turns or [{"role": "user", "content": "(empty)"}]},
                  headers={"x-api-key": self._key(), "anthropic-version": "2023-06-01"}, timeout=timeout)
        return {"content": "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"),
                "tool_calls": [], "model": mdl, "provider": self.id, "done_reason": d.get("stop_reason", "")}

# ---------------------------------------------------------- coding agents ----
HOST_SESSION_ENV = ("CLAUDE", "ANTHROPIC", "OPENAI", "CODEX")

def agent_env():
    """Environment for a CLI coding agent: its OWN sign-in only. Nothing from a parent AI session (base URLs, session
    tokens, sockets) and no provider keys from the host shell reach it."""
    return {k: v for k, v in os.environ.items() if not k.upper().startswith(HOST_SESSION_ENV)}

# Claude Code as a job engine: edits only, inside the job folder; it must not inherit the host's hooks, MCP servers
# or saved sessions.
CLAUDE_CODE_ARGS = ["-p", "--permission-mode", "acceptEdits", "--setting-sources", "project", "--strict-mcp-config",
                    "--no-session-persistence", "--allowedTools", "Read,Edit,Write,Glob,Grep", "--output-format", "text"]

class CLIAgent(Provider):
    """A coding agent run through its own CLI login (Claude Code, Codex). AIXMOS never holds that login."""
    kind = "coding_agent"; privacy = "CLOUD"; cost = "customer account"; capabilities = ("code",)
    def __init__(self, id_, exe, args, stdin_prompt=False):
        self.id, self.exe, self.args, self.stdin_prompt = id_, exe, args, stdin_prompt
    def list_models(self):
        if not shutil.which(self.exe):
            raise ProviderError(self.exe + " is not installed", "offline", self.id)
        return [self.id]
    def run(self, prompt, cwd=None, timeout=900):
        # multi-line prompts do not survive a Windows .cmd shim as an argument; use stdin where the CLI supports it
        argv = [shutil.which(self.exe)] + self.args + ([] if self.stdin_prompt else [prompt])
        r = subprocess.run(argv, cwd=cwd, input=(prompt if self.stdin_prompt else None), capture_output=True, text=True,
                           env=agent_env(), encoding="utf-8", errors="replace", timeout=timeout)
        if r.returncode != 0:
            raise ProviderError("%s exited %s: %s" % (self.id, r.returncode, (r.stderr or r.stdout or "").strip()[-300:]),
                                "server", self.id)
        return r.stdout

# ---------------------------------------------------------------- registry ----
def all_providers():
    return [Ollama(), OpenAICompat("lmstudio"),
            Anthropic(), OpenAICompat("openai", "https://api.openai.com/v1", ("openai", "api_key"), kind="cloud"),
            CLIAgent("claude-code", "claude", CLAUDE_CODE_ARGS, stdin_prompt=True),
            CLIAgent("codex", "codex", ["exec", "--full-auto"])]

def get(pid):
    return next((p for p in all_providers() if p.id == pid), None)

_HEALTH, _HLOCK = {}, threading.Lock()

def health(p, fresh=False):
    key = (p.id, getattr(p, "url", ""))
    with _HLOCK:
        hit = _HEALTH.get(key)
        if hit and not fresh and time.time() - hit[0] < _HEALTH_TTL:
            return hit[1]
    h = p.health()
    with _HLOCK:
        _HEALTH[key] = (time.time(), h)
    return h

def forget_health():
    with _HLOCK:
        _HEALTH.clear()

def policy():
    mode = settings.pref("privacy_mode") or "LOCAL-PREFERRED"
    mode = mode if mode in PRIVACY_MODES else "LOCAL-PREFERRED"
    cloud = bool(settings.pref("cloud_allowed")) and mode != "PRIVATE-LOCAL"
    return {"privacy_mode": mode, "cloud_allowed": cloud}

def status(fresh=False):
    pol = policy()
    out = []
    for p in all_providers():
        h = health(p, fresh)
        blocked = p.privacy == "CLOUD" and not pol["cloud_allowed"]
        out.append(dict(p.info(), available=h["ok"], models=h.get("models", []), reason=h.get("error", ""),
                        usable=h["ok"] and not blocked, policy_note="cloud is off in your privacy settings" if blocked else ""))
    return {"policy": pol, "providers": out}

def pick_model(provider, prefer=None):
    """Best installed model on a provider: explicit choice, the owner's setting, then commercial-licence defaults."""
    try:
        models = health(provider)["models"] or provider.list_models()
    except Exception:
        models = []
    if provider.id != "ollama":
        return prefer if prefer in models else (models[0] if models else (prefer or ""))
    for cand in (prefer, settings.pref("chat_model")) + PREFERRED_LOCAL:
        if cand and cand in models:
            return cand
    small = [m for m in models if any(t in m for t in ("3b", "4b")) and "embed" not in m]
    return small[0] if small else (models[0] if models else PREFERRED_LOCAL[0])

def resolve(model):
    """UI/API model names: "lmstudio/<id>", "anthropic/<id>", "openai/<id>"; anything else is an Ollama tag."""
    m = str(model or "")
    for pid in ("lmstudio", "anthropic", "openai"):
        if m.startswith(pid + "/"):
            return get(pid), m[len(pid) + 1:]
    return (get("ollama"), m) if m else (None, "")

def candidates(task="chat", need=()):
    """Providers in the order route() would try them, filtered by policy, health and capability."""
    pol = policy()
    need = set(need) | ({"tools"} if task == "agent" else set())
    order = ["ollama", "lmstudio"]
    cloud = ["anthropic", "openai"]
    if pol["cloud_allowed"]:
        prefer_cloud = task in ("complex", "long_context") or settings.pref("prefer_cloud")
        order = (cloud + order) if prefer_cloud else (order + cloud)
    out = []
    for pid in order:
        p = get(pid)
        if p.privacy == "CLOUD" and not pol["cloud_allowed"]:
            continue
        if not need <= set(p.capabilities):
            continue
        if health(p)["ok"]:
            out.append(p)
    return out

def route(task="chat", need=()):
    """-> (provider | None, reason)"""
    c = candidates(task, need)
    if c:
        p = c[0]
        return p, ("local first" if p.kind == "local" else "cloud (allowed in your settings)")
    pol = policy()
    return None, "no model available%s: start Ollama or LM Studio%s" % (
        "" if pol["cloud_allowed"] else " on this computer", "" if pol["cloud_allowed"] else ", or allow a connected cloud model")

def _charge(p, interactive):
    if p.kind == "cloud":
        from . import guard
        guard.charge(p.id, "chat", interactive=interactive, ref="llm")

def _audit_fallback(failed, err):
    try:
        from . import store
        store.audit("model.fallback", failed, {"error": str(err)[:200], "kind": _classify(err)})
    except Exception:
        pass

def chat(messages, model=None, task="chat", need=(), interactive=False, **kw):
    """Run one chat on the first provider that works, falling back on outages (never on bad requests or policy).
    An explicit model ("lmstudio/x" or an Ollama tag) is tried first, then the routed order."""
    tried, last = [], None
    first, mdl = resolve(model or settings.pref("chat_model"))
    order = ([first] if first else []) + [p for p in candidates(task, need) if not first or p.id != first.id]
    if first and first.privacy == "CLOUD" and not policy()["cloud_allowed"]:
        raise ProviderError("cloud models are off in your privacy settings", "policy", first.id)
    for p in order:
        try:
            _charge(p, interactive)
            r = p.chat(messages, model=(mdl if p is first else None), **kw)
            if tried:
                r["fallback_from"] = tried
            return r
        except Exception as e:
            kind = _classify(e)
            if kind in ("bad_request", "policy"):
                raise
            tried.append(p.id); last = e
            _audit_fallback(p.id, e)
            with _HLOCK:
                _HEALTH.pop((p.id, getattr(p, "url", "")), None)
    if last:
        raise ProviderError("no model answered (%s): %s" % (", ".join(tried), last), _classify(last))
    raise ProviderError(route(task, need)[1], "offline")

def stream(messages, model=None, interactive=True, **kw):
    """Yield text pieces; falls back to the next provider only if the first fails before producing any text."""
    first, mdl = resolve(model or settings.pref("chat_model"))
    order = ([first] if first else []) + [p for p in candidates("chat", ("stream",)) if not first or p.id != first.id]
    if first and first.privacy == "CLOUD" and not policy()["cloud_allowed"]:
        raise ProviderError("cloud models are off in your privacy settings", "policy", first.id)
    last = None
    for p in order:
        started = False
        try:
            _charge(p, interactive)
            for piece in p.stream(messages, model=(mdl if p is first else None), **kw):
                started = True
                yield piece
            return
        except Exception as e:
            if started or _classify(e) in ("bad_request", "policy"):
                raise
            last = e
            _audit_fallback(p.id, e)
    raise ProviderError("no model answered: %s" % (last or route("chat")[1]), _classify(last) if last else "offline")

def models_for_ui():
    """Every usable chat model, in the names resolve() understands, plus the routed default."""
    names = []
    for p in candidates("chat"):
        for m in health(p)["models"]:
            if p.id == "ollama":
                if "embed" not in m:
                    names.append(m)
            else:
                names.append("%s/%s" % (p.id, m))
    p, _ = route("chat")
    default = ""
    if p:
        m = pick_model(p)
        default = m if p.id == "ollama" else "%s/%s" % (p.id, m)
    return {"models": [{"name": n} for n in names], "default": default}
