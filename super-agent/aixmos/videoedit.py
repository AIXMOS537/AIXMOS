"""
videoedit.py -- edit any video with a plain-language prompt.

  instruction -> plan (LLM JSON, with a keyword parser as fast path / fallback)
              -> validated operation list -> ffmpeg filter graph -> new file.

Everything runs locally (ffmpeg + whisper.cpp for captions). A generative
"ai_edit" op is routed to Runway (gen4_aleph) when a key is configured.
"""
import os, re, json, time, base64, subprocess, tempfile
from . import settings, media, llm, jobs

ROOT = settings.ROOT
WHISPER_CLI = os.path.join(ROOT, "whisper", "bin", "Release", "whisper-cli.exe")
WHISPER_MODEL = os.path.join(ROOT, "whisper", "models", "ggml-base.en.bin")

OPS = {
    "trim":          {"start": "sec", "end": "sec (negative = from the end)"},
    "remove":        {"start": "sec", "end": "sec"},
    "speed":         {"factor": "0.25-8"},
    "crop":          {"aspect": "9:16|1:1|16:9|4:5|4:3"},
    "resize":        {"width": "px", "height": "px"},
    "rotate":        {"degrees": "90|180|270"},
    "flip":          {"axis": "h|v"},
    "mute":          {},
    "volume":        {"factor": "0-5"},
    "fade":          {"in": "sec", "out": "sec"},
    "text":          {"text": "string", "position": "top|center|bottom", "start": "sec", "end": "sec", "size": "px", "color": "name"},
    "color":         {"brightness": "-1..1", "contrast": "0..3", "saturation": "0..3"},
    "grayscale": {}, "sepia": {}, "invert": {}, "vignette": {}, "sharpen": {}, "denoise": {}, "stabilize": {},
    "blur":          {"amount": "1-20"},
    "reverse":       {},
    "loop":          {"times": "2-10"},
    "fps":           {"value": "fps"},
    "gif":           {"fps": "fps", "width": "px"},
    "extract_audio": {},
    "captions":      {},
    "overlay":       {"image": "media url", "position": "tl|tr|bl|br|center", "scale": "0.05-1", "opacity": "0-1"},
    "music":         {"audio": "media url", "mode": "replace|mix", "volume": "0-2"},
    "ai_edit":       {"instruction": "string"},
}

# --------------------------------------------------------------- planning ----
def _t(s):
    """'1:30' / '90' / '1m30s' -> seconds."""
    s = str(s).strip().lower()
    m = re.match(r"^(\d+):(\d{1,2})(?::(\d{1,2}))?$", s)
    if m:
        p = [int(x) for x in m.groups() if x is not None]
        return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
    m = re.match(r"^(?:(\d+)\s*m(?:in)?)?\s*(?:(\d+(?:\.\d+)?)\s*s(?:ec)?)?$", s)
    if m and (m.group(1) or m.group(2)):
        return int(m.group(1) or 0) * 60 + float(m.group(2) or 0)
    try:
        return float(s)
    except ValueError:
        return None

TIME = r"(\d+:\d{1,2}(?::\d{1,2})?|\d+(?:\.\d+)?\s*(?:s|sec|seconds?|m|min|minutes?)?)"
GENERATIVE = (r"make it look like|in the style of|\banime\b|\bcartoon\b|cyberpunk|watercolou?r|claymation|"
              r"change the (sky|background|weather|season|colou?r of)|replace the|remove the (person|people|car|man|woman|background)|"
              r"add (a |an )?(dragon|robot|explosion|rain|snow|fire|fireworks)|turn (it|this|the video) into (a |an )?(painting|cartoon|anime|sketch)")

# Evidence an LLM-proposed op must have in the instruction text; protects against hallucinated filters.
EVIDENCE = {
    "trim": r"\d|first|last|beginning|start|end|keep|only|trim|cut|shorten|clip",
    "remove": r"\d|remove|cut out|delete|drop|skip",
    "speed": r"speed|fast|slow|quick|time-?lapse|\dx",
    "crop": r"crop|vertical|portrait|square|widescreen|landscape|\d+:\d+|tiktok|reels?|shorts|instagram|youtube|aspect",
    "resize": r"resize|scale|\d+p\b|smaller|bigger|larger|shrink|width|height|resolution",
    "rotate": r"rotat|upside|sideways|turn it", "flip": r"flip|mirror",
    "mute": r"mute|silen|no (audio|sound)|remove (the )?(audio|sound)", "volume": r"volume|loud|quiet|soft|boost|audio level",
    "fade": r"fade", "text": r"text|title|caption|words|say|write|label|overlay", "color": r"bright|dark|contrast|satur|vivid|vibrant|colou?r|light|mood|wash|pop|punch",
    "grayscale": r"black and white|gray|grey|mono|desatur|noir", "sepia": r"sepia|vintage|old|retro|warm|nostalg", "invert": r"invert|negative",
    "vignette": r"vignette|dark(ened)? edges|cinematic", "sharpen": r"sharp|crisp", "denoise": r"noise|grain|clean", "stabilize": r"stabil|shak|steady",
    "blur": r"blur|soft|dreamy", "reverse": r"reverse|backward|rewind", "loop": r"loop|repeat", "fps": r"fps|frame rate|smooth",
    "gif": r"gif", "extract_audio": r"audio|mp3|sound|music|extract", "captions": r"caption|subtitle|transcri|lyric",
    "overlay": r"overlay|watermark|logo|image|picture", "music": r"music|song|track|soundtrack|audio", "ai_edit": GENERATIVE,
}

def keyword_plan(text, extras=None):
    """Deterministic parser for the common phrasings; used as fast path and as LLM fallback."""
    low = " " + text.lower().strip() + " "
    ops, extras = [], extras or {}
    m = re.search(r"(remove|cut|delete|drop|skip|trim)(?: off| out| away)? the first " + TIME, low)
    if m: ops.append({"op": "trim", "start": _t(m.group(2))})
    m = re.search(r"(keep|only|just) the first " + TIME, low)
    if m: ops.append({"op": "trim", "end": _t(m.group(2))})
    m = re.search(r"(remove|cut|delete|drop|trim)(?: off| out)? the last " + TIME, low)
    if m: ops.append({"op": "trim", "end": -_t(m.group(2))})
    m = re.search(r"(keep|only|just) the last " + TIME, low)
    if m: ops.append({"op": "trim", "start": -_t(m.group(2))})
    m = re.search(r"(remove|cut out|delete|drop)(?: the part| the section| everything)? (?:from|between) " + TIME + r" (?:to|and|-) " + TIME, low)
    if m: ops.append({"op": "remove", "start": _t(m.group(2)), "end": _t(m.group(3))})
    else:
        m = re.search(r"(?:from|between|keep) " + TIME + r" (?:to|and|-|until) " + TIME, low)
        if m: ops.append({"op": "trim", "start": _t(m.group(1)), "end": _t(m.group(2))})
    m = re.search(r"(?:speed(?: it)? up|faster)(?: by| to)? (\d+(?:\.\d+)?)\s*x", low) or re.search(r"(\d+(?:\.\d+)?)\s*x (?:speed|faster)", low)
    if m: ops.append({"op": "speed", "factor": float(m.group(1))})
    elif re.search(r"speed(?: it)? up|faster|time-?lapse", low): ops.append({"op": "speed", "factor": 2.0})
    elif re.search(r"slow(?: it)? down|slow[- ]?mo(?:tion)?|slower", low):
        m = re.search(r"(\d+(?:\.\d+)?)\s*x slow", low)
        ops.append({"op": "speed", "factor": (1.0 / float(m.group(1))) if m else 0.5})
    if re.search(r"black and white|grayscale|greyscale|monochrome", low): ops.append({"op": "grayscale"})
    if re.search(r"\bsepia\b|vintage", low): ops.append({"op": "sepia"})
    if re.search(r"\binvert\b|negative", low): ops.append({"op": "invert"})
    if re.search(r"vignette", low): ops.append({"op": "vignette"})
    if re.search(r"sharpen|sharper|crisper", low): ops.append({"op": "sharpen"})
    if re.search(r"denoise|remove (the )?noise|grainy|less grain", low): ops.append({"op": "denoise"})
    if re.search(r"stabili[sz]e|shaky|steady", low): ops.append({"op": "stabilize"})
    m = re.search(r"\bblur(?:ry|red)?\b", low)
    if m: ops.append({"op": "blur", "amount": 6})
    if re.search(r"\bmute\b|remove (the )?(audio|sound)|no (audio|sound)|silence the", low): ops.append({"op": "mute"})
    m = re.search(r"volume (?:to |at )?(\d+)\s*%", low)
    if m: ops.append({"op": "volume", "factor": int(m.group(1)) / 100.0})
    elif re.search(r"louder|boost (the )?(audio|volume)|turn (it |the volume )?up", low): ops.append({"op": "volume", "factor": 1.6})
    elif re.search(r"quieter|softer|turn (it |the volume )?down|lower the volume", low): ops.append({"op": "volume", "factor": 0.6})
    col = {}
    if re.search(r"brighter|brighten|more light|lighter", low): col["brightness"] = 0.12
    if re.search(r"darker|darken|moodier", low): col["brightness"] = -0.12
    if re.search(r"more contrast|punchier|contrasty", low): col["contrast"] = 1.3
    if re.search(r"less contrast|flatter|softer look", low): col["contrast"] = 0.8
    if re.search(r"more (saturat|vibrant|colou?rful)|vivid|pop", low): col["saturation"] = 1.45
    if re.search(r"desaturat|less (saturat|colou?r)|muted colou?rs|washed", low): col["saturation"] = 0.6
    if col: ops.append({"op": "color", **col})
    if re.search(r"\breverse\b|backwards|rewind", low): ops.append({"op": "reverse"})
    if re.search(r"\bgif\b", low): ops.append({"op": "gif"})
    if re.search(r"vertical|portrait|9:16|tiktok|reels?|shorts|stories", low): ops.append({"op": "crop", "aspect": "9:16"})
    elif re.search(r"\bsquare\b|1:1|instagram post", low): ops.append({"op": "crop", "aspect": "1:1"})
    elif re.search(r"widescreen|16:9|landscape|youtube", low): ops.append({"op": "crop", "aspect": "16:9"})
    elif re.search(r"4:5", low): ops.append({"op": "crop", "aspect": "4:5"})
    m = re.search(r"rotate(?: it| by)? (\d+)", low)
    if m: ops.append({"op": "rotate", "degrees": int(m.group(1))})
    elif re.search(r"rotate|upside down|turn it sideways", low): ops.append({"op": "rotate", "degrees": 180 if "upside" in low else 90})
    if re.search(r"flip (it )?(horizontal|sideways)|mirror", low): ops.append({"op": "flip", "axis": "h"})
    elif re.search(r"flip (it )?(vertical|upside)", low): ops.append({"op": "flip", "axis": "v"})
    fi = 1.0 if re.search(r"fade[- ]?in", low) else 0
    fo = 1.0 if re.search(r"fade[- ]?out", low) else 0
    if not (fi or fo) and re.search(r"\bfades?\b", low): fi = fo = 1.0
    if fi or fo: ops.append({"op": "fade", "in": fi, "out": fo})
    if re.search(r"captions?|subtitles?|transcri", low): ops.append({"op": "captions"})
    m = re.search(r"(?:add|put|overlay|write)(?: the| a| some)? (?:text|title|caption|words?)[^\"'“‘]*[\"'“‘](.+?)[\"'”’]", text, flags=re.I) or \
        re.search(r"(?:text|title) (?:saying|that says|reading) [\"'“‘]?(.+?)[\"'”’]?(?:\s+(?:at|on|in) the (?:top|bottom|center|middle)|$)", text, flags=re.I)
    if m:
        pos = "top" if re.search(r"\btitle\b|at the top|on top", low) else ("center" if re.search(r"center|middle", low) else "bottom")
        ops.append({"op": "text", "text": m.group(1).strip(), "position": pos})
    if re.search(r"extract (the )?audio|audio only|as (an )?mp3|just the (audio|sound)|rip the audio", low): ops.append({"op": "extract_audio"})
    m = re.search(r"loop(?: it)? (\d+)", low)
    if m: ops.append({"op": "loop", "times": int(m.group(1))})
    elif re.search(r"\bloop\b", low): ops.append({"op": "loop", "times": 2})
    m = re.search(r"(\d{2,3})\s*fps", low)
    if m: ops.append({"op": "fps", "value": int(m.group(1))})
    m = re.search(r"(2160|1440|1080|720|480|360)p", low)
    if m: ops.append({"op": "resize", "height": int(m.group(1))})
    if re.search(r"watermark|logo|overlay (an |the |my )?(image|picture)", low) and extras.get("overlay"):
        pos = "tl" if re.search(r"top[- ]left", low) else ("bl" if re.search(r"bottom[- ]left", low) else ("tr" if re.search(r"top[- ]right", low) else "br"))
        ops.append({"op": "overlay", "image": extras["overlay"], "position": pos, "scale": 0.18, "opacity": 0.85})
    if re.search(r"music|soundtrack|background (audio|track|song)|add (the )?(audio|song)", low) and extras.get("audio"):
        ops.append({"op": "music", "audio": extras["audio"], "mode": "mix" if re.search(r"\bmix\b|under|behind|keep the (original )?(audio|sound)", low) else "replace", "volume": 0.9})
    if re.search(GENERATIVE, low) and not re.search(r"\b(gif|mp3|audio|vertical|square|widescreen|loop|slow|fast)\b", low):
        ops.append({"op": "ai_edit", "instruction": text.strip()})
    # de-dup by op name (keep last)
    seen, out = {}, []
    for o in ops:
        seen[o["op"]] = o
    for o in ops:
        if seen.get(o["op"]) is o:
            out.append(o)
    return out

def llm_plan(text, info, extras=None):
    cat = "\n".join("- %s %s" % (k, json.dumps(v) if v else "") for k, v in OPS.items())
    sysmsg = ("You convert plain-language video editing requests into a JSON plan. Use ONLY these operations "
              "(parameters in braces):\n" + cat +
              "\nRules: include an operation ONLY if the request explicitly asks for it; use the fewest operations possible. "
              "Times are seconds. 'trim' KEEPS the range start..end ('cut the first 5 seconds' = trim start 5); "
              "'remove' DELETES the range. Use 'ai_edit' only for generative changes (restyling, adding/removing objects, "
              "changing scenery). Do not invent operations.\n"
              'Examples:\n"cut the first 5 seconds and mute it" -> {"ops":[{"op":"trim","start":5},{"op":"mute"}]}\n'
              '"make it vintage looking" -> {"ops":[{"op":"sepia"},{"op":"vignette"}]}\n'
              '"speed it up 3x and add the title Hello" -> {"ops":[{"op":"speed","factor":3},{"op":"text","text":"Hello","position":"top"}]}\n'
              'Return JSON: {"ops":[{"op":"...", ...}], "summary":"one short sentence"}')
    user = ("Video: %.1f s, %dx%d, %s fps, audio: %s.%s\nRequest: %s" %
            (info.get("duration", 0), info.get("width", 0), info.get("height", 0), info.get("fps", 0),
             "yes" if info.get("has_audio") else "no",
             (" Overlay image available: %s." % extras["overlay"]) if (extras or {}).get("overlay") else "",
             text))
    out = llm.json_call(sysmsg, user, temperature=0.1, num_ctx=3072, timeout=180)
    if not out or not isinstance(out.get("ops"), list):
        return None
    return out

def _num(v, lo, hi, default=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))

def validate(plan_ops, info, extras=None):
    """Whitelist + coerce every op. Returns (ops, warnings)."""
    ops, warn = [], []
    dur = float(info.get("duration") or 0)
    for raw in plan_ops or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("op") or raw.get("name") or "").lower().strip()
        if name not in OPS:
            warn.append("ignored unknown op '%s'" % name); continue
        o = {"op": name}
        if name in ("trim", "remove"):
            s, e = raw.get("start"), raw.get("end")
            s = _t(s) if s not in (None, "") else None
            e = _t(e) if e not in (None, "") else None
            if s is not None and s < 0 and dur: s = max(0, dur + s)
            if e is not None and e < 0 and dur: e = max(0, dur + e)
            if name == "trim":
                if s is None and e is None: continue
                o["start"], o["end"] = (s or 0), e
                if e is not None and e <= o["start"]:
                    warn.append("trim range empty, skipped"); continue
            else:
                if s is None or e is None or e <= s: warn.append("remove needs start<end"); continue
                o["start"], o["end"] = s, e
        elif name == "speed":
            o["factor"] = _num(raw.get("factor"), 0.25, 8, 2.0)
        elif name == "crop":
            a = str(raw.get("aspect") or "9:16").strip()
            if a not in ("9:16", "1:1", "16:9", "4:5", "4:3", "3:4"): a = "9:16"
            o["aspect"] = a
        elif name == "resize":
            w, h = _num(raw.get("width"), 64, 4096), _num(raw.get("height"), 64, 4096)
            if not w and not h: continue
            o["width"], o["height"] = (int(w) if w else None), (int(h) if h else None)
        elif name == "rotate":
            d = int(_num(raw.get("degrees"), -360, 360, 90)) % 360
            o["degrees"] = 90 if d in (90, -270) else (180 if d == 180 else (270 if d in (270, -90) else 90))
        elif name == "flip":
            o["axis"] = "v" if str(raw.get("axis", "h")).lower().startswith("v") else "h"
        elif name == "volume":
            o["factor"] = _num(raw.get("factor"), 0, 5, 1.5)
        elif name == "fade":
            o["in"], o["out"] = _num(raw.get("in"), 0, 10, 0) or 0, _num(raw.get("out"), 0, 10, 0) or 0
            if not (o["in"] or o["out"]): o["in"] = o["out"] = 1.0
        elif name == "text":
            t = str(raw.get("text") or "").strip()[:200]
            if not t: continue
            o.update({"text": t, "position": str(raw.get("position") or "bottom").lower(),
                      "start": _num(raw.get("start"), 0, 36000, 0) or 0, "end": _num(raw.get("end"), 0, 36000, None),
                      "size": int(_num(raw.get("size"), 10, 200, 0) or 0), "color": re.sub(r"[^a-zA-Z0-9#]", "", str(raw.get("color") or "white"))[:12] or "white"})
            if o["position"] not in ("top", "center", "bottom"): o["position"] = "bottom"
        elif name == "color":
            o["brightness"] = _num(raw.get("brightness"), -1, 1, 0) or 0
            o["contrast"] = _num(raw.get("contrast"), 0, 3, 1) or 1
            o["saturation"] = _num(raw.get("saturation"), 0, 3, 1) or 1
        elif name == "blur":
            o["amount"] = int(_num(raw.get("amount"), 1, 20, 6))
        elif name == "loop":
            o["times"] = int(_num(raw.get("times"), 2, 10, 2))
        elif name == "fps":
            o["value"] = int(_num(raw.get("value"), 5, 120, 30))
        elif name == "gif":
            o["fps"], o["width"] = int(_num(raw.get("fps"), 5, 30, 12)), int(_num(raw.get("width"), 120, 1080, 480))
        elif name == "overlay":
            img = media.path_for(raw.get("image") or (extras or {}).get("overlay"))
            if not img: warn.append("overlay needs an image from the media library"); continue
            o.update({"image": img, "position": str(raw.get("position") or "br").lower(),
                      "scale": _num(raw.get("scale"), 0.05, 1, 0.18), "opacity": _num(raw.get("opacity"), 0, 1, 0.85)})
        elif name == "music":
            aud = media.path_for(raw.get("audio") or (extras or {}).get("audio"))
            if not aud: warn.append("music needs an audio/video file from the media library"); continue
            o.update({"audio": aud, "mode": "mix" if str(raw.get("mode", "replace")).lower() == "mix" else "replace",
                      "volume": _num(raw.get("volume"), 0, 2, 0.9)})
        elif name == "ai_edit":
            o["instruction"] = str(raw.get("instruction") or "").strip()[:800]
            if not o["instruction"]: continue
            if not settings.configured("runway"):
                warn.append("generative edit skipped: add a Runway key in Integrations to restyle / add / remove things"); continue
        ops.append(o)
    if any(o["op"] == "reverse" for o in ops) and dur > 120:
        ops = [o for o in ops if o["op"] != "reverse"]; warn.append("reverse is limited to clips under 2 minutes")
    return ops, warn

def plan(source_path, instruction, extras=None, use_llm=True):
    info = media.probe(source_path)
    low = (instruction or "").lower()
    ops, warn = validate(keyword_plan(instruction, extras), info, extras)   # deterministic parse is the backbone
    summary = ""
    if use_llm and instruction.strip():
        out = llm_plan(instruction, info, extras)
        if out and out.get("ops"):
            summary = str(out.get("summary") or "")[:200]
            have = {o["op"] for o in ops}
            extra = []
            for o in out["ops"]:
                if not isinstance(o, dict):
                    continue
                name = str(o.get("op") or "").lower()
                if name in have or name not in OPS:
                    continue
                if not re.search(EVIDENCE.get(name, r"$^"), low):
                    warn.append("dropped '%s' (not asked for)" % name); continue
                extra.append(o)
            vext, w2 = validate(extra, info, extras)
            ops += vext; warn += w2
    return {"ops": ops, "warnings": warn, "summary": summary, "info": info}

# --------------------------------------------------------------- execute ----
def _fontfile():
    return media.font_file() or None

def _esc_path(p):
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")

def _tempo_chain(f):
    parts = []
    while f > 2.0:
        parts.append("atempo=2.0"); f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5"); f *= 2.0
    parts.append("atempo=%.4f" % f)
    return parts

def _even(x):
    x = int(round(x)); return x if x % 2 == 0 else x - 1

def transcribe_srt(src, workdir, progress=None):
    cli, model = media.whisper_cli(), media.whisper_model()
    if not (cli and model):
        raise RuntimeError("whisper.cpp is not installed, captions unavailable")
    wav = os.path.join(workdir, "cap.wav"); base = os.path.join(workdir, "cap")
    if progress: progress("captions: extracting audio")
    media.run_ffmpeg(["-i", src, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav], timeout=600)
    if progress: progress("captions: transcribing (whisper.cpp)")
    subprocess.run([cli, "-m", model, "-f", wav, "-osrt", "-of", base, "-np"],
                   capture_output=True, timeout=1800, cwd=os.path.dirname(cli), **media._no_window())
    srt = base + ".srt"
    if not os.path.isfile(srt) or os.path.getsize(srt) < 10:
        raise RuntimeError("no speech found to caption")
    return srt

def apply(source_path, ops, progress=lambda m: None, workdir=None):
    """Run the validated ops on source_path; returns dict with url/info/output kind."""
    info = media.probe(source_path)
    if not info.get("width") and not any(o["op"] == "extract_audio" for o in ops):
        raise RuntimeError("could not read the video (unsupported file?)")
    workdir = workdir or tempfile.mkdtemp(prefix="aixmos_edit_", dir=os.path.join(media.MEDIA, "tmp"))
    os.makedirs(workdir, exist_ok=True)
    names = [o["op"] for o in ops]
    ai = next((o for o in ops if o["op"] == "ai_edit"), None)
    src = source_path
    if ai:
        progress("ai edit: sending to Runway")
        src = _runway_aleph(src, ai["instruction"], workdir, progress)
        ops = [o for o in ops if o["op"] != "ai_edit"]
        info = media.probe(src)
        if not ops:
            return _finish(src, "mp4", info)
    out_kind = "gif" if "gif" in names else ("mp3" if "extract_audio" in names else "mp4")
    mute = "mute" in names or out_kind == "gif"
    has_audio = bool(info.get("has_audio")) and not mute
    warnings = []
    dur = float(info.get("duration") or 0)
    W, H = int(info.get("width") or 0), int(info.get("height") or 0)
    pre_in = []
    inputs = ["-i", src]
    vchain, achain = [], []
    extra_inputs = 0
    # --- segment stage
    seg_v, seg_a = "[0:v]", "[0:a]"
    graph = []
    trims = [o for o in ops if o["op"] == "trim"]
    removes = [o for o in ops if o["op"] == "remove"]
    if trims:
        t = trims[-1]; s, e = float(t.get("start") or 0), t.get("end")
        rng = "start=%.3f" % s + (":end=%.3f" % float(e) if e is not None else "")
        graph.append("%strim=%s,setpts=PTS-STARTPTS[vseg]" % (seg_v, rng)); seg_v = "[vseg]"
        if has_audio:
            graph.append("%satrim=%s,asetpts=PTS-STARTPTS[aseg]" % (seg_a, rng)); seg_a = "[aseg]"
        dur = (float(e) if e is not None else dur) - s
    elif removes:
        r = removes[-1]; s, e = float(r["start"]), float(r["end"])
        graph.append("[0:v]trim=end=%.3f,setpts=PTS-STARTPTS[v0];[0:v]trim=start=%.3f,setpts=PTS-STARTPTS[v1];[v0][v1]concat=n=2:v=1:a=0[vseg]" % (s, e))
        seg_v = "[vseg]"
        if has_audio:
            graph.append("[0:a]atrim=end=%.3f,asetpts=PTS-STARTPTS[a0];[0:a]atrim=start=%.3f,asetpts=PTS-STARTPTS[a1];[a0][a1]concat=n=2:v=0:a=1[aseg]" % (s, e))
            seg_a = "[aseg]"
        dur = max(0.1, dur - (e - s))
    # --- linear filters
    for o in ops:
        k = o["op"]
        if k == "speed":
            f = float(o["factor"]); vchain.append("setpts=PTS/%.4f" % f); achain += _tempo_chain(f); dur = dur / f if f else dur
        elif k == "crop" and W and H:
            a, b = [int(x) for x in o["aspect"].split(":")]
            tw, th = min(W, int(H * a / b)), min(H, int(W * b / a))
            tw, th = _even(tw), _even(th)
            vchain.append("crop=%d:%d:(iw-%d)/2:(ih-%d)/2" % (tw, th, tw, th)); W, H = tw, th
        elif k == "resize":
            w, h = o.get("width"), o.get("height")
            vchain.append("scale=%s:%s" % (_even(w) if w else -2, _even(h) if h else -2))
        elif k == "rotate":
            d = o["degrees"]
            vchain.append({"90": "transpose=1", "180": "hflip,vflip", "270": "transpose=2"}[str(d)])
            if d in (90, 270): W, H = H, W
        elif k == "flip":
            vchain.append("hflip" if o["axis"] == "h" else "vflip")
        elif k == "volume" and has_audio:
            achain.append("volume=%.3f" % float(o["factor"]))
        elif k == "color":
            vchain.append("eq=brightness=%.3f:contrast=%.3f:saturation=%.3f" % (o["brightness"], o["contrast"], o["saturation"]))
        elif k == "grayscale": vchain.append("hue=s=0")
        elif k == "sepia": vchain.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif k == "invert": vchain.append("negate")
        elif k == "vignette": vchain.append("vignette")
        elif k == "sharpen": vchain.append("unsharp=5:5:1.0:5:5:0.0")
        elif k == "denoise": vchain.append("hqdn3d")
        elif k == "stabilize": vchain.append("deshake")
        elif k == "blur": vchain.append("boxblur=%d" % o["amount"])
        elif k == "reverse":
            vchain.append("reverse")
            if has_audio: achain.append("areverse")
        elif k == "loop":
            pre_in = ["-stream_loop", str(o["times"] - 1)]; dur *= o["times"]
        elif k == "fps": vchain.append("fps=%d" % o["value"])
        elif k == "text":
            tf = os.path.join(workdir, "text_%d.txt" % len(vchain))
            with open(tf, "w", encoding="utf-8") as f:
                f.write(o["text"])
            size = o.get("size") or max(24, int((H or 720) / 18))
            y = {"top": "h*0.06", "center": "(h-text_h)/2", "bottom": "h-text_h-h*0.06"}[o["position"]]
            ff = _fontfile()
            dt = "drawtext=textfile='%s':fontsize=%d:fontcolor=%s:borderw=2:bordercolor=black@0.8:x=(w-text_w)/2:y=%s" % (
                _esc_path(tf), size, o["color"], y)
            if ff: dt += ":fontfile='%s'" % _esc_path(ff)
            if o.get("end") is not None or o.get("start"):
                dt += ":enable='between(t,%.2f,%.2f)'" % (o.get("start") or 0, o["end"] if o.get("end") is not None else 1e6)
            vchain.append(dt)
        elif k == "captions":
            try:
                srt = transcribe_srt(src, workdir, progress)
                vchain.append("subtitles='%s':force_style='FontSize=18,Outline=1,Shadow=0,MarginV=28,PrimaryColour=&H00FFFFFF&'" % _esc_path(srt))
            except Exception as e:
                warnings.append("captions skipped: %s" % (str(e) or "transcription failed"))
        elif k == "overlay":
            extra_inputs += 1; inputs += ["-i", o["image"]]
            idx = extra_inputs
            pos = {"tl": "20:20", "tr": "W-w-20:20", "bl": "20:H-h-20", "br": "W-w-20:H-h-20", "center": "(W-w)/2:(H-h)/2"}.get(o["position"], "W-w-20:H-h-20")
            graph.append("[%d:v]scale=%d:-1,format=rgba,colorchannelmixer=aa=%.2f[wm%d]" % (idx, max(16, int((W or 1280) * o["scale"])), o["opacity"], idx))
            o["_wm"] = "[wm%d]" % idx; o["_pos"] = pos; o["_idx"] = idx
        elif k == "music":
            extra_inputs += 1; idx = extra_inputs
            inputs += ["-stream_loop", "-1", "-i", o["audio"]]
            o["_idx"] = idx
    # --- fade last (needs final duration)
    for o in ops:
        if o["op"] == "fade":
            if o["in"]: vchain.append("fade=t=in:st=0:d=%.2f" % o["in"])
            if o["out"] and dur: vchain.append("fade=t=out:st=%.2f:d=%.2f" % (max(0, dur - o["out"]), o["out"]))
            if has_audio:
                if o["in"]: achain.append("afade=t=in:st=0:d=%.2f" % o["in"])
                if o["out"] and dur: achain.append("afade=t=out:st=%.2f:d=%.2f" % (max(0, dur - o["out"]), o["out"]))
    # --- assemble video graph (skipped entirely for audio-only output)
    vf = ",".join(vchain) if vchain else "null"
    cur = "[vmain]"
    if out_kind == "mp3":
        graph = [g for g in graph if not g.startswith("[0:v]")]
    else:
        graph.append("%s%s%s" % (seg_v, vf, cur))
    for o in ops:
        if o["op"] == "overlay" and o.get("_wm"):
            graph.append("%s%soverlay=%s[vov%d]" % (cur, o["_wm"], o["_pos"], o["_idx"]))
            cur = "[vov%d]" % o["_idx"]
    if out_kind == "gif":
        g = next(o for o in ops if o["op"] == "gif")
        graph.append("%sfps=%d,scale=%d:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5[vout]" % (cur, g["fps"], g["width"]))
        cur = "[vout]"
    # --- assemble audio graph
    music = next((o for o in ops if o["op"] == "music"), None)
    acur = None
    if not mute:
        if music and music["mode"] == "replace":
            graph.append("[%d:a]volume=%.2f[aout]" % (music["_idx"], music["volume"])); acur = "[aout]"
        elif has_audio:
            af = ",".join(achain) if achain else "anull"
            graph.append("%s%s[amain]" % (seg_a, af)); acur = "[amain]"
            if music:
                graph.append("[%d:a]volume=%.2f[mus];[amain][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]" % (music["_idx"], music["volume"])); acur = "[aout]"
        elif music:
            graph.append("[%d:a]volume=%.2f[aout]" % (music["_idx"], music["volume"])); acur = "[aout]"
    # --- output
    ext = {"gif": ".gif", "mp3": ".mp3", "mp4": ".mp4"}[out_kind]
    out = os.path.join(workdir, "out" + ext)
    args = pre_in + inputs + ["-filter_complex", ";".join(graph)]
    if out_kind == "mp3":
        if not acur: raise RuntimeError("this video has no audio track to extract")
        args += ["-map", acur, "-c:a", "libmp3lame", "-q:a", "2", out]
    elif out_kind == "gif":
        args += ["-map", cur, "-loop", "0", out]
    else:
        args += ["-map", cur]
        if acur: args += ["-map", acur, "-c:a", "aac", "-b:a", "160k"]
        args += ["-c:v", "libx264", "-preset", "superfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                 "-threads", str(int(settings.pref("llm_threads") or 3))]
        if music or pre_in: args += ["-shortest"]
        args += [out]
    progress("ffmpeg: rendering (%s)" % ", ".join(names))
    media.run_ffmpeg(args, timeout=3600)
    res = _finish(out, out_kind, None)
    res["warnings"] = warnings
    return res

def _finish(path, kind, info):
    with open(path, "rb") as f:
        data = f.read()
    ext = {"gif": ".gif", "mp3": ".mp3"}.get(kind, ".mp4")
    folder = "audio" if kind == "mp3" else "videos"
    p, url = media.save_bytes(folder, ext, data)
    return {"url": url, "kind": kind, "info": info or media.probe(p), "size": len(data)}

def _runway_aleph(src, instruction, workdir, progress):
    import requests
    if not settings.configured("runway"):
        raise RuntimeError("generative video edits need a Runway API key (Integrations panel)")
    if os.path.getsize(src) > 15 * 1024 * 1024:
        progress("ai edit: compressing source for upload")
        small = os.path.join(workdir, "small.mp4")
        media.run_ffmpeg(["-i", src, "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-t", "10", small], timeout=1800)
        src = small
    with open(src, "rb") as f:
        uri = "data:video/mp4;base64," + base64.b64encode(f.read()).decode()
    hdr = {"Authorization": "Bearer " + settings.get("runway", "api_key"), "X-Runway-Version": "2024-11-06", "Content-Type": "application/json"}
    info = media.probe(src)
    ratio = "720:1280" if info.get("height", 0) > info.get("width", 0) else "1280:720"
    r = requests.post("https://api.dev.runwayml.com/v1/video_to_video", headers=hdr,
                      json={"model": settings.get("runway", "edit_model"), "videoUri": uri, "promptText": instruction, "ratio": ratio}, timeout=180)
    if r.status_code >= 400:
        raise RuntimeError("Runway: " + imagegen_apierr(r))
    from . import videogen
    data = videogen._runway_wait(r.json()["id"], hdr, progress)
    out = os.path.join(workdir, "aleph.mp4")
    with open(out, "wb") as f:
        f.write(data)
    return out

def imagegen_apierr(r):
    from . import imagegen
    return imagegen._apierr(r)

def edit(source_url, instruction, extras=None, ops=None, use_llm=True, on_done=None):
    """Start an edit job. If `ops` is given (user-approved plan) it is used instead of re-planning."""
    src = media.path_for(source_url)
    if not src:
        raise ValueError("source video not found in the media library")
    instruction = (instruction or "").strip()
    def run(progress):
        progress("planning")
        if ops:
            plan_ops, warn, summary = validate(ops, media.probe(src), extras)[0], [], ""
        else:
            p = plan(src, instruction, extras, use_llm=use_llm)
            plan_ops, warn, summary = p["ops"], p["warnings"], p["summary"]
        if not plan_ops:
            raise RuntimeError("I could not map that request to any edit. Try e.g. 'trim the first 5 seconds', "
                               "'make it vertical', 'add captions', 'speed up 2x', 'add text \"Hello\" at the top'.")
        res = apply(src, plan_ops, progress)
        res.update({"ops": plan_ops, "warnings": warn + (res.get("warnings") or []), "summary": summary,
                    "source": source_url, "instruction": instruction})
        return res
    return jobs.create("edit", run, {"source": source_url, "instruction": instruction}, on_done=on_done)
