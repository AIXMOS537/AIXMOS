"""
settings.py -- local settings store (memory/settings.json).

Holds model choices, preferences and non-secret provider fields. Secret values (API keys, OAuth client
secrets) are NOT kept here: settings.json stores the marker "__secret__" and the value lives in secret_store
(DPAPI on Windows, Keychain on macOS). Keys an older version wrote in plain text are moved on first load.
The browser only ever sees a masked "....last4" indicator.
"""
import os, json, threading

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# AIXMOS_MEMDIR points a scratch install or the test suite at its own data folder.
MEMDIR   = os.environ.get("AIXMOS_MEMDIR") or os.path.join(ROOT, "memory")
FILE     = os.path.join(MEMDIR, "settings.json")
_LOCK    = threading.Lock()
RUNTIME  = {"port": 8770}

# Provider registry: what each provider needs and what it can do.
PROVIDERS = {
    "pollinations": {"label": "Pollinations (free, no key)", "fields": [], "caps": ["image"],
                     "defaults": {"image_model": "flux"}, "help": "No account needed. Rate limited, public service."},
    "anthropic":  {"label": "Claude (Anthropic API)", "fields": ["api_key"], "caps": ["chat"],
                   "defaults": {"chat_model": "claude-sonnet-5-5"},
                   "help": "console.anthropic.com -> API keys. Used only when cloud models are allowed in Privacy."},
    "openai":     {"label": "OpenAI", "fields": ["api_key"], "caps": ["image", "image_edit", "video", "chat"],
                   "defaults": {"image_model": "gpt-image-1", "video_model": "sora-2", "chat_model": "gpt-4.1-mini"},
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
    "ghl":        {"label": "GoHighLevel (CRM)", "fields": ["api_key", "location_id"], "caps": ["crm"], "defaults": {},
                   "help": "In your sub-account: Settings -> Private Integrations -> create one with read on contacts, "
                           "conversations, opportunities, calendars; write on contacts (notes, tasks, tags). Paste the token "
                           "here and the Location ID (Settings -> Business Profile). AIXMOS never sends messages through it."},
    "google_oauth":    {"label": "Google account sign-in (Gmail)", "fields": ["client_id", "client_secret"],
                        "caps": ["email"], "defaults": {},
                        "help": "console.cloud.google.com -> OAuth client (Web) with redirect http://localhost:8770/oauth/google"},
    "microsoft_oauth": {"label": "Microsoft account sign-in (Outlook / M365)", "fields": ["client_id"],
                        "caps": ["email"], "defaults": {},
                        "help": "portal.azure.com -> App registration (public client, PKCE) with redirect http://localhost:8770/oauth/microsoft"},
}
SECRET_FIELDS = {"api_key", "client_secret"}
SECRET_MARK = "__secret__"
_migrated = False

def _secret_name(provider, field):
    return "provider.%s.%s" % (provider, field)

DEFAULT_PREFS = {
    "image_provider": "auto", "video_provider": "auto", "chat_model": "",
    "image_size": "1024x1024", "video_aspect": "16:9", "video_seconds": 5,
    "enhance_prompts": True, "assistant_name": "AIXMOS",
    # knowledge vault + skills
    "kit_path": "", "active_skill": "", "use_knowledge": True,
    # super agent
    "agent_model": "", "agent_autonomy": "builder", "agent_roots": "", "agent_max_steps": 24,
    # MCP and /v1 callers cannot answer the agent's questions, so they default to read-only tools.
    "agent_allow_send": False, "mcp_autonomy": "safe",
    # Pollinations is a free *public* service: prompts leave the machine. On by default so images work with no key
    # (owner decision 2026-09-12); switch off in Integrations for private-only.
    "image_free_public": True,
    # model layer (providers.py): local first; cloud models only when allowed here AND connected
    "ollama_url": "http://127.0.0.1:11434", "lmstudio_url": "http://127.0.0.1:1234/v1",
    "privacy_mode": "LOCAL-PREFERRED",   # PRIVATE-LOCAL | LOCAL-PREFERRED | CLOUD-OK
    "cloud_allowed": False, "prefer_cloud": False,
    # registry.py: per-tool approval mode overrides, e.g. {"run_command": "ALWAYS", "web_fetch": "BLOCKED"}
    "tool_policy": {},
    # performance build (tuned for a 2-core laptop driving a USB display; see README "Performance")
    "llm_threads": 3,          # leave one logical core for the UI / DisplayLink compositor
    "llm_ctx": 4096,           # ONE context size for every call so the model never reloads between features
    "chat_history": 12,        # messages replayed per turn (each capped); prompt processing is ~20 tok/s here
    "ui_performance": "auto",  # auto | on | off: drop blur, scanlines and idle animations on weak/USB displays
    # head-agent rails (guard.py): texts never go out in quiet hours; daily caps; automatic paid calls stop at the budget
    "quiet_start": 21, "quiet_end": 8, "send_cap_email": 200, "send_cap_sms": 100, "send_cap_per_contact": 3,
    "spend_daily_usd": 2.0,
    # approvals.py: per-skill autopilot, e.g. {"followup": ["email.send"]}. Empty = every send waits for the owner.
    "autopilot": {},
    # skills/leads: watch for leads waiting for a reply every 30 min (drafts only; nothing sends without approval)
    "leads_watch": True, "leads_lookback_days": 3, "leads_followup_days": 2, "leads_max_per_run": 10,
    # skillkit.persona(): characters of a built-in skill's guide given to the model (most relevant sections first)
    "skill_prompt_chars": 4000,
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

def _migrate_plaintext(d):
    """Move secret values an older version wrote into settings.json into the secret store."""
    from . import secret_store
    moved = False
    for p, fields in d["providers"].items():
        for f in list(fields or {}):
            v = fields[f]
            if f in SECRET_FIELDS and v not in (None, "", SECRET_MARK):
                secret_store.put(_secret_name(p, f), v)
                fields[f] = SECRET_MARK
                moved = True
    return moved

def load():
    global _migrated
    with _LOCK:
        d = _read()
        if not _migrated:
            _migrated = True
            try:
                if _migrate_plaintext(d):
                    _write(d)
            except Exception as e:
                print("  Secrets ->  migration skipped (%s)" % type(e).__name__)
        return d

def get(provider, field, default=None):
    d = load()
    v = (d["providers"].get(provider) or {}).get(field)
    if v == SECRET_MARK:
        from . import secret_store
        v = secret_store.get(_secret_name(provider, field))
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

def public_image_ok():
    """True only when the user opted into the free public image service."""
    return bool(pref("image_free_public")) or pref("image_provider") == "pollinations"

def providers_for(cap):
    """Configured providers offering a capability, in registry order."""
    return [p for p, m in PROVIDERS.items() if cap in m["caps"] and configured(p)
            and (p != "pollinations" or public_image_ok())]

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
                    if k in SECRET_FIELDS:
                        from . import secret_store
                        secret_store.delete(_secret_name(p, k))
                elif isinstance(v, str) and v.strip() == "":
                    continue
                elif k in SECRET_FIELDS:
                    from . import secret_store
                    secret_store.put(_secret_name(p, k), v.strip() if isinstance(v, str) else v)
                    cur[k] = SECRET_MARK
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
            fields[f] = _mask(get(p, f)) if f in SECRET_FIELDS and cur.get(f) else ("" if f in SECRET_FIELDS else (cur.get(f) or ""))
        models = {k: (cur.get(k) or v) for k, v in meta["defaults"].items()}
        out["providers"][p] = {"label": meta["label"], "caps": meta["caps"], "help": meta["help"],
                               "fields": fields, "models": models, "configured": configured(p)}
    return out
