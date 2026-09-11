"""
settings.py -- local settings store (memory/settings.json).

Holds provider API keys, model choices and preferences. Keys are only ever
written here (a gitignored folder on this machine) and are never echoed back
to the browser except as a masked "....last4" indicator.
"""
import os, json, threading

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMDIR   = os.path.join(ROOT, "memory")
FILE     = os.path.join(MEMDIR, "settings.json")
_LOCK    = threading.Lock()
RUNTIME  = {"port": 8770}

# Provider registry: what each provider needs and what it can do.
PROVIDERS = {
    "pollinations": {"label": "Pollinations (free, no key)", "fields": [], "caps": ["image"],
                     "defaults": {"image_model": "flux"}, "help": "No account needed. Rate limited, public service."},
    "openai":     {"label": "OpenAI", "fields": ["api_key"], "caps": ["image", "image_edit", "video"],
                   "defaults": {"image_model": "gpt-image-1", "video_model": "sora-2"},
                   "help": "platform.openai.com/api-keys"},
    "stability":  {"label": "Stability AI", "fields": ["api_key"], "caps": ["image"],
                   "defaults": {"image_model": "core"}, "help": "platform.stability.ai/account/keys"},
    "replicate":  {"label": "Replicate", "fields": ["api_key"], "caps": ["image", "video"],
                   "defaults": {"image_model": "black-forest-labs/flux-schnell", "video_model": "minimax/video-01"},
                   "help": "replicate.com/account/api-tokens"},
    "fal":        {"label": "fal.ai", "fields": ["api_key"], "caps": ["image", "video"],
                   "defaults": {"image_model": "fal-ai/flux/schnell", "video_model": "fal-ai/minimax/video-01"},
                   "help": "fal.ai/dashboard/keys"},
    "gemini":     {"label": "Google AI (Gemini / Imagen / Veo)", "fields": ["api_key"], "caps": ["image", "video"],
                   "defaults": {"image_model": "gemini-2.5-flash-image", "video_model": "veo-3.0-generate-001"},
                   "help": "aistudio.google.com/apikey"},
    "runway":     {"label": "Runway", "fields": ["api_key"], "caps": ["video", "video_edit"],
                   "defaults": {"video_model": "gen4_turbo", "edit_model": "gen4_aleph"},
                   "help": "dev.runwayml.com"},
    "luma":       {"label": "Luma Dream Machine", "fields": ["api_key"], "caps": ["video"],
                   "defaults": {"video_model": "ray-2"}, "help": "lumalabs.ai/dream-machine/api/keys"},
    "google_search": {"label": "Google Search (Custom Search JSON API)", "fields": ["api_key", "cx"], "caps": ["search"],
                      "defaults": {}, "help": "console.cloud.google.com -> enable Custom Search API -> key; programmablesearchengine.google.com -> engine that searches the entire web -> cx (Search engine ID). Without it, research falls back to DuckDuckGo."},
    "serpapi":       {"label": "SerpAPI (Google results)", "fields": ["api_key"], "caps": ["search"],
                      "defaults": {}, "help": "serpapi.com/manage-api-key"},
    "google_oauth":    {"label": "Google account sign-in (Gmail)", "fields": ["client_id", "client_secret"],
                        "caps": ["email"], "defaults": {},
                        "help": "console.cloud.google.com -> OAuth client (Web) with redirect http://localhost:8770/oauth/google"},
    "microsoft_oauth": {"label": "Microsoft account sign-in (Outlook / M365)", "fields": ["client_id"],
                        "caps": ["email"], "defaults": {},
                        "help": "portal.azure.com -> App registration (public client, PKCE) with redirect http://localhost:8770/oauth/microsoft"},
}
SECRET_FIELDS = {"api_key", "client_secret"}

DEFAULT_PREFS = {
    "image_provider": "auto", "video_provider": "auto", "chat_model": "",
    "image_size": "1024x1024", "video_aspect": "16:9", "video_seconds": 5,
    "enhance_prompts": True, "assistant_name": "AIXMOS",
    # knowledge vault + skills
    "kit_path": "", "active_skill": "", "use_knowledge": True,
    # super agent
    "agent_model": "", "agent_autonomy": "builder", "agent_roots": "", "agent_max_steps": 24,
    "agent_allow_send": False, "mcp_autonomy": "builder",
}

def _read():
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except (OSError, ValueError):
        d = {}
    d.setdefault("providers", {})
    d.setdefault("prefs", {})
    return d

def _write(d):
    os.makedirs(MEMDIR, exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, FILE)

def load():
    with _LOCK:
        return _read()

def get(provider, field, default=None):
    d = load()
    v = (d["providers"].get(provider) or {}).get(field)
    if v in (None, ""):
        v = (PROVIDERS.get(provider, {}).get("defaults") or {}).get(field, default)
    return v

def pref(name):
    d = load()
    return d["prefs"].get(name, DEFAULT_PREFS.get(name))

def configured(provider):
    meta = PROVIDERS.get(provider)
    if not meta:
        return False
    if not meta["fields"]:
        return True
    cur = load()["providers"].get(provider) or {}
    need = [f for f in meta["fields"] if f in SECRET_FIELDS or f in ("client_id", "cx")]
    return all(cur.get(f) for f in need)

def providers_for(cap):
    """Configured providers offering a capability, in registry order."""
    return [p for p, m in PROVIDERS.items() if cap in m["caps"] and configured(p)]

def update(providers=None, prefs=None):
    """Merge updates. Empty string keeps the old value; the literal '__clear__' deletes it."""
    with _LOCK:
        d = _read()
        for p, fields in (providers or {}).items():
            if p not in PROVIDERS or not isinstance(fields, dict):
                continue
            cur = d["providers"].setdefault(p, {})
            for k, v in fields.items():
                if not isinstance(k, str):
                    continue
                if v == "__clear__":
                    cur.pop(k, None)
                elif isinstance(v, str) and v.strip() == "":
                    continue
                else:
                    cur[k] = v.strip() if isinstance(v, str) else v
        for k, v in (prefs or {}).items():
            if k in DEFAULT_PREFS:
                d["prefs"][k] = v
        _write(d)
        return d

def _mask(v):
    v = str(v or "")
    if not v:
        return ""
    return ("•" * 4) + v[-4:] if len(v) > 4 else "•" * 4

def public_view():
    d = load()
    out = {"providers": {}, "prefs": {**DEFAULT_PREFS, **d["prefs"]}}
    for p, meta in PROVIDERS.items():
        cur = d["providers"].get(p) or {}
        fields = {}
        for f in meta["fields"]:
            fields[f] = _mask(cur.get(f)) if f in SECRET_FIELDS else (cur.get(f) or "")
        models = {k: (cur.get(k) or v) for k, v in meta["defaults"].items()}
        out["providers"][p] = {"label": meta["label"], "caps": meta["caps"], "help": meta["help"],
                               "fields": fields, "models": models, "configured": configured(p)}
    return out
