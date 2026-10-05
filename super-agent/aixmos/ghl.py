"""
ghl.py -- the GoHighLevel connector (official API v2, https://services.leadconnectorhq.com).

Setup: Integrations -> GoHighLevel. The owner pastes a Private Integration Token from their sub-account
(Settings -> Private Integrations) and the Location ID. The token goes to the OS keystore (secret_store) like every
other key; it is never logged, never put in a prompt, never written to the audit trail.

Reads (agent tools, LOW risk, output marked UNTRUSTED: lead text is data, never orders)
  location()  find_contacts(query, limit)  contact(id)  notes(id)  tasks(id)  conversations(contact_id)
  messages(conversation_id)  pipelines()  opportunities(contact_id)  calendars()  tags()
Writes (only through the approvals inbox, kind "ghl.write"; the owner approves each one)
  add_note(contact_id, body)  add_task(contact_id, title, due, description)  add_tags(contact_id, tags)
Not here on purpose: sending messages (SMS / email / WhatsApp), deleting contacts or opportunities, workflows,
payments. Those need their own reviewed step.

Errors are classified so the agent and the owner see what actually happened: auth (401: token wrong or revoked),
scope (403: the token lacks that permission), not_found, bad_request, rate_limited (429, retried with Retry-After),
server (5xx, retried once), offline.
"""
import json, time, urllib.error, urllib.parse, urllib.request

from . import settings

API = "https://services.leadconnectorhq.com"
V_DEFAULT, V_CONVERSATIONS, V_CALENDARS = "2021-07-28", "2021-04-15", "2021-04-15"

class GHLError(RuntimeError):
    def __init__(self, msg, kind="server", status=0):
        super().__init__(msg)
        self.kind, self.status = kind, status

def connected():
    return bool(settings.get("ghl", "api_key")) and bool(settings.get("ghl", "location_id"))

def _http(method, url, headers, body, timeout):
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read() or b"{}")

TRANSPORT = _http          # tests replace this with a recorded fake; nothing else does

class Client:
    def __init__(self, token=None, location_id=None, timeout=30):
        self.token = token or settings.get("ghl", "api_key")
        self.loc = location_id or settings.get("ghl", "location_id")
        if not self.token or not self.loc:
            raise GHLError("GoHighLevel is not connected (Integrations -> GoHighLevel: token + Location ID)", "auth")
        self.timeout = timeout

    def req(self, method, path, query=None, body=None, version=V_DEFAULT):
        url = API + path + (("?" + urllib.parse.urlencode({k: v for k, v in query.items() if v not in (None, "")})) if query else "")
        headers = {"Authorization": "Bearer " + self.token, "Version": version, "Accept": "application/json",
                   "Content-Type": "application/json", "User-Agent": "AIXMOS-connector/1"}
        for attempt in range(3):
            try:
                return TRANSPORT(method, url, headers, body, self.timeout)[1]
            except urllib.error.HTTPError as e:
                code = e.code
                try:
                    msg = (json.loads(e.read() or b"{}") or {}).get("message") or ""
                except ValueError:
                    msg = ""
                msg = (", ".join(msg) if isinstance(msg, list) else str(msg))[:200]
                if code == 429 and attempt < 2:
                    time.sleep(min(float(e.headers.get("Retry-After") or 2) if e.headers else 2, 10)); continue
                if code >= 500 and attempt < 1 and method == "GET":
                    time.sleep(1); continue
                kind = {401: "auth", 403: "scope", 404: "not_found", 400: "bad_request", 422: "bad_request",
                        429: "rate_limited"}.get(code, "server")
                hint = {"auth": "the token is wrong or was revoked: paste a new Private Integration Token",
                        "scope": "the token does not have permission for this: add the scope to the Private Integration"}.get(kind, msg)
                raise GHLError("GoHighLevel %s %s: %s (%s)" % (method, path.split("?")[0], code, hint or msg), kind, code)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt < 1 and method == "GET":
                    time.sleep(1); continue
                raise GHLError("GoHighLevel unreachable: %s" % (getattr(e, "reason", None) or e), "offline")

    # ------------------------------------------------------------------ reads ----
    def location(self):
        d = self.req("GET", "/locations/%s" % self.loc).get("location") or {}
        return {k: d.get(k) for k in ("id", "name", "timezone", "website", "city", "state")}

    def find_contacts(self, query="", limit=20, tag=None):
        body = {"locationId": self.loc, "pageLimit": max(1, min(int(limit or 20), 100))}
        if query:
            body["query"] = str(query)[:100]
        if tag:
            body["filters"] = [{"field": "tags", "operator": "contains", "value": str(tag)}]
        d = self.req("POST", "/contacts/search", body=body)
        return {"total": d.get("total", 0), "contacts": [_contact(c) for c in d.get("contacts") or []]}

    def contact(self, cid):
        return _contact(self.req("GET", "/contacts/%s" % _id(cid)).get("contact") or {})

    def notes(self, cid):
        return [{"id": n.get("id"), "body": (n.get("body") or "")[:2000], "date": n.get("dateAdded")}
                for n in self.req("GET", "/contacts/%s/notes" % _id(cid)).get("notes") or []]

    def tasks(self, cid):
        return [{"id": t.get("id"), "title": t.get("title"), "due": t.get("dueDate"), "done": bool(t.get("completed"))}
                for t in self.req("GET", "/contacts/%s/tasks" % _id(cid)).get("tasks") or []]

    def conversations(self, contact_id=None, limit=20):
        d = self.req("GET", "/conversations/search", {"locationId": self.loc, "contactId": contact_id, "limit": limit},
                     version=V_CONVERSATIONS)
        return [{"id": c.get("id"), "contact_id": c.get("contactId"), "name": c.get("fullName") or c.get("contactName"),
                 "last_message": (c.get("lastMessageBody") or "")[:300], "last_type": c.get("lastMessageType"),
                 "last_direction": c.get("lastMessageDirection"), "unread": c.get("unreadCount"),
                 "last_date": c.get("lastMessageDate")} for c in d.get("conversations") or []]

    def messages(self, conversation_id, limit=30):
        d = self.req("GET", "/conversations/%s/messages" % _id(conversation_id), {"limit": limit}, version=V_CONVERSATIONS)
        box = d.get("messages") or {}
        rows = box.get("messages") if isinstance(box, dict) else box
        return [{"direction": m.get("direction"), "type": m.get("messageType") or m.get("type"),
                 "body": (m.get("body") or "")[:1500], "date": m.get("dateAdded")} for m in rows or []]

    def pipelines(self):
        return [{"id": p.get("id"), "name": p.get("name"), "stages": [s.get("name") for s in p.get("stages") or []]}
                for p in self.req("GET", "/opportunities/pipelines", {"locationId": self.loc}).get("pipelines") or []]

    def opportunities(self, contact_id=None, limit=20):
        d = self.req("GET", "/opportunities/search", {"location_id": self.loc, "contact_id": contact_id, "limit": limit})
        return [{"id": o.get("id"), "name": o.get("name"), "status": o.get("status"), "value": o.get("monetaryValue"),
                 "stage_id": o.get("pipelineStageId"), "pipeline_id": o.get("pipelineId"),
                 "contact_id": (o.get("contact") or {}).get("id") or o.get("contactId")} for o in d.get("opportunities") or []]

    def calendars(self):
        return [{"id": c.get("id"), "name": c.get("name")}
                for c in self.req("GET", "/calendars/", {"locationId": self.loc}, version=V_CALENDARS).get("calendars") or []]

    def tags(self):
        return [t.get("name") for t in self.req("GET", "/locations/%s/tags" % self.loc).get("tags") or []]

    # ----------------------------------------------------------------- writes ----
    # Called only by the approvals executor below (after the owner approved) or by tests against the sandbox.
    def add_note(self, cid, body):
        d = self.req("POST", "/contacts/%s/notes" % _id(cid), body={"body": str(body)[:5000]})
        return {"note_id": (d.get("note") or {}).get("id")}

    def add_task(self, cid, title, due, description=""):
        d = self.req("POST", "/contacts/%s/tasks" % _id(cid),
                     body={"title": str(title)[:200], "body": str(description or "")[:2000], "dueDate": due, "completed": False})
        return {"task_id": (d.get("task") or {}).get("id")}

    def add_tags(self, cid, tags):
        tags = [str(t).strip()[:60] for t in (tags or []) if str(t).strip()][:10]
        if not tags:
            raise GHLError("no tags given", "bad_request")
        d = self.req("POST", "/contacts/%s/tags" % _id(cid), body={"tags": tags})
        return {"tags": d.get("tags") or tags}

def _id(v):
    v = str(v or "").strip()
    if not v or not all(ch.isalnum() or ch in "-_" for ch in v):
        raise GHLError("bad id", "bad_request")
    return v

def _contact(c):
    name = " ".join(x for x in (c.get("firstName") or c.get("firstNameLowerCase"), c.get("lastName")) if x) or c.get("contactName") or ""
    return {"id": c.get("id"), "name": name.strip(), "email": c.get("email"), "phone": c.get("phone"),
            "tags": c.get("tags") or [], "source": c.get("source"), "added": c.get("dateAdded"),
            "dnd": bool(c.get("dnd")), "company": c.get("companyName")}

def status():
    """For the Command Center / Integrations: connected?, location name, or the classified error."""
    if not connected():
        return {"connected": False, "reason": "not set up"}
    try:
        return {"connected": True, "location": Client().location()}
    except GHLError as e:
        return {"connected": False, "reason": str(e), "kind": e.kind}

# -------------------------------------------------------------- approvals ----
WRITE_OPS = ("note", "task", "tags")

def execute_write(payload):
    """Approvals executor "ghl.write": runs one approved CRM change."""
    op, cid = payload.get("op"), payload.get("contact_id")
    c = Client()
    if op == "note":
        return c.add_note(cid, payload.get("body") or "")
    if op == "task":
        return c.add_task(cid, payload.get("title") or "Follow up", payload.get("due"), payload.get("description") or "")
    if op == "tags":
        return c.add_tags(cid, payload.get("tags") or [])
    raise GHLError("unknown CRM change %r" % op, "bad_request")

def _register():
    from . import approvals
    approvals.register("ghl.write", execute_write)

_register()
