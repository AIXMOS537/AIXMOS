#!/usr/bin/env bash
# Load all known env files for AIX / TMMT ops (first wins per key).
aix_biz_load_env() {
  local root="$1"
  local f
  for f in \
    "$root/TMMT MANAGEMENT/AUTOMATIONS/.env" \
    "$root/TMMT MANAGEMENT/tmmt-os/.env.local" \
    "$root/AIX_AI_COMMAND_SYSTEM/.env" \
    "$root/.env"
  do
    if [[ -f "$f" ]]; then
      set -a
      # shellcheck disable=SC1090
      source "$f"
      set +a
    fi
  done
  export AIX_ROOT="$root"
  export AIX_COMMAND_CENTER="$root"
  # Vercel/CLI proxy vars break local Supabase fetches
  unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy NO_PROXY no_proxy 2>/dev/null || true
}
