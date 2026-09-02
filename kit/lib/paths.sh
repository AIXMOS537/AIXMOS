#!/usr/bin/env bash
# paths.sh - the bash half of the same map. Mac (incl. the bootable build) and
# Linux read the identical kit.json, so a lane is in one place, not two.

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIT_FILE="$KIT_ROOT/kit.json"

# Under a home directory means the installed copy; anywhere else (a mounted
# stick, a booted image) means the on-drive layout.
case "$KIT_ROOT" in
  "$HOME"/*|/Users/*/*|/home/*/*) KIT_MODE="local";  KIT_WORKSPACE="$(dirname "$KIT_ROOT")" ;;
  *)                              KIT_MODE="portable"
                                  KIT_WORKSPACE="$(df -P "$KIT_ROOT" 2>/dev/null | awk 'NR==2{print $NF}')"
                                  [ -z "$KIT_WORKSPACE" ] && KIT_WORKSPACE="$(dirname "$KIT_ROOT")" ;;
esac

_kit_json() {
  # python3 is on every macOS and every Linux image we boot; jq is not.
  python3 -c "
import json,sys
k=json.load(open(sys.argv[1]))
print(eval(sys.argv[2],{'k':k}) or '')
" "$KIT_FILE" "$1" 2>/dev/null
}

kit_lane() {
  local name="$1" rel
  rel="$(_kit_json "k['lanes'].get('$name',{}).get('$([ "$KIT_MODE" = local ] && echo local || echo drive)')")"
  [ -z "$rel" ] && rel="$(_kit_json "k['lanes'].get('$name',{}).get('local')")"
  [ -z "$rel" ] && { echo "unknown lane: $name" >&2; return 1; }
  echo "$KIT_WORKSPACE/$rel"
}

kit_lanes()   { _kit_json "' '.join(k['lanes'].keys())"; }
kit_version() { _kit_json "k['version']"; }
