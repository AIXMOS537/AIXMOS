#!/usr/bin/env python3
"""
build_installer.py -- builds the AIXMOS 4THEPEOPLE bundle:

  dist/AIXMOS-4THEPEOPLE/
    AIXMOS-4THEPEOPLE-Setup.exe   Windows, ONE file: native C# stub + appended payload.zip
    mac-linux/                    install.sh, AIXMOS-Install.command, aixmos-app.zip
    START-HERE.txt, SHA256SUMS.txt

  python installer/build_installer.py                  # full build
  python installer/build_installer.py --reuse-payload  # keep payload.zip, rebuild stub + bundle

No PyInstaller, no SDK: the stub compiles with the csc.exe every Windows 10/11 ships
(C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319). Payload contents:
  app files            project_aixmos_server.py, context_tools.py, index.html, aixmos/, README, TODO
  setup/installer.py   the provisioning script the stub hands off to
  vendor/              requests + pillow (cp314 wheels, match the bundled runtime)
  whisper/             whisper-cli.exe + DLLs + ggml-base.en.bin
  bin/                 ffmpeg.exe + ffprobe.exe
  memory/kit/          the AI Building Kit + tmmt-operator-kit (regenerated through the brain's
                       allowlist / domain / PII gates on every build)
  operator/            TMMT operator console (generated handout from CommandCenter)
  runtime/             python-3.14.x-embed-amd64
GATE: the build refuses to ship if any payload text file carries a live-looking secret.
"""
import os, re, sys, glob, shutil, struct, hashlib, zipfile, subprocess, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CACHE = os.path.join(HERE, "cache")
PAYLOAD = os.path.join(HERE, "payload.zip")
DIST = os.path.join(ROOT, "dist")
BUNDLE = os.path.join(DIST, "AIXMOS-4THEPEOPLE")
EXE_NAME = "AIXMOS-4THEPEOPLE-Setup.exe"
APP_FILES = ["aixmos_local.py", "LOCAL-AGENT.md", "project_aixmos_server.py", "context_tools.py", "index.html", "README.md", "TODO.md"]
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
BRAIN = os.path.join(HOME, "AIXMOS-Brain")
# Business material only (playbooks, scorecards, onboarding). The owner's blueprint, device, NAS
# and local-AI notes stay home; build-operator-kit.ps1 -Business emits exactly this set.
OPERATOR_KIT = os.path.join(BRAIN, "dist", "operator-kit-business")
PII_MARKERS = os.path.join(HOME, ".aixmos-pii-markers.txt")
OPERATOR_CONSOLE = os.path.join(HOME, "CommandCenter", "TeamDashboards", "_onboarding", "Dashboard-New-Operator.html")
CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
MAGIC = b"AIXMOS4P"
SECRET_RX = re.compile(rb"(sb_secret_[A-Za-z0-9_-]{10,}|eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|(?<![A-Za-z0-9])sk-(?:ant-|proj-)?[A-Za-z0-9_-]{24,}|"
                       rb"ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[bpa]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
TEXT_EXT = {".py", ".md", ".txt", ".json", ".html", ".js", ".css", ".csv", ".yml", ".yaml", ".sh", ".cmd", ".bat", ".ps1", ".env"}

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
    ico = os.path.join(HERE, "aixmos.ico")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return ico if os.path.isfile(ico) else None
    base = Image.new("RGBA", (256, 256), (3, 8, 16, 255)); d = ImageDraw.Draw(base)
    c, c2 = (56, 224, 255, 255), (14, 165, 233, 255)
    d.ellipse([16, 16, 240, 240], outline=(56, 224, 255, 110), width=4)
    for i in range(0, 360, 30):
        d.arc([40, 40, 216, 216], start=i, end=i + 18, fill=c, width=14)
    d.arc([76, 76, 180, 180], start=0, end=360, fill=c2, width=6)
    d.polygon([(128, 82), (170, 156), (86, 156)], outline=c, width=7)
    d.ellipse([110, 110, 146, 146], fill=c)
    base.save(ico, format="ICO", sizes=[(s, s) for s in (256, 128, 64, 48, 32, 16)])
    return ico

def refresh_operator_kit():
    """Regenerate the shippable half of the brain through its own allowlist/domain/PII gates."""
    script = os.path.join(BRAIN, "build-operator-kit.ps1")
    if os.path.isfile(script):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-Business"], check=True)
    if not os.path.isdir(OPERATOR_KIT):
        raise SystemExit("operator kit missing at %s" % OPERATOR_KIT)

def add_app(z, win=True):
    for f in APP_FILES:
        p = os.path.join(ROOT, f)
        if os.path.isfile(p):
            z.write(p, f)
    add_tree(z, os.path.join(ROOT, "aixmos"), "aixmos")
    add_tree(z, os.path.join(ROOT, "memory", "kit"), "memory/kit")
    add_tree(z, OPERATOR_KIT, "memory/kit/tmmt-operator-kit")
    # The operator console is NOT shipped: it carries the owner's name, mail and dashboard link.
    # Owner rule 2026-09-21: no personal information to anyone. pii_gate enforces it.
    z.writestr("memory/workspace/README.txt", "Agent workspace. Files the super agent creates land here.\n")

def build_payload():
    py_zip = glob.glob(os.path.join(CACHE, "python-3.14*-embed-amd64.zip"))
    if not py_zip:
        raise SystemExit("put python-3.14.x-embed-amd64.zip in installer/cache (https://www.python.org/ftp/python/)")
    ff = find_ffmpeg()
    refresh_operator_kit()
    ico = make_icon()
    if os.path.exists(PAYLOAD):
        os.remove(PAYLOAD)
    with zipfile.ZipFile(PAYLOAD, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        add_app(z)
        z.write(os.path.join(HERE, "installer.py"), "setup/installer.py")
        add_tree(z, os.path.join(ROOT, "vendor"), "vendor")
        add_tree(z, os.path.join(ROOT, "whisper", "bin", "Release"), "whisper/bin/Release")
        z.write(os.path.join(ROOT, "whisper", "models", "ggml-base.en.bin"), "whisper/models/ggml-base.en.bin")
        for tool, p in ff.items():
            z.write(p, "bin/%s.exe" % tool)
        if ico:
            z.write(ico, "aixmos.ico")
        with zipfile.ZipFile(py_zip[0]) as pz:
            for name in pz.namelist():
                z.writestr("runtime/" + name, pz.read(name))
    print("payload.zip: %d MB" % (os.path.getsize(PAYLOAD) >> 20))

def refresh_setup_in_payload():
    """--reuse-payload still ships the current installer.py and app code (small files), not stale copies."""
    tmp = PAYLOAD + ".tmp"
    fresh = {}
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        add_app(z)
        z.write(os.path.join(HERE, "installer.py"), "setup/installer.py")
        fresh = set(z.namelist())
        with zipfile.ZipFile(PAYLOAD) as old:
            for i in old.infolist():
                if i.filename not in fresh and not i.filename.startswith(("aixmos/", "memory/kit/", "operator/")):
                    z.writestr(i, old.read(i.filename))
    os.replace(tmp, PAYLOAD)

def secret_gate(path):
    bad = []
    third_party = ("vendor/", "runtime/", "whisper/", "bin/")   # upstream packages; their test vectors are not our secrets
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            if i.filename.startswith(third_party):
                continue
            if os.path.splitext(i.filename)[1].lower() in TEXT_EXT or i.filename.endswith(".env"):
                if SECRET_RX.search(z.read(i.filename)):
                    bad.append(i.filename)
            base = i.filename.rsplit("/", 1)[-1]
            if base in ("settings.json", "conversation.json", "crm.json", ".env.local") or (base == ".env"):
                bad.append(i.filename + " (forbidden file)")
    if bad:
        raise SystemExit("SECRET GATE: refusing to ship. Offending entries:\n  " + "\n  ".join(bad))
    print("secret gate: clean")
    pii_gate(path)

def pii_gate(path):
    """Refuse to ship any owner-personal marker. The markers live outside the repo, one per line."""
    if not os.path.isfile(PII_MARKERS):
        raise SystemExit("PII GATE: %s is missing, so personal info cannot be ruled out. Refusing to ship." % PII_MARKERS)
    with open(PII_MARKERS, encoding="utf-8") as f:
        marks = [m.strip().lower().encode() for m in f if m.strip() and not m.startswith("#")]
    bad = []
    third_party = ("vendor/", "runtime/", "whisper/", "bin/")
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            if i.filename.startswith("operator/"):
                bad.append(i.filename + " (operator console carries owner details)")
            if i.filename.startswith(third_party) or os.path.splitext(i.filename)[1].lower() not in TEXT_EXT:
                continue
            low = z.read(i.filename).lower()
            hits = sum(1 for m in marks if m in low)
            if hits:
                bad.append("%s  [%d marker(s)]" % (i.filename, hits))
    if bad:
        raise SystemExit("PII GATE: refusing to ship. Offending entries:\n  " + "\n  ".join(bad))
    print("pii gate: clean (%d markers)" % len(marks))

def build_stub(ico):
    out = os.path.join(HERE, "stub", "AixmosSetup.stub.exe")
    fw = os.path.dirname(CSC)
    cmd = [CSC, "/nologo", "/optimize+", "/target:exe", "/platform:anycpu", "/out:" + out,
           "/win32manifest:" + os.path.join(HERE, "stub", "app.manifest"),
           "/r:" + os.path.join(fw, "System.IO.Compression.dll"), "/r:" + os.path.join(fw, "System.IO.Compression.FileSystem.dll")]
    if ico and os.path.isfile(ico):
        cmd.append("/win32icon:" + ico)
    cmd.append(os.path.join(HERE, "stub", "AixmosSetup.cs"))
    subprocess.run(cmd, check=True)
    return out

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def build_bundle(stub):
    if os.path.isdir(BUNDLE):
        shutil.rmtree(BUNDLE)
    os.makedirs(os.path.join(BUNDLE, "mac-linux"))
    exe = os.path.join(BUNDLE, EXE_NAME)
    size = os.path.getsize(PAYLOAD)
    with open(exe, "wb") as o:
        with open(stub, "rb") as s:
            shutil.copyfileobj(s, o)
        with open(PAYLOAD, "rb") as p:
            shutil.copyfileobj(p, o, 1 << 22)
        o.write(struct.pack("<q", size) + MAGIC)
    ml = os.path.join(BUNDLE, "mac-linux")
    with zipfile.ZipFile(os.path.join(ml, "aixmos-app.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        add_app(z, win=False)
    secret_gate(os.path.join(ml, "aixmos-app.zip"))
    for f in ("install.sh", "AIXMOS-Install.command"):
        with open(os.path.join(HERE, "unix", f), "rb") as src, open(os.path.join(ml, f), "wb") as dst:
            dst.write(src.read().replace(b"\r\n", b"\n"))   # LF, or bash chokes on macOS/Linux
    shutil.copyfile(os.path.join(HERE, "bundle", "START-HERE.txt"), os.path.join(BUNDLE, "START-HERE.txt"))
    sums = []
    for dp, _, fn in os.walk(BUNDLE):
        for f in sorted(fn):
            full = os.path.join(dp, f)
            sums.append("%s  %s" % (sha256(full), os.path.relpath(full, BUNDLE).replace("\\", "/")))
    with open(os.path.join(BUNDLE, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sums) + "\n")
    print("built: %s (%d MB)" % (exe, os.path.getsize(exe) >> 20))
    print("bundle: %s" % BUNDLE)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse-payload", action="store_true", help="keep the heavy payload, refresh app + setup files only")
    a = ap.parse_args()
    if a.reuse_payload and os.path.isfile(PAYLOAD):
        refresh_operator_kit()
        refresh_setup_in_payload()
        ico = make_icon()
    else:
        build_payload()
        ico = os.path.join(HERE, "aixmos.ico")
    secret_gate(PAYLOAD)
    build_bundle(build_stub(ico))
