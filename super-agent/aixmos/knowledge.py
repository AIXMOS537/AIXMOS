"""
knowledge.py -- local knowledge vault: ingests the AI BUILDING KIT (and any folder of
markdown/text) into heading-aware chunks with a pure-Python BM25 index. No embeddings,
no network, instant on this machine.

  ingest(root)            -> (re)build memory/knowledge/index.json from a folder tree
  search(query, k, pack)  -> ranked chunks with snippets
  packs()                 -> pack list with titles / summaries / file counts
  read(rel_path)          -> raw file text (safe, inside the kit root)
"""
import os, re, json, math, threading, time
from collections import Counter, defaultdict
from . import settings

KB_DIR = os.path.join(settings.MEMDIR, "knowledge")
INDEX = os.path.join(KB_DIR, "index.json")
DEFAULT_ROOT = os.path.join(settings.MEMDIR, "kit")
_LOCK = threading.Lock()
_IDX = {"loaded": False, "chunks": [], "post": {}, "len": [], "avg": 1.0, "root": DEFAULT_ROOT, "built": 0}
STOP = set("""a an the of in on at to for and or is are was were be been by with from as it its this that these those
you your we our they their i me my he she his her him them us can will would should could may might do does did not no yes
if then than so such into onto over under out up down about after before again also just very more most less all any each
how what when where which who whom why here there own same too s t don ll re ve""".split())
TEXT_EXT = {".md", ".txt", ".json", ".html", ".csv", ".yml", ".yaml"}

def _tok(s):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9\-']*", (s or "").lower()) if w not in STOP and len(w) > 1]

def _chunks_from(text, max_len=900):
    """Split markdown on headings, then on paragraph boundaries into ~max_len pieces."""
    out, title, buf = [], "", []
    def flush():
        body = "\n".join(buf).strip()
        if len(body) > 40:
            out.append((title, body))
        buf.clear()
    for line in text.splitlines():
        if re.match(r"^#{1,3}\s", line):
            flush(); title = line.strip("# ").strip()
        else:
            buf.append(line)
            if sum(len(x) + 1 for x in buf) > max_len and (not line.strip()):
                flush()
    flush()
    # second pass: hard-split anything still too long
    final = []
    for t, b in out:
        while len(b) > max_len * 1.6:
            cut = b.rfind("\n", 0, max_len)
            cut = cut if cut > max_len // 2 else max_len
            final.append((t, b[:cut])); b = b[cut:].strip()
        final.append((t, b))
    return final

def ingest(root=None):
    root = os.path.abspath(root or settings.pref("kit_path") or DEFAULT_ROOT)
    chunks = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".") and d != "node_modules"]
        for f in sorted(fn):
            ext = os.path.splitext(f)[1].lower()
            if ext not in TEXT_EXT:
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            if ext == ".html":
                text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
                text = re.sub(r"<[^>]+>", " ", text)
            rel = os.path.relpath(p, root).replace("\\", "/")
            pack = rel.split("/")[0] if "/" in rel else "(root)"
            for i, (title, body) in enumerate(_chunks_from(text)):
                chunks.append({"id": "%s#%d" % (rel, i), "pack": pack, "file": rel, "title": title or os.path.basename(f), "text": body})
    post, lens = defaultdict(dict), []
    for ci, c in enumerate(chunks):
        toks = _tok(c["title"] + " " + c["text"])
        lens.append(len(toks) or 1)
        for w, n in Counter(toks).items():
            post[w][ci] = n
    idx = {"root": root, "built": time.time(), "chunks": chunks, "post": post, "len": lens,
           "avg": (sum(lens) / len(lens)) if lens else 1.0}
    os.makedirs(KB_DIR, exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    with _LOCK:
        _IDX.update(idx); _IDX["loaded"] = True
    return {"root": root, "files": len({c["file"] for c in chunks}), "chunks": len(chunks), "packs": len({c["pack"] for c in chunks})}

def _load():
    with _LOCK:
        if _IDX["loaded"]:
            return
        try:
            with open(INDEX, "r", encoding="utf-8") as f:
                d = json.load(f)
            _IDX.update(d); _IDX["loaded"] = True
        except (OSError, ValueError):
            _IDX["loaded"] = True   # empty index; ingest() fills it

def stats():
    _load()
    return {"chunks": len(_IDX["chunks"]), "files": len({c["file"] for c in _IDX["chunks"]}),
            "packs": len({c["pack"] for c in _IDX["chunks"]}), "root": _IDX.get("root"), "built": _IDX.get("built", 0)}

def search(query, k=5, pack=None, k1=1.4, b=0.75):
    _load()
    q = _tok(query)
    chunks, post, lens, avg = _IDX["chunks"], _IDX["post"], _IDX["len"], _IDX["avg"]
    if not q or not chunks:
        return []
    N = len(chunks); scores = defaultdict(float)
    for w in set(q):
        plist = post.get(w)
        if not plist:
            continue
        idf = math.log(1 + (N - len(plist) + 0.5) / (len(plist) + 0.5))
        for ci, tf in plist.items():
            ci = int(ci)
            if pack and chunks[ci]["pack"] != pack:
                continue
            dl = lens[ci]
            scores[ci] += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg))
    top = sorted(scores.items(), key=lambda x: -x[1])[:k]
    out = []
    for ci, sc in top:
        c = chunks[ci]
        out.append({**c, "score": round(sc, 2), "snippet": _snippet(c["text"], q)})
    return out

def _snippet(text, q, width=260):
    low = text.lower()
    pos = min([low.find(w) for w in q if low.find(w) >= 0] or [0])
    start = max(0, pos - 60)
    s = text[start:start + width].strip().replace("\n", " ")
    return ("…" if start else "") + s + ("…" if start + width < len(text) else "")

def context_for(query, k=3, min_score=4.0, max_chars=2600):
    """Formatted knowledge block for a system prompt, or '' when nothing relevant."""
    hits = [h for h in search(query, k=k) if h["score"] >= min_score]
    if not hits:
        return ""
    parts, total = [], 0
    for h in hits:
        piece = "[%s / %s — %s]\n%s" % (h["pack"], h["file"].split("/")[-1], h["title"], h["text"][:1200])
        if total + len(piece) > max_chars:
            break
        parts.append(piece); total += len(piece)
    return "\n\n".join(parts)

def packs():
    _load()
    root = _IDX.get("root") or DEFAULT_ROOT
    out = {}
    for c in _IDX["chunks"]:
        p = out.setdefault(c["pack"], {"id": c["pack"], "files": set(), "title": "", "summary": "", "chunks": 0})
        p["files"].add(c["file"]); p["chunks"] += 1
    for pid, p in out.items():
        p["files"] = sorted(p["files"])
        start = next((f for f in p["files"] if f.endswith("00-START-HERE.md")), None) or next((f for f in p["files"] if f.lower().endswith("readme.md") or f.lower().endswith("readme-kit.md")), None)
        if start:
            txt = read(start) or ""
            m = re.search(r"^#\s+(.+)$", txt, flags=re.M)
            p["title"] = (m.group(1).strip() if m else pid)
            m2 = re.search(r"\*\*What this is:\*\*\s*(.+?)(?:\n\n|\Z)", txt, flags=re.S) or re.search(r"^###\s+(.+)$", txt, flags=re.M)
            p["summary"] = re.sub(r"\s+", " ", m2.group(1)).strip()[:300] if m2 else ""
        else:
            p["title"] = pid.replace("-", " ").title()
    return sorted(out.values(), key=lambda x: x["id"])

def read(rel):
    _load()
    root = os.path.abspath(_IDX.get("root") or DEFAULT_ROOT)
    full = os.path.abspath(os.path.join(root, *str(rel).replace("\\", "/").split("/")))
    from .media import inside
    if not inside(root, full) or not os.path.isfile(full):
        return None
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None
