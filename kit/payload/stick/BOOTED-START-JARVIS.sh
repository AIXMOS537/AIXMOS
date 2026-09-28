#!/usr/bin/env bash
# BOOTED-START-JARVIS.sh - after booting the Surface from this stick (Debian Live):
#
#     bash BOOTED-START-JARVIS.sh
#
# Starts the offline brain (if a Linux Ollama is on the stick) and JARVIS, then
# opens it. FAT32/exFAT cannot carry the exec bit, which is why this is run with
# `bash` and why Ollama is copied to RAM before it runs.
set -u

up() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

find_root() {
  local here; here="$(cd "$(dirname "$0")" && pwd)"
  for d in "$here" /run/live/medium /media/*/* /media/* /mnt/aixmos; do
    [ -f "$d/AIXMOS-KIT/kit.json" ] && { echo "$d"; return 0; }
  done
  # Two-partition stick: this script sits on BOOT, the work sits on DATA.
  if [ -e /dev/disk/by-label/AIXMOS-X ]; then
    sudo mkdir -p /mnt/aixmos
    sudo mount -o uid="$(id -u)",gid="$(id -g)" /dev/disk/by-label/AIXMOS-X /mnt/aixmos 2>/dev/null
    [ -f /mnt/aixmos/AIXMOS-KIT/kit.json ] && { echo /mnt/aixmos; return 0; }
  fi
  return 1
}

ROOT="$(find_root)" || { echo "Cannot find the AIXMOS data (AIXMOS-KIT/kit.json). Is the stick plugged in?"; exit 1; }
echo "AIXMOS data: $ROOT"
command -v python3 >/dev/null || { echo "python3 is not in this live image - JARVIS cannot start."; exit 1; }

# Same map as Windows: every path comes from kit.json.
. "$ROOT/AIXMOS-KIT/lib/paths.sh"
JARVIS="$(kit_lane automation)/project-aixmos"
export OLLAMA_MODELS="$ROOT/$(_kit_json "k['bootstick']['models']")"
LINUX_OLLAMA="$ROOT/$(_kit_json "k['bootstick']['linux_ollama']['drive']")"

if up 11434; then
  echo "offline brain already running"
elif [ -f "$LINUX_OLLAMA/bin/ollama" ]; then
  rm -rf /tmp/aixmos-ollama
  cp -r "$LINUX_OLLAMA" /tmp/aixmos-ollama && chmod +x /tmp/aixmos-ollama/bin/ollama
  nohup /tmp/aixmos-ollama/bin/ollama serve >/tmp/aixmos-ollama.log 2>&1 &
  for _ in $(seq 1 40); do up 11434 && break; sleep 1; done
  up 11434 && echo "offline brain up" || echo "Ollama did not start - see /tmp/aixmos-ollama.log"
else
  echo "No Linux Ollama on this stick yet (_RUNTIME/linux/ollama)."
  echo "JARVIS will open, but its chat needs the brain. The plain offline LLM still works: bash BOOTED-RUN-LLM.sh"
fi

if ! up 8770; then
  nohup python3 "$JARVIS/project_aixmos_server.py" 8770 >/tmp/aixmos-jarvis.log 2>&1 &
  for _ in $(seq 1 60); do up 8770 && break; sleep 1; done
fi
if up 8770; then
  echo "JARVIS online -> http://localhost:8770"
  (xdg-open http://localhost:8770 >/dev/null 2>&1 &)
else
  echo "JARVIS did not start - see /tmp/aixmos-jarvis.log"
fi
