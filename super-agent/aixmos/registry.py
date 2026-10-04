"""
registry.py -- the typed Tool Registry: what each tool is allowed to do, decided by data, not by if-statements.

Every tool (core agent tools and every built-in skill's tools) has a ToolSpec:
  risk      LOW (read / search / analyse / draft) | MEDIUM (changes local records, creates drafts) |
            HIGH (talks to people, publishes, runs code, deletes, spends or commits)
  access    read | write
  action    the authority class (ACTIONS below, from the private line's authority model)
  mode      AUTO     run it
            SESSION  ask once per run ("allow commands for this run?")
            ALWAYS   needs a yes for every call; tools with an inbox kind are queued in the approvals inbox instead
            BLOCKED  never runs
  timeout, retries (read tools only, transient errors only), paid (charged to the spend budget), tainting (its output
  is untrusted: web pages, CRM records, inbound mail)

Mode = the owner's override in prefs tool_policy {tool: MODE}, else the action class default. Conservative defaults:
sending is always approved by a person, code execution is approved once per run, deleting unique data, spending
outside the budget, signing and deploying are never automated.
"""
from dataclasses import dataclass, field

from . import settings

RISKS = ("LOW", "MEDIUM", "HIGH")
MODES = ("AUTO", "SESSION", "ALWAYS", "BLOCKED")

# authority classes -> decision (provisioner/authority.py in the private line) -> default mode
ACTIONS = {
    "read_machine": "ALLOWED",                  # files inside the allowed roots, the knowledge vault
    "read_web": "ALLOWED",                      # fetch / search (untrusted output)
    "read_business_data": "ALLOWED",            # local CRM, memory (untrusted output when it came from outside)
    "write_product_workspace": "ALLOWED",       # files inside the agent workspace / allowed roots
    "write_local_business_data": "ALLOWED",     # local CRM records, notes, drafts
    "use_media_service": "ALLOWED",             # image / video generation; paid ones are held to the spend budget
    "run_code": "CONDITIONAL",                  # shell / python inside the workspace
    "use_customer_connector_read": "AUTHORIZED_SCOPE",
    "use_customer_connector_write": "APPROVAL",
    "activate_automation": "APPROVAL",
    "send_customer_communication": "APPROVAL",
    "publish_content": "APPROVAL",
    "spend_money": "HUMAN",
    "sign_agreement": "HUMAN",
    "create_external_account": "HUMAN",
    "delete_unique_data": "RESTRICTED",
    "production_deploy": "RELEASE",
    "control": "ALLOWED",                       # ask_user / finish
}
DECISION_MODE = {"ALLOWED": "AUTO", "AUTHORIZED_SCOPE": "AUTO", "CONDITIONAL": "SESSION", "APPROVAL": "ALWAYS",
                 "HUMAN": "BLOCKED", "RESTRICTED": "BLOCKED", "RELEASE": "BLOCKED"}
LEVEL_RISK = {"safe": "LOW", "builder": "MEDIUM", "full": "HIGH"}

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: dict
    required: list
    fn: object
    level: str = "safe"
    risk: str = "LOW"
    access: str = "read"
    action: str = "read_machine"
    connector: str = ""
    timeout: float = 0            # 0 = the tool manages its own time (ask_user waits for a person)
    retries: int = 0
    paid: bool = False
    tainting: bool = False
    inbox: str = ""               # approvals kind: ALWAYS-mode calls are queued there instead of asked inline
    source: str = "core"          # core | skill:<id>
    notes: dict = field(default_factory=dict, compare=False)

    def default_mode(self):
        return DECISION_MODE.get(ACTIONS.get(self.action, "RESTRICTED"), "BLOCKED")

    def mode(self):
        pol = settings.pref("tool_policy") or {}
        m = str(pol.get(self.name) or "").upper() if isinstance(pol, dict) else ""
        return m if m in MODES else self.default_mode()

    def schema(self):
        props = {k: ({"type": "array", "items": {"type": "string"}} if t == "array" else {"type": t})
                 for k, t in self.params.items()}
        return {"type": "function", "function": {"name": self.name, "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": list(self.required)}}}

    def describe(self):
        return {"name": self.name, "risk": self.risk, "access": self.access, "action": self.action,
                "mode": self.mode(), "default_mode": self.default_mode(), "level": self.level, "paid": self.paid,
                "untrusted_output": self.tainting, "inbox": self.inbox, "timeout": self.timeout,
                "retries": self.retries, "source": self.source, "connector": self.connector}

# Metadata for the core tools. Anything not listed (skill tools) is derived from its autonomy level.
CORE = {
    "list_dir":             dict(risk="LOW", access="read", action="read_machine"),
    "read_file":            dict(risk="LOW", access="read", action="read_machine"),
    "search_files":         dict(risk="LOW", access="read", action="read_machine", timeout=120),
    "write_file":           dict(risk="MEDIUM", access="write", action="write_product_workspace"),
    "run_command":          dict(risk="HIGH", access="write", action="run_code"),
    "run_python":           dict(risk="HIGH", access="write", action="run_code"),
    "web_fetch":            dict(risk="LOW", access="read", action="read_web", tainting=True, timeout=90, retries=1),
    "web_search":           dict(risk="LOW", access="read", action="read_web", tainting=True, paid=True, timeout=60, retries=1),
    "research":             dict(risk="LOW", access="read", action="read_web", tainting=True, paid=True, timeout=900),
    "knowledge_search":     dict(risk="LOW", access="read", action="read_machine", timeout=60),
    "remember":             dict(risk="MEDIUM", access="write", action="write_local_business_data"),
    "recall":               dict(risk="LOW", access="read", action="read_business_data"),
    "generate_image":       dict(risk="MEDIUM", access="write", action="use_media_service", paid=True, timeout=600),
    "generate_video":       dict(risk="MEDIUM", access="write", action="use_media_service", paid=True, timeout=120),
    "edit_video":           dict(risk="MEDIUM", access="write", action="use_media_service", paid=True, timeout=120),
    "crm_add_lead":         dict(risk="MEDIUM", access="write", action="write_local_business_data", connector="crm"),
    # lead names, notes and hooks come from forms and the web: data, never orders
    "crm_list_leads":       dict(risk="LOW", access="read", action="read_business_data", connector="crm", tainting=True),
    "crm_book_appointment": dict(risk="MEDIUM", access="write", action="write_local_business_data", connector="crm"),
    "crm_start_sequence":   dict(risk="MEDIUM", access="write", action="write_local_business_data", connector="crm"),
    "draft_email":          dict(risk="MEDIUM", access="write", action="write_local_business_data", connector="email", timeout=300),
    "send_email":           dict(risk="HIGH", access="write", action="send_customer_communication", connector="email",
                                 inbox="email.send"),
    "ask_user":             dict(risk="LOW", access="read", action="control"),
    "finish":               dict(risk="LOW", access="read", action="control"),
}

_CACHE = {}

def spec(t, source="core"):
    """ToolSpec for a tool tuple (name, description, params, required, fn, level). Cached per tuple identity, so a
    replaced tuple (tests, skill reload) gets a fresh spec."""
    key = (id(t), t[0])
    s = _CACHE.get(key)
    if s is not None and s.fn is t[4]:
        return s
    name, desc, params, req, fn, level = t
    meta = dict(CORE.get(name) or {}) if source == "core" else {}
    if not meta:
        risk = LEVEL_RISK.get(level, "HIGH")
        meta = dict(risk=risk, access="read" if level == "safe" else "write",
                    action={"LOW": "read_business_data", "MEDIUM": "write_local_business_data"}.get(risk, "activate_automation"))
    s = ToolSpec(name=name, description=desc, params=params, required=list(req), fn=fn, level=level, source=source, **meta)
    if len(_CACHE) > 500:
        _CACHE.clear()
    _CACHE[key] = s
    return s

def table(tools, source_of=lambda t: "core"):
    return [spec(t, source_of(t)).describe() for t in tools]

def sanitize(args, n=160):
    """Tool arguments for the audit trail: values cut short, anything that looks like a secret masked."""
    out = {}
    for k, v in (args or {}).items():
        if any(w in k.lower() for w in ("key", "token", "secret", "password", "auth")):
            out[k] = "****"
        else:
            s = v if isinstance(v, str) else repr(v)
            out[k] = s if len(s) <= n else s[:n] + "...(%d chars)" % len(s)
    return out
