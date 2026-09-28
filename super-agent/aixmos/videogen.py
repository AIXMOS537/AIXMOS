"""
videogen.py -- text/image -> video across providers, run as background jobs.

Providers: Replicate, fal.ai, Runway, Luma, Google Veo (Gemini API), OpenAI Sora, and a
zero-key LOCAL storyboard fallback (scene prompts -> images -> Ken Burns motion -> mp4 via ffmpeg)
so video generation always works on this machine even with no API keys.
"""
import os, json, time, base64, re, threading
from . import settings, media, llm, jobs, imagegen

LOG_FILE = os.path.join(settings.MEMDIR, "video_log.json")
_LOCK = threading.Lock()
POLL = 5
MAX_WAIT = 20 * 60

def _log(item):
    with _LOCK:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)
        except (OSError, ValueError):
            items = []
        items.append(item)
        items = items[-200:]
        os.makedirs(settings.MEMDIR, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)

def list_items(limit=40):
    with _LOCK:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)
        except (OSError, ValueError):
            items = []
    return [i for i in reversed(items[-limit:]) if media.path_for(i.get("url"))]

def _data_uri(path):
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (media.mime_for(path), base64.b64encode(f.read()).decode())

def _apierr(r):
    return imagegen._apierr(r)

def _dims(aspect):
    return (720, 1280) if aspect == "9:16" else ((1024, 1024) if aspect == "1:1" else (1280, 720))

# ------------------------------------------------------------ providers ----
def _p_replicate(prompt, model, image, secs, aspect, progress):
    import requests
    key = settings.get("replicate", "api_key")
    inp = {"prompt": prompt}
    if image:
        inp["first_frame_image"] = _data_uri(image)
        inp["image"] = inp["first_frame_image"]
    if aspect:
        inp["aspect_ratio"] = aspect
    r = requests.post("https://api.replicate.com/v1/models/%s/predictions" % model,
                      headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                      json={"input": inp}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Replicate: " + _apierr(r))
    pred = r.json(); t0 = time.time()
    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() - t0 > MAX_WAIT:
            raise RuntimeError("Replicate: timed out")
        progress("replicate: " + pred.get("status", "?"))
        time.sleep(POLL)
        pred = requests.get(pred["urls"]["get"], headers={"Authorization": "Bearer " + key}, timeout=60).json()
    if pred.get("status") != "succeeded":
        raise RuntimeError("Replicate: " + str(pred.get("error") or pred.get("status")))
    out = pred.get("output")
    return media.download(out[0] if isinstance(out, list) else out, timeout=600)

def _p_fal(prompt, model, image, secs, aspect, progress):
    import requests
    key = settings.get("fal", "api_key"); hdr = {"Authorization": "Key " + key}
    body = {"prompt": prompt}
    if image:
        body["image_url"] = _data_uri(image)
    if aspect:
        body["aspect_ratio"] = aspect
    r = requests.post("https://queue.fal.run/" + model, headers=hdr, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("fal: " + _apierr(r))
    q = r.json(); t0 = time.time()
    while True:
        s = requests.get(q["status_url"], headers=hdr, timeout=60).json()
        if s.get("status") == "COMPLETED":
            break
        if time.time() - t0 > MAX_WAIT:
            raise RuntimeError("fal: timed out")
        progress("fal: " + str(s.get("status", "?")).lower() + (" (queue %s)" % s["queue_position"] if s.get("queue_position") is not None else ""))
        time.sleep(POLL)
    res = requests.get(q["response_url"], headers=hdr, timeout=60).json()
    url = (res.get("video") or {}).get("url") or next((v for v in _urls(res) if ".mp4" in v), None)
    if not url:
        raise RuntimeError("fal: no video in response")
    return media.download(url, timeout=600)

def _urls(obj):
    if isinstance(obj, str):
        return [obj] if obj.startswith("http") else []
    if isinstance(obj, dict):
        return [u for v in obj.values() for u in _urls(v)]
    if isinstance(obj, list):
        return [u for v in obj for u in _urls(v)]
    return []

def _p_runway(prompt, model, image, secs, aspect, progress):
    import requests
    key = settings.get("runway", "api_key")
    hdr = {"Authorization": "Bearer " + key, "X-Runway-Version": "2024-11-06", "Content-Type": "application/json"}
    ratio = "720:1280" if aspect == "9:16" else ("960:960" if aspect == "1:1" else "1280:720")
    if not image:
        progress("runway: generating a first frame")
        img = imagegen.generate(prompt, enhance=False, note="first frame for video", allow_fallback=True)
        image = media.path_for(img["url"])
    body = {"model": model, "promptImage": _data_uri(image), "promptText": prompt[:1000], "ratio": ratio,
            "duration": 10 if int(secs or 5) > 7 else 5}
    r = requests.post("https://api.dev.runwayml.com/v1/image_to_video", headers=hdr, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Runway: " + _apierr(r))
    return _runway_wait(r.json()["id"], hdr, progress)

def _runway_wait(tid, hdr, progress):
    import requests
    t0 = time.time()
    while True:
        t = requests.get("https://api.dev.runwayml.com/v1/tasks/" + tid, headers=hdr, timeout=60).json()
        st = t.get("status")
        if st == "SUCCEEDED":
            return media.download(t["output"][0], timeout=600)
        if st in ("FAILED", "CANCELLED"):
            raise RuntimeError("Runway: " + str(t.get("failure") or st))
        if time.time() - t0 > MAX_WAIT:
            raise RuntimeError("Runway: timed out")
        progress("runway: " + str(st).lower() + (" %d%%" % int(float(t.get("progress", 0)) * 100) if t.get("progress") else ""))
        time.sleep(POLL)

def _p_luma(prompt, model, image, secs, aspect, progress):
    import requests
    key = settings.get("luma", "api_key")
    hdr = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    body = {"prompt": prompt, "model": model, "aspect_ratio": aspect or "16:9", "duration": ("9s" if int(secs or 5) > 6 else "5s")}
    r = requests.post("https://api.lumalabs.ai/dream-machine/v1/generations", headers=hdr, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Luma: " + _apierr(r))
    gid = r.json()["id"]; t0 = time.time()
    while True:
        g = requests.get("https://api.lumalabs.ai/dream-machine/v1/generations/" + gid, headers=hdr, timeout=60).json()
        if g.get("state") == "completed":
            return media.download(g["assets"]["video"], timeout=600)
        if g.get("state") == "failed":
            raise RuntimeError("Luma: " + str(g.get("failure_reason") or "failed"))
        if time.time() - t0 > MAX_WAIT:
            raise RuntimeError("Luma: timed out")
        progress("luma: " + str(g.get("state")))
        time.sleep(POLL)

def _p_gemini(prompt, model, image, secs, aspect, progress):
    import requests
    key = settings.get("gemini", "api_key")
    hdr = {"x-goog-api-key": key, "Content-Type": "application/json"}
    inst = {"prompt": prompt}
    if image:
        with open(image, "rb") as f:
            inst["image"] = {"bytesBase64Encoded": base64.b64encode(f.read()).decode(), "mimeType": media.mime_for(image)}
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:predictLongRunning" % model,
                      headers=hdr, json={"instances": [inst], "parameters": {"aspectRatio": aspect or "16:9"}}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Google Veo: " + _apierr(r))
    name = r.json()["name"]; t0 = time.time()
    while True:
        op = requests.get("https://generativelanguage.googleapis.com/v1beta/" + name, headers=hdr, timeout=60).json()
        if op.get("done"):
            if op.get("error"):
                raise RuntimeError("Google Veo: " + str(op["error"].get("message")))
            resp = op.get("response") or {}
            samples = (resp.get("generateVideoResponse") or resp).get("generatedSamples") or []
            uri = samples[0]["video"]["uri"] if samples else None
            if not uri:
                raise RuntimeError("Google Veo: no video returned (may be filtered)")
            return media.download(uri, timeout=600, headers={"x-goog-api-key": key})
        if time.time() - t0 > MAX_WAIT:
            raise RuntimeError("Google Veo: timed out")
        progress("veo: rendering"); time.sleep(POLL)

def _p_openai(prompt, model, image, secs, aspect, progress):
    import requests
    key = settings.get("openai", "api_key"); hdr = {"Authorization": "Bearer " + key}
    seconds = "12" if int(secs or 5) > 10 else ("8" if int(secs or 5) > 5 else "4")
    size = "720x1280" if aspect == "9:16" else "1280x720"
    if image:
        with open(image, "rb") as f:
            r = requests.post("https://api.openai.com/v1/videos", headers=hdr,
                              data={"model": model, "prompt": prompt, "seconds": seconds, "size": size},
                              files={"input_reference": (os.path.basename(image), f, media.mime_for(image))}, timeout=120)
    else:
        r = requests.post("https://api.openai.com/v1/videos", headers=hdr,
                          json={"model": model, "prompt": prompt, "seconds": seconds, "size": size}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("OpenAI Sora: " + _apierr(r))
    vid = r.json()["id"]; t0 = time.time()
    while True:
        v = requests.get("https://api.openai.com/v1/videos/" + vid, headers=hdr, timeout=60).json()
        st = v.get("status")
        if st == "completed":
            c = requests.get("https://api.openai.com/v1/videos/%s/content" % vid, headers=hdr, timeout=600)
            c.raise_for_status()
            return c.content
        if st in ("failed", "cancelled"):
            raise RuntimeError("OpenAI Sora: " + str((v.get("error") or {}).get("message") or st))
        if time.time() - t0 > MAX_WAIT:
            raise RuntimeError("OpenAI Sora: timed out")
        progress("sora: %s %s%%" % (st, v.get("progress", 0))); time.sleep(POLL)

# ------------------------------------------------- local storyboard --------
def _scenes(prompt, n):
    out = llm.json_call(
        "You are a storyboard artist. Split the video idea into %d consecutive shots. Each shot is a self-contained "
        "text-to-image prompt (max 40 words) describing what the camera sees: subject, setting, lighting, mood, "
        'camera angle. Keep characters and style consistent across shots. Return JSON: {"scenes": ["...", "..."]}' % n,
        "Video idea: " + prompt, temperature=0.6, num_ctx=2048, timeout=150)
    scenes = [re.sub(r"^[\s{\[\"'(]+|[\s}\]\"')]+$", "", s) for s in ((out or {}).get("scenes") or []) if isinstance(s, str)]
    scenes = [s for s in scenes if len(s) > 8][:n]
    if len(scenes) < 2:
        angles = ["wide establishing shot", "medium shot, cinematic lighting", "close-up detail, shallow depth of field",
                  "dramatic low angle", "golden hour, final reveal", "aerial view"]
        scenes = ["%s, %s" % (prompt, angles[i % len(angles)]) for i in range(n)]
    return scenes

def _local_storyboard(prompt, image, secs, aspect, progress, nscenes=None):
    W, H = _dims(aspect)
    per = 4.0
    n = nscenes or max(2, min(6, int(round(float(secs or 12) / per))))
    scenes = _scenes(prompt, n)
    frames = []
    if image:
        frames.append(image)
    for i, s in enumerate(scenes):
        if len(frames) >= n:
            break
        progress("storyboard: image %d/%d" % (len(frames) + 1, n))
        it = imagegen.generate(s, enhance=False, size="%dx%d" % ((1280, 720) if W >= H else (720, 1280)),
                               note="storyboard shot for: " + prompt[:80], allow_fallback=True)
        frames.append(media.path_for(it["url"]))
    tmp = os.path.join(media.MEDIA, "tmp"); os.makedirs(tmp, exist_ok=True)
    clips = []
    fps, nf = 25, int(per * 25)
    for i, fpath in enumerate(frames):
        progress("storyboard: rendering motion %d/%d" % (i + 1, len(frames)))
        zoom = ("min(zoom+0.0012,1.35)" if i % 2 == 0 else "if(eq(on,1),1.35,max(zoom-0.0012,1.0))")
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
              "zoompan=z='%s':d=%d:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=%dx%d:fps=%d,"
              "fade=t=in:st=0:d=0.4,fade=t=out:st=%.1f:d=0.4,format=yuv420p"
              % (W * 3 // 2, H * 3 // 2, W * 3 // 2, H * 3 // 2, zoom, nf, W, H, fps, per - 0.4))
        clip = os.path.join(tmp, "sb_%s_%d.mp4" % (media.new_id(), i))
        media.run_ffmpeg(["-i", fpath, "-vf", vf, "-frames:v", nf, "-r", fps, "-c:v", "libx264", "-preset", "superfast", "-threads", str(int(settings.pref("llm_threads") or 3)),
                          "-crf", "24", "-an", clip], timeout=900)
        clips.append(clip)
    lst = os.path.join(tmp, "sb_%s.txt" % media.new_id())
    with open(lst, "w", encoding="utf-8") as f:
        for c in clips:
            f.write("file '%s'\n" % c.replace("\\", "/").replace("'", "'\\''"))
    out = os.path.join(tmp, "sb_out_%s.mp4" % media.new_id())
    progress("storyboard: assembling")
    media.run_ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out], timeout=600)
    with open(out, "rb") as f:
        data = f.read()
    for p in clips + [lst, out]:
        try: os.remove(p)
        except OSError: pass
    return data, scenes

PROVIDER_FNS = {"replicate": _p_replicate, "fal": _p_fal, "runway": _p_runway, "luma": _p_luma,
                "gemini": _p_gemini, "openai": _p_openai}

def choose_provider(requested=None):
    if requested == "local":
        return "local"
    if requested and requested != "auto" and settings.configured(requested) and requested in PROVIDER_FNS:
        return requested
    p = settings.pref("video_provider")
    if p == "local":
        return "local"
    if p and p != "auto" and settings.configured(p) and p in PROVIDER_FNS:
        return p
    for cand in settings.providers_for("video"):
        if cand in PROVIDER_FNS:
            return cand
    return "local"

def generate(prompt, provider=None, model=None, image_url=None, seconds=None, aspect=None, on_done=None):
    prompt = (prompt or "").strip()
    if not prompt and not image_url:
        raise ValueError("empty prompt")
    prov = choose_provider(provider)
    aspect = aspect or settings.pref("video_aspect") or "16:9"
    seconds = int(seconds or settings.pref("video_seconds") or 5)
    image = media.path_for(image_url) if image_url else None
    mdl = model or (settings.get(prov, "video_model") if prov != "local" else "storyboard")

    def run(progress):
        progress("%s: submitting" % prov)
        used, used_model, scenes, warning = prov, mdl, None, ""
        if prov == "local":
            data, scenes = _local_storyboard(prompt or "the image", image, seconds, aspect, progress)
        else:
            try:
                data = PROVIDER_FNS[prov](prompt, mdl, image, seconds, aspect, progress)
            except Exception as e:
                if provider and provider not in ("auto", "local"):
                    raise            # the user picked this provider explicitly: surface the real error
                progress("%s failed (%s) -> local storyboard fallback" % (prov, str(e)[:120]))
                data, scenes = _local_storyboard(prompt or "the image", image, seconds, aspect, progress)
                used, used_model, warning = "local", "storyboard", "%s failed: %s" % (prov, str(e)[:160])
        path, url = media.save_bytes("videos", ".mp4", data)
        item = {"id": os.path.splitext(os.path.basename(path))[0], "prompt": prompt, "provider": used, "model": used_model,
                "url": url, "image_url": image_url, "ts": time.time(), "info": media.probe(path), "scenes": scenes,
                "warning": warning}
        _log(item)
        return item
    return jobs.create("video", run, {"prompt": prompt, "provider": prov, "model": mdl}, on_done=on_done)
