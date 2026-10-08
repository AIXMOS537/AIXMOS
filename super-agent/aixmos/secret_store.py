"""
secret_store.py -- where provider keys and tokens live. Never in settings.json, the config file,
Git, logs or prompts.

  Windows : DPAPI (CryptProtectData, current user) -> memory/secrets.dpapi.json holds only ciphertext
  macOS   : login Keychain via /usr/bin/security (service "aixmos")
  other   : memory/secrets.local.json with 0600 permissions, reported as backend "file-0600" so the
            installer and System page can say plainly that this machine has no OS keystore

  put(name, value) / get(name) / delete(name) / names() / backend()
Names are short refs such as "provider.openai.api_key" or "aixmos.ghl" (config secret_ref "keychain:aixmos.ghl").
Values are never printed; describe() returns only names and whether each is set.
"""
import os, sys, json, base64, threading, subprocess

from . import settings

_LOCK = threading.Lock()
SERVICE = "aixmos"

def backend():
    if sys.platform == "win32":
        return "dpapi"
    if sys.platform == "darwin" and os.path.exists("/usr/bin/security"):
        return "keychain"
    return "file-0600"

# ------------------------------------------------------------------ DPAPI ----
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _blob(b):
        buf = ctypes.create_string_buffer(b, len(b))
        return _BLOB(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    def _dpapi(data, protect):
        crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
        inb, _keep = _blob(data)
        out = _BLOB()
        fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        ok = fn(ctypes.byref(inb), None, None, None, None, 0x01, ctypes.byref(out))  # UI_FORBIDDEN
        if not ok:
            raise OSError("DPAPI call failed (%d)" % kernel32.GetLastError())
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            kernel32.LocalFree(out.pbData)

def _file():
    return os.path.join(settings.MEMDIR, "secrets.dpapi.json" if backend() == "dpapi" else "secrets.local.json")

def _read_file():
    try:
        with open(_file(), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}

def _write_file(d):
    os.makedirs(settings.MEMDIR, exist_ok=True)
    p = _file(); tmp = p + ".tmp"
    if backend() == "file-0600":
        # create the temp file 0600 so the plain-text values are never readable by others, not even briefly
        try:
            os.unlink(tmp)
        except OSError:
            pass
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    else:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    os.replace(tmp, p)
    if backend() == "file-0600":
        try:
            os.chmod(p, 0o600)  # an older file may predate the 0600 rule
        except OSError:
            pass

# ------------------------------------------------------------------ API ----
def put(name, value):
    value = "" if value is None else str(value)
    b = backend()
    with _LOCK:
        if b == "keychain":
            subprocess.run(["/usr/bin/security", "add-generic-password", "-U", "-s", SERVICE, "-a", name, "-w", value],
                           capture_output=True, check=True)
            idx = _read_file(); idx[name] = "keychain"; _write_file(idx)
        elif b == "dpapi":
            d = _read_file(); d[name] = base64.b64encode(_dpapi(value.encode("utf-8"), True)).decode(); _write_file(d)
        else:
            d = _read_file(); d[name] = value; _write_file(d)

def get(name, default=None):
    b = backend()
    with _LOCK:
        d = _read_file()
        if name not in d:
            return default
        try:
            if b == "keychain":
                r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
                                   capture_output=True, text=True)
                return r.stdout.rstrip("\n") if r.returncode == 0 else default
            if b == "dpapi":
                return _dpapi(base64.b64decode(d[name]), False).decode("utf-8")
            return d[name]
        except Exception:
            return default

def delete(name):
    b = backend()
    with _LOCK:
        d = _read_file()
        if b == "keychain":
            subprocess.run(["/usr/bin/security", "delete-generic-password", "-s", SERVICE, "-a", name], capture_output=True)
        d.pop(name, None)
        _write_file(d)

def names():
    with _LOCK:
        return sorted(_read_file().keys())

def resolve_ref(ref):
    """config secret_ref "keychain:aixmos.ghl" -> value, or None when missing. Never logged."""
    if not ref or not str(ref).startswith("keychain:"):
        return None
    return get(str(ref).split(":", 1)[1])

def describe():
    """Safe view for the UI and installer: names and set/unset, never values."""
    return {"backend": backend(), "secrets": [{"name": n, "set": bool(get(n))} for n in names()]}
