#!/usr/bin/env python3
"""
build_installer.py -- packs Project AIXMOS into dist/AIXMOS-Setup.exe (one file).

  python installer/build_installer.py            # builds payload.zip, icon, then PyInstaller onefile
  python installer/build_installer.py --payload  # only rebuild payload.zip

Payload contents (all extracted to the install dir on the target machine):
  app files            project_aixmos_server.py, context_tools.py, index.html, aixmos/, README, TODO
  vendor/              requests + pillow (cp314 wheels, matches the bundled runtime)
  whisper/             whisper-cli.exe + DLLs + ggml-base.en.bin
  bin/                 ffmpeg.exe + ffprobe.exe
  memory/kit/          the AI Building Kit (markdown)
  runtime/             python-3.14.x-embed-amd64 (unzipped)
  aixmos.ico           tab icon rendered from the arc-reactor logo
Needs: installer/cache/python-3.14.5-embed-amd64.zip (downloaded from python.org) and ffmpeg on this
machine (winget Gyan.FFmpeg or ffmpeg on PATH). Requires: pip install pyinstaller pillow
"""
import os, sys, glob, shutil, zipfile, subprocess, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
PAYLOAD = os.path.join(HERE, "payload.zip")
DIST = os.path.join(ROOT, "dist")
APP_FILES = ["project_aixmos_server.py", "context_tools.py", "index.html", "README.md", "TODO.md", ".gitignore"]
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}

def find_ffmpeg():
    out = {}
    for tool in ("ffmpeg", "ffprobe"):
        p = shutil.which(tool)
        if not p:
            cands = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", tool + ".exe"))
            cands += glob.glob(os.path.join(ROOT, "bin", tool + ".exe"))
            p = cands[0] if cands else None
        if not p:
            raise SystemExit("%s not found on this machine; install ffmpeg first (winget install Gyan.FFmpeg)" % tool)
        out[tool] = p
    return out

def add_tree(z, src, arc, skip=SKIP_DIRS):
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in skip]
        for f in fn:
            if f.endswith(".pyc"):
                continue
            full = os.path.join(dp, f)
            z.write(full, os.path.join(arc, os.path.relpath(full, src)).replace("\\", "/"))

def make_icon():
    from PIL import Image, ImageDraw
    sizes = [256, 128, 64, 48, 32, 16]
    base = Image.new("RGBA", (256, 256), (3, 8, 16, 255)); d = ImageDraw.Draw(base)
    c, c2 = (56, 224, 255, 255), (14, 165, 233, 255)
    d.ellipse([16, 16, 240, 240], outline=(56, 224, 255, 110), width=4)
    for i in range(0, 360, 30):
        d.arc([40, 40, 216, 216], start=i, end=i + 18, fill=c, width=14)
    d.arc([76, 76, 180, 180], start=0, end=360, fill=c2, width=6)
    d.polygon([(128, 82), (170, 156), (86, 156)], outline=c, width=7)
    d.ellipse([110, 110, 146, 146], fill=c)
    ico = os.path.join(HERE, "aixmos.ico")
    base.save(ico, format="ICO", sizes=[(s, s) for s in sizes])
    return ico

def build_payload():
    py_zip = glob.glob(os.path.join(CACHE, "python-3.14*-embed-amd64.zip"))
    if not py_zip:
        raise SystemExit("put python-3.14.x-embed-amd64.zip in installer/cache (https://www.python.org/ftp/python/)")
    ff = find_ffmpeg()
    ico = make_icon()
    if os.path.exists(PAYLOAD):
        os.remove(PAYLOAD)
    with zipfile.ZipFile(PAYLOAD, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in APP_FILES:
            p = os.path.join(ROOT, f)
            if os.path.isfile(p):
                z.write(p, f)
        add_tree(z, os.path.join(ROOT, "aixmos"), "aixmos")
        add_tree(z, os.path.join(ROOT, "vendor"), "vendor")
        add_tree(z, os.path.join(ROOT, "whisper", "bin", "Release"), "whisper/bin/Release", SKIP_DIRS | set())
        z.write(os.path.join(ROOT, "whisper", "models", "ggml-base.en.bin"), "whisper/models/ggml-base.en.bin")
        for tool, p in ff.items():
            z.write(p, "bin/%s.exe" % tool)
        add_tree(z, os.path.join(ROOT, "memory", "kit"), "memory/kit")
        z.write(ico, "aixmos.ico")
        with zipfile.ZipFile(py_zip[0]) as pz:
            for name in pz.namelist():
                z.writestr("runtime/" + name, pz.read(name))
        z.writestr("memory/workspace/README.txt", "Agent workspace. Files the super agent creates land here.\n")
    print("payload.zip: %d MB" % (os.path.getsize(PAYLOAD) >> 20))
    return ico

def build_exe(ico):
    os.makedirs(DIST, exist_ok=True)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
           "--name", "AIXMOS-Setup", "--icon", ico, "--add-data", PAYLOAD + os.pathsep + ".",
           "--distpath", DIST, "--workpath", os.path.join(HERE, "build"), "--specpath", HERE,
           os.path.join(HERE, "installer.py")]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    exe = os.path.join(DIST, "AIXMOS-Setup.exe")
    print("built:", exe, "%d MB" % (os.path.getsize(exe) >> 20))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", action="store_true", help="only rebuild payload.zip")
    ap.add_argument("--reuse-payload", action="store_true", help="skip payload.zip, only rebuild the exe")
    a = ap.parse_args()
    if a.reuse_payload and os.path.isfile(PAYLOAD):
        ico = os.path.join(HERE, "aixmos.ico")
        if not os.path.isfile(ico):
            ico = make_icon()
    else:
        ico = build_payload()
    if not a.payload:
        build_exe(ico)
