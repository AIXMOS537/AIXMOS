"""
channels.py -- the only door automated messages go out through.

Every send re-checks the guard at the moment of sending (an opt-out that arrived after the owner approved still
wins), goes out through the owner's own connected account, and is recorded in the send ledger.

  send_email(payload)   payload: {to, subject, body, account?, skill?, ref?}  -> {"sent_to", "subject", "account"}
                        registered as the approval executor "email.send"
"""
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

def send_email(payload):
    from . import email_tools
    to = str(payload.get("to") or "").strip()
    d = guard.check_send("email", to)
    if not d:
        store.audit("send.blocked", guard.normalize(to), {"channel": "email", "reason": d.reason, "ref": payload.get("ref")})
        raise PermissionError("not sent: %s" % d.reason)
    aid = _account(payload.get("account"))
    email_tools.send(aid, to, payload.get("subject") or "", payload.get("body") or "")
    guard.record_send("email", to, payload.get("skill") or "", payload.get("ref"))
    store.audit("send.email", guard.normalize(to), {"skill": payload.get("skill"), "ref": payload.get("ref"),
                                                    "subject": (payload.get("subject") or "")[:120]})
    return {"sent_to": to, "subject": payload.get("subject"), "account": aid}

approvals.register("email.send", send_email)
