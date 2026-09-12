"""
imagegen.py -- image generation across providers plus a self-improving learning loop.

Learning loop (memory/image_learning.json):
  every generation is recorded (prompt, enhanced prompt, provider, file);
  the user rates results (+1 / -1) and can leave notes or ask for refinements;
  a style profile (likes / avoid / notes) is re-derived from the ratings, and
  every new prompt is enhanced with that profile before it reaches a model.
"""
import os, json, time, base64, random, re, threading, urllib.parse
from collections import Counter
from . import settings, media, llm

LEARN_FILE = os.path.join(settings.MEMDIR, "image_learning.json")
_LOCK = threading.Lock()
MAX_ITEMS = 400

# ---------------------------------------------------------------- store ----
def _load():
    try:
        with open(LEARN_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("items", [])
    d.setdefault("profile", {"likes": [], "avoid": [], "notes": "", "updated": 0})
    d.setdefault("stats", {})
    return d

def _save(d):
    os.makedirs(settings.MEMDIR, exist_ok=True)
    if len(d["items"]) > MAX_ITEMS:
        d["items"] = d["items"][-MAX_ITEMS:]
    tmp = LEARN_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LEARN_FILE)

def list_items(limit=60):
    with _LOCK:
        d = _load()
    return list(reversed(d["items"][-limit:]))

def get_item(iid):
    with _LOCK:
        d = _load()
    for it in d["items"]:
        if it["id"] == iid:
            return it
    return None

def profile():
    with _LOCK:
        d = _load()
    rated = [i for i in d["items"] if i.get("rating")]
    return {**d["profile"], "stats": d["stats"], "total": len(d["items"]),
            "liked": sum(1 for i in rated if i["rating"] > 0),
            "disliked": sum(1 for i in rated if i["rating"] < 0)}

def _clean_list(v, n):
    if isinstance(v, str):
        v = re.split(r"[,\n;]", v)
    out = []
    for x in v or []:
        x = str(x).strip().lower()[:60]
        if x and x not in out:
            out.append(x)
    return out[:n]

def set_profile(likes=None, avoid=None, notes=None):
    """Owner edits the learned taste directly; the next rating rebuilds on top of this."""
    with _LOCK:
        d = _load()
        p = d["profile"]
        if likes is not None: p["likes"] = _clean_list(likes, 12)
        if avoid is not None: p["avoid"] = _clean_list(avoid, 8)
        if notes is not None: p["notes"] = str(notes).strip()[:500]
        p["updated"] = time.time()
        _save(d)
    return profile()

def reset_profile(clear_ratings=False, clear_history=False):
    """Wipe the learned taste. Optionally also forget every rating (or the whole generation history)."""
    with _LOCK:
        d = _load()
        d["profile"] = {"likes": [], "avoid": [], "notes": "", "updated": time.time()}
        if clear_history:
            d["items"] = []; d["stats"] = {}
        elif clear_ratings:
            for i in d["items"]:
                i["rating"] = 0; i["note"] = ""
            for st in d["stats"].values():
                st["up"] = 0; st["down"] = 0
        _save(d)
    return profile()

# ------------------------------------------------------------ learning ----
def _phrases(prompt):
    out = []
    for p in re.split(r"[,.;\n]", prompt or ""):
        p = p.strip().lower()
        if 3 <= len(p) <= 40 and not re.match(r"^(a|an|the)\s", p) and len(p.split()) <= 4:
            out.append(p)
    return out

def _profile_text(d):
    prof = d["profile"]
    lines = []
    if prof.get("likes"):
        lines.append("Preferred style elements (the user rated these highly): " + ", ".join(prof["likes"][:10]))
    if prof.get("avoid"):
        lines.append("Avoid (the user disliked these): " + ", ".join(prof["avoid"][:6]))
    if prof.get("notes"):
        lines.append("Notes about the user's taste: " + prof["notes"])
    return "\n".join(lines)

def _relearn():
    """Rebuild the style profile from ratings: deterministic pass, then an optional LLM summary."""
    with _LOCK:
        d = _load()
    liked = [i for i in d["items"] if i.get("rating", 0) > 0]
    disliked = [i for i in d["items"] if i.get("rating", 0) < 0]
    lc, dc = Counter(), Counter()
    for i in liked:
        lc.update(set(_phrases(i.get("final_prompt")) + _phrases(i.get("refined_with"))))
    for i in disliked:
        dc.update(set(_phrases(i.get("final_prompt"))))
    likes = [p for p, n in lc.most_common(40) if n >= max(1, min(2, len(liked) // 3)) and dc[p] < n][:10]
    avoid = [p for p, n in dc.most_common(20) if lc[p] == 0][:6]
    notes = d["profile"].get("notes", "")
    # LLM summary of taste from the rated examples + user notes (best effort)
    examples = []
    for i in liked[-6:]:
        examples.append("LIKED: %s%s" % (i.get("final_prompt", "")[:200], (" | note: " + i["note"]) if i.get("note") else ""))
    for i in disliked[-4:]:
        examples.append("DISLIKED: %s%s" % (i.get("final_prompt", "")[:200], (" | note: " + i["note"]) if i.get("note") else ""))
    refs = [i["refined_with"] for i in d["items"] if i.get("refined_with")][-6:]
    if examples:
        out = llm.json_call(
            "You analyse a user's taste in AI-generated images from their ratings. Return JSON: "
            '{"likes":[up to 8 short style descriptors they respond to],"avoid":[up to 5 things to avoid],'
            '"notes":"one or two sentences summarising their taste"}. Be concrete (lighting, palette, medium, mood, composition).',
            "\n".join(examples) + ("\nRefinement requests they made: " + "; ".join(refs) if refs else ""),
            temperature=0.2, num_ctx=3072, timeout=180)
        if out:
            ll = [str(x).strip().lower() for x in (out.get("likes") or []) if str(x).strip()][:8]
            aa = [str(x).strip().lower() for x in (out.get("avoid") or []) if str(x).strip()][:5]
            for x in ll:
                if x not in likes:
                    likes.append(x)
            for x in aa:
                if x not in avoid and x not in likes:
                    avoid.append(x)
            if isinstance(out.get("notes"), str) and out["notes"].strip():
                notes = out["notes"].strip()[:400]
    with _LOCK:
        d = _load()
        d["profile"] = {"likes": likes[:10], "avoid": avoid[:6], "notes": notes, "updated": time.time()}
        _save(d)

def rate(iid, rating, note=""):
    with _LOCK:
        d = _load()
        item = next((i for i in d["items"] if i["id"] == iid), None)
        if not item:
            raise ValueError("unknown image id")
        item["rating"] = max(-1, min(1, int(rating or 0)))
        if note:
            item["note"] = str(note)[:300]
        st = d["stats"].setdefault(item.get("provider", "?"), {"ok": 0, "fail": 0, "up": 0, "down": 0})
        if item["rating"] > 0: st["up"] += 1
        if item["rating"] < 0: st["down"] += 1
        _save(d)
    threading.Thread(target=_relearn, daemon=True).start()
    return item

def enhance_prompt(prompt, style=None):
    """User prompt + learned profile -> model-ready prompt. LLM when available, deterministic otherwise."""
    with _LOCK:
        d = _load()
    prof = d["profile"]
    liked = [i for i in d["items"] if i.get("rating", 0) > 0][-4:]
    shots = "\n".join("Example the user liked: " + i.get("final_prompt", "")[:180] for i in liked)
    sys = ("You are an expert prompt engineer for text-to-image models. Rewrite the request into ONE vivid, "
           "concrete image prompt of at most 70 words: subject, setting, composition, lighting, colour palette, "
           "medium/style, quality tags. Keep the user's intent exactly; never add text, captions or watermarks. "
           "Apply the learned preferences below when they do not conflict with the request.\n"
           + _profile_text(d) + ("\n" + shots if shots else "")
           + ("\nRequested style: " + style if style else "")
           + '\nReturn JSON: {"prompt": "..."}')
    out = llm.json_call(sys, "Request: " + prompt, temperature=0.5, num_ctx=3072, timeout=150)
    if out and isinstance(out.get("prompt"), str) and 8 < len(out["prompt"].strip()) < 800:
        return out["prompt"].strip()
    tags = [t for t in prof.get("likes", [])[:6] if t not in prompt.lower()]
    p = prompt + ((", " + style) if style else "") + ((", " + ", ".join(tags)) if tags else "")
    if prof.get("avoid"):
        p += ". Avoid: " + ", ".join(prof["avoid"][:4])
    return p

# ------------------------------------------------------------ providers ----
def _dims(size):
    try:
        w, h = [int(x) for x in str(size).lower().split("x")]
        return max(256, min(2048, w)), max(256, min(2048, h))
    except Exception:
        return 1024, 1024

def _aspect(size):
    w, h = _dims(size)
    r = w / h
    if r > 1.6:  return "16:9"
    if r > 1.15: return "4:3"
    if r < 0.62: return "9:16"
    if r < 0.87: return "3:4"
    return "1:1"

def _apierr(r):
    try:
        j = r.json()
        return str((j.get("error") or {}).get("message") or j.get("message") or j.get("detail") or j)[:300]
    except Exception:
        return (r.text or str(r.status_code))[:300]

def _p_pollinations(prompt, model, size, source=None):
    w, h = _dims(size)
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:900]) +
           "?width=%d&height=%d&model=%s&nologo=true&seed=%d" % (w, h, model or "flux", random.randint(1, 10 ** 9)))
    data = media.download(url, timeout=240, headers={"User-Agent": "AIXMOS/2.0"})
    if not data or len(data) < 2000:
        raise RuntimeError("Pollinations returned an empty image")
    return data, ".jpg"

def _p_openai(prompt, model, size, source=None):
    import requests
    key = settings.get("openai", "api_key")
    w, h = _dims(size)
    if model.startswith("dall-e"):
        sz = "1792x1024" if w > h else ("1024x1792" if h > w else "1024x1024")
    else:
        sz = "1536x1024" if w > h else ("1024x1536" if h > w else "1024x1024")
    hdr = {"Authorization": "Bearer " + key}
    if source:
        with open(source, "rb") as f:
            r = requests.post("https://api.openai.com/v1/images/edits", headers=hdr,
                              data={"model": model, "prompt": prompt, "size": sz},
                              files={"image": (os.path.basename(source), f, media.mime_for(source))}, timeout=300)
    else:
        r = requests.post("https://api.openai.com/v1/images/generations", headers=hdr,
                          json={"model": model, "prompt": prompt, "size": sz, "n": 1}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError("OpenAI: " + _apierr(r))
    d0 = r.json()["data"][0]
    if d0.get("b64_json"):
        return base64.b64decode(d0["b64_json"]), ".png"
    return media.download(d0["url"]), ".png"

def _p_stability(prompt, model, size, source=None):
    import requests
    key = settings.get("stability", "api_key")
    r = requests.post("https://api.stability.ai/v2beta/stable-image/generate/" + (model or "core"),
                      headers={"Authorization": "Bearer " + key, "Accept": "image/*"},
                      files={"none": ""}, data={"prompt": prompt, "output_format": "png", "aspect_ratio": _aspect(size)},
                      timeout=300)
    if r.status_code >= 400:
        raise RuntimeError("Stability: " + _apierr(r))
    return r.content, ".png"

def _p_replicate(prompt, model, size, source=None):
    import requests
    key = settings.get("replicate", "api_key")
    hdr = {"Authorization": "Bearer " + key, "Content-Type": "application/json", "Prefer": "wait=60"}
    r = requests.post("https://api.replicate.com/v1/models/%s/predictions" % model, headers=hdr,
                      json={"input": {"prompt": prompt, "aspect_ratio": _aspect(size), "output_format": "png"}}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Replicate: " + _apierr(r))
    pred = r.json()
    t0 = time.time()
    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() - t0 > 600:
            raise RuntimeError("Replicate: timed out")
        time.sleep(3)
        pred = requests.get(pred["urls"]["get"], headers={"Authorization": "Bearer " + key}, timeout=60).json()
    if pred.get("status") != "succeeded":
        raise RuntimeError("Replicate: " + str(pred.get("error") or pred.get("status")))
    out = pred.get("output")
    url = out[0] if isinstance(out, list) else out
    return media.download(url), ".png"

def _p_fal(prompt, model, size, source=None):
    import requests
    key = settings.get("fal", "api_key")
    a = _aspect(size)
    isz = {"16:9": "landscape_16_9", "4:3": "landscape_4_3", "9:16": "portrait_16_9", "3:4": "portrait_4_3"}.get(a, "square_hd")
    r = requests.post("https://fal.run/" + model, headers={"Authorization": "Key " + key},
                      json={"prompt": prompt, "image_size": isz, "num_images": 1}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError("fal: " + _apierr(r))
    j = r.json()
    url = (j.get("images") or [{}])[0].get("url") or (j.get("image") or {}).get("url")
    if not url:
        raise RuntimeError("fal: no image in response")
    return media.download(url), ".png"

def _p_gemini(prompt, model, size, source=None):
    import requests
    key = settings.get("gemini", "api_key")
    base = "https://generativelanguage.googleapis.com/v1beta/models/"
    hdr = {"x-goog-api-key": key, "Content-Type": "application/json"}
    if model.startswith("imagen"):
        r = requests.post(base + model + ":predict", headers=hdr,
                          json={"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1, "aspectRatio": _aspect(size)}}, timeout=300)
        if r.status_code >= 400:
            raise RuntimeError("Google: " + _apierr(r))
        b64 = r.json()["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(b64), ".png"
    parts = [{"text": prompt}]
    if source:
        with open(source, "rb") as f:
            parts.insert(0, {"inlineData": {"mimeType": media.mime_for(source), "data": base64.b64encode(f.read()).decode()}})
    r = requests.post(base + model + ":generateContent", headers=hdr,
                      json={"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError("Google: " + _apierr(r))
    for c in r.json().get("candidates", []):
        for p in (c.get("content") or {}).get("parts", []):
            if p.get("inlineData"):
                mt = p["inlineData"].get("mimeType", "image/png")
                return base64.b64decode(p["inlineData"]["data"]), (".jpg" if "jpeg" in mt else ".png")
    raise RuntimeError("Google: no image in response (model may have replied with text only)")

PROVIDER_FNS = {"pollinations": _p_pollinations, "openai": _p_openai, "stability": _p_stability,
                "replicate": _p_replicate, "fal": _p_fal, "gemini": _p_gemini}
EDIT_CAPABLE = {"openai", "gemini"}

NO_PROVIDER = ("No image provider is set up. Add a key under Integrations, or switch on "
               "'Pollinations (free, public)' there; with Pollinations your prompts go to a public service.")

def choose_provider(requested=None):
    if requested and requested != "auto" and settings.configured(requested) and requested in PROVIDER_FNS:
        return requested
    p = settings.pref("image_provider")
    if p and p != "auto" and settings.configured(p) and p in PROVIDER_FNS:
        return p
    for cand in settings.providers_for("image"):
        if cand != "pollinations":
            return cand
    if settings.public_image_ok():
        return "pollinations"
    raise RuntimeError(NO_PROVIDER)

# ------------------------------------------------------------- generate ----
def generate(prompt, provider=None, model=None, size=None, enhance=None, parent=None,
             source_url=None, note="", style=None, allow_fallback=True):
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("empty prompt")
    size = size or settings.pref("image_size") or "1024x1024"
    if enhance is None:
        enhance = bool(settings.pref("enhance_prompts"))
    source = media.path_for(source_url) if source_url else None
    prov = choose_provider(provider)
    if source and prov not in EDIT_CAPABLE:
        source = None   # provider cannot take a source image; fall back to prompt-only refinement
    final = enhance_prompt(prompt, style) if (enhance and not source) else prompt
    mdl = model or settings.get(prov, "image_model")
    warning = ""
    try:
        data, ext = PROVIDER_FNS[prov](final, mdl, size, source)
    except Exception as e:
        _bump(prov, "fail")
        if allow_fallback and prov != "pollinations" and settings.public_image_ok():
            warning = "%s failed (%s); used Pollinations instead" % (prov, str(e)[:160])
            prov, mdl = "pollinations", settings.get("pollinations", "image_model")
            data, ext = _p_pollinations(final, mdl, size)
        else:
            raise
    _bump(prov, "ok")
    path, url = media.save_bytes("images", ext, data)
    item = {"id": os.path.splitext(os.path.basename(path))[0], "prompt": prompt, "final_prompt": final,
            "provider": prov, "model": mdl, "size": size, "url": url, "ts": time.time(), "rating": 0,
            "note": note or "", "parent": parent, "refined_with": note if parent else "", "warning": warning}
    with _LOCK:
        d = _load()
        d["items"].append(item)
        _save(d)
    return item

def _bump(prov, key):
    with _LOCK:
        d = _load()
        st = d["stats"].setdefault(prov, {"ok": 0, "fail": 0, "up": 0, "down": 0})
        st[key] = st.get(key, 0) + 1
        _save(d)

def refine(iid, instruction, mode="prompt", provider=None):
    """Iterate on an existing image: rewrite its prompt with the instruction (or edit the pixels when supported)."""
    item = get_item(iid)
    if not item:
        raise ValueError("unknown image id")
    instruction = (instruction or "").strip()
    if not instruction:
        raise ValueError("empty instruction")
    prov = choose_provider(provider or item.get("provider"))
    if mode == "edit" and prov in EDIT_CAPABLE:
        return generate(instruction, provider=prov, size=item.get("size"), enhance=False, parent=iid,
                        source_url=item["url"], note=instruction, allow_fallback=False)
    out = llm.json_call(
        "You revise text-to-image prompts. Apply the user's instruction to the existing prompt, changing only what "
        'the instruction asks and keeping everything else. Max 80 words. Return JSON: {"prompt": "..."}',
        "Existing prompt: %s\nInstruction: %s" % (item.get("final_prompt") or item["prompt"], instruction),
        temperature=0.4, num_ctx=2048, timeout=150)
    new_prompt = (out or {}).get("prompt") if out else None
    if not isinstance(new_prompt, str) or len(new_prompt.strip()) < 8:
        new_prompt = (item.get("final_prompt") or item["prompt"]) + ", " + instruction
    return generate(new_prompt, provider=prov, size=item.get("size"), enhance=False, parent=iid, note=instruction)
