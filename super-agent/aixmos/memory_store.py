"""
memory_store.py -- structured customer memory with provenance (memory/aixmos-memory.db). Persists across restarts.

Learning != training the model. AIXMOS remembers typed facts with where they came from:
  SOURCE_DATA | EXTRACTED_FACT | USER_STATEMENT | MODEL_SUMMARY | INFERENCE | VERIFIED_FACT | PREFERENCE | DECISION | PROCEDURE
Rules:
  * anything a model produces is stored as MODEL_SUMMARY or INFERENCE, never as a fact about the customer
  * only the customer (origin=user) or a passed verification can promote an item to VERIFIED_FACT
  * every item has a scope: LOCAL_ONLY (never sent to cloud engines) or CLOUD_OK
  * the customer can list, forget and export everything
"""
import json, os, sqlite3, threading, time

from . import settings

CLASSES = ("SOURCE_DATA", "EXTRACTED_FACT", "USER_STATEMENT", "MODEL_SUMMARY", "INFERENCE", "VERIFIED_FACT", "PREFERENCE", "DECISION", "PROCEDURE")
MODEL_ALLOWED = ("MODEL_SUMMARY", "INFERENCE")
_LOCK = threading.Lock()

def _db():
    os.makedirs(settings.MEMDIR, exist_ok=True)
    c = sqlite3.connect(os.path.join(settings.MEMDIR, "aixmos-memory.db"), timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, text TEXT NOT NULL, klass TEXT NOT NULL,
                 origin TEXT NOT NULL, source TEXT, topic TEXT, confidence REAL, scope TEXT NOT NULL DEFAULT 'LOCAL_ONLY',
                 created REAL, verified_by TEXT, verified_at REAL, forgotten INTEGER DEFAULT 0)""")
    return c

def remember(text, klass, origin="user", source="", topic="", confidence=None, scope="LOCAL_ONLY"):
    if klass not in CLASSES:
        raise ValueError("unknown memory class " + klass)
    if origin not in ("user", "model", "system", "import"):
        raise ValueError("origin must be user, model, system or import")
    if origin == "model" and klass not in MODEL_ALLOWED:
        raise PermissionError("a model can only store MODEL_SUMMARY or INFERENCE, not " + klass)
    if klass == "VERIFIED_FACT" and origin != "user":
        raise PermissionError("only the customer or a passed verification (promote) can create a VERIFIED_FACT")
    if scope not in ("LOCAL_ONLY", "CLOUD_OK"):
        raise ValueError("scope must be LOCAL_ONLY or CLOUD_OK")
    with _LOCK:
        c = _db()
        rid = c.execute("INSERT INTO memory (text, klass, origin, source, topic, confidence, scope, created) VALUES (?,?,?,?,?,?,?,?)",
                        (str(text)[:4000], klass, origin, source, topic, confidence, scope, time.time())).lastrowid
        c.commit(); c.close()
    return rid

def promote(rid, by):
    """Customer confirms an item (or a verification passed). by = 'customer' or 'verification:<check id>'."""
    if not (by == "customer" or str(by).startswith("verification:")):
        raise PermissionError("only the customer or a verification can promote")
    with _LOCK:
        c = _db(); c.execute("UPDATE memory SET klass='VERIFIED_FACT', verified_by=?, verified_at=? WHERE id=? AND forgotten=0", (by, time.time(), rid))
        c.commit(); c.close()

def recall(query="", limit=20, for_cloud=False, klass=None):
    """Keyword recall. for_cloud=True excludes LOCAL_ONLY items (they never leave this computer)."""
    sql, p = "SELECT id, text, klass, origin, source, topic, confidence, scope, created, verified_by FROM memory WHERE forgotten=0", []
    for w in [w for w in str(query).lower().split() if len(w) > 2][:6]:
        sql += " AND lower(text || ' ' || coalesce(topic,'')) LIKE ?"; p.append("%" + w + "%")
    if for_cloud:
        sql += " AND scope='CLOUD_OK'"
    if klass:
        sql += " AND klass=?"; p.append(klass)
    sql += " ORDER BY (klass='VERIFIED_FACT') DESC, created DESC LIMIT ?"; p.append(int(limit))
    c = _db(); rows = c.execute(sql, p).fetchall(); c.close()
    keys = ("id", "text", "klass", "origin", "source", "topic", "confidence", "scope", "created", "verified_by")
    return [dict(zip(keys, r)) for r in rows]

_STOP = set("the a an and or of to in on for with is are was were be how many much what which who when where why does do did "
             "has have had in one short sentence please tell me my our your this that it its can could would should".split())

def relevant(question, limit=5, for_cloud=False):
    """Context retrieval for a question: any meaningful word may match; ranked by overlap, verified facts first."""
    words = {w for w in "".join(ch if ch.isalnum() else " " for ch in str(question).lower()).split() if len(w) > 2 and w not in _STOP}
    if not words:
        return []
    sql = "SELECT id, text, klass, origin, source, topic, confidence, scope, created, verified_by FROM memory WHERE forgotten=0 AND (" + \
          " OR ".join("lower(text) LIKE ?" for _ in words) + ")" + (" AND scope='CLOUD_OK'" if for_cloud else "")
    c = _db(); rows = c.execute(sql, ["%" + w + "%" for w in words]).fetchall(); c.close()
    keys = ("id", "text", "klass", "origin", "source", "topic", "confidence", "scope", "created", "verified_by")
    items = [dict(zip(keys, r)) for r in rows]
    for it in items:
        t = it["text"].lower()
        it["_score"] = sum(1 for w in words if w in t) + (2 if it["klass"] == "VERIFIED_FACT" else 1 if it["origin"] == "user" else 0)
    items.sort(key=lambda x: (-x["_score"], -x["created"]))
    return items[:limit]

def forget(rid):
    with _LOCK:
        c = _db(); c.execute("UPDATE memory SET forgotten=1, text='[forgotten]' WHERE id=?", (rid,)); c.commit(); c.close()

def stats():
    c = _db()
    rows = c.execute("SELECT klass, COUNT(*) FROM memory WHERE forgotten=0 GROUP BY klass").fetchall(); c.close()
    return dict(rows)

def export(path):
    items = recall("", limit=100000)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"format": "aixmos-memory/1", "exported": time.strftime("%Y-%m-%dT%H:%M:%S"), "items": items}, f, indent=1)
    return len(items)
