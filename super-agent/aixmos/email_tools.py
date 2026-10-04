"""
email_tools.py -- write, refine and send email for any connected account.

Account types
  smtp       any provider via SMTP/IMAP (Gmail/Outlook/Yahoo/iCloud app passwords, Zoho, custom)
  google     Gmail via OAuth (needs a Google OAuth client id/secret in Integrations)
  microsoft  Outlook / Microsoft 365 via OAuth + PKCE (needs an Azure app client id only)

Secrets are stored in memory/email_accounts.json, wrapped with Windows DPAPI
(user-scoped) when available. Sending always requires an explicit /api/email/send call.
"""
import os, re, json, time, base64, hashlib, secrets, smtplib, imaplib, ssl, threading, ctypes, urllib.parse
from email.message import EmailMessage
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, formataddr
from . import settings, media, llm

ACC_FILE = os.path.join(settings.MEMDIR, "email_accounts.json")
SENT_FILE = os.path.join(settings.MEMDIR, "email_sent.json")
_LOCK = threading.Lock()
_PENDING = {}   # oauth state -> {provider, verifier, ts}

PRESETS = {
    "gmail":   {"label": "Gmail (app password)", "smtp_host": "smtp.gmail.com", "smtp_port": 587, "imap_host": "imap.gmail.com",
                "note": "Turn on 2-Step Verification, then create an App Password at myaccount.google.com/apppasswords."},
    "outlook": {"label": "Outlook / Hotmail (app password)", "smtp_host": "smtp-mail.outlook.com", "smtp_port": 587, "imap_host": "outlook.office365.com",
                "note": "Personal accounts: create an app password at account.live.com/proofs/AppPassword. Work accounts usually need the Microsoft sign-in instead."},
    "yahoo":   {"label": "Yahoo Mail", "smtp_host": "smtp.mail.yahoo.com", "smtp_port": 465, "imap_host": "imap.mail.yahoo.com",
                "note": "Generate an app password under Yahoo Account Security."},
    "icloud":  {"label": "iCloud Mail", "smtp_host": "smtp.mail.me.com", "smtp_port": 587, "imap_host": "imap.mail.me.com",
                "note": "Create an app-specific password at appleid.apple.com."},
    "zoho":    {"label": "Zoho Mail", "smtp_host": "smtp.zoho.com", "smtp_port": 465, "imap_host": "imap.zoho.com", "note": ""},
    "custom":  {"label": "Custom SMTP / IMAP", "smtp_host": "", "smtp_port": 587, "imap_host": "", "note": ""},
}

# ------------------------------------------------------------- DPAPI ----
def _dpapi(data, protect=True):
    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]
    crypt = ctypes.windll.crypt32
    buf = ctypes.create_string_buffer(data, len(data))
    inb = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    outb = BLOB()
    fn = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    if not fn(ctypes.byref(inb), None, None, None, None, 0, ctypes.byref(outb)):
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(outb.pbData, outb.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(outb.pbData)

def _protect(s):
    if not s:
        return ""
    try:
        return "dpapi:" + base64.b64encode(_dpapi(s.encode("utf-8"), True)).decode()
    except Exception:
        return "plain:" + s

def _unprotect(s):
    if not s:
        return ""
    if s.startswith("dpapi:"):
        try:
            return _dpapi(base64.b64decode(s[6:]), False).decode("utf-8")
        except Exception:
            return ""
    return s[6:] if s.startswith("plain:") else s

# ------------------------------------------------------------- store ----
def _load():
    try:
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []

def _save(accs):
    os.makedirs(settings.MEMDIR, exist_ok=True)
    tmp = ACC_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(accs, f, indent=1)
    os.replace(tmp, ACC_FILE)

def list_accounts():
    with _LOCK:
        accs = _load()
    return [{"id": a["id"], "type": a["type"], "label": a.get("label") or a["email"], "email": a["email"],
             "name": a.get("name") or "", "imap": bool(a.get("imap_host")) or a["type"] != "smtp",
             "added": a.get("added")} for a in accs]

def _get(aid):
    with _LOCK:
        for a in _load():
            if a["id"] == aid:
                return a
    return None

def remove_account(aid):
    with _LOCK:
        accs = [a for a in _load() if a["id"] != aid]
        _save(accs)
    return True

def _redirect(provider):
    return "http://localhost:%d/oauth/%s" % (settings.RUNTIME.get("port", 8770), provider)

# ------------------------------------------------------------- SMTP ----
def _smtp_connect(a):
    host, port = a["smtp_host"], int(a.get("smtp_port") or 587)
    ctx = ssl.create_default_context()
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, timeout=30, context=ctx)
    else:
        s = smtplib.SMTP(host, port, timeout=30); s.ehlo(); s.starttls(context=ctx); s.ehlo()
    s.login(a.get("username") or a["email"], _unprotect(a["password"]))
    return s

def add_smtp(fields):
    preset = PRESETS.get(str(fields.get("preset") or "custom"), PRESETS["custom"])
    email_addr = (fields.get("email") or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_addr):
        raise ValueError("a valid email address is required")
    pw = fields.get("password") or ""
    if not pw:
        raise ValueError("password / app password is required")
    a = {"id": secrets.token_hex(4), "type": "smtp", "email": email_addr, "name": (fields.get("name") or "").strip(),
         "label": (fields.get("label") or "").strip() or email_addr, "username": (fields.get("username") or "").strip() or email_addr,
         "smtp_host": (fields.get("smtp_host") or preset["smtp_host"]).strip(), "smtp_port": int(fields.get("smtp_port") or preset["smtp_port"]),
         "imap_host": (fields.get("imap_host") or preset["imap_host"]).strip(), "password": _protect(pw), "added": time.time()}
    if not a["smtp_host"]:
        raise ValueError("SMTP host is required")
    s = _smtp_connect(a)      # verify credentials before saving
    s.quit()
    with _LOCK:
        accs = [x for x in _load() if x["email"] != email_addr or x["type"] != "smtp"]
        accs.append(a); _save(accs)
    return {"id": a["id"], "email": a["email"]}

def _smtp_send(a, msg):
    s = _smtp_connect(a)
    try:
        s.send_message(msg)
    finally:
        s.quit()

def _imap_inbox(a, n=12):
    if not a.get("imap_host"):
        return []
    M = imaplib.IMAP4_SSL(a["imap_host"], 993, timeout=30)
    try:
        M.login(a.get("username") or a["email"], _unprotect(a["password"]))
        M.select("INBOX", readonly=True)
        typ, data = M.search(None, "ALL")
        ids = data[0].split()[-n:]
        out = []
        for i in reversed(ids):
            typ, msgdata = M.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)] BODY.PEEK[TEXT]<0.500>)")
            hdr, body = b"", b""
            for part in msgdata:
                if isinstance(part, tuple):
                    if b"HEADER" in part[0]: hdr = part[1]
                    elif b"TEXT" in part[0]: body = part[1]
            m = message_from_bytes(hdr)
            snippet = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace")))[:200]
            out.append({"id": i.decode(), "from": _hdr(m.get("From")), "subject": _hdr(m.get("Subject")),
                        "date": _date(m.get("Date")), "snippet": snippet})
        return out
    finally:
        try: M.logout()
        except Exception: pass

def _imap_read(a, mid):
    M = imaplib.IMAP4_SSL(a["imap_host"], 993, timeout=30)
    try:
        M.login(a.get("username") or a["email"], _unprotect(a["password"]))
        M.select("INBOX", readonly=True)
        typ, data = M.fetch(mid.encode(), "(RFC822)")
        raw = next((p[1] for p in data if isinstance(p, tuple)), b"")
        m = message_from_bytes(raw)
        return {"id": mid, "from": _hdr(m.get("From")), "to": _hdr(m.get("To")), "subject": _hdr(m.get("Subject")),
                "date": _date(m.get("Date")), "body": _plain(m)[:6000], "message_id": m.get("Message-ID", "")}
    finally:
        try: M.logout()
        except Exception: pass

def _hdr(v):
    try:
        return str(make_header(decode_header(v or "")))
    except Exception:
        return str(v or "")

def _date(v):
    try:
        return parsedate_to_datetime(v).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(v or "")[:25]

def _plain(m):
    if m.is_multipart():
        for part in m.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        for part in m.walk():
            if part.get_content_type() == "text/html":
                return _strip_html(part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace"))
        return ""
    payload = m.get_payload(decode=True) or b""
    txt = payload.decode(m.get_content_charset() or "utf-8", "replace")
    return _strip_html(txt) if m.get_content_type() == "text/html" else txt

def _strip_html(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", h)
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", h)).strip()

# ------------------------------------------------------------ OAuth ----
def oauth_start(provider):
    state = secrets.token_urlsafe(16)
    if provider == "google":
        cid = settings.get("google_oauth", "client_id")
        if not cid:
            raise ValueError("add a Google OAuth client id/secret in Integrations first")
        _PENDING[state] = {"provider": "google", "ts": time.time()}
        q = {"client_id": cid, "redirect_uri": _redirect("google"), "response_type": "code",
             "scope": "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email",
             "access_type": "offline", "prompt": "consent", "state": state}
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(q)
    if provider == "microsoft":
        cid = settings.get("microsoft_oauth", "client_id")
        if not cid:
            raise ValueError("add a Microsoft (Azure app) client id in Integrations first")
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        _PENDING[state] = {"provider": "microsoft", "verifier": verifier, "ts": time.time()}
        q = {"client_id": cid, "response_type": "code", "redirect_uri": _redirect("microsoft"),
             "scope": "offline_access Mail.Send Mail.Read User.Read", "code_challenge": challenge,
             "code_challenge_method": "S256", "state": state, "response_mode": "query"}
        return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urllib.parse.urlencode(q)
    raise ValueError("unknown provider")

def oauth_finish(provider, code, state):
    import requests
    p = _PENDING.pop(state, None)
    if not p or p["provider"] != provider:
        raise ValueError("sign-in session expired, start again")
    if provider == "google":
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": settings.get("google_oauth", "client_id"),
            "client_secret": settings.get("google_oauth", "client_secret") or "",
            "redirect_uri": _redirect("google"), "grant_type": "authorization_code"}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError("Google token error: " + r.text[:300])
        tok = r.json()
        prof = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/profile",
                            headers={"Authorization": "Bearer " + tok["access_token"]}, timeout=30).json()
        email_addr = prof.get("emailAddress", "")
        name = ""
    else:
        r = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data={
            "client_id": settings.get("microsoft_oauth", "client_id"), "grant_type": "authorization_code",
            "code": code, "redirect_uri": _redirect("microsoft"), "code_verifier": p["verifier"],
            "scope": "offline_access Mail.Send Mail.Read User.Read"}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError("Microsoft token error: " + r.text[:300])
        tok = r.json()
        me = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": "Bearer " + tok["access_token"]}, timeout=30).json()
        email_addr = me.get("mail") or me.get("userPrincipalName") or ""
        name = me.get("displayName") or ""
    if not email_addr:
        raise RuntimeError("could not read the account's email address")
    a = {"id": secrets.token_hex(4), "type": provider, "email": email_addr, "name": name, "label": email_addr,
         "access": _protect(tok.get("access_token", "")), "refresh": _protect(tok.get("refresh_token", "")),
         "expires": time.time() + int(tok.get("expires_in", 3600)) - 60, "added": time.time()}
    with _LOCK:
        accs = [x for x in _load() if not (x["email"] == email_addr and x["type"] == provider)]
        accs.append(a); _save(accs)
    return {"id": a["id"], "email": email_addr}

def _token(a):
    import requests
    if time.time() < float(a.get("expires") or 0):
        return _unprotect(a["access"])
    refresh = _unprotect(a.get("refresh", ""))
    if not refresh:
        raise RuntimeError("session expired, reconnect the account")
    if a["type"] == "google":
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "refresh_token": refresh, "client_id": settings.get("google_oauth", "client_id"),
            "client_secret": settings.get("google_oauth", "client_secret") or "", "grant_type": "refresh_token"}, timeout=60)
    else:
        r = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data={
            "client_id": settings.get("microsoft_oauth", "client_id"), "grant_type": "refresh_token",
            "refresh_token": refresh, "scope": "offline_access Mail.Send Mail.Read User.Read"}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError("token refresh failed: " + r.text[:200])
    tok = r.json()
    with _LOCK:
        accs = _load()
        for x in accs:
            if x["id"] == a["id"]:
                x["access"] = _protect(tok["access_token"]); x["expires"] = time.time() + int(tok.get("expires_in", 3600)) - 60
                if tok.get("refresh_token"): x["refresh"] = _protect(tok["refresh_token"])
                a.update(x)
        _save(accs)
    return tok["access_token"]

def _gmail_inbox(a, n=12):
    import requests
    hdr = {"Authorization": "Bearer " + _token(a)}
    r = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers=hdr,
                     params={"maxResults": n, "labelIds": "INBOX"}, timeout=30).json()
    out = []
    for m in r.get("messages", []):
        d = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/messages/" + m["id"], headers=hdr,
                         params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]}, timeout=30).json()
        h = {x["name"].lower(): x["value"] for x in (d.get("payload") or {}).get("headers", [])}
        out.append({"id": m["id"], "from": h.get("from", ""), "subject": h.get("subject", ""), "date": _date(h.get("date")),
                    "snippet": d.get("snippet", ""), "thread": d.get("threadId")})
    return out

def _gmail_read(a, mid):
    import requests
    hdr = {"Authorization": "Bearer " + _token(a)}
    d = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/messages/" + mid, headers=hdr, params={"format": "raw"}, timeout=30).json()
    raw = base64.urlsafe_b64decode(d.get("raw", "") + "==")
    m = message_from_bytes(raw)
    return {"id": mid, "from": _hdr(m.get("From")), "to": _hdr(m.get("To")), "subject": _hdr(m.get("Subject")),
            "date": _date(m.get("Date")), "body": _plain(m)[:6000], "message_id": m.get("Message-ID", ""), "thread": d.get("threadId")}

def _gmail_send(a, msg, thread=None):
    import requests
    body = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    if thread: body["threadId"] = thread
    r = requests.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                      headers={"Authorization": "Bearer " + _token(a)}, json=body, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError("Gmail send failed: " + r.text[:300])

def _graph_inbox(a, n=12):
    import requests
    r = requests.get("https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages",
                     headers={"Authorization": "Bearer " + _token(a)},
                     params={"$top": n, "$select": "id,from,subject,receivedDateTime,bodyPreview", "$orderby": "receivedDateTime desc"}, timeout=30).json()
    return [{"id": m["id"], "from": ((m.get("from") or {}).get("emailAddress") or {}).get("address", ""),
             "subject": m.get("subject", ""), "date": (m.get("receivedDateTime") or "")[:16].replace("T", " "),
             "snippet": m.get("bodyPreview", "")} for m in r.get("value", [])]

def _graph_read(a, mid):
    import requests
    m = requests.get("https://graph.microsoft.com/v1.0/me/messages/" + mid, headers={"Authorization": "Bearer " + _token(a)},
                     params={"$select": "id,from,toRecipients,subject,receivedDateTime,body,internetMessageId"}, timeout=30).json()
    body = (m.get("body") or {}).get("content", "")
    if (m.get("body") or {}).get("contentType", "").lower() == "html":
        body = _strip_html(body)
    return {"id": mid, "from": ((m.get("from") or {}).get("emailAddress") or {}).get("address", ""),
            "to": ", ".join((t.get("emailAddress") or {}).get("address", "") for t in m.get("toRecipients", [])),
            "subject": m.get("subject", ""), "date": (m.get("receivedDateTime") or "")[:16].replace("T", " "),
            "body": body[:6000], "message_id": m.get("internetMessageId", "")}

def _graph_send(a, to, cc, bcc, subject, body, attachments):
    import requests
    def rcpt(lst): return [{"emailAddress": {"address": x}} for x in lst]
    msg = {"subject": subject, "body": {"contentType": "Text", "content": body}, "toRecipients": rcpt(to)}
    if cc: msg["ccRecipients"] = rcpt(cc)
    if bcc: msg["bccRecipients"] = rcpt(bcc)
    if attachments:
        msg["attachments"] = []
        for p in attachments:
            with open(p, "rb") as f:
                msg["attachments"].append({"@odata.type": "#microsoft.graph.fileAttachment", "name": os.path.basename(p),
                                           "contentType": media.mime_for(p), "contentBytes": base64.b64encode(f.read()).decode()})
    r = requests.post("https://graph.microsoft.com/v1.0/me/sendMail", headers={"Authorization": "Bearer " + _token(a)},
                      json={"message": msg, "saveToSentItems": True}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Outlook send failed: " + r.text[:300])

# ------------------------------------------------------------ inbox ----
def inbox(aid, n=12):
    a = _get(aid)
    if not a: raise ValueError("unknown account")
    return {"smtp": _imap_inbox, "google": _gmail_inbox, "microsoft": _graph_inbox}[a["type"]](a, n)

def read(aid, mid):
    a = _get(aid)
    if not a: raise ValueError("unknown account")
    return {"smtp": _imap_read, "google": _gmail_read, "microsoft": _graph_read}[a["type"]](a, mid)

# ------------------------------------------------------- AI writing ----
def _voice_examples():
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            sent = json.load(f)
    except (OSError, ValueError):
        sent = []
    return sent[-3:]

def _sender(aid):
    a = _get(aid) if aid else None
    if a:
        return (a.get("name") or a["email"].split("@")[0].replace(".", " ").title()), a["email"]
    return settings.pref("assistant_name") or "AIXMOS", ""

def draft(intent, to=None, tone="professional", account_id=None, reply_to=None, length="medium"):
    name, addr = _sender(account_id)
    ex = _voice_examples()
    voice = "\n\n".join("Previously sent by the user (match this voice):\nSubject: %s\n%s" % (s["subject"], s["body"][:600]) for s in ex)
    ctx = ""
    if reply_to:
        ctx = ("\nYou are replying to this message:\nFrom: %s\nSubject: %s\n%s\n" %
               (reply_to.get("from", ""), reply_to.get("subject", ""), (reply_to.get("body") or "")[:2500]))
    sysmsg = ("You write emails on behalf of %s%s. Write a complete, ready-to-send email in plain text (no markdown, "
              "no placeholders like [Name] unless truly unknown). Tone: %s. Length: %s. Include a natural greeting and a "
              "sign-off with the sender's name. Return JSON: {\"subject\": \"...\", \"body\": \"...\"}%s"
              % (name, (" <%s>" % addr) if addr else "", tone, length, ("\n\n" + voice) if voice else ""))
    user = "Recipient: %s\nWhat the email should do: %s%s" % (", ".join(to or []) or "(unspecified)", intent, ctx)
    out = llm.json_call(sysmsg, user, temperature=0.5, num_ctx=4096, timeout=240)
    subject = (out or {}).get("subject") if out else None
    body = (out or {}).get("body") if out else None
    if not isinstance(body, str) or len(body.strip()) < 10:
        subject = subject if isinstance(subject, str) and subject.strip() else ("Re: " + reply_to["subject"] if reply_to else "Hello")
        body = "Hi,\n\n%s\n\nBest regards,\n%s" % (intent.strip(), name)
    if reply_to and isinstance(subject, str) and not subject.lower().startswith("re:"):
        subject = "Re: " + reply_to.get("subject", "").strip()
    return {"subject": str(subject).strip()[:200], "body": body.strip(), "tone": tone}

def refine(subject, body, instruction, account_id=None):
    name, addr = _sender(account_id)
    out = llm.json_call(
        "You edit an existing email on behalf of %s. Apply the instruction and keep everything else (facts, recipients, "
        "sign-off). Plain text only. Return JSON: {\"subject\": \"...\", \"body\": \"...\"}" % name,
        "Subject: %s\n\n%s\n\nInstruction: %s" % (subject, body, instruction), temperature=0.4, num_ctx=4096, timeout=240)
    if out and isinstance(out.get("body"), str) and len(out["body"].strip()) > 5:
        return {"subject": str(out.get("subject") or subject).strip()[:200], "body": out["body"].strip()}
    raise RuntimeError("the local model could not apply that change, try rephrasing the instruction")

# ------------------------------------------------------------- send ----
def _addr_list(v):
    if isinstance(v, str):
        v = re.split(r"[,;\s]+", v)
    return [x.strip() for x in (v or []) if x and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x.strip())]

def send(account_id, to, subject, body, cc=None, bcc=None, attachments=None, reply_to=None):
    to, cc, bcc = _addr_list(to), _addr_list(cc), _addr_list(bcc)
    if not to:
        raise ValueError("at least one valid recipient is required")
    from . import guard                  # opt-outs and do-not-contact hold for every send, manual or automatic
    for r in to + cc + bcc:
        why = guard.blocked(r)
        if why:
            raise ValueError("not sent: %s is %s" % (r, why))
    a = _get(account_id)
    if not a:
        raise ValueError("choose a connected account")
    subject = (subject or "").strip() or "(no subject)"
    body = (body or "").strip()
    if not body:
        raise ValueError("email body is empty")
    files = []
    total = 0
    for u in attachments or []:
        p = media.path_for(u)
        if p:
            total += os.path.getsize(p)
            if total > 20 * 1024 * 1024:
                raise ValueError("attachments exceed 20 MB")
            files.append(p)
    if a["type"] == "microsoft":
        _graph_send(a, to, cc, bcc, subject, body, files)
    else:
        msg = EmailMessage()
        msg["From"] = formataddr((a.get("name") or "", a["email"])) if a.get("name") else a["email"]
        msg["To"] = ", ".join(to)
        if cc: msg["Cc"] = ", ".join(cc)
        if bcc: msg["Bcc"] = ", ".join(bcc)
        msg["Subject"] = subject
        if reply_to and reply_to.get("message_id"):
            msg["In-Reply-To"] = reply_to["message_id"]; msg["References"] = reply_to["message_id"]
        msg.set_content(body)
        for p in files:
            mt = media.mime_for(p).split("/")
            with open(p, "rb") as f:
                msg.add_attachment(f.read(), maintype=mt[0], subtype=mt[1], filename=os.path.basename(p))
        if a["type"] == "google":
            _gmail_send(a, msg, (reply_to or {}).get("thread"))
        else:
            _smtp_send(a, msg)
    _record_sent(a, to, subject, body)
    return {"ok": True, "to": to, "subject": subject, "from": a["email"]}

def _record_sent(a, to, subject, body):
    with _LOCK:
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                sent = json.load(f)
        except (OSError, ValueError):
            sent = []
        sent.append({"ts": time.time(), "from": a["email"], "to": to, "subject": subject, "body": body[:1500]})
        sent = sent[-40:]
        os.makedirs(settings.MEMDIR, exist_ok=True)
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(sent, f, ensure_ascii=False, indent=1)

def sent_log(limit=20):
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return list(reversed(json.load(f)[-limit:]))
    except (OSError, ValueError):
        return []
