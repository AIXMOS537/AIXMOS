"""
channels.py -- the only door automated messages go out through.

Every send re-checks the guard at the moment of sending (an opt-out that arrived after the owner approved still
wins), goes out through the owner's own connected account, and is recorded in the send ledger.

  send_email(payload)   payload: {to, subject, body, account?, skill?, ref?}  -> {"sent_to", "subject", "account"}
                        registered as the approval executor "email.send"
"""
import re
from . import guard, approvals, store

def _account(aid=None):
    from . import email_tools
    accs = email_tools.list_accounts()
    if not accs:
        raise RuntimeError("no email account connected (Mail > Connect account)")
    if aid:
        if not any(a.get("id") == aid for a in accs):
            raise RuntimeError("that email account is no longer connected")
        return aid
    return accs[0]["id"]

def recipients(*fields):
    """'a@x.com, b@y.com; c@z.com' (and lists) -> ['a@x.com', 'b@y.com', 'c@z.com']"""
    out = []
    for f in fields:
        for part in (f if isinstance(f, (list, tuple)) else re.split(r"[,;\n]+", str(f or ""))):
            part = str(part).strip()
            if part:
                out.append(part)
    return out

def send_email(payload):
    """payload: {to, subject, body, account?, cc?, bcc?, attachments?, reply_to?, skill?, ref?}. Every recipient
    (to, cc and bcc) is checked; one blocked recipient stops the whole message."""
    from . import email_tools
    to = payload.get("to") or ""
    every = recipients(to, payload.get("cc"), payload.get("bcc"))
    if not every:
        raise ValueError("no recipient")
    for rcpt in every:
        # The owner writing an email by hand is not held to the automation caps; opt-outs still hold for everyone.
        d = guard.Decision(not guard.blocked(rcpt), guard.blocked(rcpt) or "ok") if payload.get("manual") \
            else guard.check_send("email", rcpt)
        if not d:
            store.audit("send.blocked", guard.normalize(rcpt), {"channel": "email", "reason": d.reason, "ref": payload.get("ref")})
            raise PermissionError("not sent: %s (%s)" % (d.reason, rcpt))
    aid = _account(payload.get("account"))
    extra = {k: payload[k] for k in ("cc", "bcc", "attachments", "reply_to") if payload.get(k)}
    res = email_tools.send(aid, to, payload.get("subject") or "", payload.get("body") or "", **extra)
    for rcpt in every:
        guard.record_send("email", rcpt, payload.get("skill") or "", payload.get("ref"))
    store.audit("send.email", guard.normalize(every[0]), {"skill": payload.get("skill"), "ref": payload.get("ref"),
                                                          "recipients": len(every), "subject": (payload.get("subject") or "")[:120]})
    out = {"sent_to": to, "subject": payload.get("subject"), "account": aid}
    if isinstance(res, dict):
        out.update({k: res[k] for k in ("to", "from") if k in res})
    return out

approvals.register("email.send", send_email)
