# AIXMOS Starter Pack v1

A USB-bootable, offline-capable local AI for small business owners. Plug in, install once, chat forever — no monthly fees, no internet required for daily use.

## What you get

- **Local AI brain** trained with the TMMT × AIXMOS Operations playbook baked in
- **Open WebUI** chat interface (works in any browser)
- **Brain-dump agent** — talk into your laptop, it captures + organizes
- **Three small models** that run on any laptop with 8GB+ RAM
- **One USB drive = the ignition key.** Pull it = AI stops. Plug it back in = AI runs.

## Quick start (3 minutes)

1. Plug the USB into any Mac or Windows laptop with 8GB+ RAM
2. Double-click the launcher:
   - **Mac:** `LAUNCH.command`
   - **Windows:** `LAUNCH.cmd`
3. From the menu, choose **`1) Install AIXMOS (first time)`**
4. When it finishes (~3 min on first run), choose **`2) Start AIXMOS`**
5. Your browser opens to a local chat. Talk to your AI.

## Daily use

- Plug USB in → double-click `LAUNCH` → pick `2) Start AIXMOS`
- Done with work → pick `3) Stop AIXMOS` → unplug USB

## What "8GB+ RAM" actually means

Old laptops are fine. Targets we've tested against:
- 2015-era MacBook Pro (8GB) ✓
- 2017 Dell Latitude / Inspiron (8GB) ✓
- Any Lenovo ThinkPad from the last decade with 8GB ✓
- 4GB machines will NOT work — RAM is the hard floor

## Folder map

```
LAUNCH.command / LAUNCH.cmd     ← double-click to open the menu
_starter/                       ← install / start / stop / doctor / uninstall scripts
_runtime/                       ← Ollama binary + Open WebUI + brain-dump agent (run from USB)
_models/                        ← 3 small models (download once via _starter/download-models)
_brain/                         ← TMMT × AIXMOS operations brain (system prompt + Modelfile)
_pro/                           ← optional power-user packs (locked by default)
docs/                           ← deeper docs
logs/                           ← runtime logs
```

## Troubleshooting

If chat won't open: run `_starter/doctor.sh` (Mac) or `_starter/doctor.ps1` (Windows). It prints what's wrong and how to fix it.

## Uninstall

Removes models and `~/.aixmos/` from the host. Drive stays clean.
- Mac: `bash _starter/uninstall.sh`
- Win: `powershell _starter/uninstall.ps1`

---

**Version:** 1.0 — 2026-06-04
**Built on top of:** TMMT × AIXMOS BrainKit + AI-OPS-STARTER
