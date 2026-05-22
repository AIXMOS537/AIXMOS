#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" && "$MODE" != "--verify-only" ]]; then
  echo "Usage: $0 [--dry-run|--apply|--verify-only]" >&2
  exit 2
fi

export COPYFILE_DISABLE=1

HOME_ROOT="${PORTABLE_KIT_HOME:-$HOME}"
VOLUMES_ROOT="${PORTABLE_KIT_VOLUMES_ROOT:-/Volumes}"
KIT_NAME="AIXMOS-PORTABLE-KIT"
DATE_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

DRIVE_NAMES=("AIXMOS02" "CYBORG" "LEXAR")
DRIVE_ROLES=("MASTER" "WORK" "FIELD")

COMMON_EXCLUDES=(
  "--exclude=.git/"
  "--exclude=.sync-inspect/"
  "--exclude=.env"
  "--exclude=.env.*"
  "--exclude=imports/"
  "--exclude=secrets/"
  "--exclude=SECRETS/"
  "--exclude=*secret*"
  "--exclude=*Secret*"
  "--exclude=*token*"
  "--exclude=*Token*"
  "--exclude=*TOKEN*"
  "--exclude=*KEY*"
  "--exclude=*.key"
  "--exclude=*.pem"
  "--exclude=*.zip"
  "--exclude=*.tar"
  "--exclude=*.tar.gz"
  "--exclude=*.tgz"
  "--exclude=id_rsa"
  "--exclude=id_ed25519"
  "--exclude=node_modules/"
  "--exclude=.next/"
  "--exclude=.vercel/"
  "--exclude=.venv/"
  "--exclude=venv/"
  "--exclude=__pycache__/"
  "--exclude=.pytest_cache/"
  "--exclude=test-results/"
  "--exclude=*.tsbuildinfo"
  "--exclude=.DS_Store"
  "--exclude=._*"
)

log() {
  printf '%s\n' "$*"
}

run() {
  if [[ "$MODE" == "--dry-run" ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

drive_path() {
  printf '%s/%s\n' "$VOLUMES_ROOT" "$1"
}

kit_path() {
  printf '%s/%s/%s\n' "$VOLUMES_ROOT" "$1" "$KIT_NAME"
}

ensure_drive() {
  local drive="$1"
  local path
  path="$(drive_path "$drive")"
  [[ -d "$path" ]] || {
    echo "Missing drive: $path" >&2
    exit 1
  }
}

mkdirs_for_drive() {
  local drive="$1"
  local kit
  kit="$(kit_path "$drive")"
  run mkdir -p "$kit"/{AI-OPS-STARTER,AIXMOS-AGENTS,AIX-Command-Center,portable-setup,docs/team,docs/fleet,installers,scripts/mac,scripts/windows,scripts/common,checksums,reports,work}
}

write_file() {
  local path="$1"
  shift
  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] write $path"
  else
    mkdir -p "$(dirname "$path")"
    cat > "$path" "$@"
  fi
}

write_root_entrypoints() {
  local drive="$1"
  local role="$2"
  local root
  root="$(drive_path "$drive")"

  write_file "$root/START-HERE.md" <<EOF_ROOT
# AIXMOS Portable Kit - $role

Plug this drive into a Mac or Windows computer, then open:

- Mac: \`START_MAC.command\`
- Windows: \`START_WINDOWS.bat\`
- Manual docs: \`$KIT_NAME/START-HERE.md\`

Role: $role
Generated: $DATE_UTC

No setup script should ask you to paste secrets into chat. Keep API keys in a password manager or local machine env files.
EOF_ROOT

  write_file "$root/README_LOAD_FIRST.txt" <<EOF_README
AIXMOS PORTABLE KIT - $role

1. Open START-HERE.md first.
2. Mac users run START_MAC.command.
3. Windows users run START_WINDOWS.bat.
4. Keep secrets out of the FIELD drive.
5. Use Tailscale for private remote access.
EOF_README

  write_file "$root/START_MAC.command" <<'EOF_MAC'
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/AIXMOS-PORTABLE-KIT"
echo "AIXMOS Portable Kit"
echo "Drive: $DIR"
echo
if command -v open >/dev/null 2>&1; then
  open START-HERE.md || true
fi
bash scripts/mac/bootstrap-mac.sh
EOF_MAC

  write_file "$root/START_WINDOWS.bat" <<'EOF_BAT'
@echo off
setlocal
cd /d "%~dp0AIXMOS-PORTABLE-KIT"
echo AIXMOS Portable Kit
echo Drive: %~dp0
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\bootstrap-windows.ps1
pause
EOF_BAT

  if [[ "$MODE" != "--dry-run" ]]; then
    chmod +x "$root/START_MAC.command"
  fi
}

write_kit_docs() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"

  write_file "$kit/START-HERE.md" <<EOF_START
# AIXMOS Portable Kit

Role: $role
Drive: $drive
Generated: $DATE_UTC

## What this kit is for

- Start work from a Mac or Windows computer.
- Reach Brainiac 7, the home PC AI brain, through Tailscale.
- Use the work Mac as the coding brain when it is online.
- Keep production hosting on GitHub, Vercel, and Supabase.

## Quick start

### Mac

Run from the drive root:

\`\`\`bash
./START_MAC.command
\`\`\`

### Windows

Double-click:

\`\`\`text
START_WINDOWS.bat
\`\`\`

## Machine map

- Home PC: Brainiac 7, local AI, Open WebUI, n8n, Qdrant.
- Work Mac: coding brain, TMMT development, tests, deploy tooling.
- Personal Mac: mobile control and flash-drive refresh.

## Safety

- Do not expose Ollama, Open WebUI, n8n, Qdrant, SSH, or local dev servers to the public internet.
- Use Tailscale or LAN only.
- Do not put real API keys, service-role keys, private keys, or production env files on FIELD.
- Customer-facing and money-facing actions require human approval.
EOF_START

  write_file "$kit/ROLE-$role.md" <<EOF_ROLE
# Role: $role

Generated: $DATE_UTC

MASTER is the owner-only gold source.
WORK is the daily developer transport.
FIELD is the simplified team/recovery kit with no real secrets.
EOF_ROLE

  write_file "$kit/scripts/mac/bootstrap-mac.sh" <<'EOF_BOOT_MAC'
#!/usr/bin/env bash
set -euo pipefail

echo "Mac bootstrap check"
echo

check() {
  local name="$1"
  local cmd="$2"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[OK] $name"
  else
    echo "[MISSING] $name"
  fi
}

check "git" git
check "node" node
check "npm" npm
check "ollama" ollama
check "tailscale" tailscale

echo
echo "Recommended work paths:"
echo "- Code on Mac: ~/dev/TMMT or ~/Documents/TMMT"
echo "- Brainiac 7 WebUI: http://brainiac-7:3000"
echo "- Brainiac 7 Ollama: http://brainiac-7:11434"
echo
echo "If this is a new Mac, install missing tools first. Keep secrets in your password manager, not on the flash drive."
EOF_BOOT_MAC

  write_file "$kit/scripts/windows/bootstrap-windows.ps1" <<'EOF_BOOT_WIN'
$ErrorActionPreference = "Stop"

Write-Host "Windows bootstrap check"
Write-Host ""

function Test-Command($Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) {
    Write-Host "[OK] $Name"
  } else {
    Write-Host "[MISSING] $Name"
  }
}

Test-Command git
Test-Command node
Test-Command npm
Test-Command ollama
Test-Command tailscale

Write-Host ""
Write-Host "Recommended work paths:"
Write-Host "- Code on Windows: C:\dev\TMMT"
Write-Host "- Brainiac 7 WebUI: http://brainiac-7:3000"
Write-Host "- Brainiac 7 Ollama: http://brainiac-7:11434"
Write-Host ""
Write-Host "If this is a new Windows computer, install missing tools first. Keep secrets in your password manager, not on the flash drive."
EOF_BOOT_WIN

  if [[ "$MODE" != "--dry-run" ]]; then
    chmod +x "$kit/scripts/mac/bootstrap-mac.sh"
  fi
}

sync_dir() {
  local src="$1"
  local dst="$2"
  [[ -d "$src" ]] || {
    log "skip missing source: $src"
    return 0
  }
  run mkdir -p "$dst"
  run rsync -a --delete --delete-excluded "${COMMON_EXCLUDES[@]}" "$src/" "$dst/"
}

copy_file_if_exists() {
  local src="$1"
  local dst="$2"
  [[ -f "$src" ]] || return 0
  run mkdir -p "$(dirname "$dst")"
  run rsync -a "${COMMON_EXCLUDES[@]}" "$src" "$dst"
}

sync_common_sources() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"

  sync_dir "$HOME_ROOT/AI-OPS-STARTER" "$kit/AI-OPS-STARTER"
  sync_dir "$HOME_ROOT/AIXMOS-AGENTS" "$kit/AIXMOS-AGENTS"
  sync_dir "$HOME_ROOT/portable-setup" "$kit/portable-setup"

  if [[ "$role" == "FIELD" ]]; then
    sync_dir "$HOME_ROOT/AIX-Command-Center/guides" "$kit/AIX-Command-Center/guides"
    sync_dir "$HOME_ROOT/AIX-Command-Center/docs" "$kit/AIX-Command-Center/docs"
    sync_dir "$HOME_ROOT/AIX-Command-Center/agents" "$kit/AIX-Command-Center/agents"
    copy_file_if_exists "$HOME_ROOT/AIX-Command-Center/README.md" "$kit/AIX-Command-Center/README.md"
  else
    sync_dir "$HOME_ROOT/AIX-Command-Center" "$kit/AIX-Command-Center"
    sync_dir "$HOME_ROOT/TMMT" "$kit/work/TMMT"
  fi

  if [[ -d "$HOME_ROOT/Desktop" ]]; then
    run mkdir -p "$kit/docs/team"
    find "$HOME_ROOT/Desktop" -maxdepth 1 -type f \( -name 'TEAM_*' -o -name '*GUIDE*' -o -name '*AIXMOS*' \) -print0 2>/dev/null |
      while IFS= read -r -d '' file; do
        run rsync -a "${COMMON_EXCLUDES[@]}" "$file" "$kit/docs/team/"
      done
  fi
}

write_manifest() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"
  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] write $kit/MANIFEST.txt"
    return 0
  fi
  {
    echo "AIXMOS Portable Kit Manifest"
    echo "Drive: $drive"
    echo "Role: $role"
    echo "Generated: $DATE_UTC"
    echo
    find "$kit" -maxdepth 3 -mindepth 1 | sed "s#^$kit/##" | sort
  } > "$kit/MANIFEST.txt"
}

write_checksums() {
  local drive="$1"
  local kit
  kit="$(kit_path "$drive")"
  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] write $kit/checksums/SHA256SUMS.txt"
    return 0
  fi
  (
    cd "$kit"
    find . -type f \
      ! -path './checksums/SHA256SUMS.txt' \
      ! -path './reports/verification.txt' \
      ! -name '.DS_Store' \
      -print0 | sort -z | xargs -0 shasum -a 256
  ) > "$kit/checksums/SHA256SUMS.txt"
}

verify_kit() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"
  local report="$kit/reports/verification.txt"
  local bad

  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] verify $kit"
    return 0
  fi

  bad="$(find "$kit" \( \
    -name '.env' -o \
    -name '.env.*' -o \
    -iname '*secret*' -o \
    -iname '*token*' -o \
    -name '*.key' -o \
    -name '*.pem' -o \
    -name 'id_rsa' -o \
    -name 'id_ed25519' -o \
    -name 'node_modules' -o \
    -name '.next' -o \
    -name '.venv' -o \
    -name '__pycache__' -o \
    -name '.pytest_cache' -o \
    -name 'test-results' -o \
    -name '._*' \
  \) -print 2>/dev/null || true)"

  {
    echo "Verification report"
    echo "Drive: $drive"
    echo "Role: $role"
    echo "Generated: $DATE_UTC"
    echo
    if [[ -n "$bad" ]]; then
      echo "FAIL"
      echo "$bad"
    else
      echo "PASS"
    fi
  } > "$report"

  [[ -z "$bad" ]] || {
    echo "Verification failed for $drive. See $report" >&2
    return 1
  }
}

build_drive() {
  local drive="$1"
  local role="$2"
  ensure_drive "$drive"
  mkdirs_for_drive "$drive"
  write_root_entrypoints "$drive" "$role"
  write_kit_docs "$drive" "$role"
  if [[ "$MODE" != "--verify-only" ]]; then
    sync_common_sources "$drive" "$role"
    write_manifest "$drive" "$role"
    write_checksums "$drive"
  fi
  verify_kit "$drive" "$role"
  log "done: $drive ($role)"
}

for i in "${!DRIVE_NAMES[@]}"; do
  build_drive "${DRIVE_NAMES[$i]}" "${DRIVE_ROLES[$i]}"
done
