"""llm.py -- small helper around the local Ollama daemon for non-streaming calls (planning, JSON)."""
import json, re, urllib.request, urllib.error
from . import settings

OLLAMA = "http://localhost:11434"
FALLBACK_MODEL = "qwen2.5:3b"

def list_models():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []

def pick_model(prefer=None):
    models = list_models()
    for cand in (prefer, settings.pref("chat_model"), FALLBACK_MODEL):
        if cand and cand in models:
            return cand
    for m in models:
        if "3b" in m:
            return m
    return models[0] if models else FALLBACK_MODEL

KEEP_ALIVE = "30m"

def options(temperature=0.3, num_ctx=None):
    """Uniform runtime options. num_ctx is deliberately the same for every caller: Ollama restarts
    the model runner whenever the context size changes, which cost ~4 s per call on this machine."""
    return {"temperature": temperature, "num_ctx": int(settings.pref("llm_ctx") or 4096),
            "num_thread": int(settings.pref("llm_threads") or 3)}

def chat(messages, model=None, json_mode=False, temperature=0.3, num_ctx=None, timeout=240):
    payload = {"model": model or pick_model(), "messages": messages, "stream": False,
               "keep_alive": KEEP_ALIVE, "options": options(temperature)}
    if json_mode:
        payload["format"] = "json"
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return (json.loads(r.read()).get("message") or {}).get("content", "")

def chat_raw(messages, model=None, tools=None, temperature=0.2, num_ctx=None, timeout=600):
    """Full Ollama response dict (message may carry tool_calls)."""
    payload = {"model": model or pick_model(), "messages": messages, "stream": False,
               "keep_alive": KEEP_ALIVE, "options": options(temperature)}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def text(system, user, **kw):
    try:
        return chat([{"role": "system", "content": system}, {"role": "user", "content": user}], **kw).strip()
    except Exception:
        return ""

def parse_json(s):
    if not s:
        return None
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    try:
        return json.loads(s)
    except ValueError:
        m = re.search(r"\{.*\}", s, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
    return None

def json_call(system, user, **kw):
    """Ask for JSON; returns dict or None (never raises)."""
    try:
        out = chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                   json_mode=True, **kw)
    except Exception:
        return None
    d = parse_json(out)
    return d if isinstance(d, dict) else None
