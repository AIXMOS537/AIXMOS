"""
research.py -- scour the web and cross-reference it with the baked-in vault.

  search(query)            Google Custom Search (key + cx) -> SerpAPI (key) -> DuckDuckGo (no key)
  fetch(url)               readable page text
  research(question)       search, read the top pages in parallel, pull the passages that matter
  cross_reference(q, web)  vault passages vs web passages -> agreements / conflicts / gaps, with sources
  run(question)            the whole pipeline, saved to memory/research.json
"""
import os, re, json, time, html, threading, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from . import settings, llm, knowledge

FILE = os.path.join(settings.MEMDIR, "research.json")
_LOCK = threading.Lock()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIXMOS/2.0 research"}

# ---------------------------------------------------------------- search ----
def _apierr(r):
    try:
        j = r.json(); return str((j.get("error") or {}).get("message") or j.get("message") or j)[:200]
    except Exception:
        return (r.text or str(r.status_code))[:200]

def _google_cse(query, n):
    import requests
    key, cx = settings.get("google_search", "api_key"), settings.get("google_search", "cx")
    r = requests.get("https://www.googleapis.com/customsearch/v1", params={"key": key, "cx": cx, "q": query, "num": min(10, n)}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError("Google Custom Search: " + _apierr(r))
    return [{"title": i.get("title", ""), "url": i.get("link", ""), "snippet": i.get("snippet", ""), "engine": "google"}
            for i in r.json().get("items", [])]

def _serpapi(query, n):
    import requests
    r = requests.get("https://serpapi.com/search.json", params={"engine": "google", "q": query, "num": min(10, n),
                                                                 "api_key": settings.get("serpapi", "api_key")}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError("SerpAPI: " + _apierr(r))
    return [{"title": i.get("title", ""), "url": i.get("link", ""), "snippet": i.get("snippet", ""), "engine": "google/serpapi"}
            for i in r.json().get("organic_results", [])]

def _ddg(query, n):
    import requests
    r = requests.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=30, headers=UA)
    out = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?(?:<a[^>]+class="result__snippet"[^>]*>(.*?)</a>)?', r.text, flags=re.S):
        href = m.group(1)
        mm = re.search(r"uddg=([^&]+)", href)
        if mm:
            href = urllib.parse.unquote(mm.group(1))
        if not href.startswith("http"):
            continue
        out.append({"title": html.unescape(re.sub(r"<[^>]+>", "", m.group(2)).strip()), "url": href,
                    "snippet": html.unescape(re.sub(r"<[^>]+>", "", m.group(3) or "").strip()), "engine": "duckduckgo"})
        if len(out) >= n:
            break
    return out

def engines():
    e = []
    if settings.configured("google_search"): e.append("google")
    if settings.configured("serpapi"): e.append("google/serpapi")
    e.append("duckduckgo")
    return e

def search(query, n=8):
    """Best available engine first; falls back down the chain on any error."""
    errors = []
    chain = []
    if settings.configured("google_search"): chain.append(_google_cse)
    if settings.configured("serpapi"): chain.append(_serpapi)
    chain.append(_ddg)
    for fn in chain:
        try:
            res = fn(query, n)
            if res:
                return res, errors
            errors.append("%s: no results" % fn.__name__.strip("_"))
        except Exception as e:
            errors.append("%s: %s" % (fn.__name__.strip("_"), str(e)[:160]))
    return [], errors

# ----------------------------------------------------------------- fetch ----
def fetch(url, max_chars=12000, timeout=25):
    import requests
    if not re.match(r"^https?://", url):
        url = "https://" + url
    r = requests.get(url, timeout=timeout, headers=UA, allow_redirects=True)
    ct = r.headers.get("Content-Type", "")
    text = r.text
    title = ""
    if "html" in ct or "<html" in text[:800].lower():
        m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.S | re.I)
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:160] if m else ""
        text = re.sub(r"(?is)<(script|style|noscript|nav|footer|header|svg|form|iframe).*?</\1>", " ", text)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>|</tr>", "\n", text)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
    return {"url": r.url, "status": r.status_code, "title": title, "text": text.strip()[:max_chars]}

def _passages(text, query, k=4, size=700):
    """Rank paragraph windows of a page by overlap with the query (cheap BM25-ish scoring)."""
    q = set(knowledge._tok(query))
    if not q:
        return []
    paras, buf = [], ""
    for p in re.split(r"\n\s*\n", text):
        p = p.strip()
        if len(p) < 40:
            continue
        buf = (buf + "\n" + p).strip()
        if len(buf) >= size:
            paras.append(buf); buf = ""
    if buf:
        paras.append(buf)
    scored = []
    for p in paras:
        toks = knowledge._tok(p)
        if not toks:
            continue
        hit = sum(1 for t in set(toks) if t in q)
        if hit:
            scored.append((hit / (len(q) ** 0.5) * (1 + min(len(toks), 200) / 400), p[:size + 200]))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:k]]

# -------------------------------------------------------------- research ----
def research(question, results=6, pages=4, progress=lambda m: None):
    progress("searching the web")
    hits, errors = search(question, n=results)
    findings, fetched = [], []
    def read(h):
        try:
            page = fetch(h["url"])
            if page["status"] >= 400 or len(page["text"]) < 200:
                return None
            return {**h, "title": h["title"] or page["title"], "passages": _passages(page["text"], question), "chars": len(page["text"])}
        except Exception as e:
            return {**h, "error": str(e)[:120], "passages": []}
    todo = [h for h in hits if not re.search(r"\.(pdf|zip|exe|dmg)(\?|$)", h["url"], re.I)][:pages]
    progress("reading %d pages" % len(todo))
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(read, todo):
            if res:
                fetched.append(res)
    for h in hits:
        f = next((x for x in fetched if x["url"] == h["url"]), None)
        findings.append(f or {**h, "passages": []})
    return {"question": question, "engines": engines(), "errors": errors, "results": findings}

def cross_reference(question, web, progress=lambda m: None):
    progress("cross-referencing with the vault")
    vault = knowledge.search(question, k=5)
    vault_txt = "\n\n".join("[V%d] %s / %s — %s\n%s" % (i + 1, h["pack"], h["file"].split("/")[-1], h["title"], h["text"][:900])
                            for i, h in enumerate(vault)) or "(nothing relevant in the vault)"
    web_txt, n = [], 0
    for r in web.get("results", []):
        body = "\n".join(r.get("passages") or [])[:1400] or r.get("snippet", "")
        if not body:
            continue
        n += 1
        web_txt.append("[W%d] %s — %s\n%s" % (n, r.get("title", "")[:100], r["url"], body))
        if n >= 6:
            break
    web_block = "\n\n".join(web_txt) or "(no readable web content)"
    out = llm.json_call(
        "You are a meticulous research analyst. Compare what the user's own playbook vault says (V sources) with what the "
        "web says (W sources) about the question. Quote or paraphrase only what the sources actually contain; never invent "
        "facts, numbers or sources. Cite with [V#] / [W#] tags. Return JSON:\n"
        "{\"answer\": \"direct 2-5 sentence answer synthesising both, with citations\",\n"
        " \"agreements\": [\"point where vault and web agree [V#][W#]\"],\n"
        " \"conflicts\": [\"point where they disagree, with both positions [V#] vs [W#]\"],\n"
        " \"vault_only\": [\"useful point only the vault makes [V#]\"],\n"
        " \"web_only\": [\"useful point only the web adds [W#]\"],\n"
        " \"confidence\": \"high|medium|low\", \"confidence_reason\": \"one sentence\",\n"
        " \"next_step\": \"one concrete action for the user\"}",
        "QUESTION: %s\n\nVAULT SOURCES:\n%s\n\nWEB SOURCES:\n%s" % (question, vault_txt, web_block),
        temperature=0.2, num_ctx=8192, timeout=420)
    if not out or not out.get("answer"):
        out = {"answer": "The local model could not produce a comparison; the raw sources are listed below.",
               "agreements": [], "conflicts": [], "vault_only": [], "web_only": [], "confidence": "low",
               "confidence_reason": "model returned no structured comparison", "next_step": "retry with a narrower question"}
    for k in ("agreements", "conflicts", "vault_only", "web_only"):
        out[k] = [str(x)[:400] for x in (out.get(k) or []) if str(x).strip()][:8]
    return {"analysis": out, "vault": [{"tag": "V%d" % (i + 1), "pack": h["pack"], "file": h["file"], "title": h["title"], "score": h["score"], "snippet": h["snippet"]} for i, h in enumerate(vault)],
            "web": [{"tag": "W%d" % (i + 1), "title": w.get("title", ""), "url": w["url"], "engine": w.get("engine"), "snippet": (w.get("passages") or [w.get("snippet", "")])[0][:300]} for i, w in enumerate([r for r in web.get("results", []) if (r.get("passages") or r.get("snippet"))][:6])]}

def run(question, depth="normal", cross=True, progress=lambda m: None):
    question = (question or "").strip()
    if not question:
        raise ValueError("question is required")
    results, pages = {"quick": (5, 2), "normal": (8, 4), "deep": (10, 7)}.get(depth, (8, 4))
    web = research(question, results=results, pages=pages, progress=progress)
    rep = {"ts": time.time(), "question": question, "depth": depth, "engines": web["engines"], "errors": web["errors"],
           "results": [{k: v for k, v in r.items() if k != "passages"} | {"passages": (r.get("passages") or [])[:2]} for r in web["results"]]}
    if cross:
        rep.update(cross_reference(question, web, progress))
    rep["markdown"] = to_markdown(rep)
    with _LOCK:
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
        except (OSError, ValueError):
            hist = []
        hist.insert(0, rep); hist = hist[:60]
        os.makedirs(settings.MEMDIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=1)
    return rep

def history(limit=30):
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)[:limit]
    except (OSError, ValueError):
        return []

def to_markdown(rep):
    a = rep.get("analysis")
    lines = ["Research: %s" % rep["question"], "Engines: %s%s" % (", ".join(rep.get("engines") or []), ("  (issues: " + "; ".join(rep["errors"]) + ")") if rep.get("errors") else "")]
    if a:
        lines += ["", a["answer"], "", "Confidence: %s — %s" % (a.get("confidence"), a.get("confidence_reason", ""))]
        for label, key in (("Where vault and web agree", "agreements"), ("Where they conflict", "conflicts"),
                           ("Only in your vault", "vault_only"), ("Only on the web", "web_only")):
            if a.get(key):
                lines += ["", label + ":"] + ["- " + x for x in a[key]]
        if a.get("next_step"):
            lines += ["", "Next step: " + a["next_step"]]
        if rep.get("vault"):
            lines += ["", "Vault sources:"] + ["[%s] %s / %s — %s" % (v["tag"], v["pack"], v["file"].split("/")[-1], v["title"]) for v in rep["vault"]]
        if rep.get("web"):
            lines += ["", "Web sources:"] + ["[%s] %s — %s" % (w["tag"], w["title"][:80], w["url"]) for w in rep["web"]]
    else:
        lines += [""] + ["- %s — %s\n  %s" % (r.get("title", "")[:80], r["url"], r.get("snippet", "")[:160]) for r in rep.get("results", [])[:8]]
    return "\n".join(lines)
