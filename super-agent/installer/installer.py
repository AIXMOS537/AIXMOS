#!/usr/bin/env python3
"""
AIXMOS-Setup -- one-file Windows installer for Project AIXMOS.

Built by build_installer.py into dist/AIXMOS-Setup.exe. Carries a payload.zip with the app,
vendored packages, whisper.cpp + model, ffmpeg/ffprobe, the AI Building Kit and an embeddable
Python runtime. On the target machine it:

  1. extracts everything to %LOCALAPPDATA%/AIXMOS (no admin needed; --dir to change)
  2. wires the embeddable Python to the app (._pth) so no system Python is required
  3. installs Ollama if missing (downloads the official installer, silent) and pulls qwen2.5:3b
  4. writes a launcher, a desktop shortcut and a per-user logon autostart task
  5. starts the server on port 8770 and opens the UI

Re-running upgrades the app files and keeps memory/ (conversation, settings, CRM, media).
Flags: --dir PATH  --port N  --no-ollama  --no-model  --no-autostart  --no-launch  --quiet
"""
import os, sys, io, json, time, shutil, zipfile, socket, ctypes, argparse, subprocess, urllib.request, tempfile

APP = "AIXMOS"
PORT = 8770
MODEL = "qwen2.5:3b"
OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"

def base_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def payload_path():
    p = os.path.join(base_dir(), "payload.zip")
    if not os.path.isfile(p):
        raise SystemExit("payload.zip missing next to the installer; rebuild with build_installer.py")
    return p

class Log:
    def __init__(self, path, quiet=False):
        self.f = open(path, "a", encoding="utf-8"); self.quiet = quiet
    def __call__(self, msg, end="\n"):
        line = time.strftime("%H:%M:%S ") + msg
        self.f.write(line + "\n"); self.f.flush()
        if not self.quiet:
            try:
                print(msg, end=end, flush=True)
            except UnicodeEncodeError:
                print(msg.encode("ascii", "replace").decode(), end=end, flush=True)

def banner():
    print("=" * 62)
    print("   PROJECT AIXMOS  //  JARVIS super agent  //  Windows setup")
    print("=" * 62)

def port_open(port):
    s = socket.socket(); s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port)); return True
    except OSError:
        return False
    finally:
        s.close()

def download(url, dest, log, label):
    log("  downloading %s" % label)
    req = urllib.request.Request(url, headers={"User-Agent": "AIXMOS-Setup/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0); done = 0; last = -1
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk); done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct // 5 != last // 5:
                    log("    %3d%%  (%d / %d MB)" % (pct, done >> 20, total >> 20), end="\r"); last = pct
    log("    done (%d MB)" % (os.path.getsize(dest) >> 20))

def run(cmd, log, timeout=None, check=False, **kw):
    log("  > " + " ".join(cmd) if isinstance(cmd, list) else "  > " + cmd)
    p = subprocess.run(cmd, capture_output=True, timeout=timeout, **kw)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    err = (p.stderr or b"").decode("utf-8", "replace").strip()
    if out: log("    " + out[-600:].replace("\n", "\n    "))
    if err and (p.returncode or check): log("    " + err[-600:].replace("\n", "\n    "))
    if check and p.returncode:
        raise RuntimeError("command failed (%d)" % p.returncode)
    return p.returncode

# ------------------------------------------------------------------ steps ----
def extract_payload(dest, log):
    log("[1/6] Extracting AIXMOS to %s" % dest)
    os.makedirs(dest, exist_ok=True)
    keep_memory = os.path.isdir(os.path.join(dest, "memory"))
    with zipfile.ZipFile(payload_path()) as z:
        names = z.namelist(); n = 0
        for name in names:
            # never overwrite the user's memory folder, except the kit which is app content
            if name.startswith("memory/") and keep_memory and not name.startswith("memory/kit/"):
                continue
            z.extract(name, dest); n += 1
            if n % 200 == 0:
                log("    %d / %d files" % (n, len(names)), end="\r")
    log("    %d files in place%s" % (n, " (existing memory kept)" if keep_memory else ""))

def wire_python(dest, log):
    log("[2/6] Wiring the bundled Python runtime")
    rt = os.path.join(dest, "runtime")
    pth = [f for f in os.listdir(rt) if f.endswith("._pth")]
    if not pth:
        raise RuntimeError("embeddable python ._pth not found in runtime/")
    with open(os.path.join(rt, pth[0]), "w", encoding="utf-8") as f:
        f.write("\n".join([pth[0].split("._pth")[0] + ".zip", ".", "..", "..\\vendor", "import site", ""]))
    py = os.path.join(rt, "python.exe")
    rc = run([py, "-c", "import sys, requests, PIL, ctypes; print('python', sys.version.split()[0], 'requests', requests.__version__, 'pillow', PIL.__version__)"], log, timeout=60, cwd=dest)
    if rc:
        raise RuntimeError("bundled python could not import the vendored packages")
    return py

def ensure_ollama(dest, log, want_ollama, want_model):
    log("[3/6] Ollama + local model")
    exe = shutil.which("ollama") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if not os.path.isfile(exe):
        if not want_ollama:
            log("    skipped (--no-ollama); install it later from https://ollama.com"); return None
        tmp = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        try:
            download(OLLAMA_URL, tmp, log, "Ollama installer")
        except Exception as e:
            log("    could not download Ollama (%s). Install it from https://ollama.com and re-run setup." % e); return None
        log("    installing Ollama silently (this can take a minute)")
        run([tmp, "/VERYSILENT", "/NORESTART", "/SP-"], log, timeout=1800)
        exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
        if not os.path.isfile(exe):
            log("    Ollama installer finished but ollama.exe was not found; install it manually from https://ollama.com"); return None
    log("    ollama: %s" % exe)
    # make sure the daemon is up
    if not port_open(11434):
        try:
            subprocess.Popen([exe, "serve"], creationflags=0x08000000 | 0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
        for _ in range(30):
            if port_open(11434): break
            time.sleep(1)
    log("    daemon %s" % ("online" if port_open(11434) else "not responding (it starts with the Ollama app)"))
    if want_model and port_open(11434):
        try:
            have = json.loads(urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10).read()).get("models", [])
        except Exception:
            have = []
        if any(m.get("name") == MODEL for m in have):
            log("    model %s already present" % MODEL)
        else:
            log("    pulling %s (about 2 GB, one time)" % MODEL)
            p = subprocess.Popen([exe, "pull", MODEL], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=0x08000000)
            for line in p.stdout:
                line = line.strip()
                if line: log("    " + line[-100:], end="\r")
            p.wait(); log("    pull finished (%s)" % ("ok" if p.returncode == 0 else "code %d" % p.returncode))
    return exe

def write_launchers(dest, py, port, log, autostart):
    log("[4/6] Launcher, shortcut, autostart")
    pyw = os.path.join(dest, "runtime", "pythonw.exe")
    server = os.path.join(dest, "project_aixmos_server.py")
    bat = os.path.join(dest, "Start AIXMOS.cmd")
    P = str(port)
    start_lines = [
        "@echo off", "title AIXMOS", 'cd /d "%~dp0"',
        'powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; '
        "try{$c.Connect('127.0.0.1'," + P + ");$c.Close()}catch{ Start-Process -WindowStyle Hidden '" + pyw +
        "' -ArgumentList '\\\"" + server + "\\\"','" + P + "'; Start-Sleep -Seconds 3 }\"",
        'start "" http://localhost:' + P, ""]
    with open(bat, "w", encoding="utf-8") as f:
        f.write("\r\n".join(start_lines))
    stop = os.path.join(dest, "Stop AIXMOS.cmd")
    stop_lines = [
        "@echo off",
        'for /f "tokens=5" %%p in (\'netstat -ano ^| findstr :' + P + ' ^| findstr LISTENING\') do taskkill /F /PID %%p >nul 2>&1',
        "echo AIXMOS stopped.", ""]
    with open(stop, "w", encoding="utf-8") as f:
        f.write("\r\n".join(stop_lines))
    # desktop shortcut via PowerShell COM
    ico = os.path.join(dest, "aixmos.ico")
    ps = ("$w=New-Object -ComObject WScript.Shell; $d=[Environment]::GetFolderPath('Desktop'); $s=$w.CreateShortcut(\"$d\\AIXMOS.lnk\"); "
          "$s.TargetPath='%s'; $s.WorkingDirectory='%s'; $s.IconLocation='%s'; $s.Description='Project AIXMOS - JARVIS super agent'; $s.Save()"
          % (bat, dest, ico if os.path.isfile(ico) else bat))
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], log, timeout=60)
    if autostart:
        tr = '"%s" "%s" %d' % (pyw, server, port)
        run(["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", "AIXMOS-Server", "/TR", tr, "/RL", "LIMITED"], log, timeout=60)
    else:
        log("    autostart skipped (--no-autostart)")

def start_server(dest, port, log, launch):
    log("[5/6] Starting the server on port %d" % port)
    if port_open(port):
        log("    something already answers on %d; leaving it (run 'Stop AIXMOS.cmd' then 'Start AIXMOS.cmd' to switch)" % port)
    else:
        pyw = os.path.join(dest, "runtime", "pythonw.exe")
        subprocess.Popen([pyw, os.path.join(dest, "project_aixmos_server.py"), str(port)], cwd=dest,
                         creationflags=0x08000000 | 0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if port_open(port): break
            time.sleep(0.5)
        log("    server %s" % ("online" if port_open(port) else "did not answer yet (check install.log / Start AIXMOS.cmd)"))
    try:
        j = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/api/telemetry" % port, timeout=30).read())
        c = j.get("caps", {})
        log("    vault %s passages | ffmpeg %s | whisper %s | ollama %s" % (
            (c.get("knowledge") or {}).get("chunks", "?"), "ok" if c.get("video_edit") else "missing", "ok" if c.get("captions") else "missing", "online" if c.get("ollama") else "offline"))
    except Exception as e:
        log("    (telemetry not readable yet: %s)" % e)
    if launch:
        log("[6/6] Opening http://localhost:%d" % port)
        os.startfile("http://localhost:%d" % port)
    else:
        log("[6/6] Done. Open http://localhost:%d" % port)

def main():
    ap = argparse.ArgumentParser(description="AIXMOS setup")
    ap.add_argument("--dir", default=os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), APP))
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-ollama", action="store_true"); ap.add_argument("--no-model", action="store_true")
    ap.add_argument("--no-autostart", action="store_true"); ap.add_argument("--no-launch", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    if os.name != "nt":
        raise SystemExit("This installer targets Windows.")
    banner()
    dest = os.path.abspath(a.dir)
    os.makedirs(dest, exist_ok=True)
    log = Log(os.path.join(dest, "install.log"), a.quiet)
    log("AIXMOS setup started -> %s" % dest)
    try:
        extract_payload(dest, log)
        py = wire_python(dest, log)
        ensure_ollama(dest, log, not a.no_ollama, not a.no_model)
        write_launchers(dest, py, a.port, log, not a.no_autostart)
        start_server(dest, a.port, log, not a.no_launch)
        log("")
        log("AIXMOS is installed. Launcher: %s" % os.path.join(dest, "Start AIXMOS.cmd"))
        log("Add API keys, email accounts and your business profile under Integrations / Vault when ready.")
    except Exception as e:
        log("SETUP FAILED: %s" % e)
        log("See %s" % os.path.join(dest, "install.log"))
        if not a.quiet:
            input("\nPress Enter to close.")
        sys.exit(1)
    if not a.quiet and not a.no_launch:
        time.sleep(2)

if __name__ == "__main__":
    main()
