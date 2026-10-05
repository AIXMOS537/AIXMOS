"""llm.py -- non-streaming model calls (planning, JSON, agent steps). Routing, fallback and privacy live in providers.py;
this module keeps the small helper API every feature already uses."""
import json, re
from . import settings, providers

FALLBACK_MODEL = providers.PREFERRED_LOCAL[0]
KEEP_ALIVE = providers.KEEP_ALIVE

def ollama_url():
    return providers.ollama_url()

def list_models():
    """Installed models on the local Ollama ([] when it is not running)."""
    return providers.health(providers.get("ollama"))["models"]

def available():
    """True when any model the owner's policy allows is up (Ollama, LM Studio, or an allowed cloud model)."""
    return bool(providers.candidates("chat"))

def pick_model(prefer=None):
    return providers.pick_model(providers.get("ollama"), prefer)

def options(temperature=0.3, num_ctx=None):
    """Uniform Ollama runtime options (one num_ctx for every caller, so the model never reloads between features)."""
    return providers.get("ollama").options(temperature)

def chat(messages, model=None, json_mode=False, temperature=0.3, num_ctx=None, timeout=240):
    return providers.chat(messages, model=model, json_mode=json_mode, temperature=temperature, timeout=timeout)["content"]

def chat_raw(messages, model=None, tools=None, temperature=0.2, num_ctx=None, timeout=600):
    """One agent step. Returns {"message": {"content", "tool_calls"}, "model", "provider"} on the first provider
    that can call tools (Ollama, then LM Studio)."""
    r = providers.chat(messages, model=model, task="agent" if tools else "chat", need=("tools",) if tools else (),
                       tools=tools, temperature=temperature, timeout=timeout)
    return {"message": {"role": "assistant", "content": r["content"], "tool_calls": r["tool_calls"]},
            "model": r["model"], "provider": r["provider"], "done_reason": r.get("done_reason", "")}

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
