"""
carousel.py -- Instagram carousel generator from the kit's carousel-system template:
the local model writes the slides (hook -> context -> one-idea bodies -> recap -> single CTA),
Pillow renders 1080x1350 PNG slides in the brand colours, ready to post.
"""
import os, re, json, time, textwrap
from . import settings, llm, media, skills, knowledge

LAYOUTS = {"A_how_to": "how-to steps", "B_list": "numbered list of tips", "C_mistakes": "common mistakes and fixes",
           "D_story": "short story with a lesson", "E_framework": "a named framework explained"}
DEFAULT_BRAND = {"bg": "#061021", "text": "#dcf4ff", "accent": "#38e0ff", "muted": "#7ea4bd", "font": "segoeui.ttf", "font_bold": "segoeuib.ttf", "handle": ""}

def brand():
    b = settings.load().get("brand") or {}
    return {**DEFAULT_BRAND, **{k: v for k, v in b.items() if v}}

def save_brand(fields):
    with settings._LOCK:
        d = settings._read(); b = d.setdefault("brand", {})
        for k, v in (fields or {}).items():
            if k in DEFAULT_BRAND:
                b[k] = str(v or "").strip()[:80]
        settings._write(d)
    return brand()

def write(topic, audience="", layout="B_list", slides=6, extra=""):
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic is required")
    layout = layout if layout in LAYOUTS else "B_list"
    n_body = max(2, min(6, int(slides) - 3))
    guide = knowledge.context_for("carousel cover hook body slides summary cta " + topic, k=2, min_score=2.0, max_chars=1400)
    out = llm.json_call(
        "You write Instagram carousel copy using the carousel-system playbook: cover = scroll-stopping hook under 8 words, specific not clever; "
        "context slide = why it matters / who it's for in one line; body slides = ONE idea each, bold headline (max 9 words) + one supporting "
        "line (max 18 words), value front-loaded, talk to one person ('you'); summary = recap list of every body point (max 6 words each); "
        "cta = ONE ask only (save / follow / comment WORD / share). No paragraphs, no clickbait the slides cannot pay off, never invent statistics. "
        "Layout: %s (%s). Return JSON: {\"cover\":\"..\",\"context\":{\"headline\":\"..\",\"subtext\":\"..\"},\"body\":[{\"headline\":\"..\",\"subtext\":\"..\"}] (exactly %d items),"
        "\"summary\":[\"..\"],\"cta\":{\"headline\":\"..\",\"ask\":\"..\"},\"caption\":\"2-3 line caption ending with the CTA\",\"hashtags\":[\"..\" x 8]}"
        % (layout, LAYOUTS[layout], n_body) + ("\n\nPlaybook notes:\n" + guide if guide else "") + ("\n" + skills.profile_text()),
        "Topic: %s\nAudience: %s%s" % (topic, audience or "general", ("\nExtra direction: " + extra) if extra else ""),
        temperature=0.6, num_ctx=6144, timeout=300)
    if not out or not out.get("cover") or not out.get("body"):
        raise RuntimeError("the local model did not return carousel copy; try a more specific topic")
    body = [b for b in out["body"] if isinstance(b, dict) and b.get("headline")][:n_body]
    slides_out = [{"kind": "cover", "headline": str(out["cover"])[:80], "subtext": ""},
                  {"kind": "context", "headline": str((out.get("context") or {}).get("headline") or "")[:90], "subtext": str((out.get("context") or {}).get("subtext") or "")[:160]}]
    slides_out += [{"kind": "body", "headline": str(b["headline"])[:90], "subtext": str(b.get("subtext") or "")[:160]} for b in body]
    summ = [str(x)[:60] for x in (out.get("summary") or []) if str(x).strip()][:6] or [b["headline"] for b in slides_out[2:]]
    slides_out.append({"kind": "summary", "headline": "Recap", "points": summ})
    cta = out.get("cta") or {}
    slides_out.append({"kind": "cta", "headline": str(cta.get("headline") or "Save this for later")[:80], "subtext": str(cta.get("ask") or "")[:120]})
    return {"topic": topic, "audience": audience, "layout": layout, "slides": slides_out,
            "caption": str(out.get("caption") or "")[:800], "hashtags": [re.sub(r"[^#\w]", "", "#" + str(h).lstrip("#")) for h in (out.get("hashtags") or [])][:12]}

# ---------------------------------------------------------------- render ----
def _font(name, size):
    from PIL import ImageFont
    bold = "bold" in (name or "").lower() or (name or "").lower().endswith(("b.ttf", "bd.ttf"))
    cands = [name] if (name and os.path.isabs(name)) else []
    if os.name == "nt" and name:
        cands.append(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", name))
    cands += [media.font_file(bold=bold), media.font_file(bold=False)]
    for p in cands:
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

def _hex(c, default):
    c = (c or "").strip()
    return c if re.match(r"^#[0-9a-fA-F]{6}$", c) else default

def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _fit_font(draw, text, name, max_w, start, minimum, max_lines):
    size = start
    while size > minimum:
        f = _font(name, size)
        lines = _wrap(draw, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
        size -= 6
    f = _font(name, minimum)
    return f, _wrap(draw, text, f, max_w)[:max_lines]

def render(copy, brand_override=None, stem=None):
    from PIL import Image, ImageDraw
    b = {**brand(), **(brand_override or {})}
    W, H, PAD = 1080, 1350, 90
    bg, fg, ac, mu = _hex(b["bg"], "#061021"), _hex(b["text"], "#dcf4ff"), _hex(b["accent"], "#38e0ff"), _hex(b["muted"], "#7ea4bd")
    slides = copy["slides"]; total = len(slides); urls = []
    stem = stem or ("carousel-" + media.new_id())
    for i, s in enumerate(slides):
        img = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 14], fill=ac)                                # accent top bar
        d.rectangle([PAD, H - 120, PAD + 160, H - 112], fill=ac)             # footer rule
        small = _font(b["font"], 30)
        d.text((PAD, H - 96), (b.get("handle") or skills.profile().get("name") or "AIXMOS")[:40], font=small, fill=mu)
        d.text((W - PAD - 120, H - 96), "%d / %d" % (i + 1, total), font=small, fill=mu)
        if i < total - 1:
            d.text((W - PAD - 220, H - 96), "swipe →", font=small, fill=ac)
        y = PAD + 120
        if s["kind"] == "cover":
            f, lines = _fit_font(d, s["headline"], b["font_bold"], W - 2 * PAD, 118, 64, 5)
            y = (H - len(lines) * (f.size + 14)) // 2 - 60
            for ln in lines:
                d.text((PAD, y), ln, font=f, fill=fg); y += f.size + 14
            d.rectangle([PAD, y + 24, PAD + 220, y + 34], fill=ac)
        elif s["kind"] == "summary":
            f = _font(b["font_bold"], 84); d.text((PAD, y), s["headline"], font=f, fill=ac); y += 130
            pf = _font(b["font"], 46)
            for n, pt in enumerate(s.get("points") or [], 1):
                for j, ln in enumerate(_wrap(d, pt, pf, W - 2 * PAD - 90)[:2]):
                    d.text((PAD, y), ("%d." % n) if j == 0 else "", font=pf, fill=ac)
                    d.text((PAD + 70, y), ln, font=pf, fill=fg); y += 64
                y += 18
        else:
            tag = {"context": "WHY IT MATTERS", "cta": "ONE THING TO DO", "body": "%02d" % (i - 1)}.get(s["kind"], "")
            if tag:
                d.text((PAD, y - 60), tag, font=_font(b["font_bold"], 30), fill=ac)
            f, lines = _fit_font(d, s["headline"], b["font_bold"], W - 2 * PAD, 92, 56, 4)
            for ln in lines:
                d.text((PAD, y), ln, font=f, fill=fg); y += f.size + 12
            if s.get("subtext"):
                y += 30; sf = _font(b["font"], 44)
                for ln in _wrap(d, s["subtext"], sf, W - 2 * PAD)[:5]:
                    d.text((PAD, y), ln, font=sf, fill=mu); y += 58
        path = os.path.join(media.MEDIA, "images", "%s-%02d.png" % (stem, i + 1))
        media.ensure_dirs(); img.save(path, "PNG", optimize=True)
        urls.append(media.url_for(path))
    return urls

def build(topic, audience="", layout="B_list", slides=6, extra="", brand_override=None):
    copy = write(topic, audience, layout, slides, extra)
    urls = render(copy, brand_override)
    for s, u in zip(copy["slides"], urls):
        s["url"] = u
    copy["ts"] = time.time()
    hist = os.path.join(settings.MEMDIR, "carousels.json")
    try:
        with open(hist, "r", encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError):
        items = []
    items.insert(0, copy); items = items[:40]
    with open(hist, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    return copy

def history():
    try:
        with open(os.path.join(settings.MEMDIR, "carousels.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []
