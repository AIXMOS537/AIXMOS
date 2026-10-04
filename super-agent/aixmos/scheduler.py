"""
scheduler.py -- runs skill work on time, survives restarts, never runs a job twice at once.

  handler(name)(fn)           register fn(payload, job) for an action name like "followup.step"
  schedule(action, payload=, due=, skill=, dedupe=, max_attempts=3)  -> job dict (dedupe: one live job per key)
  cancel(job_id=None, dedupe=None)
  run_due(now=None)           claim due jobs (lease) and run them; returns [(job_id, status)]
  start(interval=30)          background thread for the server
  jobs(status=None)

A handler can raise Later(at, reason) to move itself (quiet hours, waiting on the owner) without using up
an attempt. Any other exception counts as an attempt; after max_attempts the job is marked failed.
"""
import json, time, uuid, threading
from . import store

HANDLERS = {}
LEASE = 300
_started = threading.Event()

class Later(Exception):
    def __init__(self, at, reason=""):
        super().__init__(reason or "rescheduled")
        self.at, self.reason = float(at), reason

def handler(name):
    def deco(fn):
        HANDLERS[name] = fn
        return fn
    return deco

def _row(r):
    if r and r.get("payload"):
        try:
            r["payload"] = json.loads(r["payload"])
        except ValueError:
            pass
    return r

def get(job_id):
    return _row(store.one("SELECT * FROM jobs WHERE id=?", (job_id,)))

def schedule(action, payload=None, due=None, skill="", dedupe=None, max_attempts=3):
    due = float(due if due is not None else time.time())
    if dedupe:
        old = store.one("SELECT id, status FROM jobs WHERE dedupe=?", (dedupe,))
        if old and old["status"] in ("pending", "running"):
            return get(old["id"])
        if old:                          # finished job with the same key: free the key for the new one
            with store.tx() as c:
                c.execute("UPDATE jobs SET dedupe=NULL WHERE id=?", (old["id"],))
    jid = uuid.uuid4().hex[:12]
    with store.tx() as c:
        c.execute("INSERT INTO jobs(id, created, skill, action, payload, due, status, max_attempts, dedupe) "
                  "VALUES (?,?,?,?,?,?, 'pending', ?, ?)",
                  (jid, time.time(), skill or action.split(".")[0], action,
                   json.dumps(payload or {}, ensure_ascii=False, default=str), due, int(max_attempts), dedupe))
    return get(jid)

def cancel(job_id=None, dedupe=None):
    with store.tx() as c:
        if job_id:
            n = c.execute("UPDATE jobs SET status='cancelled', finished=? WHERE id=? AND status='pending'", (time.time(), job_id)).rowcount
        else:
            n = c.execute("UPDATE jobs SET status='cancelled', finished=? WHERE dedupe=? AND status='pending'", (time.time(), dedupe)).rowcount
    return n

def _claim(now, limit):
    with store.tx() as c:
        rows = c.execute("SELECT id FROM jobs WHERE (status='pending' AND due<=?) OR (status='running' AND lease_until<?) "
                         "ORDER BY due LIMIT ?", (now, now, int(limit))).fetchall()
        ids = [r["id"] for r in rows]
        for jid in ids:
            c.execute("UPDATE jobs SET status='running', lease_until=?, attempts=attempts+1 WHERE id=?", (now + LEASE, jid))
    return [get(j) for j in ids]

def run_due(now=None, limit=20):
    now = float(now if now is not None else time.time())
    out = []
    for job in _claim(now, limit):
        fn = HANDLERS.get(job["action"])
        try:
            if not fn:
                raise RuntimeError("no handler for %s" % job["action"])
            res = fn(job["payload"], job)
            with store.tx() as c:
                c.execute("UPDATE jobs SET status='done', finished=?, result=?, lease_until=NULL WHERE id=?",
                          (time.time(), json.dumps(res, ensure_ascii=False, default=str)[:4000] if res is not None else None, job["id"]))
            out.append((job["id"], "done"))
        except Later as l:
            with store.tx() as c:
                c.execute("UPDATE jobs SET status='pending', due=?, attempts=MAX(attempts-1, 0), last_error=?, lease_until=NULL WHERE id=?",
                          (l.at, ("later: " + l.reason)[:500], job["id"]))
            out.append((job["id"], "later"))
        except Exception as e:
            err = (str(e) or type(e).__name__)[:1000]
            if job["attempts"] >= job["max_attempts"]:
                with store.tx() as c:
                    c.execute("UPDATE jobs SET status='failed', finished=?, last_error=?, lease_until=NULL WHERE id=?", (time.time(), err, job["id"]))
                store.audit("job.failed", job["id"], {"action": job["action"], "error": err[:300]})
                out.append((job["id"], "failed"))
            else:
                backoff = 60 * (5 ** (job["attempts"] - 1))          # 1 min, 5 min, 25 min ...
                with store.tx() as c:
                    c.execute("UPDATE jobs SET status='pending', due=?, last_error=?, lease_until=NULL WHERE id=?", (now + backoff, err, job["id"]))
                out.append((job["id"], "retry"))
    return out

def jobs(status=None, limit=100):
    if status:
        rows = store.q("SELECT * FROM jobs WHERE status=? ORDER BY due LIMIT ?", (status, int(limit)))
    else:
        rows = store.q("SELECT * FROM jobs ORDER BY due DESC LIMIT ?", (int(limit),))
    return [_row(r) for r in rows]

def counts():
    return {r["status"]: r["n"] for r in store.q("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status")}

def start(interval=30):
    """One background loop per process. Errors are logged, never fatal."""
    if _started.is_set():
        return False
    _started.set()
    def loop():
        while True:
            try:
                run_due()
            except Exception as e:
                try:
                    store.audit("scheduler.error", None, str(e)[:300])
                except Exception:
                    pass
            time.sleep(interval)
    threading.Thread(target=loop, name="aixmos-scheduler", daemon=True).start()
    return True
