#!/usr/bin/env python3
"""
installer.py -- provisioning half of AIXMOS-4THEPEOPLE-Setup.exe (Project AIXMOS // 4THEPEOPLE).

The native stub (installer/stub/AixmosSetup.cs) extracts the payload into the install dir and then
runs this file with the bundled runtime:  runtime\\python.exe setup\\installer.py --installed-dir DIR
It is stdlib-only, so it runs before the vendored packages are wired. On the target machine it:

  2. wires the embeddable Python to the app (._pth) so no system Python is required
  3. installs Ollama if missing (official installer, silent) and pulls the local model
  4. asks who the machine is for -- student / employee / TMMT pathway / TMMT operator / builder /
     Everything (full station) -- and provisions it:
       * everyone: the super agent, the playbook vault, first-boot Genesis intro seeded with the role
       * TMMT roles: operator playbooks in the vault + the operator console on the desktop
       * --tmmt-dev (or yes at the prompt): Git, Node, GitHub CLI, Claude Code, the canon TMMT repo
         (AIXMOS537/TMMT -- private; needs an owner-granted GitHub account) with a secrets-free .env
       * Claude Code, when present, gets AIXMOS registered as an MCP server
  5. writes Start/Stop launchers, a desktop shortcut and a per-user logon autostart
  6. starts the server and opens the first-boot introduction

Re-running upgrades the app and keeps memory/ (conversation, settings, CRM, media, genesis).
Flags: --role student|employee|tmmt_pathway|tmmt_operator|builder|everything  --tmmt-dev  --no-tmmt-dev
       --port N  --no-ollama  --no-model  --no-autostart  --no-launch  --quiet
"everything" = every feature + operator kit + console + certification path, and the TMMT developer lane
runs without asking (skip it with --no-tmmt-dev).
Secrets never ship: no API key, service-role key or .env value is in the payload. Keys are
entered by the person who owns them, on their own machine, in the Integrations panel.
"""
import os, sys, json, time, shutil, socket, argparse, subprocess, urllib.request, tempfile

APP = "AIXMOS"
PORT = 8770
MODEL = "qwen2.5:3b"
OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_PUBLISHER = "Ollama"          # must appear in the Authenticode signer subject
TMMT_REPO = "https://github.com/AIXMOS537/TMMT.git"   # canonical private repo; access granted separately
ROLES = {"1": "student", "2": "employee", "3": "tmmt_pathway", "4": "tmmt_operator", "5": "aixmos_member", "6": "everything"}
ROLE_ALIASES = {"builder": "aixmos_member", "entrepreneur": "aixmos_member", "movement": "aixmos_member",
                "pathway": "tmmt_pathway", "candidate": "tmmt_pathway", "operator": "tmmt_operator",
                "all": "everything", "full": "everything"}
VALID_ROLES = set(ROLES.values()) | {"both"}          # "both" = older installs; still honoured
OPERATOR_ROLES = ("tmmt_operator", "both", "everything")   # get the role-locked console and the dev lane
TMMT_ROLES = OPERATOR_ROLES + ("tmmt_pathway",)        # get the operator playbooks + certification path
NOWIN = 0x08000000

class Log:
    def __init__(self, path, quiet=False):
        self.f = open(path, "a", encoding="utf-8"); self.quiet = quiet
    def __call__(self, msg, end="\n"):
        self.f.write(time.strftime("%H:%M:%S ") + msg + "\n"); self.f.flush()
        if not self.quiet:
            try:
                print(msg, end=end, flush=True)
            except UnicodeEncodeError:
                print(msg.encode("ascii", "replace").decode(), end=end, flush=True)

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
    req = urllib.request.Request(url, headers={"User-Agent": "AIXMOS-Setup/2.0"})
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

def signed_by(path, publisher, log):
    """Only run a downloaded executable when Windows says its Authenticode signature is valid and the
    signer is the expected publisher. A tampered or swapped download fails here instead of running."""
    ps = ("$s=Get-AuthenticodeSignature -LiteralPath '%s'; "
          "Write-Output ($s.Status.ToString() + '|' + $s.SignerCertificate.Subject)") % path.replace("'", "''")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                             capture_output=True, text=True, timeout=120, creationflags=NOWIN).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        log("    could not check the signature (%s)" % e); return False
    status, _, subject = out.partition("|")
    log("    signature: %s (%s)" % (status or "unknown", subject or "no signer"))
    return status == "Valid" and publisher.lower() in subject.lower()

def run(cmd, log, timeout=None, check=False, **kw):
    log("  > " + (" ".join(cmd) if isinstance(cmd, list) else cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, **kw)
    except (OSError, subprocess.TimeoutExpired) as e:
        log("    (%s)" % e)
        if check:
            raise
        return 1
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    err = (p.stderr or b"").decode("utf-8", "replace").strip()
    if out: log("    " + out[-600:].replace("\n", "\n    "))
    if err and (p.returncode or check): log("    " + err[-600:].replace("\n", "\n    "))
    if check and p.returncode:
        raise RuntimeError("command failed (%d)" % p.returncode)
    return p.returncode

def refresh_path():
    try:
        import winreg
        parts = []
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                          (winreg.HKEY_CURRENT_USER, "Environment")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    parts.append(os.path.expandvars(winreg.QueryValueEx(k, "Path")[0]))
            except OSError:
                pass
        if parts:
            os.environ["PATH"] = ";".join(parts + [os.environ.get("PATH", "")])
    except ImportError:
        pass

def ask(prompt, default, quiet):
    if quiet or not sys.stdin or not sys.stdin.isatty():
        return default
    try:
        v = input(prompt).strip()
    except EOFError:
        return default
    return v or default

# ------------------------------------------------------------------ steps ----
def wire_python(dest, log):
    log("[2/6] Wiring the bundled Python runtime")
    rt = os.path.join(dest, "runtime")
    pth = [f for f in os.listdir(rt) if f.endswith("._pth")]
    if not pth:
        raise RuntimeError("embeddable python ._pth not found in runtime/")
    with open(os.path.join(rt, pth[0]), "w", encoding="utf-8") as f:
        f.write("\n".join([pth[0].split("._pth")[0] + ".zip", ".", "..", "..\\vendor", "import site", ""]))
    py = os.path.join(rt, "python.exe")
    rc = run([py, "-c", "import sys, requests, PIL; print('python', sys.version.split()[0], 'requests', requests.__version__, 'pillow', PIL.__version__)"],
             log, timeout=60, cwd=dest)
    if rc:
        raise RuntimeError("bundled python could not import the vendored packages")
    return py

def ensure_ollama(log, want_ollama, want_model):
    log("[3/6] Ollama + local model")
    if not want_ollama and not want_model:
        log("    local model setup skipped; paired clients can use tools without it")
        return None
    exe = shutil.which("ollama") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if not os.path.isfile(exe):
        if not want_ollama:
            log("    skipped (--no-ollama); install it later from https://ollama.com"); return None
        tmp = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
        try:
            download(OLLAMA_URL, tmp, log, "Ollama installer (official, ollama.com)")
        except Exception as e:
            log("    could not download Ollama (%s). Install it from https://ollama.com and re-run setup." % e); return None
        if not signed_by(tmp, OLLAMA_PUBLISHER, log):
            log("    the download is not validly signed by %s, so it was NOT run. Install Ollama from https://ollama.com and re-run setup." % OLLAMA_PUBLISHER)
            try: os.remove(tmp)
            except OSError: pass
            return None
        log("    installing Ollama silently (this can take a minute)")
        run([tmp, "/VERYSILENT", "/NORESTART", "/SP-"], log, timeout=1800)
        exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
        if not os.path.isfile(exe):
            log("    Ollama finished but ollama.exe was not found; install it manually from https://ollama.com"); return None
    log("    ollama: %s" % exe)
    if not port_open(11434):
        try:
            subprocess.Popen([exe, "serve"], creationflags=NOWIN | 0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            p = subprocess.Popen([exe, "pull", MODEL], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=NOWIN)
            for line in p.stdout:
                line = line.strip()
                if line: log("    " + line[-100:], end="\r")
            p.wait(); log("    pull finished (%s)" % ("ok" if p.returncode == 0 else "code %d" % p.returncode))
    return exe

def choose_role(a, log):
    role = (a.role or "").strip().lower()
    role = ROLE_ALIASES.get(role, role)
    if role not in VALID_ROLES:
        print("\n  Who is this machine for?")
        print("    1) Student         school, a program, or teaching yourself")
        print("    2) Employee        get your job done faster; work data stays on this machine")
        print("    3) TMMT pathway    you want to become a licensed TMMT operator")
        print("    4) TMMT operator   you already run rentals / detailing / dispatch / sales for TMMT")
        print("    5) Entrepreneur    build your own business, product or project")
        print("    6) Everything      full station: all of the above + the TMMT app developer lane")
        role = ROLES.get(ask("  Choose 1-6 [5]: ", "5", a.quiet), "aixmos_member")
    log("    role: %s" % role)
    return role

def seed_genesis(dest, role):
    path = os.path.join(dest, "memory", "genesis.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    if not d.get("role"):
        d["role"] = role
    d.setdefault("installed_ts", time.time())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)

SHORTCUTS = {"on": True}

def shortcut(name, target, workdir, icon, desc, log):
    if not SHORTCUTS["on"]:
        log("    shortcut '%s' skipped (--no-shortcuts)" % name); return
    ps = ("$w=New-Object -ComObject WScript.Shell; $d=[Environment]::GetFolderPath('Desktop'); $s=$w.CreateShortcut(\"$d\\%s.lnk\"); "
          "$s.TargetPath='%s'; $s.WorkingDirectory='%s'; $s.IconLocation='%s'; $s.Description='%s'; $s.Save()"
          % (name, target.replace("'", "''"), workdir.replace("'", "''"), icon.replace("'", "''"), desc.replace("'", "''")))
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], log, timeout=60)

def tmmt_dev(log, quiet):
    """Developer lane for TMMT operators who will work on the app itself. Every step is non-fatal."""
    log("    TMMT developer tools")
    if not shutil.which("winget"):
        log("    winget (App Installer) is missing -- install 'App Installer' from the Microsoft Store, then re-run with --tmmt-dev"); return
    for pid, label, exe in (("Git.Git", "Git", "git"), ("OpenJS.NodeJS.LTS", "Node.js LTS", "node"), ("GitHub.cli", "GitHub CLI", "gh")):
        if shutil.which(exe):
            log("    %s already installed" % label); continue
        run(["winget", "install", "--id", pid, "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"], log, timeout=1800)
    refresh_path()
    if not shutil.which("claude") and shutil.which("npm"):
        run(["cmd", "/c", "npm", "install", "-g", "@anthropic-ai/claude-code"], log, timeout=1800)
        refresh_path()
    repo = os.path.join(os.path.expanduser("~"), "TMMT-canon")
    gh = shutil.which("gh"); git = shutil.which("git")
    if os.path.isdir(os.path.join(repo, ".git")):
        log("    canon repo already at %s (not touched; pull it yourself with --ff-only)" % repo)
    elif gh and git:
        if run([gh, "auth", "status"], log, timeout=30) != 0 and not quiet:
            log("    sign in to GitHub with the account the owner granted access to AIXMOS537/TMMT")
            subprocess.call([gh, "auth", "login", "--web", "--git-protocol", "https"])
        if run([git, "clone", TMMT_REPO, repo], log, timeout=1800) == 0:
            env, example = os.path.join(repo, ".env"), os.path.join(repo, ".env.example")
            if not os.path.exists(env) and os.path.exists(example):
                shutil.copyfile(example, env)
                log("    .env created from .env.example (no secrets; the owner issues keys separately)")
            log("    next: cd %s ; npm install ; npm run dev  -> http://localhost:3000" % repo)
        else:
            log("    could not clone the canon repo. It is private: ask the owner to add your GitHub account to AIXMOS537/TMMT, then re-run with --tmmt-dev")
    else:
        log("    git / gh not on PATH yet -- open a new terminal and re-run with --tmmt-dev")

def register_mcp(dest, port, log):
    py = os.path.join(dest, "runtime", "python.exe")
    entry = os.path.join(dest, "aixmos_local.py")
    # Always provide a portable JSON example; pair installed clients without deleting registrations.
    config = os.path.join(dest, "aixmos-mcp.json")
    run([py, entry, "pair", "--client", "json", "--config", config, "--replace"], log, timeout=60)
    if os.path.isdir(os.path.join(os.path.expanduser("~"), ".cursor")):
        run([py, entry, "pair", "--client", "cursor"], log, timeout=60)
    if shutil.which("claude"):
        run([py, entry, "pair", "--client", "claude-code"], log, timeout=60)


def provision(dest, a, log):
    log("[4/6] Provisioning this machine")
    role = choose_role(a, log)
    seed_genesis(dest, role)
    ico = os.path.join(dest, "aixmos.ico")
    if role in TMMT_ROLES:
        kit = os.path.join(dest, "memory", "kit", "tmmt-operator-kit")
        log("    TMMT operator playbooks in the vault: %s" % ("yes" if os.path.isdir(kit) else "missing"))
        if role == "tmmt_pathway":
            log("    certification path: type /pathway in chat after first boot")
    if role in OPERATOR_ROLES:
        console = os.path.join(dest, "operator", "TMMT-Operator-Console.html")
        if os.path.isfile(console):
            shortcut("TMMT Operator Console", console, os.path.dirname(console), ico, "TMMT operator console", log)
        if a.no_tmmt_dev:
            want_dev = False
        elif a.tmmt_dev or role == "everything":
            want_dev = True
        else:
            want_dev = ask("  Also set up TMMT developer tools (Git, Node, GitHub CLI, Claude Code, the app repo)? y/N: ", "n", a.quiet).lower().startswith("y")
        if want_dev:
            tmmt_dev(log, a.quiet)
    if not a.no_mcp:
        register_mcp(dest, a.port, log)
    return role

def write_launchers(dest, port, log, autostart):
    log("[5/6] Launchers, pairing, shortcut, autostart")
    py = os.path.join(dest, "runtime", "python.exe")
    pyw = os.path.join(dest, "runtime", "pythonw.exe")
    entry = os.path.join(dest, "aixmos_local.py")
    actions = {"Start AIXMOS.cmd": "start --open --port %d" % port,
               "Stop AIXMOS.cmd": "stop --port %d" % port,
               "Status AIXMOS.cmd": "status --port %d" % port,
               "Pair Cursor.cmd": "pair --client cursor",
               "Pair Claude Code.cmd": "pair --client claude-code",
               "Pair Claude Desktop.cmd": "pair --client claude-desktop"}
    for filename, action in actions.items():
        with open(os.path.join(dest, filename), "w", encoding="utf-8", newline="") as f:
            f.write('@echo off\r\n"%~dp0runtime\\python.exe" "%~dp0aixmos_local.py" ' + action + '\r\nif errorlevel 1 pause\r\n')
    bat = os.path.join(dest, "Start AIXMOS.cmd")
    ico = os.path.join(dest, "aixmos.ico")
    shortcut("AIXMOS", bat, dest, ico if os.path.isfile(ico) else bat, "AIXMOS local agent", log)
    if autostart:
        tr = '"%s" "%s" start --port %d' % (pyw, entry, port)
        rc = run(["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", "AIXMOS-Server", "/TR", tr, "/RL", "LIMITED"], log, timeout=60)
        if rc:
            log("    autostart was NOT registered; use Start AIXMOS.cmd")
    else:
        log("    autostart skipped (--no-autostart)")


def start_server(dest, port, log, launch):
    log("[6/6] Starting the local AIXMOS service")
    cmd = [os.path.join(dest, "runtime", "python.exe"), os.path.join(dest, "aixmos_local.py"), "start", "--port", str(port)]
    if launch:
        cmd.append("--open")
    run(cmd, log, timeout=90, check=True)


SHOWCASE = """
  WHAT YOUR SUPER AGENT CAN DO NOW
  --------------------------------
  Think    private chat brain with memory | playbook vault (24 packs) | web research + fact-check
  Build    super agent with real tools (files, commands, Python, web) | app & automation builder
           MCP server + OpenAI-compatible API for Claude Code, Cursor and friends
  Grow     CRM, lead scoring, appointments, follow-up sequences | email writer | Instagram carousels
  Create   image lab that learns your taste | video lab | plain-English video editing + captions | voice
  Skills   /skill receptionist, appointment-setter, cold-outreach, content-engine, sales-pack, agency-os ...

  On first open, AIXMOS introduces itself, learns what you are building and writes your first build plan.
"""

def main():
    ap = argparse.ArgumentParser(description="AIXMOS 4THEPEOPLE setup")
    ap.add_argument("--installed-dir", required=True)
    ap.add_argument("--role", default="")
    ap.add_argument("--tmmt-dev", action="store_true"); ap.add_argument("--no-tmmt-dev", action="store_true")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-ollama", action="store_true"); ap.add_argument("--no-model", action="store_true")
    ap.add_argument("--no-autostart", action="store_true"); ap.add_argument("--no-launch", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-shortcuts", action="store_true"); ap.add_argument("--no-mcp", action="store_true")
    a, _ = ap.parse_known_args()
    if not 1024 <= a.port <= 65535:
        ap.error("port must be between 1024 and 65535")
    SHORTCUTS["on"] = not a.no_shortcuts
    dest = os.path.abspath(a.installed_dir)
    log = Log(os.path.join(dest, "install.log"), a.quiet)
    log("AIXMOS 4THEPEOPLE setup -> %s" % dest)
    try:
        wire_python(dest, log)
        ensure_ollama(log, not a.no_ollama, not a.no_model)
        role = provision(dest, a, log)
        write_launchers(dest, a.port, log, not a.no_autostart)
        start_server(dest, a.port, log, not a.no_launch)
        log(SHOWCASE)
        log("AIXMOS is installed (%s). Launcher: %s" % (role, os.path.join(dest, "Start AIXMOS.cmd")))
    except Exception as e:
        log("SETUP FAILED: %s" % e)
        log("See %s" % os.path.join(dest, "install.log"))
        if not a.quiet:
            input("\nPress Enter to close.")
        sys.exit(1)
    if not a.quiet:
        input("\nPress Enter to close this window.")

if __name__ == "__main__":
    main()
