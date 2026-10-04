"""
store.py -- one local SQLite database (memory/aixmos.db) for the head agent's durable state.

Holds the approvals inbox, scheduled jobs, the contact policy (opt-outs / do-not-contact), the send and
spend ledgers, per-skill state and an audit trail. WAL mode, one connection per thread, short
BEGIN IMMEDIATE transactions, so the web server, the scheduler thread and the agent can share it.

  tx()                 -> context manager yielding a cursor inside one write transaction
  q(sql, args)         -> list of row dicts (read)
  audit(kind, ref, detail)
  state_get(skill, key, default) / state_set(skill, key, value)   per-skill JSON values
"""
import os, json, time, sqlite3, threading
from contextlib import contextmanager
from . import settings

DB = os.path.join(settings.MEMDIR, "aixmos.db")
_INIT = threading.Lock()
_ready = set()

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY, created REAL NOT NULL, kind TEXT NOT NULL, skill TEXT, title TEXT NOT NULL,
  summary TEXT, payload TEXT NOT NULL, risk TEXT NOT NULL DEFAULT 'send',
  status TEXT NOT NULL DEFAULT 'pending', decided REAL, decided_by TEXT, note TEXT,
  result TEXT, error TEXT, dedupe TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS approvals_status ON approvals(status, created);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, created REAL NOT NULL, skill TEXT, action TEXT NOT NULL, payload TEXT NOT NULL,
  due REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3, lease_until REAL, last_error TEXT, result TEXT,
  finished REAL, dedupe TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS jobs_due ON jobs(status, due);
CREATE TABLE IF NOT EXISTS contact_policy (
  contact TEXT PRIMARY KEY, kind TEXT NOT NULL, reason TEXT, source TEXT, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sends (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, channel TEXT NOT NULL, contact TEXT NOT NULL,
  skill TEXT, ref TEXT);
CREATE INDEX IF NOT EXISTS sends_ts ON sends(ts);
CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, provider TEXT NOT NULL, op TEXT NOT NULL,
  usd REAL NOT NULL, interactive INTEGER NOT NULL DEFAULT 0, ref TEXT);
CREATE INDEX IF NOT EXISTS spend_ts ON spend(ts);
CREATE TABLE IF NOT EXISTS skill_state (
  skill TEXT NOT NULL, key TEXT NOT NULL, value TEXT, updated REAL, PRIMARY KEY (skill, key));
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, kind TEXT NOT NULL, ref TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);
"""

def _open():
    """A short-lived connection per operation: the web server runs each request on its own thread, so
    per-thread connections would pile up. SQLite opens are cheap; WAL lets readers and one writer overlap."""
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=15, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=15000")
    if DB not in _ready:
        with _INIT:
            if DB not in _ready:
                c.execute("PRAGMA journal_mode=WAL")
                c.executescript(SCHEMA)
                c.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '1')")
                _ready.add(DB)
    return c

@contextmanager
def tx():
    c = _open()
    try:
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise
    finally:
        c.close()

def q(sql, args=()):
    c = _open()
    try:
        return [dict(r) for r in c.execute(sql, args).fetchall()]
    finally:
        c.close()

def one(sql, args=()):
    c = _open()
    try:
        r = c.execute(sql, args).fetchone()
        return dict(r) if r else None
    finally:
        c.close()

def audit(kind, ref=None, detail=None):
    d = detail if isinstance(detail, str) or detail is None else json.dumps(detail, ensure_ascii=False, default=str)
    with tx() as c:
        c.execute("INSERT INTO events(ts, kind, ref, detail) VALUES (?,?,?,?)", (time.time(), kind, ref, (d or "")[:2000]))

def events(limit=100, kind=None):
    if kind:
        return q("SELECT * FROM events WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, int(limit)))
    return q("SELECT * FROM events ORDER BY id DESC LIMIT ?", (int(limit),))

def state_get(skill, key, default=None):
    r = one("SELECT value FROM skill_state WHERE skill=? AND key=?", (skill, key))
    if not r or r["value"] is None:
        return default
    try:
        return json.loads(r["value"])
    except ValueError:
        return default

def state_set(skill, key, value):
    with tx() as c:
        c.execute("INSERT INTO skill_state(skill, key, value, updated) VALUES (?,?,?,?) "
                  "ON CONFLICT(skill, key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
                  (skill, key, json.dumps(value, ensure_ascii=False, default=str), time.time()))
