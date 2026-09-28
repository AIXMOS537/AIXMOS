"""jobs.py -- tiny background job runner with polling status (video generation / editing take minutes)."""
import threading, time, traceback, uuid

JOBS = {}
_LOCK = threading.Lock()
MAX_KEEP = 60

def create(kind, fn, meta=None, on_done=None):
    jid = uuid.uuid4().hex[:10]
    job = {"id": jid, "kind": kind, "status": "queued", "progress": "queued", "created": time.time(),
           "updated": time.time(), "result": None, "error": None, "meta": meta or {}}
    with _LOCK:
        JOBS[jid] = job
        if len(JOBS) > MAX_KEEP:
            for old in sorted(JOBS.values(), key=lambda j: j["created"])[:len(JOBS) - MAX_KEEP]:
                if old["status"] in ("done", "error"):
                    JOBS.pop(old["id"], None)
    def run():
        job["status"], job["progress"], job["updated"] = "running", "starting", time.time()
        try:
            job["result"] = fn(lambda msg: progress(jid, msg))
            job["status"], job["progress"] = "done", "complete"
        except Exception as e:
            job["status"], job["error"] = "error", str(e) or e.__class__.__name__
            job["progress"] = "failed"
            traceback.print_exc()
        job["updated"] = time.time()
        if on_done:
            try:
                on_done(job)
            except Exception:
                traceback.print_exc()
    threading.Thread(target=run, daemon=True).start()
    return job

def progress(jid, msg):
    j = JOBS.get(jid)
    if j:
        j["progress"], j["updated"] = str(msg)[:200], time.time()

def get(jid):
    return JOBS.get(jid)

def list_jobs(limit=30):
    return sorted(JOBS.values(), key=lambda j: j["created"], reverse=True)[:limit]
