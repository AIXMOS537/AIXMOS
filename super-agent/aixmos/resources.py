"""
resources.py -- know BEFORE dispatch whether a local model can run. Measure -> admit -> (wait) -> run.

  snapshot()        RAM total/available, WSL/Docker memory, loaded Ollama models (+ VRAM they hold), heavy processes
  admit(model)      READY | WAIT_FOR_RESOURCES | OTHER_JOB_CONFLICT | INSUFFICIENT_MACHINE (+ numbers and reason)
Rules:
  * never unload or kill anything this job did not start; memory held by other work means WAIT
  * the admission estimate is a heuristic (tunable: prefs admission_factor / admission_overhead_gb)
    calibrated on a 32 GB workstation 2026-09-24: a 9 GB model loaded (slowly) with ~7 GB available and failed with HTTP 500 at <1 GB
"""
import ctypes, json, os, platform, subprocess, time, urllib.request

from . import settings, providers

GB = 1024 ** 3

def _ram():
    if platform.system() == "Windows":
        class M(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                        ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("x", ctypes.c_ulonglong)]
        m = M(); m.l = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.total / GB, m.avail / GB
    try:
        info = dict(l.split(":", 1) for l in open("/proc/meminfo").read().splitlines())
        return int(info["MemTotal"].split()[0]) / 1024 ** 2, int(info["MemAvailable"].split()[0]) / 1024 ** 2
    except Exception:
        return 0.0, 0.0

def _ollama(path):
    with urllib.request.urlopen(providers.ollama_url() + path, timeout=5) as r:
        return json.loads(r.read())

def loaded_models():
    try:
        return [{"name": m["name"], "size_gb": round(m.get("size", 0) / GB, 1), "vram_gb": round(m.get("size_vram", 0) / GB, 1),
                 "expires": m.get("expires_at", "")} for m in _ollama("/api/ps").get("models", [])]
    except Exception:
        return []

def model_size_gb(name):
    try:
        for m in _ollama("/api/tags").get("models", []):
            if m["name"] == name:
                return round(m.get("size", 0) / GB, 1)
    except Exception:
        pass
    return None

def _heavy_processes(limit=6):
    if platform.system() != "Windows":
        return []
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First %d Name,WorkingSet64 | ConvertTo-Json" % limit],
                             capture_output=True, text=True, timeout=20,
                             creationflags=0x08000000).stdout      # CREATE_NO_WINDOW: no console flash under pythonw
        rows = json.loads(out or "[]")
        rows = rows if isinstance(rows, list) else [rows]
        return [{"name": r["Name"], "gb": round(r["WorkingSet64"] / GB, 1)} for r in rows]
    except Exception:
        return []

def snapshot():
    total, avail = _ram()
    heavy = _heavy_processes()
    return {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "ram_total_gb": round(total, 1), "ram_available_gb": round(avail, 1),
            "wsl_docker_gb": round(sum(p["gb"] for p in heavy if p["name"].lower().startswith("vmmem")), 1),
            "ollama_loaded": loaded_models(), "heavy_processes": heavy,
            "vram_note": "per-model VRAM from Ollama; total VRAM not reliably readable on this GPU"}

def admit(model, snap=None):
    """Can this model run NOW without disturbing other work? -> dict(decision, need_gb, available_gb, reason, snapshot)"""
    snap = snap or snapshot()
    size = model_size_gb(model)
    factor = float(settings.pref("admission_factor") or 0.6)
    overhead = float(settings.pref("admission_overhead_gb") or 1.5)
    res = {"model": model, "model_gb": size, "available_gb": snap["ram_available_gb"], "snapshot": snap}
    if size is None:
        return dict(res, decision="INSUFFICIENT_MACHINE", need_gb=None, reason="model not installed on this machine")
    need = round(size * factor + overhead, 1)
    res["need_gb"] = need
    if any(m["name"] == model for m in snap["ollama_loaded"]):
        return dict(res, decision="READY", reason="model already loaded")
    if snap["ram_total_gb"] and snap["ram_total_gb"] < need + 4:
        return dict(res, decision="INSUFFICIENT_MACHINE", reason="%.1f GB RAM total cannot host a %.1f GB model safely" % (snap["ram_total_gb"], size))
    if snap["ram_available_gb"] >= need:
        return dict(res, decision="READY", reason="%.1f GB available >= %.1f GB needed" % (snap["ram_available_gb"], need))
    others = [m["name"] for m in snap["ollama_loaded"]]
    if others:
        return dict(res, decision="OTHER_JOB_CONFLICT",
                    reason="other work holds %s; not ours to unload -> wait (%.1f GB available, %.1f GB needed)" % (", ".join(others), snap["ram_available_gb"], need))
    return dict(res, decision="WAIT_FOR_RESOURCES", reason="%.1f GB available, %.1f GB needed (memory held by other processes)" % (snap["ram_available_gb"], need))
