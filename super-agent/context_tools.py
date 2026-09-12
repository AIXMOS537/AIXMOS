#!/usr/bin/env python3
"""
context_tools.py -- gathers SAFE live signals to ground Project AIXMOS's answers.

Included (safe): local date/time + timezone, approximate location from public IP,
current weather for that location, and machine stats (CPU / RAM / disk / battery).

Deliberately EXCLUDED: the _VAULT, secrets/credentials, and any personal/family
files. This module never reads user documents -- only OS-level counters and two
public no-key web APIs (ip-api.com for geo, open-meteo.com for weather).
External calls are cached and fail-safe: if offline, those lines are simply omitted.
"""
import time, json, ctypes, shutil, threading, urllib.request
from ctypes import wintypes
from datetime import datetime

_CACHE = {"geo": (0, None), "wx": (0, None)}
_GEO_TTL = 1800   # 30 min
_WX_TTL  = 900    # 15 min
_LOCK = threading.Lock()

# ---- external signals (public, no API key) ---------------------------------
def _get_json(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "CrimsonShadow/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def get_geo():
    now = time.time()
    with _LOCK:
        ts, val = _CACHE["geo"]
        if val and now - ts < _GEO_TTL:
            return val
    try:
        d = _get_json("http://ip-api.com/json/?fields=status,country,regionName,city,lat,lon,timezone,query")
        if d.get("status") == "success":
            geo = {"city": d.get("city"), "region": d.get("regionName"), "country": d.get("country"),
                   "lat": d.get("lat"), "lon": d.get("lon"), "tz": d.get("timezone")}
            with _LOCK:
                _CACHE["geo"] = (now, geo)
            return geo
    except Exception:
        pass
    return _CACHE["geo"][1]

_WMO = {0:"clear sky",1:"mainly clear",2:"partly cloudy",3:"overcast",45:"fog",48:"rime fog",
        51:"light drizzle",53:"drizzle",55:"heavy drizzle",61:"light rain",63:"rain",65:"heavy rain",
        71:"light snow",73:"snow",75:"heavy snow",77:"snow grains",80:"rain showers",81:"rain showers",
        82:"violent rain showers",85:"snow showers",86:"snow showers",95:"thunderstorm",
        96:"thunderstorm w/ hail",99:"thunderstorm w/ heavy hail"}

def get_weather(lat, lon):
    if lat is None or lon is None:
        return None
    now = time.time()
    with _LOCK:
        ts, val = _CACHE["wx"]
        if val and now - ts < _WX_TTL:
            return val
    try:
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
               "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m"
               "&temperature_unit=fahrenheit&wind_speed_unit=mph" % (lat, lon))
        d = _get_json(url)
        c = d.get("current", {})
        wx = {"temp": c.get("temperature_2m"), "feels": c.get("apparent_temperature"),
              "humidity": c.get("relative_humidity_2m"), "wind": c.get("wind_speed_10m"),
              "desc": _WMO.get(c.get("weather_code"), "?")}
        with _LOCK:
            _CACHE["wx"] = (now, wx)
        return wx
    except Exception:
        return _CACHE["wx"][1]

# ---- local machine stats (ctypes / stdlib, no external deps) ----------------
class _MEMEX(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

class _PWR(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]

def _ft(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

def get_system():
    k = ctypes.windll.kernel32
    # CPU % over a short sample
    i1, ke1, u1 = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
    k.GetSystemTimes(ctypes.byref(i1), ctypes.byref(ke1), ctypes.byref(u1))
    time.sleep(0.18)
    i2, ke2, u2 = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
    k.GetSystemTimes(ctypes.byref(i2), ctypes.byref(ke2), ctypes.byref(u2))
    idle = _ft(i2) - _ft(i1); total = (_ft(ke2) - _ft(ke1)) + (_ft(u2) - _ft(u1))
    cpu = round((1 - idle / total) * 100) if total else 0
    # RAM
    m = _MEMEX(); m.dwLength = ctypes.sizeof(m); k.GlobalMemoryStatusEx(ctypes.byref(m))
    gb = 1024 ** 3
    ram = {"load": m.dwMemoryLoad, "free_gb": round(m.ullAvailPhys / gb, 1), "total_gb": round(m.ullTotalPhys / gb, 1)}
    # Disk C:
    du = shutil.disk_usage("C:\\")
    disk_free = round(du.free / gb)
    # Battery
    p = _PWR(); bat = None
    if k.GetSystemPowerStatus(ctypes.byref(p)):
        pct = p.BatteryLifePercent
        bat = {"pct": (None if pct == 255 else pct), "ac": (p.ACLineStatus == 1)}
    return {"cpu": cpu, "ram": ram, "disk_free_gb": disk_free, "battery": bat}

# ---- assemble the injected block -------------------------------------------
def build_context(light=False):
    """light=True skips the CPU sample (a 0.18 s sleep) and machine stats: the chat path only
    needs time, place and weather, and a short stable block keeps the model's prompt cache warm."""
    if light:
        geo = get_geo()
        now = datetime.now()
        lines = ["Now: " + now.strftime("%A %Y-%m-%d %I:%M %p") + ((" (%s)" % geo["tz"]) if geo and geo.get("tz") else "")]
        if geo and geo.get("city"):
            lines.append("Location (approx.): " + ", ".join(x for x in [geo.get("city"), geo.get("region")] if x))
            wx = get_weather(geo.get("lat"), geo.get("lon"))
            if wx and wx.get("temp") is not None:
                lines.append("Weather: %s degF, %s" % (wx["temp"], wx["desc"]))
        return "\n".join(lines)
    lines = ["[LIVE CONTEXT -- read from THIS machine right now, for accurate answers]"]
    geo = get_geo()
    tzname = (geo or {}).get("tz")
    now = datetime.now()
    lines.append("Now: " + now.strftime("%A %Y-%m-%d %I:%M %p") + (" (%s)" % tzname if tzname else ""))
    if geo and geo.get("city"):
        loc = ", ".join(x for x in [geo.get("city"), geo.get("region"), geo.get("country")] if x)
        lines.append("Location: %s  (approximate, from public IP)" % loc)
        wx = get_weather(geo.get("lat"), geo.get("lon"))
        if wx and wx.get("temp") is not None:
            lines.append("Weather: %s degF (feels %s), %s, humidity %s%%, wind %s mph"
                         % (wx["temp"], wx["feels"], wx["desc"], wx["humidity"], wx["wind"]))
    try:
        s = get_system()
        b = s["battery"]
        bs = ("battery %s%% (%s)" % (b["pct"], "plugged in" if b["ac"] else "on battery")) if b and b["pct"] is not None else ""
        lines.append("System: CPU %s%%, RAM %s%% used (%s GB free of %s), disk C: %s GB free%s"
                     % (s["cpu"], s["ram"]["load"], s["ram"]["free_gb"], s["ram"]["total_gb"],
                        s["disk_free_gb"], (", " + bs) if bs else ""))
    except Exception:
        pass
    lines.append("(Use these when relevant. Location/weather are approximate from IP; do not state them as exact.)")
    return "\n".join(lines)

def prewarm():
    try:
        g = get_geo()
        if g:
            get_weather(g.get("lat"), g.get("lon"))
    except Exception:
        pass

if __name__ == "__main__":
    print(build_context())
