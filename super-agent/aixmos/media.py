"""media.py -- on-disk media store (memory/media/...), ffmpeg/ffprobe discovery and helpers."""
import os, glob, json, uuid, shutil, subprocess, time
from . import settings

MEDIA = os.path.join(settings.MEMDIR, "media")
KINDS = ("images", "videos", "uploads", "audio", "tmp")
EXT_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
            ".gif": "image/gif", ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
            ".mkv": "video/x-matroska", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
            ".srt": "text/plain", ".txt": "text/plain"}

def ensure_dirs():
    for k in KINDS:
        os.makedirs(os.path.join(MEDIA, k), exist_ok=True)

def new_id():
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

def save_bytes(kind, ext, data, stem=None):
    ensure_dirs()
    ext = ext if ext.startswith(".") else "." + ext
    name = (stem or new_id()) + ext.lower()
    path = os.path.join(MEDIA, kind, name)
    with open(path, "wb") as f:
        f.write(data)
    return path, "/media/%s/%s" % (kind, name)

def url_for(path):
    rel = os.path.relpath(path, MEDIA).replace("\\", "/")
    return "/media/" + rel

def path_for(url):
    """Resolve a /media/... url (or absolute media path) to a safe file path, or None."""
    if not url:
        return None
    if os.path.isabs(url):
        full = os.path.abspath(url)
        return full if full.startswith(os.path.abspath(MEDIA)) and os.path.isfile(full) else None
    if not url.startswith("/media/"):
        return None
    rel = url[len("/media/"):].split("?")[0]
    full = os.path.abspath(os.path.join(MEDIA, *rel.split("/")))
    if not full.startswith(os.path.abspath(MEDIA)) or not os.path.isfile(full):
        return None
    return full

def mime_for(path):
    return EXT_MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")

def download(url, timeout=180, headers=None):
    import requests
    r = requests.get(url, timeout=timeout, headers=headers or {})
    r.raise_for_status()
    return r.content

# ---- ffmpeg discovery ------------------------------------------------------
_FF = {}
def _find(tool):
    if tool in _FF:
        return _FF[tool]
    p = shutil.which(tool)
    if not p:
        # The server may be started by a scheduled task with a stripped environment, so look in
        # every place winget / manual installs put ffmpeg, for every user profile on the box.
        roots = [os.environ.get("LOCALAPPDATA", ""), os.path.join(os.path.expanduser("~"), "AppData", "Local")]
        roots += glob.glob(os.path.join("C:\\", "Users", "*", "AppData", "Local"))
        cands = [os.path.join(settings.ROOT, "bin", tool + ".exe")]
        for local in [r for r in roots if r]:
            cands.append(os.path.join(local, "Microsoft", "WinGet", "Links", tool + ".exe"))
            cands += glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", tool + ".exe"))
        cands += glob.glob(os.path.join("C:\\", "ffmpeg", "bin", tool + ".exe"))
        cands += glob.glob(os.path.join("C:\\", "Program Files", "ffmpeg", "bin", tool + ".exe"))
        cands += glob.glob(os.path.join("C:\\", "Program Files", "*", "ffmpeg*", "bin", tool + ".exe"))
        for c in cands:
            if os.path.isfile(c):
                p = c
                break
    _FF[tool] = p
    return p

def ffmpeg():  return _find("ffmpeg")
def ffprobe(): return _find("ffprobe")

def _no_window():
    if os.name == "nt":
        si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si, "creationflags": 0x08000000}
    return {}

def run_ffmpeg(args, timeout=1800):
    exe = ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg not found (install with: winget install Gyan.FFmpeg)")
    proc = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y"] + [str(a) for a in args],
                          capture_output=True, timeout=timeout, **_no_window())
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + proc.stderr.decode("utf-8", "replace")[-800:])
    return proc

def probe(path):
    exe = ffprobe()
    if not exe or not path:
        return {}
    try:
        proc = subprocess.run([exe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                              capture_output=True, timeout=60, **_no_window())
        d = json.loads(proc.stdout or b"{}")
    except Exception:
        return {}
    info = {"duration": float((d.get("format") or {}).get("duration") or 0), "has_audio": False,
            "width": 0, "height": 0, "fps": 0}
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and not info["width"]:
            info["width"], info["height"] = int(s.get("width") or 0), int(s.get("height") or 0)
            try:
                n, m = s.get("r_frame_rate", "0/1").split("/")
                info["fps"] = round(float(n) / float(m), 2) if float(m) else 0
            except Exception:
                pass
        if s.get("codec_type") == "audio":
            info["has_audio"] = True
    return info

def tools_status():
    return {"ffmpeg": bool(ffmpeg()), "ffprobe": bool(ffprobe()), "ffmpeg_path": ffmpeg() or ""}

# ---- cross-platform helpers (Windows bundle, macOS/Linux installs) ---------
def whisper_cli():
    """Bundled whisper-cli.exe on Windows, otherwise whisper.cpp from PATH (brew install whisper-cpp)."""
    bundled = os.path.join(settings.ROOT, "whisper", "bin", "Release", "whisper-cli.exe")
    if os.path.isfile(bundled):
        return bundled
    for name in ("whisper-cli", "whisper-cpp", "whisper"):
        p = shutil.which(name)
        if p:
            return p
    return ""

def whisper_model():
    for p in (os.path.join(settings.ROOT, "whisper", "models", "ggml-base.en.bin"),
              os.path.join(os.path.expanduser("~"), "AIXMOS", "whisper", "models", "ggml-base.en.bin"),
              os.path.join(os.path.expanduser("~"), ".cache", "whisper", "ggml-base.en.bin")):
        if os.path.isfile(p):
            return p
    return ""

def whisper_ok():
    return bool(whisper_cli() and whisper_model())

def font_file(bold=False):
    """A TrueType font that exists on this OS, for drawtext and carousel rendering."""
    if os.name == "nt":
        d = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        names = ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf") if bold else ("segoeui.ttf", "arial.ttf", "calibri.ttf")
        cands = [os.path.join(d, n) for n in names]
    else:
        cands = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"] if bold else \
                ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for c in cands:
        if os.path.isfile(c):
            return c
    return ""
