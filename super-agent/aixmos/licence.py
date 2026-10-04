"""
licence.py -- verify-only licence check (compatible with licences issued by the owner's aixlic tool).

A licence file is JSON {"payload": b64(json body), "sig": b64(ed25519 signature)} signed by the issuer key.
The public key ships with the app (licence/AIX-ISSUER-ED25519.pub). This module can NOT issue licences; the
private key never ships. Signatures are checked with the 'cryptography' package when present, otherwise with
ed25519_verify (pure Python, RFC 8032), because the bundled Windows runtime ships without 'cryptography'.

States: LICENSED | UNLICENSED | EXPIRED | INVALID | WRONG_MACHINE | REVOKED
Every failure is closed: anything but LICENSED means has_feature() is False.

Honest limits: this is local software. Someone who edits the Python source can remove the check. The licence is
an entitlement record and an honest gate for paid skills, not DRM. Offline revocation only works when the shipped
revocation list is updated.

  status()           -> {"state", "tier", "features", "expires", "node", "to", "detail", "this_machine"}
  has_feature(name)  -> bool
  fingerprint()      -> this machine's node id (AIX- + 24 hex), same algorithm as the issuer tool
"""
import os, json, time, base64, hashlib, platform, subprocess, threading

from . import settings

PK_NAME = "AIX-ISSUER-ED25519.pub"
REVOKED = "AIX-REVOKED.json"
TIER_ALIAS = {"operator": "aixmos", "client": "aixmos", "trial": "aixmos", "owner": "master"}
_LOCK = threading.Lock()
_fp_cache = None
_status_cache = {"at": 0, "value": None}

def fingerprint():
    """Same algorithm as the issuer tool, so node ids match what the owner issues against."""
    global _fp_cache
    if _fp_cache:
        return _fp_cache
    bits = []
    sysname = platform.system()
    try:
        if sysname == "Darwin":
            out = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                                 capture_output=True, text=True, timeout=10).stdout
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    bits.append(line.split('"')[-2]); break
        elif sysname == "Windows":
            out = subprocess.run(["powershell", "-NoProfile", "-Command",
                                  "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
                                 capture_output=True, text=True, timeout=20).stdout.strip()
            if out:
                bits.append(out)
        else:
            for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if os.path.exists(p):
                    bits.append(open(p).read().strip()); break
    except Exception:
        pass
    if not bits:
        bits.append(platform.node() + "|" + platform.machine())
    raw = "|".join(bits) + "|" + sysname
    _fp_cache = "AIX-" + hashlib.sha256(raw.encode()).hexdigest()[:24].upper()
    return _fp_cache

def public_key_path():
    return os.path.join(settings.ROOT, "licence", PK_NAME)

def licence_path():
    cand = os.path.join(settings.MEMDIR, "licence.aixlic")
    if os.path.isfile(cand):
        return cand
    d = os.path.join(settings.ROOT, "licence")
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if n.endswith(".aixlic"):
                return os.path.join(d, n)
    return ""

def _result(state, detail="", body=None):
    body = body or {}
    tier = TIER_ALIAS.get(str(body.get("tier") or "").lower(), body.get("tier") or "")
    return {"state": state, "detail": detail, "tier": tier, "features": body.get("features") or [],
            "expires": body.get("expires"), "node": body.get("node") or "", "to": body.get("to") or "",
            "this_machine": fingerprint()}

def _sig_ok(pub_bytes, payload, sig):
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        from . import ed25519_verify
        return ed25519_verify.verify(pub_bytes, payload, sig)
    try:
        Ed25519PublicKey.from_public_bytes(pub_bytes).verify(sig, payload)
        return True
    except Exception:
        return False

def verify(lic_path, pub_path, node=None, now=None):
    """Pure check, no caching. Returns a status dict."""
    if not lic_path or not os.path.isfile(lic_path):
        return _result("UNLICENSED", "no licence file installed")
    try:
        with open(pub_path, "r", encoding="utf-8") as f:
            pub = base64.b64decode(json.load(f)["pub"])
        with open(lic_path, "r", encoding="utf-8") as f:
            lic = json.load(f)
        payload = base64.b64decode(lic["payload"])
        if not _sig_ok(pub, payload, base64.b64decode(lic["sig"])):
            return _result("INVALID", "signature does not verify")
        body = json.loads(payload)
    except Exception as e:
        return _result("INVALID", "licence unreadable (%s)" % type(e).__name__)
    now = int(now if now is not None else time.time())
    if int(body.get("expires") or 0) < now:
        return _result("EXPIRED", "expired " + time.strftime("%Y-%m-%d", time.localtime(int(body.get("expires") or 0))), body)
    me = node or fingerprint()
    if body.get("node") != me:
        return _result("WRONG_MACHINE", "licensed to a different machine", body)
    rv = os.path.join(os.path.dirname(os.path.abspath(pub_path)), REVOKED)
    if os.path.exists(rv):
        try:
            with open(rv, "r", encoding="utf-8") as f:
                if body.get("node") in (json.load(f).get("revoked") or []):
                    return _result("REVOKED", "revoked by the issuer", body)
        except Exception:
            return _result("INVALID", "revocation list unreadable (failing closed)", body)
    return _result("LICENSED", "%d days left" % ((int(body["expires"]) - now) // 86400), body)

def status(max_age=300):
    with _LOCK:
        if _status_cache["value"] is None or time.time() - _status_cache["at"] > max_age:
            _status_cache["value"] = verify(licence_path(), public_key_path())
            _status_cache["at"] = time.time()
        return _status_cache["value"]

def has_feature(name):
    st = status()
    if st["state"] != "LICENSED":
        return False
    feats = st.get("features") or []
    return "*" in feats or name in feats

def reset_cache():
    _status_cache["value"] = None
